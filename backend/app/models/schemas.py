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
    preference_alignment: float | None = None
    diversity: float | None = None
    ndcg_at_10: float | None = None
    intra_list_diversity_at_10: float | None = None
    hits_count: int | None = None
    miss_count: int | None = None
    explanation_quality: float | None = None
    feedback_adaptability: float | None = None


class MetricsResponse(BaseModel):
    collaborative_filtering: ModelMetrics | None = None
    svd_matrix_factorization: ModelMetrics | None = None
    agentic_ai_framework: ModelMetrics
    business_mapping: dict[str, str]
    evaluated_users: int
    generated_at: datetime | None = None


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


class ExplainabilitySummaryMetrics(BaseModel):
    evidence_coverage_rate: float
    preference_trace_rate: float
    score_component_coverage_rate: float
    groundedness_rate: float
    rank_shift_coverage_rate: float
    ungrounded_claim_count: int
    average_rank_shift_for_ground_truth_hits: float | None = None


class ExplainabilityExampleRow(BaseModel):
    customer_id: str
    article_id: str
    hybrid_rank: int
    svd_rank: int | str | None = None
    rank_shift: int | str | None = None
    is_ground_truth: bool | str
    normalized_svd_score: float | str | None = None
    normalized_agentic_score: float | str | None = None
    diversity_bonus: float | str | None = None
    hybrid_score: float | str | None = None
    product_type_name: str | None = None
    product_group_name: str | None = None
    graphical_appearance_name: str | None = None
    colour_group_name: str | None = None
    garment_group_name: str | None = None
    department_name: str | None = None
    section_name: str | None = None
    index_name: str | None = None
    prod_name: str | None = None
    detail_desc: str | None = None
    matched_preference_fields_json: str
    explanation_text: str
    grounded_claim_count: int
    ungrounded_claim_count: int


class ExplainabilityCaseStudy(BaseModel):
    customer_id: str
    ground_truth_article_id: str | None = None
    recommended_article_id: str
    is_ground_truth: bool
    user_history_summary: dict[str, object]
    item_metadata: dict[str, object]
    svd_rank: int | None = None
    hybrid_rank: int
    rank_shift: int | None = None
    score_components: dict[str, object]
    matched_preference_fields: list[dict[str, object]]
    explanation_text: str
    limitation_note: str | None = None


class ExplainabilityPageResponse(BaseModel):
    summary: dict[str, object]
    examples: list[ExplainabilityExampleRow]
    rank_shift_highlights: dict[str, object]
    case_study: ExplainabilityCaseStudy | None = None
    warnings: list[str]
    limitations: list[str]


class ArtifactDemoMethodItem(BaseModel):
    article_id: str
    rank: int | None = None
    score: float | None = None
    reason: str | None = None
    is_ground_truth: bool = False
    product_type_name: str | None = None
    product_group_name: str | None = None
    colour_group_name: str | None = None
    graphical_appearance_name: str | None = None
    garment_group_name: str | None = None


class ArtifactDemoWorkflowCase(BaseModel):
    label: str
    category: str
    customer_id: str
    customer_id_short: str
    training_history_summary: dict[str, object]
    ground_truth: dict[str, object]
    candidate_pool_size: int
    preference_agent: dict[str, object]
    evidence_agent: dict[str, object]
    decision_agent: dict[str, object]
    svd_top10: list[ArtifactDemoMethodItem]
    agentic_top10: list[ArtifactDemoMethodItem]
    hybrid_top10: list[ArtifactDemoMethodItem]
    hybrid_selected_explanation: dict[str, object]
    hybrid_score_components: dict[str, object]
    rank_shift: int | None = None
    diversity_comparison: dict[str, object]


class ArtifactDemoWorkflowCasesResponse(BaseModel):
    artifact_prefix: str
    explainability_prefix: str
    cases: list[ArtifactDemoWorkflowCase]
