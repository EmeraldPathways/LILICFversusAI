from __future__ import annotations

import json
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

    def infer_user_intent(self, user_id: str, train_df: pd.DataFrame) -> dict[str, Any]:
        history = train_df[train_df["customer_id"] == user_id].copy()
        if history.empty:
            raise AgenticServiceError(f"User {user_id} has no training history.")

        dominant_groups = self._top_values(history["product_group"])
        dominant_types = self._top_values(history["product_type"])
        dominant_colours = self._top_values(history["colour"])
        dominant_appearance = self._top_values(history["appearance"])

        prompt_payload = {
            "user_id": user_id,
            "dominant_product_groups": dominant_groups,
            "dominant_product_types": dominant_types,
            "dominant_colours": dominant_colours,
            "dominant_appearance": dominant_appearance,
        }
        llm_result = self._request_structured_completion(
            system_prompt=(
                "You are an e-commerce recommendation analyst. "
                "Return JSON only with keys: inferred_intent, preferred_categories, "
                "preferred_product_types, preferred_colours, preferred_appearance, shopping_context."
            ),
            user_payload=prompt_payload,
        )

        required_keys = {
            "inferred_intent",
            "preferred_categories",
            "preferred_product_types",
            "preferred_colours",
            "preferred_appearance",
            "shopping_context",
        }
        if not required_keys.issubset(llm_result):
            raise AgenticServiceError("LLM response was missing one or more required user-intent fields.")

        return {
            "user_id": user_id,
            "inferred_intent": str(llm_result["inferred_intent"]),
            "preferred_categories": [str(item) for item in llm_result["preferred_categories"]],
            "preferred_product_types": [str(item) for item in llm_result["preferred_product_types"]],
            "preferred_colours": [str(item) for item in llm_result["preferred_colours"]],
            "preferred_appearance": [str(item) for item in llm_result["preferred_appearance"]],
            "shopping_context": str(llm_result["shopping_context"]),
        }

    def retrieve_candidate_products(
        self,
        user_profile: dict[str, Any],
        train_df: pd.DataFrame,
    ) -> pd.DataFrame:
        user_history = set(
            train_df.loc[train_df["customer_id"] == user_profile["user_id"], "article_id"].astype(str)
        )
        catalogue = train_df.drop_duplicates("article_id").copy()
        catalogue = catalogue[~catalogue["article_id"].astype(str).isin(user_history)].copy()

        preferred_groups = set(user_profile["preferred_categories"])
        preferred_types = set(user_profile["preferred_product_types"])
        preferred_colours = set(user_profile["preferred_colours"])
        preferred_appearance = set(user_profile["preferred_appearance"])
        intent_terms = set(str(user_profile["inferred_intent"]).lower().split())

        def retrieval_score(row: pd.Series) -> float:
            name_terms = set(str(row["product_name"]).lower().split())
            score = 0.0
            score += 2.0 if row["product_group"] in preferred_groups else 0.0
            score += 2.5 if row["product_type"] in preferred_types else 0.0
            score += 1.5 if row["colour"] in preferred_colours else 0.0
            score += 1.5 if row["appearance"] in preferred_appearance else 0.0
            score += min(1.0, len(intent_terms & name_terms) * 0.3)
            return score

        catalogue["retrieval_score"] = catalogue.apply(retrieval_score, axis=1)
        ranked = catalogue.sort_values(
            ["retrieval_score", "transaction_date"], ascending=[False, False]
        ).head(self.settings.candidate_pool_size)
        return ranked

    def score_candidates(
        self,
        user_profile: dict[str, Any],
        candidates: pd.DataFrame,
        train_df: pd.DataFrame,
    ) -> list[dict[str, Any]]:
        if candidates.empty:
            return []

        preferences = self._load_feedback_weights(user_profile["user_id"])
        profile_history = train_df[train_df["customer_id"] == user_profile["user_id"]]
        type_counts = Counter(profile_history["product_type"])
        group_counts = Counter(profile_history["product_group"])
        colour_counts = Counter(profile_history["colour"])
        appearance_counts = Counter(profile_history["appearance"])

        seen_types: set[str] = set()
        scored_items: list[dict[str, Any]] = []
        intent_terms = set(user_profile["inferred_intent"].lower().split())

        for _, row in candidates.iterrows():
            intent_match = self._intent_match(row, user_profile, intent_terms)
            preference_alignment = self._preference_alignment(row, user_profile, preferences)
            product_relevance = self._product_relevance(
                row, group_counts, type_counts, colour_counts, appearance_counts
            )
            diversity = 1.0 if row["product_type"] not in seen_types else 0.4 / preferences["diversity_penalty"]
            behavioural_signal = self._behavioural_signal(row, group_counts, type_counts)
            final_score = (
                0.30 * intent_match
                + 0.25 * preference_alignment
                + 0.20 * product_relevance
                + 0.15 * diversity
                + 0.10 * behavioural_signal
            )
            seen_types.add(str(row["product_type"]))
            scored_items.append(
                {
                    "article_id": str(row["article_id"]),
                    "product_name": str(row["product_name"]),
                    "product_type": str(row["product_type"]),
                    "product_group": str(row["product_group"]),
                    "colour": str(row["colour"]),
                    "appearance": str(row["appearance"]),
                    "score": round(float(final_score), 4),
                    "model": "agentic_ai_framework",
                    "intent_match": round(float(intent_match), 4),
                    "preference_alignment": round(float(preference_alignment), 4),
                    "product_relevance": round(float(product_relevance), 4),
                    "diversity": round(float(diversity), 4),
                    "behavioural_signal": round(float(behavioural_signal), 4),
                }
            )

        scored_items.sort(key=lambda item: item["score"], reverse=True)
        return scored_items[: self.settings.top_n]

    def generate_explanation(self, user_profile: dict[str, Any], scored_item: dict[str, Any]) -> str:
        llm_result = self._request_structured_completion(
            system_prompt=(
                "You explain why an e-commerce product was recommended. "
                "Return JSON only with a single key called explanation. "
                "Keep the explanation to one sentence and ground it in the provided profile and scores."
            ),
            user_payload={
                "user_profile": user_profile,
                "recommendation": scored_item,
            },
        )
        explanation = llm_result.get("explanation")
        if not explanation:
            raise AgenticServiceError("LLM response did not include an explanation field.")
        return str(explanation)

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

    def generate_all(self, train_df: pd.DataFrame, user_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
        outputs: dict[str, list[dict[str, Any]]] = {}
        traces: dict[str, list[dict[str, Any]]] = {}
        for user_id in user_ids:
            enriched, trace = self.generate_for_user(user_id, train_df)
            outputs[user_id] = enriched
            traces[user_id] = trace

        self.settings.agentic_output_path.write_text(json.dumps(outputs, indent=2), encoding="utf-8")
        self.settings.agentic_trace_path.write_text(json.dumps(traces, indent=2), encoding="utf-8")
        return outputs

    def generate_for_user(
        self,
        user_id: str,
        train_df: pd.DataFrame,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        profile = self.infer_user_intent(user_id, train_df)
        candidates = self.retrieve_candidate_products(profile, train_df)
        scored = self.score_candidates(profile, candidates, train_df)
        enriched = []
        for item in scored:
            enriched_item = dict(item)
            enriched_item["reason"] = self.generate_explanation(profile, item)
            enriched.append(enriched_item)
        trace = self._build_agent_trace(user_id, profile, candidates, scored, enriched)
        return enriched, trace

    def load_traces(self) -> dict[str, list[dict[str, Any]]]:
        return self._read_json_file(self.settings.agentic_trace_path, default={})

    def load_outputs(self) -> dict[str, list[dict[str, Any]]]:
        return self._read_json_file(self.settings.agentic_output_path, default={})

    def _load_feedback_weights(self, user_id: str) -> dict[str, float]:
        state = self._read_json_file(self.settings.feedback_state_path, default={})
        weights = state.get(user_id, {}).get("weights", {})
        return {key: float(weights.get(key, value)) for key, value in self.BASE_WEIGHTS.items()}

    def _request_structured_completion(self, system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.openai_api_key:
            raise AgenticServiceError(
                "OPENAI_API_KEY is required for the agentic intention and explanation services."
            )

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
            content = payload["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise AgenticServiceError("Unable to parse structured JSON from OpenAI response.") from exc

    @staticmethod
    def _top_values(series: pd.Series, limit: int = 3) -> list[str]:
        return [str(value) for value in series.value_counts().head(limit).index.tolist()]

    @staticmethod
    def _intent_match(row: pd.Series, user_profile: dict[str, Any], intent_terms: set[str]) -> float:
        score = 0.0
        if row["product_group"] in user_profile["preferred_categories"]:
            score += 0.35
        if row["product_type"] in user_profile["preferred_product_types"]:
            score += 0.35
        if row["colour"] in user_profile["preferred_colours"]:
            score += 0.15
        if row["appearance"] in user_profile["preferred_appearance"]:
            score += 0.1
        score += min(0.05, len(intent_terms & set(str(row["product_name"]).lower().split())) * 0.02)
        return min(score, 1.0)

    @staticmethod
    def _preference_alignment(
        row: pd.Series,
        user_profile: dict[str, Any],
        preferences: dict[str, float],
    ) -> float:
        score = 0.0
        score += 0.25 * preferences["category_weight"] if row["product_group"] in user_profile["preferred_categories"] else 0.0
        score += 0.25 * preferences["product_type_weight"] if row["product_type"] in user_profile["preferred_product_types"] else 0.0
        score += 0.25 * preferences["colour_weight"] if row["colour"] in user_profile["preferred_colours"] else 0.0
        score += 0.25 * preferences["appearance_weight"] if row["appearance"] in user_profile["preferred_appearance"] else 0.0
        return min(score / max(preferences["product_type_weight"], 1.0), 1.0)

    @staticmethod
    def _product_relevance(
        row: pd.Series,
        group_counts: Counter[str],
        type_counts: Counter[str],
        colour_counts: Counter[str],
        appearance_counts: Counter[str],
    ) -> float:
        def normalized(counter: Counter[str], key: str) -> float:
            if not counter:
                return 0.0
            return counter.get(str(key), 0) / max(counter.values())

        return min(
            1.0,
            (
                normalized(group_counts, row["product_group"])
                + normalized(type_counts, row["product_type"])
                + normalized(colour_counts, row["colour"])
                + normalized(appearance_counts, row["appearance"])
            )
            / 4,
        )

    @staticmethod
    def _behavioural_signal(row: pd.Series, group_counts: Counter[str], type_counts: Counter[str]) -> float:
        total = sum(group_counts.values()) + sum(type_counts.values())
        if total == 0:
            return 0.0
        return min(
            1.0,
            (group_counts.get(str(row["product_group"]), 0) + type_counts.get(str(row["product_type"]), 0))
            / total
            * 2,
        )

    @staticmethod
    def _read_json_file(path, default: dict[str, Any]) -> dict[str, Any]:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _build_agent_trace(
        self,
        user_id: str,
        user_profile: dict[str, Any],
        candidates: pd.DataFrame,
        scored_items: list[dict[str, Any]],
        enriched_items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        candidate_preview = [
            {
                "article_id": str(row["article_id"]),
                "product_name": str(row["product_name"]),
                "product_type": str(row["product_type"]),
                "colour": str(row["colour"]),
                "retrieval_score": round(float(row["retrieval_score"]), 4),
            }
            for _, row in candidates.head(5).iterrows()
        ]
        reasoning_preview = [
            {
                "article_id": item["article_id"],
                "product_name": item["product_name"],
                "final_score": item["score"],
                "intent_match": item["intent_match"],
                "preference_alignment": item["preference_alignment"],
                "product_relevance": item["product_relevance"],
                "diversity": item["diversity"],
                "behavioural_signal": item["behavioural_signal"],
            }
            for item in scored_items[:5]
        ]
        explanation_preview = [
            {
                "article_id": item["article_id"],
                "product_name": item["product_name"],
                "reason": item["reason"],
            }
            for item in enriched_items[:3]
        ]
        feedback_state = self._read_json_file(self.settings.feedback_state_path, default={}).get(user_id, {})
        weights = self._load_feedback_weights(user_id)

        return [
            {
                "agent": "Agent 1",
                "title": "User Shopping Intention Understanding",
                "summary": "The framework converts observed category, colour, type, and appearance patterns into a structured shopping-intent profile.",
                "payload": {
                    "user_profile": user_profile,
                },
            },
            {
                "agent": "Agent 2",
                "title": "Product Retrieval",
                "summary": f"{len(candidates)} candidate products were retrieved from the filtered catalogue before ranking.",
                "payload": {
                    "candidate_count": len(candidates),
                    "candidate_preview": candidate_preview,
                },
            },
            {
                "agent": "Agent 3",
                "title": "Recommendation Reasoning",
                "summary": "Candidates are ranked with an explicit weighted score covering intent match, alignment, relevance, diversity, and behavioural signal.",
                "payload": {
                    "scoring_formula": "0.30*Intent Match + 0.25*Preference Alignment + 0.20*Product Relevance + 0.15*Diversity + 0.10*Behavioural Signal",
                    "top_scored_items": reasoning_preview,
                },
            },
            {
                "agent": "Agent 4",
                "title": "Recommendation Explanation",
                "summary": "The LLM generates one grounded explanation per top recommendation without changing ranking scores.",
                "payload": {
                    "explanation_preview": explanation_preview,
                },
            },
            {
                "agent": "Agent 5",
                "title": "Feedback Adaptation",
                "summary": "Per-user feedback weights are stored separately so the demo can show how future recommendations would adapt.",
                "payload": {
                    "current_weights": weights,
                    "last_feedback": feedback_state.get("last_feedback"),
                    "last_article_id": feedback_state.get("last_article_id"),
                    "adaptation_rules": {
                        "click": "Slightly increase category and colour weight.",
                        "add_to_cart": "Strongly increase product type and appearance weight.",
                        "ignore": "Increase diversity penalty to reduce similar-item priority.",
                        "purchase": "Treat as a strong category and product-type preference signal.",
                    },
                },
            },
        ]
