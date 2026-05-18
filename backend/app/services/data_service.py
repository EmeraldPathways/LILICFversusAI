from __future__ import annotations

import json
import math
from dataclasses import dataclass

import pandas as pd

from app.config import Settings


REQUIRED_COLUMNS = [
    "customer_id",
    "article_id",
    "product_type",
    "product_group",
    "colour",
    "appearance",
    "product_name",
    "transaction_date",
]


class DataValidationError(Exception):
    pass


@dataclass
class DataService:
    settings: Settings

    def validate_raw_files(self) -> None:
        missing = [
            path.name
            for path in [
                self.settings.transactions_path,
                self.settings.articles_path,
                self.settings.customers_path,
            ]
            if not path.exists()
        ]
        if missing:
            raise DataValidationError(
                f"Missing raw dataset files in backend/app/data/raw: {', '.join(missing)}"
            )

    def preprocess(self) -> dict[str, object]:
        self.validate_raw_files()

        transactions = pd.read_csv(
            self.settings.transactions_path,
            dtype={"article_id": "string", "customer_id": "string"},
            parse_dates=["t_dat"],
        )
        articles = pd.read_csv(
            self.settings.articles_path,
            dtype={"article_id": "string"},
        )
        _customers = pd.read_csv(self.settings.customers_path, dtype={"customer_id": "string"})

        merged = transactions.merge(articles, on="article_id", how="inner")
        renamed = merged[
            [
                "customer_id",
                "article_id",
                "product_type_name",
                "product_group_name",
                "colour_group_name",
                "graphical_appearance_name",
                "prod_name",
                "t_dat",
            ]
        ].rename(
            columns={
                "product_type_name": "product_type",
                "product_group_name": "product_group",
                "colour_group_name": "colour",
                "graphical_appearance_name": "appearance",
                "prod_name": "product_name",
                "t_dat": "transaction_date",
            }
        )

        cleaned = renamed.dropna(subset=REQUIRED_COLUMNS).copy()
        cleaned["transaction_date"] = pd.to_datetime(cleaned["transaction_date"])

        user_counts = cleaned["customer_id"].value_counts()
        product_counts = cleaned["article_id"].value_counts()
        filtered = cleaned[
            cleaned["customer_id"].isin(
                user_counts[user_counts >= self.settings.min_user_interactions].index
            )
            & cleaned["article_id"].isin(
                product_counts[product_counts >= self.settings.min_product_interactions].index
            )
        ].copy()

        filtered = filtered.sort_values("transaction_date")
        sampled = self._sample_dense_user_histories(filtered)

        sampled["transaction_date"] = sampled["transaction_date"].dt.strftime("%Y-%m-%d")
        sampled.to_csv(self.settings.interactions_path, index=False)

        train_df, test_df, boundary_date = self.create_time_based_split(sampled)
        summary = {
            "dataset": self.settings.dataset_name,
            "sample_size": int(len(sampled)),
            "distinct_users": int(sampled["customer_id"].nunique()),
            "distinct_products": int(sampled["article_id"].nunique()),
            "top_product_groups": self._top_counts(sampled, "product_group"),
            "top_colours": self._top_counts(sampled, "colour"),
            "top_appearances": self._top_counts(sampled, "appearance"),
            "train_size": int(len(train_df)),
            "test_size": int(len(test_df)),
            "split_boundary_date": boundary_date,
            "sample_user_ids": [str(user_id) for user_id in sampled["customer_id"].drop_duplicates().head(20)],
        }

        self.settings.summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary

    def create_time_based_split(self, interactions: pd.DataFrame | None = None) -> tuple[pd.DataFrame, pd.DataFrame, str]:
        if interactions is None:
            interactions = pd.read_csv(
                self.settings.interactions_path,
                dtype={"article_id": "string", "customer_id": "string"},
            )
        ordered = interactions.sort_values("transaction_date").reset_index(drop=True)
        split_index = max(1, int(len(ordered) * 0.8))
        train_df = ordered.iloc[:split_index].copy()
        test_df = ordered.iloc[split_index:].copy()
        boundary_date = str(train_df["transaction_date"].iloc[-1])

        train_df.to_csv(self.settings.train_path, index=False)
        test_df.to_csv(self.settings.test_path, index=False)
        return train_df, test_df, boundary_date

    def load_train(self) -> pd.DataFrame:
        return pd.read_csv(self.settings.train_path, dtype={"article_id": "string", "customer_id": "string"})

    def load_test(self) -> pd.DataFrame:
        return pd.read_csv(self.settings.test_path, dtype={"article_id": "string", "customer_id": "string"})

    def load_summary(self) -> dict[str, object] | None:
        if not self.settings.summary_path.exists():
            return None
        return json.loads(self.settings.summary_path.read_text(encoding="utf-8"))

    def load_interactions(self) -> pd.DataFrame:
        return pd.read_csv(
            self.settings.interactions_path,
            dtype={"article_id": "string", "customer_id": "string"},
        )

    def _sample_dense_user_histories(self, interactions: pd.DataFrame) -> pd.DataFrame:
        if len(interactions) <= self.settings.sample_size:
            return interactions.sort_values("transaction_date").reset_index(drop=True)

        user_counts = interactions.groupby("customer_id").size().sort_values(ascending=False)
        target_user_count = min(
            len(user_counts),
            max(
                2,
                min(
                    self.settings.max_eval_users * 5,
                    self.settings.sample_size // max(self.settings.min_user_interactions, 1),
                ),
            ),
        )
        selected_users: list[str] = []
        running_total = 0
        for user_id, count in user_counts.items():
            selected_users.append(str(user_id))
            running_total += int(count)
            if len(selected_users) >= target_user_count and running_total >= self.settings.sample_size:
                break
        selected = interactions[interactions["customer_id"].isin(selected_users)].copy()

        per_user_cap = max(
            self.settings.min_user_interactions,
            math.ceil(self.settings.sample_size / max(len(selected_users), 1)),
        )

        sampled_parts = []
        remainder_parts = []
        for user_id in selected_users:
            user_rows = selected[selected["customer_id"] == user_id].sort_values("transaction_date")
            sampled_parts.append(user_rows.head(per_user_cap))
            remainder_parts.append(user_rows.iloc[per_user_cap:])

        sampled = pd.concat(sampled_parts, ignore_index=True)

        if len(sampled) < self.settings.sample_size:
            remainder = (
                pd.concat(remainder_parts, ignore_index=True)
                .sort_values(["transaction_date", "customer_id", "article_id"])
            )
            needed = self.settings.sample_size - len(sampled)
            sampled = pd.concat([sampled, remainder.head(needed)], ignore_index=True)

        sampled = sampled.sort_values(["transaction_date", "customer_id", "article_id"]).reset_index(drop=True)
        if len(sampled) > self.settings.sample_size:
            sampled = sampled.iloc[: self.settings.sample_size].copy()

        return sampled.reset_index(drop=True)

    @staticmethod
    def _top_counts(frame: pd.DataFrame, column: str, limit: int = 5) -> list[dict[str, object]]:
        counts = frame[column].value_counts().head(limit)
        return [{"label": str(label), "value": int(value)} for label, value in counts.items()]
