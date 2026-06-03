from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


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


class WeightedPreferenceItem(BaseModel):
    value: str
    weight: float


class AgentProcessStage(BaseModel):
    agent: str
    title: str
    summary: str
    payload: dict[str, object]


class UserIntentResponse(BaseModel):
    user_id: str
    preferred_product_type_name_values: list[WeightedPreferenceItem]
    preferred_product_group_name_values: list[WeightedPreferenceItem]
    preferred_colour_group_name_values: list[WeightedPreferenceItem]
    preferred_graphical_appearance_name_values: list[WeightedPreferenceItem]
    soft_preferences: list[str]
    hard_constraints: dict[str, str]
    preference_summary: str


class CandidateEvidenceItem(BaseModel):
    article_id: str
    product_type_name: str
    product_group_name: str
    graphical_appearance_name: str
    colour_group_name: str
    product_description: str
    image_url: str
    matched_preference_fields: list[str]
    evidence_summary: str
    match_count: int
    missing_evidence: list[str]


class FinalRecommendationItem(BaseModel):
    rank: int
    article_id: str
    match_score: float
    recommendation_reason: str
    matched_evidence: list[str]
    constraint_status: str
    product_type_name: str
    product_group_name: str
    graphical_appearance_name: str
    colour_group_name: str
    product_description: str
    image_url: str


class RecommendationRunRequest(BaseModel):
    user_id: str
    user_request: str = ""


class TrainingHistoryItem(BaseModel):
    article_id: str
    product_name: str
    product_type: str
    product_group: str
    colour: str
    appearance: str
    transaction_date: str


class CFRecommendationResponse(BaseModel):
    user_id: str
    ground_truth_article_id: str
    hit_at_5: bool
    training_history_count: int
    training_history_preview: list[TrainingHistoryItem]
    recommendations: list[RecommendationItem]


class AgenticRunResponse(BaseModel):
    user_id: str
    user_request: str
    ground_truth_article_id: str
    hit_at_5: bool
    training_history_count: int
    training_history_preview: list[TrainingHistoryItem]
    preference_profile: UserIntentResponse
    candidate_evidence_set: list[CandidateEvidenceItem]
    final_recommendations: list[FinalRecommendationItem]
    process_trace: list[AgentProcessStage]


class ComparisonModelOutput(BaseModel):
    hit_at_5: bool
    recommendations: list[dict[str, object]]


class ComparisonResponse(BaseModel):
    user_id: str
    ground_truth_article_id: str
    training_history_count: int
    training_history_preview: list[TrainingHistoryItem]
    cf: ComparisonModelOutput
    agentic: ComparisonModelOutput


class ModelMetric(BaseModel):
    hit_at_5: float


class MetricsResponse(BaseModel):
    collaborative_filtering: ModelMetric
    agentic_ai_framework: ModelMetric
    evaluated_users: int
    generated_at: datetime


class RunExperimentResponse(BaseModel):
    dataset: str
    status: str
    sample_size: int
    train_size: int
    test_size: int
    models: list[str]
    metrics_ready: bool
    evaluated_users: int


class ExperimentSetupResponse(BaseModel):
    dataset: str
    sample_size: int
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
