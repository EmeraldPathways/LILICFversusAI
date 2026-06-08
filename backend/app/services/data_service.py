from __future__ import annotations

import csv
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from app.config import Settings
from app.utils.normalization import normalize_article_id, normalize_customer_id


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

FORMAL_TRANSACTION_COLUMNS = [
    "t_dat",
    "customer_id",
    "article_id",
    "price",
    "sales_channel_id",
]

FORMAL_ARTICLE_COLUMNS = [
    "article_id",
    "product_type_name",
    "product_group_name",
    "graphical_appearance_name",
    "colour_group_name",
    "garment_group_name",
    "department_name",
    "section_name",
    "index_name",
    "detail_desc",
]

FORMAL_JOINED_COLUMNS = [
    "customer_id",
    "article_id",
    "t_dat",
    "price",
    "sales_channel_id",
    "product_type_name",
    "product_group_name",
    "graphical_appearance_name",
    "colour_group_name",
    "garment_group_name",
    "department_name",
    "section_name",
    "index_name",
    "detail_desc",
]

CORE_METADATA_FIELDS = [
    "product_type_name",
    "product_group_name",
    "graphical_appearance_name",
    "colour_group_name",
    "garment_group_name",
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

    def build_processed_interactions_with_articles(self) -> dict[str, object]:
        self.validate_raw_files()
        transactions = self._load_formal_transactions()
        articles = self._load_formal_articles()
        _customers = pd.read_csv(self.settings.customers_path, dtype={"customer_id": "string"})

        joined = transactions.merge(articles, on="article_id", how="inner")
        joined = joined[FORMAL_JOINED_COLUMNS].copy()
        joined["t_dat"] = pd.to_datetime(joined["t_dat"]).dt.strftime("%Y-%m-%d")

        joined.to_csv(self.settings.processed_interactions_with_articles_csv_path, index=False)
        joined_json_ready = joined.where(pd.notna(joined), None)
        self.settings.processed_interactions_with_articles_json_path.write_text(
            json.dumps(joined_json_ready.to_dict(orient="records"), indent=2),
            encoding="utf-8",
        )

        report = self._build_processed_data_validation_report(transactions, articles, joined)
        self.settings.processed_data_validation_report_path.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )
        return report

    def build_leave_one_out_evaluation_base(self) -> dict[str, object]:
        processed = self._load_processed_interactions_with_articles()
        catalogue = self._build_processed_catalogue(processed)

        invalid_reason_counts: dict[str, int] = {}
        fieldnames = [
            "customer_id",
            "total_transaction_count",
            "train_count",
            "train_article_ids",
            "train_transaction_dates",
            "ground_truth_article_id",
            "ground_truth_transaction_date",
            "ground_truth_product_type_name",
            "ground_truth_product_group_name",
            "ground_truth_colour_group_name",
            "ground_truth_graphical_appearance_name",
            "ground_truth_garment_group_name",
            "ground_truth_department_name",
            "ground_truth_section_name",
            "ground_truth_index_name",
            "ground_truth_detail_desc",
            "ground_truth_detail_desc_missing",
            "train_items_in_catalog",
            "ground_truth_in_catalog",
            "article_id_format_check",
            "customer_id_format_check",
            "core_metadata_complete",
            "is_valid_for_svd_evaluation_base",
            "is_valid_for_agentic_evaluation_base",
            "is_valid_for_final_comparison_base",
            "invalid_reason",
        ]
        total_customers_before_filtering = 0
        customers_with_at_least_10_transactions = 0
        valid_final_comparison_base_users = 0
        invalid_user_count = 0
        article_id_format_passed_count = 0
        article_id_format_failed_count = 0
        customer_id_format_passed_count = 0
        customer_id_format_failed_count = 0
        ground_truth_in_catalog_count = 0
        train_items_in_catalog_count = 0
        ground_truth_detail_desc_missing_count = 0
        valid_train_counts: list[int] = []
        example_valid_users: list[str] = []
        example_invalid_users: list[str] = []

        with (
            self.settings.evaluation_base_table_svd_top10_all_valid_csv_path.open(
                "w", encoding="utf-8", newline=""
            ) as csv_file,
            self.settings.evaluation_base_table_svd_top10_all_valid_json_path.open(
                "w", encoding="utf-8"
            ) as json_file,
        ):
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            json_file.write("[\n")
            is_first_row = True

            for customer_id, group in processed.groupby("customer_id", sort=False):
                ordered = (
                    group.sort_values(["t_dat", "article_id"], ascending=[True, True])
                    .reset_index(drop=True)
                )
                total_transaction_count = int(len(ordered))
                train_rows = ordered.iloc[:-1].copy()
                ground_truth_row = ordered.iloc[-1]
                train_article_ids = [normalize_article_id(value) for value in train_rows["article_id"].tolist()]
                train_transaction_dates = pd.to_datetime(train_rows["t_dat"]).dt.strftime("%Y-%m-%d").tolist()
                ground_truth_article_id = normalize_article_id(ground_truth_row["article_id"])
                ground_truth_transaction_date = str(pd.to_datetime(ground_truth_row["t_dat"]).strftime("%Y-%m-%d"))

                train_count = len(train_article_ids)
                ground_truth_in_catalog = ground_truth_article_id in catalogue
                train_items_in_catalog = all(article_id in catalogue for article_id in train_article_ids)
                article_id_format_passed = (
                    isinstance(ground_truth_article_id, str)
                    and all(isinstance(article_id, str) and article_id != "" for article_id in train_article_ids)
                )
                customer_id_format_passed = isinstance(customer_id, str) and customer_id != ""
                ground_truth_core_complete = self._core_metadata_complete(ground_truth_row)
                train_core_complete = bool(train_count) and all(
                    self._core_metadata_complete(train_row) for _, train_row in train_rows.iterrows()
                )
                core_metadata_complete = ground_truth_core_complete and train_core_complete
                invalid_reasons = self._collect_evaluation_base_invalid_reasons(
                    total_transaction_count=total_transaction_count,
                    train_count=train_count,
                    ground_truth_article_id=ground_truth_article_id,
                    ground_truth_in_catalog=ground_truth_in_catalog,
                    train_items_in_catalog=train_items_in_catalog,
                    article_id_format_passed=article_id_format_passed,
                    customer_id_format_passed=customer_id_format_passed,
                    core_metadata_complete=core_metadata_complete,
                )
                invalid_reason = "; ".join(invalid_reasons)
                is_valid_for_svd_evaluation_base = not invalid_reasons
                is_valid_for_agentic_evaluation_base = not invalid_reasons
                is_valid_for_final_comparison_base = (
                    is_valid_for_svd_evaluation_base and is_valid_for_agentic_evaluation_base
                )
                row = {
                    "customer_id": customer_id,
                    "total_transaction_count": total_transaction_count,
                    "train_count": train_count,
                    "train_article_ids": train_article_ids,
                    "train_transaction_dates": train_transaction_dates,
                    "ground_truth_article_id": ground_truth_article_id,
                    "ground_truth_transaction_date": ground_truth_transaction_date,
                    "ground_truth_product_type_name": self._nullable_string(ground_truth_row["product_type_name"]),
                    "ground_truth_product_group_name": self._nullable_string(ground_truth_row["product_group_name"]),
                    "ground_truth_colour_group_name": self._nullable_string(ground_truth_row["colour_group_name"]),
                    "ground_truth_graphical_appearance_name": self._nullable_string(
                        ground_truth_row["graphical_appearance_name"]
                    ),
                    "ground_truth_garment_group_name": self._nullable_string(ground_truth_row["garment_group_name"]),
                    "ground_truth_department_name": self._nullable_string(ground_truth_row["department_name"]),
                    "ground_truth_section_name": self._nullable_string(ground_truth_row["section_name"]),
                    "ground_truth_index_name": self._nullable_string(ground_truth_row["index_name"]),
                    "ground_truth_detail_desc": self._nullable_string(ground_truth_row["detail_desc"]),
                    "ground_truth_detail_desc_missing": pd.isna(ground_truth_row["detail_desc"])
                    or str(ground_truth_row["detail_desc"]).strip() == "",
                    "train_items_in_catalog": train_items_in_catalog,
                    "ground_truth_in_catalog": ground_truth_in_catalog,
                    "article_id_format_check": "passed" if article_id_format_passed else "failed",
                    "customer_id_format_check": "passed" if customer_id_format_passed else "failed",
                    "core_metadata_complete": core_metadata_complete,
                    "is_valid_for_svd_evaluation_base": is_valid_for_svd_evaluation_base,
                    "is_valid_for_agentic_evaluation_base": is_valid_for_agentic_evaluation_base,
                    "is_valid_for_final_comparison_base": is_valid_for_final_comparison_base,
                    "invalid_reason": invalid_reason,
                }

                total_customers_before_filtering += 1
                if total_transaction_count >= 10:
                    customers_with_at_least_10_transactions += 1
                if article_id_format_passed:
                    article_id_format_passed_count += 1
                else:
                    article_id_format_failed_count += 1
                if customer_id_format_passed:
                    customer_id_format_passed_count += 1
                else:
                    customer_id_format_failed_count += 1
                if ground_truth_in_catalog:
                    ground_truth_in_catalog_count += 1
                if train_items_in_catalog:
                    train_items_in_catalog_count += 1
                if row["ground_truth_detail_desc_missing"]:
                    ground_truth_detail_desc_missing_count += 1

                if invalid_reasons:
                    invalid_user_count += 1
                    if len(example_invalid_users) < 5:
                        example_invalid_users.append(customer_id)
                    for reason in invalid_reasons:
                        invalid_reason_counts[reason] = invalid_reason_counts.get(reason, 0) + 1
                else:
                    valid_final_comparison_base_users += 1
                    valid_train_counts.append(train_count)
                    if len(example_valid_users) < 5:
                        example_valid_users.append(customer_id)

                writer.writerow(
                    {
                        **row,
                        "train_article_ids": json.dumps(train_article_ids),
                        "train_transaction_dates": json.dumps(train_transaction_dates),
                    }
                )
                if not is_first_row:
                    json_file.write(",\n")
                json.dump(row, json_file, ensure_ascii=False)
                is_first_row = False

            json_file.write("\n]\n")

        report = {
            "total_customers_before_filtering": total_customers_before_filtering,
            "customers_with_at_least_10_transactions": customers_with_at_least_10_transactions,
            "valid_final_comparison_base_users": valid_final_comparison_base_users,
            "invalid_user_count": invalid_user_count,
            "invalid_reason_counts": invalid_reason_counts,
            "article_id_format_check_summary": {
                "passed": article_id_format_passed_count,
                "failed": article_id_format_failed_count,
            },
            "customer_id_format_check_summary": {
                "passed": customer_id_format_passed_count,
                "failed": customer_id_format_failed_count,
            },
            "ground_truth_in_catalog_count": ground_truth_in_catalog_count,
            "train_items_in_catalog_count": train_items_in_catalog_count,
            "ground_truth_detail_desc_missing_count": ground_truth_detail_desc_missing_count,
            "min_train_count": min(valid_train_counts) if valid_train_counts else 0,
            "mean_train_count": round(sum(valid_train_counts) / len(valid_train_counts), 2)
            if valid_train_counts
            else 0.0,
            "max_train_count": max(valid_train_counts) if valid_train_counts else 0,
            "example_valid_users": example_valid_users,
            "example_invalid_users": example_invalid_users,
        }
        self.settings.evaluation_base_validation_report_svd_top10_all_valid_path.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )

        top_invalid_reasons = sorted(
            invalid_reason_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )[:5]
        print(
            "Leave-one-out base summary: "
            f"raw_customers={report['total_customers_before_filtering']}, "
            f"customers_ge_10={report['customers_with_at_least_10_transactions']}, "
            f"valid_users={report['valid_final_comparison_base_users']}, "
            f"invalid_users={report['invalid_user_count']}, "
            f"top_invalid_reasons={top_invalid_reasons}, "
            f"train_count_stats=({report['min_train_count']}/{report['mean_train_count']}/{report['max_train_count']})"
        )
        return report

    def create_experiment_subset(
        self,
        sample_size: int,
        random_seed: int,
        source: str = "all_valid",
    ) -> list[dict[str, object]]:
        """Sample customer-level experiment subsets from the saved all-valid base table.

        This is intentionally limited to customer-level sampling from
        evaluation_base_table_svd_top10_all_valid.json. It does not sample raw
        transaction rows and does not write subset artifacts in this step.
        """
        if source != "all_valid":
            raise DataValidationError(f"Unsupported subset source: {source}")
        payload = json.loads(
            self.settings.evaluation_base_table_svd_top10_all_valid_json_path.read_text(encoding="utf-8")
        )
        valid_rows = [row for row in payload if row.get("is_valid_for_final_comparison_base")]
        if sample_size >= len(valid_rows):
            return valid_rows
        rng = random.Random(random_seed)
        selected_indices = sorted(rng.sample(range(len(valid_rows)), sample_size))
        return [valid_rows[index] for index in selected_indices]

    def preprocess(
        self,
        *,
        interactions_path: Path | None = None,
        summary_path: Path | None = None,
        train_path: Path | None = None,
        test_path: Path | None = None,
        split_method: str = "time_based",
    ) -> dict[str, object]:
        self.validate_raw_files()

        transactions = self._load_formal_transactions()
        articles = self._load_formal_articles()
        _customers = pd.read_csv(self.settings.customers_path, dtype={"customer_id": "string"})

        merged = transactions.merge(articles, on="article_id", how="inner")
        if "prod_name" not in merged.columns:
            merged["prod_name"] = merged["detail_desc"].fillna("")
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
        cleaned["article_id"] = cleaned["article_id"].map(normalize_article_id)
        cleaned["customer_id"] = cleaned["customer_id"].map(normalize_customer_id)

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
        target_interactions_path = interactions_path or self.settings.interactions_path
        sampled.to_csv(target_interactions_path, index=False)

        if split_method == "leave_one_out":
            train_df, test_df, boundary_date = self.create_leave_one_out_split(
                sampled,
                train_path=train_path,
                test_path=test_path,
            )
        else:
            train_df, test_df, boundary_date = self.create_time_based_split(
                sampled,
                train_path=train_path,
                test_path=test_path,
            )
        user_counts = sampled["customer_id"].value_counts()
        product_counts = sampled["article_id"].value_counts()
        summary = {
            "dataset": self.settings.dataset_name,
            "sample_size": int(len(sampled)),
            "distinct_users": int(sampled["customer_id"].nunique()),
            "distinct_products": int(sampled["article_id"].nunique()),
            "repeat_user_ratio": round(float((user_counts >= 2).mean()), 4) if not user_counts.empty else 0.0,
            "average_interactions_per_user": round(float(user_counts.mean()), 2) if not user_counts.empty else 0.0,
            "average_interactions_per_product": round(float(product_counts.mean()), 2) if not product_counts.empty else 0.0,
            "top_product_groups": self._top_counts(sampled, "product_group"),
            "top_product_types": self._top_counts(sampled, "product_type"),
            "top_colours": self._top_counts(sampled, "colour"),
            "top_appearances": self._top_counts(sampled, "appearance"),
            "train_size": int(len(train_df)),
            "test_size": int(len(test_df)),
            "split_boundary_date": boundary_date,
            "sample_user_ids": [str(user_id) for user_id in sampled["customer_id"].drop_duplicates().head(20)],
            "evaluated_user_ids": [],
            "evaluated_users": 0,
        }

        target_summary_path = summary_path or self.settings.summary_path
        target_summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary

    def create_time_based_split(
        self,
        interactions: pd.DataFrame | None = None,
        *,
        train_path: Path | None = None,
        test_path: Path | None = None,
    ) -> tuple[pd.DataFrame, pd.DataFrame, str]:
        if interactions is None:
            interactions = pd.read_csv(
                self.settings.interactions_path,
                dtype={"article_id": "string", "customer_id": "string"},
            )
        interactions = self._normalize_interaction_ids(interactions)
        ordered = interactions.sort_values("transaction_date").reset_index(drop=True)
        split_index = max(1, int(len(ordered) * 0.8))
        train_df = ordered.iloc[:split_index].copy()
        test_df = ordered.iloc[split_index:].copy()
        boundary_date = str(train_df["transaction_date"].iloc[-1])

        target_train_path = train_path or self.settings.train_path
        target_test_path = test_path or self.settings.test_path
        train_df.to_csv(target_train_path, index=False)
        test_df.to_csv(target_test_path, index=False)
        return train_df, test_df, boundary_date

    def create_leave_one_out_split(
        self,
        interactions: pd.DataFrame | None = None,
        *,
        train_path: Path | None = None,
        test_path: Path | None = None,
    ) -> tuple[pd.DataFrame, pd.DataFrame, str]:
        if interactions is None:
            interactions = pd.read_csv(
                self.settings.interactions_path,
                dtype={"article_id": "string", "customer_id": "string"},
            )
        interactions = self._normalize_interaction_ids(interactions)

        ordered = interactions.sort_values(["customer_id", "transaction_date"]).reset_index(drop=True)
        test_indices = ordered.groupby("customer_id").tail(1).index
        test_df = ordered.loc[test_indices].copy().sort_values("transaction_date").reset_index(drop=True)
        train_df = ordered.drop(index=test_indices).copy().sort_values("transaction_date").reset_index(drop=True)
        split_descriptor = "leave_one_out_per_user"

        target_train_path = train_path or self.settings.train_path
        target_test_path = test_path or self.settings.test_path
        train_df.to_csv(target_train_path, index=False)
        test_df.to_csv(target_test_path, index=False)
        return train_df, test_df, split_descriptor

    def load_train(self) -> pd.DataFrame:
        return self._normalize_interaction_ids(
            pd.read_csv(self.settings.train_path, dtype={"article_id": "string", "customer_id": "string"})
        )

    def load_test(self) -> pd.DataFrame:
        return self._normalize_interaction_ids(
            pd.read_csv(self.settings.test_path, dtype={"article_id": "string", "customer_id": "string"})
        )

    def load_summary(self, summary_path: Path | None = None) -> dict[str, object] | None:
        target_summary_path = summary_path or self.settings.summary_path
        if not target_summary_path.exists():
            return None
        return json.loads(target_summary_path.read_text(encoding="utf-8"))

    def load_interactions(self) -> pd.DataFrame:
        return self._normalize_interaction_ids(
            pd.read_csv(
                self.settings.interactions_path,
                dtype={"article_id": "string", "customer_id": "string"},
            )
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

    def _load_formal_transactions(self) -> pd.DataFrame:
        transactions = pd.read_csv(
            self.settings.transactions_path,
            usecols=FORMAL_TRANSACTION_COLUMNS,
            dtype={"article_id": "string", "customer_id": "string"},
            parse_dates=["t_dat"],
        )
        transactions["article_id"] = transactions["article_id"].map(normalize_article_id)
        transactions["customer_id"] = transactions["customer_id"].map(normalize_customer_id)
        transactions["t_dat"] = pd.to_datetime(transactions["t_dat"])
        return transactions

    def _load_formal_articles(self) -> pd.DataFrame:
        header = pd.read_csv(self.settings.articles_path, nrows=0)
        available_columns = set(header.columns)
        usecols = FORMAL_ARTICLE_COLUMNS + (["prod_name"] if "prod_name" in available_columns else [])
        articles = pd.read_csv(
            self.settings.articles_path,
            usecols=usecols,
            dtype={"article_id": "string"},
        )
        articles["article_id"] = articles["article_id"].map(normalize_article_id)
        return articles

    def _load_processed_interactions_with_articles(self) -> pd.DataFrame:
        processed = pd.read_csv(
            self.settings.processed_interactions_with_articles_csv_path,
            dtype={"article_id": "string", "customer_id": "string"},
            parse_dates=["t_dat"],
        )
        processed["article_id"] = processed["article_id"].map(normalize_article_id)
        processed["customer_id"] = processed["customer_id"].map(normalize_customer_id)
        return processed

    @staticmethod
    def _normalize_interaction_ids(frame: pd.DataFrame) -> pd.DataFrame:
        normalized = frame.copy()
        if "article_id" in normalized.columns:
            normalized["article_id"] = normalized["article_id"].map(normalize_article_id)
        if "customer_id" in normalized.columns:
            normalized["customer_id"] = normalized["customer_id"].map(normalize_customer_id)
        return normalized

    @staticmethod
    def _build_processed_data_validation_report(
        transactions: pd.DataFrame,
        articles: pd.DataFrame,
        joined: pd.DataFrame,
    ) -> dict[str, object]:
        important_fields = [
            "product_type_name",
            "product_group_name",
            "graphical_appearance_name",
            "colour_group_name",
            "garment_group_name",
            "department_name",
            "section_name",
            "index_name",
            "detail_desc",
        ]
        missing_metadata_counts = {
            field: int(joined[field].isna().sum()) for field in important_fields
        }
        return {
            "raw_transaction_row_count": int(len(transactions)),
            "raw_article_row_count": int(len(articles)),
            "joined_row_count": int(len(joined)),
            "dropped_transaction_rows_due_to_missing_article_match": int(len(transactions) - len(joined)),
            "unique_customers": int(joined["customer_id"].nunique()),
            "unique_articles": int(joined["article_id"].nunique()),
            "article_id_type_check": "string"
            if joined["article_id"].map(lambda value: isinstance(value, str)).all()
            else "non_string_values_found",
            "customer_id_type_check": "string"
            if joined["customer_id"].map(lambda value: isinstance(value, str)).all()
            else "non_string_values_found",
            "missing_metadata_counts": missing_metadata_counts,
        }

    @staticmethod
    def _build_processed_catalogue(processed: pd.DataFrame) -> dict[str, dict[str, object]]:
        deduped = processed.drop_duplicates("article_id")
        return {
            normalize_article_id(row["article_id"]): {
                field: row[field] for field in FORMAL_JOINED_COLUMNS if field != "customer_id"
            }
            for _, row in deduped.iterrows()
        }

    @staticmethod
    def _core_metadata_complete(row: pd.Series) -> bool:
        return all(not pd.isna(row[field]) and str(row[field]).strip() != "" for field in CORE_METADATA_FIELDS)

    @staticmethod
    def _nullable_string(value) -> str | None:
        if pd.isna(value):
            return None
        text = str(value)
        return text if text.strip() != "" else None

    @staticmethod
    def _collect_evaluation_base_invalid_reasons(
        *,
        total_transaction_count: int,
        train_count: int,
        ground_truth_article_id: str,
        ground_truth_in_catalog: bool,
        train_items_in_catalog: bool,
        article_id_format_passed: bool,
        customer_id_format_passed: bool,
        core_metadata_complete: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if total_transaction_count < 10:
            reasons.append("total_transaction_count_below_10")
        if train_count < 9:
            reasons.append("train_count_below_9")
        if ground_truth_article_id == "":
            reasons.append("ground_truth_article_id_empty")
        if not ground_truth_in_catalog:
            reasons.append("ground_truth_not_in_catalog")
        if not train_items_in_catalog:
            reasons.append("train_items_not_in_catalog")
        if not article_id_format_passed:
            reasons.append("article_id_format_failed")
        if not customer_id_format_passed:
            reasons.append("customer_id_format_failed")
        if not core_metadata_complete:
            reasons.append("core_metadata_incomplete")
        return reasons
