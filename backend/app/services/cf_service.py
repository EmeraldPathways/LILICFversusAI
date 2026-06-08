from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.config import Settings
from app.utils.normalization import normalize_article_id, normalize_customer_id


@dataclass
class CollaborativeFilteringService:
    settings: Settings

    # The previous user-based cosine CF baseline is retained only for debugging.
    # The formal baseline follows the supervisor feedback and uses SVD Matrix Factorisation.

    def generate_all(self, train_df: pd.DataFrame, user_ids: list[str]) -> dict[str, list[dict[str, object]]]:
        train_df = self._normalize_ids(train_df)
        user_ids = [normalize_customer_id(user_id) for user_id in user_ids]
        matrix = self._build_user_item_matrix(train_df)
        metadata = self._article_metadata(train_df)
        user_history = train_df.groupby("customer_id")["article_id"].agg(set).to_dict()

        recommendations: dict[str, list[dict[str, object]]] = {}
        for user_id in user_ids:
            recommendations[user_id] = self.recommend_for_user(user_id, matrix, metadata, user_history)

        self.settings.cf_output_path.write_text(json.dumps(recommendations, indent=2), encoding="utf-8")
        return recommendations

    def generate_all_svd(
        self,
        train_df: pd.DataFrame,
        user_ids: list[str],
        candidate_pools: dict[str, list[str]],
        output_path=None,
    ) -> dict[str, list[dict[str, object]]]:
        train_df = self._normalize_ids(train_df)
        user_ids = [normalize_customer_id(user_id) for user_id in user_ids]
        candidate_pools = {
            normalize_customer_id(user_id): [normalize_article_id(article_id) for article_id in article_ids]
            for user_id, article_ids in candidate_pools.items()
        }
        matrix = self._build_user_item_matrix(train_df)
        metadata = self._article_metadata(train_df)
        user_history = train_df.groupby("customer_id")["article_id"].agg(set).to_dict()
        user_factors, item_factors = self._svd_factors(matrix)

        recommendations: dict[str, list[dict[str, object]]] = {}
        for user_id in user_ids:
            recommendations[user_id] = self.recommend_for_user_svd(
                user_id=user_id,
                matrix=matrix,
                metadata=metadata,
                user_history=user_history,
                user_factors=user_factors,
                item_factors=item_factors,
                candidate_article_ids=candidate_pools.get(user_id, []),
            )

        target_path = output_path or self.settings.cf_output_path
        target_path.write_text(json.dumps(recommendations, indent=2), encoding="utf-8")
        return recommendations

    def recommend_for_user(
        self,
        user_id: str,
        matrix: pd.DataFrame,
        metadata: dict[str, dict[str, str]],
        user_history: dict[str, set[str]],
    ) -> list[dict[str, object]]:
        user_id = normalize_customer_id(user_id)
        if user_id not in matrix.index:
            return []

        target = matrix.loc[user_id].to_numpy(dtype=float)
        norms = np.linalg.norm(matrix.to_numpy(dtype=float), axis=1)
        target_norm = np.linalg.norm(target)
        similarities: dict[str, float] = {}
        for idx, other_user in enumerate(matrix.index):
            if other_user == user_id or norms[idx] == 0 or target_norm == 0:
                continue
            sim = float(np.dot(target, matrix.iloc[idx].to_numpy(dtype=float)) / (target_norm * norms[idx]))
            if sim > 0:
                similarities[str(other_user)] = sim

        scores: defaultdict[str, float] = defaultdict(float)
        purchased = user_history.get(user_id, set())
        for neighbor_id, similarity in similarities.items():
            for article_id in user_history.get(neighbor_id, set()):
                if article_id in purchased:
                    continue
                scores[normalize_article_id(article_id)] += similarity

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[: self.settings.top_n]
        result = []
        for article_id, score in ranked:
            details = metadata.get(article_id)
            if not details:
                continue
            result.append(
                {
                    "article_id": article_id,
                    "product_name": details["product_name"],
                    "product_type": details["product_type"],
                    "product_group": details["product_group"],
                    "colour": details["colour"],
                    "appearance": details["appearance"],
                    "score": round(float(score), 4),
                    "model": "collaborative_filtering",
                }
            )
        return result

    def recommend_for_user_svd(
        self,
        user_id: str,
        matrix: pd.DataFrame,
        metadata: dict[str, dict[str, str]],
        user_history: dict[str, set[str]],
        user_factors: pd.DataFrame,
        item_factors: pd.DataFrame,
        candidate_article_ids: list[str],
    ) -> list[dict[str, object]]:
        user_id = normalize_customer_id(user_id)
        if user_id not in user_factors.index:
            return []

        purchased = user_history.get(user_id, set())
        scored_candidates: list[tuple[str, float]] = []
        for article_id in [normalize_article_id(article_id) for article_id in candidate_article_ids]:
            if article_id in purchased or article_id not in item_factors.index:
                continue
            score = float(np.dot(user_factors.loc[user_id], item_factors.loc[article_id]))
            scored_candidates.append((article_id, score))

        ranked = sorted(scored_candidates, key=lambda item: item[1], reverse=True)[: self.settings.top_n]
        results = []
        for article_id, score in ranked:
            details = metadata.get(article_id)
            if not details:
                continue
            results.append(
                {
                    "article_id": article_id,
                    "product_name": details["product_name"],
                    "product_type": details["product_type"],
                    "product_group": details["product_group"],
                    "colour": details["colour"],
                    "appearance": details["appearance"],
                    "score": round(score, 4),
                    "model": "svd_matrix_factorization",
                }
            )
        return results

    @staticmethod
    def _build_user_item_matrix(train_df: pd.DataFrame) -> pd.DataFrame:
        interactions = train_df.assign(interaction=1)
        return interactions.pivot_table(
            index="customer_id",
            columns="article_id",
            values="interaction",
            aggfunc="max",
            fill_value=0,
        )

    @staticmethod
    def _article_metadata(train_df: pd.DataFrame) -> dict[str, dict[str, str]]:
        deduped = train_df.drop_duplicates("article_id")
        return {
            normalize_article_id(row["article_id"]): {
                "product_name": str(row["product_name"]),
                "product_type": str(row["product_type"]),
                "product_group": str(row["product_group"]),
                "colour": str(row["colour"]),
                "appearance": str(row["appearance"]),
            }
            for _, row in deduped.iterrows()
        }

    @staticmethod
    def _normalize_ids(frame: pd.DataFrame) -> pd.DataFrame:
        normalized = frame.copy()
        normalized["article_id"] = normalized["article_id"].map(normalize_article_id)
        normalized["customer_id"] = normalized["customer_id"].map(normalize_customer_id)
        return normalized

    @staticmethod
    def _svd_factors(matrix: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        if matrix.empty:
            return pd.DataFrame(index=matrix.index), pd.DataFrame(index=matrix.columns)

        values = matrix.to_numpy(dtype=float)
        user_means = values.mean(axis=1, keepdims=True)
        centered = values - user_means
        u, singular_values, vt = np.linalg.svd(centered, full_matrices=False)
        rank = max(1, min(20, len(singular_values)))
        sigma = np.diag(np.sqrt(singular_values[:rank]))
        user_latent = pd.DataFrame(
            u[:, :rank] @ sigma,
            index=matrix.index,
        )
        item_latent = pd.DataFrame(
            (sigma @ vt[:rank, :]).T,
            index=matrix.columns,
        )
        return user_latent, item_latent
