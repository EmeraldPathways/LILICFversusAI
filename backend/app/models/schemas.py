from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


FeedbackType = Literal["click", "add_to_cart", "ignore", "purchase"]


class RecommendationItem(BaseModel):
    article_id: str
    product_name: str
    product_type: str
    product_group: str
    colour: str
    appearance: str
    score: float
    model: str


class AgenticRecommendationItem(RecommendationItem):
    reason: str
    intent_match: float
    preference_alignment: float
    product_relevance: float
    diversity: float
    behavioural_signal: float


class AgentProcessStage(BaseModel):
    agent: str
    title: str
    summary: str
    payload: dict[str, object]


class UserIntentResponse(BaseModel):
    user_id: str
    inferred_intent: str
    preferred_categories: list[str]
    preferred_product_types: list[str]
    preferred_colours: list[str]
    preferred_appearance: list[str]
    shopping_context: str


class RecommendationComparisonResponse(BaseModel):
    user_id: str
    cf_recommendations: list[RecommendationItem]
    agentic_recommendations: list[AgenticRecommendationItem]
    agentic_process: list[AgentProcessStage]


class ModelMetrics(BaseModel):
    hit_rate_at_10: float
    preference_alignment: float
    diversity: float
    explanation_quality: float | None = None
    feedback_adaptability: float | None = None


class MetricsResponse(BaseModel):
    collaborative_filtering: ModelMetrics
    agentic_ai_framework: ModelMetrics
    business_mapping: dict[str, str]
    evaluated_users: int
    generated_at: datetime


class RunExperimentResponse(BaseModel):
    dataset: str
    status: str
    experiment_mode: str | None = None
    sample_size: int
    train_size: int
    test_size: int
    models: list[str]
    metrics_ready: bool
    evaluated_users: int


class ExperimentSetupResponse(BaseModel):
    dataset: str
    sample_size: int
    experiment_mode: str | None = None
    split_method: str
    benchmark: str
    proposed_framework: str
    evaluation_metrics: list[str]
    summary: dict[str, object] | None = None


class FeedbackRequest(BaseModel):
    article_id: str
    feedback_type: FeedbackType


class FeedbackResponse(BaseModel):
    status: str
    message: str
    user_id: str
    article_id: str
    feedback_type: FeedbackType
    updated_weights: dict[str, float]


class ProcessingSummaryResponse(BaseModel):
    dataset: str
    sample_size: int
    distinct_users: int
    distinct_products: int
    top_product_groups: list[dict[str, object]]
    top_colours: list[dict[str, object]]
    top_appearances: list[dict[str, object]]
    train_size: int
    test_size: int
    split_boundary_date: str
