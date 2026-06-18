from __future__ import annotations

import json
from dataclasses import dataclass

import pandas as pd

from app.config import Settings
from app.utils.normalization import normalize_article_id, normalize_customer_id


@dataclass
class ArtifactDemoService:
    settings: Settings

    def load_workflow_cases(
        self,
        *,
        artifact_prefix: str = "seed99_robustness",
        explainability_prefix: str = "seed99_full_retry",
        sample_size: int = 1000,
        max_cases: int = 5,
    ) -> dict[str, object]:
        paths = {
            "evaluation": self.settings.evaluation_base_table_svd_top10_json_path(
                sample_size, artifact_prefix=artifact_prefix
            ),
            "svd": self.settings.svd_recommendations_top10_json_path(
                sample_size, artifact_prefix=artifact_prefix
            ),
            "agentic": self.settings.agentic_recommendations_top10_json_path(
                sample_size, artifact_prefix=artifact_prefix
            ),
            "hybrid": self.settings.hybrid_svd_agentic_recommendations_top10_json_path(
                sample_size, artifact_prefix=artifact_prefix
            ),
            "per_user": self.settings.per_user_metrics_top10_three_methods_json_path(
                sample_size, artifact_prefix=artifact_prefix
            ),
            "examples": self.settings.explainability_examples_csv_path(explainability_prefix),
            "audit": self.settings.explainability_audit_path(explainability_prefix),
        }
        missing = [str(path) for path in paths.values() if not path.exists()]
        if missing:
            raise FileNotFoundError("Missing required walkthrough artifacts: " + "; ".join(missing))

        evaluation_rows = json.loads(paths["evaluation"].read_text(encoding="utf-8"))
        svd_rows = json.loads(paths["svd"].read_text(encoding="utf-8"))
        agentic_rows = json.loads(paths["agentic"].read_text(encoding="utf-8"))
        hybrid_rows = json.loads(paths["hybrid"].read_text(encoding="utf-8"))
        per_user_rows = json.loads(paths["per_user"].read_text(encoding="utf-8"))
        explainability_examples = pd.read_csv(
            paths["examples"],
            dtype={"customer_id": "string", "article_id": "string"},
            keep_default_na=False,
        ).fillna("")
        _audit = json.loads(paths["audit"].read_text(encoding="utf-8"))

        evaluation_lookup = {normalize_customer_id(row.get("customer_id")): row for row in evaluation_rows}
        svd_lookup = {normalize_customer_id(row.get("customer_id")): row for row in svd_rows}
        agentic_lookup = {normalize_customer_id(row.get("customer_id")): row for row in agentic_rows}
        hybrid_lookup = {normalize_customer_id(row.get("customer_id")): row for row in hybrid_rows}
        per_user_lookup = {normalize_customer_id(row.get("customer_id")): row for row in per_user_rows}
        explainability_lookup = self._group_examples_by_customer(explainability_examples)

        complete_users = sorted(
            set(evaluation_lookup)
            & set(svd_lookup)
            & set(agentic_lookup)
            & set(hybrid_lookup)
            & set(per_user_lookup)
        )
        cases = [
            self._build_case(
                customer_id=customer_id,
                evaluation_row=evaluation_lookup[customer_id],
                svd_row=svd_lookup[customer_id],
                agentic_row=agentic_lookup[customer_id],
                hybrid_row=hybrid_lookup[customer_id],
                per_user_row=per_user_lookup[customer_id],
                explainability_rows=explainability_lookup.get(customer_id, []),
            )
            for customer_id in complete_users
        ]

        selected = self._select_cases(cases, limit=max_cases)
        return {
            "artifact_prefix": artifact_prefix,
            "explainability_prefix": explainability_prefix,
            "cases": selected,
        }

    @staticmethod
    def _group_examples_by_customer(examples: pd.DataFrame) -> dict[str, list[dict[str, object]]]:
        lookup: dict[str, list[dict[str, object]]] = {}
        for row in examples.to_dict(orient="records"):
            customer_id = normalize_customer_id(row.get("customer_id"))
            lookup.setdefault(customer_id, []).append(row)
        return lookup

    def _build_case(
        self,
        *,
        customer_id: str,
        evaluation_row: dict[str, object],
        svd_row: dict[str, object],
        agentic_row: dict[str, object],
        hybrid_row: dict[str, object],
        per_user_row: dict[str, object],
        explainability_rows: list[dict[str, object]],
    ) -> dict[str, object]:
        preference_profile = agentic_row.get("preference_profile") or {}
        explanation = self._select_explanation_row(
            explainability_rows=explainability_rows,
            ground_truth_article_id=evaluation_row.get("ground_truth_article_id"),
        )
        svd_items = self._map_method_items(
            svd_row.get("top_10_recommendations", []),
            ground_truth_article_id=evaluation_row.get("ground_truth_article_id"),
            score_field="score",
        )
        agentic_items = self._map_method_items(
            agentic_row.get("top_10_recommendations", []),
            ground_truth_article_id=evaluation_row.get("ground_truth_article_id"),
            score_field="score",
            include_reason=True,
        )
        hybrid_items = self._map_method_items(
            hybrid_row.get("top_10_recommendations", []),
            ground_truth_article_id=evaluation_row.get("ground_truth_article_id"),
            score_field="hybrid_score",
            include_reason=True,
        )
        decision_item = hybrid_row.get("top_10_recommendations", [{}])[0] if hybrid_row.get("top_10_recommendations") else {}
        evidence_item = agentic_row.get("top_10_recommendations", [{}])[0] if agentic_row.get("top_10_recommendations") else {}

        rank_shift = self._coerce_int(explanation.get("rank_shift")) if explanation else None
        if rank_shift is None:
            hybrid_rank = self._coerce_int(per_user_row.get("hybrid_ground_truth_rank"))
            svd_rank = self._coerce_int(per_user_row.get("svd_ground_truth_rank"))
            if hybrid_rank is not None and svd_rank is not None:
                rank_shift = svd_rank - hybrid_rank

        return {
            "label": customer_id,
            "category": "Generic Walkthrough Case",
            "customer_id": customer_id,
            "customer_id_short": self._short_customer_id(customer_id),
            "training_history_summary": {
                "interaction_count": len(evaluation_row.get("train_article_ids", [])),
                "article_ids_preview": list(evaluation_row.get("train_article_ids", []))[:6],
                "inferred_intent": preference_profile.get("inferred_intent"),
                "preferred_categories": preference_profile.get("preferred_categories", []),
                "preferred_product_types": preference_profile.get("preferred_product_types", []),
                "preferred_colours": preference_profile.get("preferred_colours", []),
                "preferred_appearance": preference_profile.get("preferred_appearance", []),
            },
            "ground_truth": {
                "article_id": normalize_article_id(evaluation_row.get("ground_truth_article_id")),
                "product_type_name": evaluation_row.get("ground_truth_product_type_name"),
                "product_group_name": evaluation_row.get("ground_truth_product_group_name"),
                "colour_group_name": evaluation_row.get("ground_truth_colour_group_name"),
                "graphical_appearance_name": evaluation_row.get("ground_truth_graphical_appearance_name"),
                "garment_group_name": evaluation_row.get("ground_truth_garment_group_name"),
            },
            "candidate_pool_size": len(evaluation_row.get("candidate_pool_article_ids", [])),
            "preference_agent": {
                "inferred_intent": preference_profile.get("inferred_intent"),
                "preferred_categories": preference_profile.get("preferred_categories", []),
                "preferred_product_types": preference_profile.get("preferred_product_types", []),
                "preferred_colours": preference_profile.get("preferred_colours", []),
                "preferred_appearance": preference_profile.get("preferred_appearance", []),
            },
            "evidence_agent": {
                "headline": evidence_item.get("recommendation_reason") or "Saved agentic evidence from the formal run.",
                "matched_evidence": evidence_item.get("matched_evidence", []),
                "item_metadata": {
                    "article_id": normalize_article_id(evidence_item.get("article_id")),
                    "product_type_name": evidence_item.get("product_type_name"),
                    "product_group_name": evidence_item.get("product_group_name"),
                    "colour_group_name": evidence_item.get("colour_group_name"),
                    "graphical_appearance_name": evidence_item.get("graphical_appearance_name"),
                    "garment_group_name": evidence_item.get("garment_group_name"),
                },
            },
            "decision_agent": {
                "headline": decision_item.get("recommendation_reason") or "Saved hybrid reranker output from the formal run.",
                "selected_article_id": normalize_article_id(decision_item.get("article_id")),
                "selected_rank": self._coerce_int(decision_item.get("rank")),
                "selected_score": self._coerce_float(decision_item.get("hybrid_score")),
            },
            "svd_top10": svd_items,
            "agentic_top10": agentic_items,
            "hybrid_top10": hybrid_items,
            "hybrid_selected_explanation": explanation,
            "hybrid_score_components": {
                "normalized_svd_score": self._coerce_float(explanation.get("normalized_svd_score")) if explanation else None,
                "normalized_agentic_score": self._coerce_float(explanation.get("normalized_agentic_score")) if explanation else None,
                "diversity_bonus": self._coerce_float(explanation.get("diversity_bonus")) if explanation else None,
                "hybrid_score": self._coerce_float(explanation.get("hybrid_score")) if explanation else None,
            },
            "rank_shift": rank_shift,
            "diversity_comparison": {
                "svd_ild_at_10": self._coerce_float(per_user_row.get("svd_ild_at_10")),
                "agentic_ild_at_10": self._coerce_float(per_user_row.get("agentic_ild_at_10")),
                "hybrid_ild_at_10": self._coerce_float(per_user_row.get("hybrid_ild_at_10")),
            },
        }

    def _select_cases(self, cases: list[dict[str, object]], limit: int) -> list[dict[str, object]]:
        selected: list[dict[str, object]] = []
        used_customer_ids: set[str] = set()

        def pick(label: str, category: str, predicate) -> None:
            for case in cases:
                if case["customer_id"] in used_customer_ids:
                    continue
                if predicate(case):
                    selected.append({**case, "label": label, "category": category})
                    used_customer_ids.add(case["customer_id"])
                    return

        pick(
            "Best Hybrid Case",
            "Best Hybrid Case",
            lambda case: bool(case["hybrid_selected_explanation"].get("is_ground_truth"))
            and case["hybrid_selected_explanation"].get("explanation_text"),
        )
        pick(
            "Rank Promotion Case",
            "Rank Promotion Case",
            lambda case: case.get("rank_shift") is not None and int(case["rank_shift"]) > 0,
        )
        pick(
            "SVD vs Hybrid Comparison",
            "SVD vs Hybrid Comparison",
            lambda case: any(item["is_ground_truth"] for item in case["svd_top10"])
            and any(item["is_ground_truth"] for item in case["hybrid_top10"]),
        )
        pick(
            "Standalone 3-Agent Weak Case",
            "Standalone 3-Agent Weak Case",
            lambda case: not any(item["is_ground_truth"] for item in case["agentic_top10"])
            and any(item["is_ground_truth"] for item in case["hybrid_top10"]),
        )
        pick(
            "Diversity Trade-off Case",
            "Diversity Trade-off Case",
            lambda case: case["diversity_comparison"].get("hybrid_ild_at_10") is not None
            and case["diversity_comparison"].get("svd_ild_at_10") is not None
            and float(case["diversity_comparison"]["hybrid_ild_at_10"])
            < float(case["diversity_comparison"]["svd_ild_at_10"]),
        )

        for index, case in enumerate(cases, start=1):
            if len(selected) >= limit:
                break
            if case["customer_id"] in used_customer_ids:
                continue
            selected.append({**case, "label": f"User {chr(64 + index)}"})
            used_customer_ids.add(case["customer_id"])

        return selected[:limit]

    def _select_explanation_row(
        self,
        *,
        explainability_rows: list[dict[str, object]],
        ground_truth_article_id: object,
    ) -> dict[str, object]:
        normalized_ground_truth = normalize_article_id(ground_truth_article_id)
        sorted_rows = sorted(
            explainability_rows,
            key=lambda row: (
                not self._is_truthy(row.get("is_ground_truth")),
                normalize_article_id(row.get("article_id")) != normalized_ground_truth,
                self._coerce_int(row.get("hybrid_rank")) or 999,
            ),
        )
        row = sorted_rows[0] if sorted_rows else {}
        matched_fields: list[dict[str, object]] = []
        raw_fields = row.get("matched_preference_fields_json")
        if isinstance(raw_fields, str) and raw_fields.strip():
            try:
                parsed = json.loads(raw_fields)
                if isinstance(parsed, list):
                    matched_fields = [item for item in parsed if isinstance(item, dict)]
            except json.JSONDecodeError:
                matched_fields = []
        return {
            "article_id": normalize_article_id(row.get("article_id")),
            "hybrid_rank": self._coerce_int(row.get("hybrid_rank")),
            "svd_rank": self._coerce_int(row.get("svd_rank")),
            "rank_shift": self._coerce_int(row.get("rank_shift")),
            "is_ground_truth": self._is_truthy(row.get("is_ground_truth")),
            "product_type_name": row.get("product_type_name") or None,
            "product_group_name": row.get("product_group_name") or None,
            "colour_group_name": row.get("colour_group_name") or None,
            "graphical_appearance_name": row.get("graphical_appearance_name") or None,
            "garment_group_name": row.get("garment_group_name") or None,
            "explanation_text": row.get("explanation_text") or "",
            "matched_preference_fields": matched_fields,
            "normalized_svd_score": self._coerce_float(row.get("normalized_svd_score")),
            "normalized_agentic_score": self._coerce_float(row.get("normalized_agentic_score")),
            "diversity_bonus": self._coerce_float(row.get("diversity_bonus")),
            "hybrid_score": self._coerce_float(row.get("hybrid_score")),
        }

    def _map_method_items(
        self,
        items: list[dict[str, object]],
        *,
        ground_truth_article_id: object,
        score_field: str,
        include_reason: bool = False,
    ) -> list[dict[str, object]]:
        normalized_ground_truth = normalize_article_id(ground_truth_article_id)
        mapped: list[dict[str, object]] = []
        for item in items[:10]:
            mapped.append(
                {
                    "article_id": normalize_article_id(item.get("article_id")),
                    "rank": self._coerce_int(item.get("rank")),
                    "score": self._coerce_float(item.get(score_field)),
                    "reason": item.get("recommendation_reason") if include_reason else None,
                    "is_ground_truth": normalize_article_id(item.get("article_id")) == normalized_ground_truth,
                    "product_type_name": item.get("product_type_name") or None,
                    "product_group_name": item.get("product_group_name") or None,
                    "colour_group_name": item.get("colour_group_name") or None,
                    "graphical_appearance_name": item.get("graphical_appearance_name") or None,
                    "garment_group_name": item.get("garment_group_name") or None,
                }
            )
        return mapped

    @staticmethod
    def _short_customer_id(customer_id: str) -> str:
        if len(customer_id) <= 12:
            return customer_id
        return f"{customer_id[:6]}...{customer_id[-4:]}"

    @staticmethod
    def _coerce_float(value: object) -> float | None:
        if value in ("", None):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _coerce_int(value: object) -> int | None:
        if value in ("", None, " "):
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _is_truthy(value: object) -> bool:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"true", "1", "yes"}
