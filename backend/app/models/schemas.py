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


class HitResult(BaseModel):
    hit_at_5: int
    hit_label: str
    matched_article_id: str | None = None
    matched_rank: int | None = None
    explanation: str


class RecommendationValidationBlock(BaseModel):
    evaluation_base_used: bool
    same_candidate_pool_source: bool
    ground_truth_in_candidate_pool: bool
    top_5_all_inside_candidate_pool: bool
    top_5_contains_training_items: bool
    article_id_format_check: str


class EvaluationBaseRowResponse(BaseModel):
    customer_id: str
    total_transaction_count: int
    train_count: int
    train_article_ids: list[str]
    train_transaction_dates: list[str]
    ground_truth_article_id: str
    ground_truth_transaction_date: str
    ground_truth_product_type: str
    ground_truth_product_group: str
    ground_truth_colour: str
    ground_truth_appearance: str
    ground_truth_in_catalog: bool
    candidate_pool_article_ids: list[str]
    candidate_pool_size: int
    ground_truth_in_candidate_pool: bool
    is_valid_for_evaluation: bool
    invalid_reason: str


class CFRecommendationResponse(BaseModel):
    customer_id: str
    method: str
    candidate_pool_size: int
    ground_truth_article_id: str
    hit_result: HitResult
    hit_at_5: bool
    hit_label: str
    explanation: str
    training_history_count: int
    training_history_preview: list[TrainingHistoryItem]
    top_5_recommendations: list[RecommendationItem]
    validation: RecommendationValidationBlock
    invalid_reason: str | None = None


class AgenticRunResponse(BaseModel):
    customer_id: str
    method: str
    candidate_pool_size: int
    user_request: str
    ground_truth_article_id: str
    hit_result: HitResult
    hit_at_5: bool
    hit_label: str
    explanation: str
    training_history_count: int
    training_history_preview: list[TrainingHistoryItem]
    preference_profile: UserIntentResponse
    candidate_evidence_set: list[CandidateEvidenceItem]
    top_5_recommendations: list[FinalRecommendationItem]
    process_trace: list[AgentProcessStage]
    validation: RecommendationValidationBlock
    invalid_reason: str | None = None


class ComparisonModelOutput(BaseModel):
    customer_id: str
    method: str
    candidate_pool_size: int
    ground_truth_article_id: str
    hit_result: HitResult
    hit_at_5: bool
    hit_label: str
    explanation: str
    recommendations: list[dict[str, object]]
    validation: RecommendationValidationBlock
    invalid_reason: str | None = None


class ComparisonResponse(BaseModel):
    user_id: str
    ground_truth_article_id: str
    training_history_count: int
    training_history_preview: list[TrainingHistoryItem]
    evaluation_base: EvaluationBaseRowResponse
    cf: ComparisonModelOutput
    agentic: ComparisonModelOutput


class ModelMetric(BaseModel):
    hit_at_5: float


class ExcludedUserReason(BaseModel):
    user_id: str
    reasons: list[str]


class MetricsResponse(BaseModel):
    collaborative_filtering: ModelMetric
    agentic_ai_framework: ModelMetric
    total_selected_users: int
    valid_evaluation_users: int
    invalid_evaluation_users: int
    evaluated_users: int
    cf_hit_at_5: float
    agentic_hit_at_5: float
    cf_hits_count: int
    agentic_hits_count: int
    evaluated_user_ids: list[str]
    excluded_user_ids_with_reasons: list[ExcludedUserReason]
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
