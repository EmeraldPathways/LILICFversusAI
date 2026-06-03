from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.config import Settings


@dataclass
class CollaborativeFilteringService:
    settings: Settings

    def generate_all(
        self,
        train_df: pd.DataFrame,
        catalog_df: pd.DataFrame,
        user_ids: list[str],
        candidate_pool_map: dict[str, list[str]] | None = None,
    ) -> dict[str, list[dict[str, object]]]:
        matrix = self._build_user_item_matrix(train_df)
        metadata = self._article_metadata(catalog_df)
        user_history = train_df.groupby("customer_id")["article_id"].agg(set).to_dict()

        recommendations: dict[str, list[dict[str, object]]] = {}
        for user_id in user_ids:
            recommendations[user_id] = self.recommend_for_user(
                user_id,
                matrix,
                metadata,
                user_history,
                candidate_pool_article_ids=candidate_pool_map.get(user_id) if candidate_pool_map else None,
            )

        self.settings.cf_output_path.write_text(json.dumps(recommendations, indent=2), encoding="utf-8")
        return recommendations

    def recommend_for_user(
        self,
        user_id: str,
        matrix: pd.DataFrame,
        metadata: dict[str, dict[str, str]],
        user_history: dict[str, set[str]],
        candidate_pool_article_ids: list[str] | None = None,
    ) -> list[dict[str, object]]:
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
        allowed_candidates = set(candidate_pool_article_ids) if candidate_pool_article_ids is not None else None
        candidate_ids = [
            article_id
            for article_id in metadata
            if article_id not in purchased and (allowed_candidates is None or article_id in allowed_candidates)
        ]
        for neighbor_id, similarity in similarities.items():
            for article_id in user_history.get(neighbor_id, set()):
                if article_id in purchased:
                    continue
                scores[article_id] += similarity

        ranked = sorted(
            ((article_id, float(scores.get(article_id, 0.0))) for article_id in candidate_ids),
            key=lambda item: (-item[1], item[0]),
        )[: self.settings.top_n]
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
            str(row["article_id"]): {
                "product_name": str(row["product_name"]),
                "product_type": str(row["product_type"]),
                "product_group": str(row["product_group"]),
                "colour": str(row["colour"]),
                "appearance": str(row["appearance"]),
            }
            for _, row in deduped.iterrows()
        }
