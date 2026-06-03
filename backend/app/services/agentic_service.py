from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

import httpx
import pandas as pd

from app.config import Settings
from app.models.schemas import FeedbackType


class AgenticServiceError(Exception):
    pass


@dataclass
class AgenticRecommendationService:
    settings: Settings

    BASE_WEIGHTS = {
        "category_weight": 1.0,
        "colour_weight": 1.0,
        "product_type_weight": 1.0,
        "appearance_weight": 1.0,
        "diversity_penalty": 1.0,
    }

    def infer_user_intent(
        self,
        user_id: str,
        train_df: pd.DataFrame,
        user_request: str = "",
    ) -> dict[str, Any]:
        history = self._user_history(user_id, train_df)
        hard_constraints = self._extract_hard_constraints(user_request)
        weighted_types = self._weighted_preferences(history["product_type"])
        weighted_groups = self._weighted_preferences(history["product_group"])
        weighted_colours = self._weighted_preferences(history["colour"])
        weighted_appearances = self._weighted_preferences(history["appearance"])

        llm_result = self._request_structured_completion(
            system_prompt=(
                "You are the Preference Agent in a fashion recommendation experiment. "
                "Infer only soft preferences from the user's historical purchases. "
                "Never convert historical behavior into hard constraints. "
                "Return JSON only with keys soft_preferences and preference_summary."
            ),
            user_payload={
                "user_id": user_id,
                "explicit_request": user_request,
                "hard_constraints": hard_constraints,
                "history_preview": history[
                    [
                        "article_id",
                        "product_name",
                        "product_type",
                        "product_group",
                        "colour",
                        "appearance",
                        "product_description",
                    ]
                ].head(15).to_dict(orient="records"),
                "weighted_preferences": {
                    "product_type_name": weighted_types,
                    "product_group_name": weighted_groups,
                    "colour_group_name": weighted_colours,
                    "graphical_appearance_name": weighted_appearances,
                },
            },
        )

        return {
            "user_id": user_id,
            "preferred_product_type_name_values": weighted_types,
            "preferred_product_group_name_values": weighted_groups,
            "preferred_colour_group_name_values": weighted_colours,
            "preferred_graphical_appearance_name_values": weighted_appearances,
            "soft_preferences": [str(item) for item in llm_result.get("soft_preferences", [])],
            "hard_constraints": hard_constraints,
            "preference_summary": str(
                llm_result.get(
                    "preference_summary",
                    "Historical behavior was converted into weighted soft preferences only.",
                )
            ),
        }

    def retrieve_candidate_products(
        self,
        user_profile: dict[str, Any],
        train_df: pd.DataFrame,
    ) -> list[dict[str, Any]]:
        history = self._user_history(user_profile["user_id"], train_df)
        seen_articles = set(history["article_id"].astype(str))
        catalogue = self._catalogue(train_df)
        candidates = catalogue[~catalogue["article_id"].astype(str).isin(seen_articles)].copy()

        type_weights = self._to_weight_map(user_profile["preferred_product_type_name_values"])
        group_weights = self._to_weight_map(user_profile["preferred_product_group_name_values"])
        colour_weights = self._to_weight_map(user_profile["preferred_colour_group_name_values"])
        appearance_weights = self._to_weight_map(
            user_profile["preferred_graphical_appearance_name_values"]
        )
        description_terms = self._description_terms(user_profile)

        evidence = []
        for _, row in candidates.iterrows():
            matched_fields = self._matched_fields(
                row, type_weights, group_weights, colour_weights, appearance_weights, description_terms
            )
            if not matched_fields:
                continue
            evidence.append(
                {
                    "article_id": str(row["article_id"]),
                    "product_type_name": str(row["product_type"]),
                    "product_group_name": str(row["product_group"]),
                    "graphical_appearance_name": str(row["appearance"]),
                    "colour_group_name": str(row["colour"]),
                    "product_description": str(row["product_description"]),
                    "image_url": str(row["image_url"]),
                    "matched_preference_fields": matched_fields,
                    "evidence_summary": f"Matched {len(matched_fields)} preference signals: {', '.join(matched_fields)}.",
                    "match_count": len(matched_fields),
                    "missing_evidence": self._missing_evidence(row),
                }
            )

        evidence.sort(key=lambda item: (item["match_count"], item["article_id"]), reverse=True)
        return evidence[: self.settings.candidate_pool_size]

    def score_candidates(
        self,
        user_profile: dict[str, Any],
        candidates: list[dict[str, Any]],
        train_df: pd.DataFrame,
    ) -> list[dict[str, Any]]:
        type_weights = self._to_weight_map(user_profile["preferred_product_type_name_values"])
        group_weights = self._to_weight_map(user_profile["preferred_product_group_name_values"])
        colour_weights = self._to_weight_map(user_profile["preferred_colour_group_name_values"])
        appearance_weights = self._to_weight_map(
            user_profile["preferred_graphical_appearance_name_values"]
        )
        description_terms = self._description_terms(user_profile)
        hard_constraints = user_profile["hard_constraints"]

        ranked = []
        for candidate in candidates:
            if self._violates_constraints(candidate, hard_constraints):
                continue
            description_score = self._description_similarity(
                candidate["product_description"], description_terms
            )
            match_score = round(
                (
                    0.30 * type_weights.get(candidate["product_type_name"], 0.0)
                    + 0.25 * group_weights.get(candidate["product_group_name"], 0.0)
                    + 0.20 * colour_weights.get(candidate["colour_group_name"], 0.0)
                    + 0.15 * appearance_weights.get(candidate["graphical_appearance_name"], 0.0)
                    + 0.10 * description_score
                ),
                4,
            )
            ranked.append(
                {
                    **candidate,
                    "match_score": match_score,
                    "matched_evidence": list(candidate["matched_preference_fields"]),
                    "constraint_status": "passed"
                    if hard_constraints
                    else "not_applied",
                }
            )

        ranked.sort(key=lambda item: item["match_score"], reverse=True)
        llm_result = self._request_structured_completion(
            system_prompt=(
                "You are the Decision Agent in a fashion recommendation experiment. "
                "Use the already computed ranking and matched evidence to explain each recommendation. "
                "Return JSON only with key recommendations as a list of objects containing article_id and recommendation_reason."
            ),
            user_payload={
                "user_profile": user_profile,
                "ranked_candidates": ranked[: self.settings.top_n],
            },
        )
        reasons = {
            str(item["article_id"]): str(item["recommendation_reason"])
            for item in llm_result.get("recommendations", [])
            if item.get("article_id") and item.get("recommendation_reason")
        }

        final = []
        for index, item in enumerate(ranked[: self.settings.top_n], start=1):
            final.append(
                {
                    "rank": index,
                    "article_id": item["article_id"],
                    "match_score": item["match_score"],
                    "recommendation_reason": reasons.get(
                        item["article_id"],
                        f"{item['article_id']} ranked well from product, group, colour, appearance, and description overlap.",
                    ),
                    "matched_evidence": item["matched_evidence"],
                    "constraint_status": item["constraint_status"],
                    "product_type_name": item["product_type_name"],
                    "product_group_name": item["product_group_name"],
                    "graphical_appearance_name": item["graphical_appearance_name"],
                    "colour_group_name": item["colour_group_name"],
                    "product_description": item["product_description"],
                    "image_url": item["image_url"],
                }
            )
        return final

    def run_three_agent_pipeline(
        self,
        user_id: str,
        user_request: str,
        train_df: pd.DataFrame,
    ) -> dict[str, Any]:
        preference_profile = self.infer_user_intent(user_id, train_df, user_request)
        candidate_evidence_set = self.retrieve_candidate_products(preference_profile, train_df)
        final_recommendations = self.score_candidates(preference_profile, candidate_evidence_set, train_df)
        return {
            "preference_profile": preference_profile,
            "candidate_evidence_set": candidate_evidence_set[:12],
            "final_recommendations": final_recommendations[:5],
            "process_trace": [
                {
                    "agent": "Preference Agent",
                    "title": "Preference Profile",
                    "summary": "Real purchase history was summarized into weighted soft preferences.",
                    "payload": preference_profile,
                },
                {
                    "agent": "Evidence Agent",
                    "title": "Candidate Evidence",
                    "summary": "Candidate products were matched against the inferred soft preferences.",
                    "payload": {"candidate_count": len(candidate_evidence_set), "candidate_preview": candidate_evidence_set[:5]},
                },
                {
                    "agent": "Decision Agent",
                    "title": "Final Recommendations",
                    "summary": "Candidates were filtered by explicit hard constraints and ranked with the fixed weighted score.",
                    "payload": {"recommendation_preview": final_recommendations[:5]},
                },
            ],
        }

    def generate_all(self, train_df: pd.DataFrame, user_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
        outputs = {}
        traces = {}
        for user_id in user_ids:
            result = self.run_three_agent_pipeline(user_id, "", train_df)
            outputs[user_id] = [
                {
                    "article_id": item["article_id"],
                    "product_name": item["product_description"][:80],
                    "product_type": item["product_type_name"],
                    "product_group": item["product_group_name"],
                    "colour": item["colour_group_name"],
                    "appearance": item["graphical_appearance_name"],
                    "score": item["match_score"],
                    "model": "agentic_ai_framework",
                    "reason": item["recommendation_reason"],
                }
                for item in result["final_recommendations"]
            ]
            traces[user_id] = result["process_trace"]
        self.settings.agentic_output_path.write_text(json.dumps(outputs, indent=2), encoding="utf-8")
        self.settings.agentic_trace_path.write_text(json.dumps(traces, indent=2), encoding="utf-8")
        return outputs

    def generate_for_user(
        self, user_id: str, train_df: pd.DataFrame, user_request: str = ""
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        result = self.run_three_agent_pipeline(user_id, user_request, train_df)
        return result, result["process_trace"]

    def load_traces(self) -> dict[str, list[dict[str, Any]]]:
        return self._read_json_file(self.settings.agentic_trace_path, default={})

    def load_outputs(self) -> dict[str, list[dict[str, Any]]]:
        return self._read_json_file(self.settings.agentic_output_path, default={})

    def adapt_from_feedback(
        self,
        user_id: str,
        article_id: str,
        feedback_type: FeedbackType,
    ) -> dict[str, float]:
        weights = self._load_feedback_weights(user_id)
        if feedback_type == "click":
            weights["category_weight"] += 0.05
            weights["colour_weight"] += 0.05
        elif feedback_type == "add_to_cart":
            weights["product_type_weight"] += 0.12
            weights["appearance_weight"] += 0.12
        elif feedback_type == "ignore":
            weights["diversity_penalty"] += 0.08
        elif feedback_type == "purchase":
            weights["product_type_weight"] += 0.2
            weights["category_weight"] += 0.15
        else:
            raise AgenticServiceError(f"Unsupported feedback type: {feedback_type}")

        state = self._read_json_file(self.settings.feedback_state_path, default={})
        state[user_id] = {"weights": weights, "last_article_id": article_id, "last_feedback": feedback_type}
        self.settings.feedback_state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        return weights

    def _load_feedback_weights(self, user_id: str) -> dict[str, float]:
        state = self._read_json_file(self.settings.feedback_state_path, default={})
        weights = state.get(user_id, {}).get("weights", {})
        return {key: float(weights.get(key, value)) for key, value in self.BASE_WEIGHTS.items()}

    @staticmethod
    def _weighted_preferences(series: pd.Series, limit: int = 5) -> list[dict[str, Any]]:
        counts = Counter(str(value) for value in series.dropna().tolist())
        total = sum(counts.values())
        if total == 0:
            return []
        return [
            {"value": label, "weight": round(count / total, 4)}
            for label, count in counts.most_common(limit)
        ]

    @staticmethod
    def _extract_hard_constraints(user_request: str) -> dict[str, str]:
        normalized = user_request.lower()
        constraints: dict[str, str] = {}
        if (
            "only black" in normalized
            or "black only" in normalized
            or re.search(r"\bonly want black\b", normalized)
        ):
            constraints["colour_group_name"] = "Black"
        if (
            "only dresses" in normalized
            or "dress only" in normalized
            or "black dresses" in normalized
            or re.search(r"\bonly want .*dresses\b", normalized)
        ):
            constraints["product_type_name"] = "Dress"
        if "only trousers" in normalized or "trousers only" in normalized:
            constraints["product_type_name"] = "Trousers"
        return constraints

    @staticmethod
    def _to_weight_map(values: list[dict[str, Any]]) -> dict[str, float]:
        return {str(item["value"]): float(item["weight"]) for item in values}

    @staticmethod
    def _description_terms(user_profile: dict[str, Any]) -> set[str]:
        terms = set()
        for sentence in user_profile.get("soft_preferences", []):
            terms.update(re.findall(r"[a-z0-9]+", sentence.lower()))
        terms.update(re.findall(r"[a-z0-9]+", user_profile.get("preference_summary", "").lower()))
        return terms

    @staticmethod
    def _description_similarity(description: str, terms: set[str]) -> float:
        if not terms:
            return 0.0
        description_terms = set(re.findall(r"[a-z0-9]+", description.lower()))
        return min(len(description_terms & terms) / len(terms), 1.0)

    @staticmethod
    def _matched_fields(
        row: pd.Series,
        type_weights: dict[str, float],
        group_weights: dict[str, float],
        colour_weights: dict[str, float],
        appearance_weights: dict[str, float],
        description_terms: set[str],
    ) -> list[str]:
        matched = []
        if row["product_type"] in type_weights:
            matched.append("product_type_name")
        if row["product_group"] in group_weights:
            matched.append("product_group_name")
        if row["colour"] in colour_weights:
            matched.append("colour_group_name")
        if row["appearance"] in appearance_weights:
            matched.append("graphical_appearance_name")
        if AgenticRecommendationService._description_similarity(str(row["product_description"]), description_terms) > 0:
            matched.append("product_description")
        return matched

    @staticmethod
    def _missing_evidence(row: pd.Series) -> list[str]:
        missing = []
        for field in ["product_description", "image_url"]:
            if not str(row.get(field, "")).strip():
                missing.append(field)
        return missing

    @staticmethod
    def _violates_constraints(candidate: dict[str, Any], constraints: dict[str, str]) -> bool:
        for field, value in constraints.items():
            if candidate.get(field) != value:
                return True
        return False

    @staticmethod
    def _catalogue(train_df: pd.DataFrame) -> pd.DataFrame:
        catalogue = train_df.drop_duplicates("article_id").copy()
        if "product_description" not in catalogue.columns:
            catalogue["product_description"] = catalogue["product_name"]
        if "image_url" not in catalogue.columns:
            catalogue["image_url"] = catalogue["article_id"].astype(str).map(
                lambda article_id: f"https://placehold.co/300x400?text={article_id}"
            )
        return catalogue

    def _user_history(self, user_id: str, train_df: pd.DataFrame) -> pd.DataFrame:
        history = train_df[train_df["customer_id"] == user_id].copy()
        if history.empty:
            raise AgenticServiceError(f"User {user_id} has no training history.")
        if "product_description" not in history.columns:
            history["product_description"] = history["product_name"]
        if "image_url" not in history.columns:
            history["image_url"] = history["article_id"].astype(str).map(
                lambda article_id: f"https://placehold.co/300x400?text={article_id}"
            )
        return history

    def _request_structured_completion(self, system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.openai_api_key:
            raise AgenticServiceError("OPENAI_API_KEY is required for the Agentic AI method.")

        request_body = {
            "model": self.settings.openai_model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload)},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.settings.llm_timeout_seconds) as client:
                response = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    json=request_body,
                    headers=headers,
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AgenticServiceError(f"OpenAI request failed: {exc}") from exc

        payload = response.json()
        try:
            return json.loads(payload["choices"][0]["message"]["content"])
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise AgenticServiceError("Unable to parse structured JSON from OpenAI response.") from exc

    @staticmethod
    def _read_json_file(path, default: dict[str, Any]) -> dict[str, Any]:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
