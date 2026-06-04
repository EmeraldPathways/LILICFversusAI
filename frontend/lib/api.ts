export type SummaryCount = {
  label: string;
  value: number;
};

export type ExperimentSummary = {
  dataset: string;
  sample_size: number;
  distinct_users: number;
  distinct_products: number;
  repeat_user_ratio: number;
  average_interactions_per_user: number;
  average_interactions_per_product: number;
  top_product_groups: SummaryCount[];
  top_product_types: SummaryCount[];
  top_colours: SummaryCount[];
  top_appearances: SummaryCount[];
  train_size: number;
  test_size: number;
  split_boundary_date: string;
  sample_user_ids?: string[];
  evaluated_user_ids?: string[];
  evaluated_users?: number;
  available_user_ids?: string[];
  completed_comparable_user_ids?: string[];
  completed_comparable_user_count?: number;
  valid_completed_user_count?: number;
  max_valid_eval_users?: number;
};

export type ExperimentSetup = {
  dataset: string;
  sample_size: number;
  split_method: string;
  benchmark: string;
  proposed_framework: string;
  evaluation_metrics: string[];
  available_user_ids: string[];
  completed_comparable_user_ids: string[];
  completed_comparable_user_count: number;
  valid_completed_user_count: number;
  max_valid_eval_users: number;
  summary: ExperimentSummary | null;
};

export type WeightedPreferenceItem = {
  value: string;
  weight: number;
};

export type TrainingHistoryItem = {
  article_id: string;
  product_name: string;
  product_type: string;
  product_group: string;
  colour: string;
  appearance: string;
  transaction_date: string;
};

export type RecommendationItem = {
  article_id: string;
  product_name: string;
  product_type: string;
  product_group: string;
  colour: string;
  appearance: string;
  score: number;
  model: string;
};

export type UserPreferenceProfile = {
  user_id: string;
  preferred_product_type_name_values: WeightedPreferenceItem[];
  preferred_product_group_name_values: WeightedPreferenceItem[];
  preferred_colour_group_name_values: WeightedPreferenceItem[];
  preferred_graphical_appearance_name_values: WeightedPreferenceItem[];
  soft_preferences: string[];
  hard_constraints: Record<string, string>;
  preference_summary: string;
};

export type CandidateEvidenceItem = {
  article_id: string;
  product_type_name: string;
  product_group_name: string;
  graphical_appearance_name: string;
  colour_group_name: string;
  product_description: string;
  image_url: string;
  matched_preference_fields: string[];
  evidence_summary: string;
  match_count: number;
  missing_evidence: string[];
};

export type FinalRecommendationItem = {
  rank: number;
  article_id: string;
  match_score: number;
  recommendation_reason: string;
  matched_evidence: string[];
  constraint_status: string;
  product_type_name: string;
  product_group_name: string;
  graphical_appearance_name: string;
  colour_group_name: string;
  product_description: string;
  image_url: string;
};

export type AgentProcessStage = {
  agent: string;
  title: string;
  summary: string;
  payload: Record<string, unknown>;
};

export type CFRecommendationResponse = {
  customer_id: string;
  method: string;
  candidate_pool_size: number;
  ground_truth_article_id: string;
  hit_result: HitResult;
  hit_at_5: number;
  hit_label: string;
  hit_explanation: string;
  explanation: string;
  training_history_count: number;
  training_history_preview: TrainingHistoryItem[];
  top_5_article_ids: string[];
  top_5_recommendations: RecommendationItem[];
  validation: RecommendationValidationBlock;
  invalid_reason?: string | null;
};

export type AgenticRunResponse = {
  customer_id: string;
  method: string;
  candidate_pool_size: number;
  user_request: string;
  ground_truth_article_id: string;
  hit_result: HitResult;
  hit_at_5: number;
  hit_label: string;
  hit_explanation: string;
  explanation: string;
  training_history_count: number;
  training_history_preview: TrainingHistoryItem[];
  preference_profile: UserPreferenceProfile;
  candidate_evidence_set: CandidateEvidenceItem[];
  top_5_article_ids: string[];
  top_5_recommendations: FinalRecommendationItem[];
  process_trace: AgentProcessStage[];
  validation: RecommendationValidationBlock;
  invalid_reason?: string | null;
};

export type HitResult = {
  hit_at_5: number;
  hit_label: string;
  matched_article_id?: string | null;
  matched_rank?: number | null;
  explanation: string;
};

export type RecommendationValidationBlock = {
  evaluation_base_used: boolean;
  same_candidate_pool_source: boolean;
  ground_truth_in_candidate_pool: boolean;
  top_5_all_inside_candidate_pool: boolean;
  top_5_contains_training_items: boolean;
  article_id_format_check: "passed" | "failed";
};

export type ComparisonModelOutput = {
  customer_id: string;
  method: string;
  candidate_pool_size: number;
  ground_truth_article_id: string;
  hit_result: HitResult;
  hit_at_5: number;
  hit_label: string;
  hit_explanation: string;
  explanation: string;
  top_5_article_ids: string[];
  top_5_recommendations: Array<Record<string, unknown>>;
  recommendations: Array<Record<string, unknown>>;
  validation: RecommendationValidationBlock;
  invalid_reason?: string | null;
};

export type ComparisonResponse = {
  customer_id: string;
  user_id: string;
  is_comparable: boolean;
  reason?: string | null;
  ground_truth_article_id?: string | null;
  training_history_count: number;
  training_history_preview: TrainingHistoryItem[];
  evaluation_base?: EvaluationBaseRow | null;
  cf?: ComparisonModelOutput | null;
  agentic?: ComparisonModelOutput | null;
};

export type ExcludedUserReason = {
  user_id: string;
  reasons: string[];
};

export type MetricsResponse = {
  collaborative_filtering: {
    hit_at_5: number;
  };
  agentic_ai_framework: {
    hit_at_5: number;
  };
  total_selected_users: number;
  valid_evaluation_users: number;
  invalid_evaluation_users: number;
  evaluated_users: number;
  completed_valid_users: number;
  cf_hit_at_5: number;
  agentic_hit_at_5: number;
  cf_hits_count: number;
  agentic_hits_count: number;
  cf_miss_count: number;
  agentic_miss_count: number;
  evaluated_user_ids: string[];
  excluded_user_ids_with_reasons: ExcludedUserReason[];
  generated_at: string;
};

export type EvaluationDebugMethod = {
  hit_at_5: boolean;
  hit_label: string;
  explanation: string;
  top_5_article_ids: string[];
  recommendations: Array<Record<string, unknown>>;
  ground_truth_in_top_5: boolean;
  candidate_pool_contains_ground_truth: boolean;
};

export type EvaluationDebugValidation = {
  is_valid: boolean;
  reasons: string[];
  candidate_pool_size: number;
  candidate_pool_article_ids_preview: string[];
  evaluation_mode: string;
};

export type EvaluationDebugResponse = {
  customer_id: string;
  number_of_total_transactions: number;
  number_of_training_transactions: number;
  training_article_ids: string[];
  ground_truth_article_id: string;
  ground_truth_article_ids: string[];
  ground_truth_exists_in_processed_product_catalog: boolean;
  validation?: EvaluationDebugValidation;
  cf: EvaluationDebugMethod;
  agentic: EvaluationDebugMethod;
};

export type EvaluationBaseRow = {
  customer_id: string;
  total_transaction_count: number;
  train_count: number;
  train_article_ids: string[];
  train_transaction_dates: string[];
  ground_truth_article_id: string;
  ground_truth_transaction_date: string;
  ground_truth_product_type: string;
  ground_truth_product_group: string;
  ground_truth_colour: string;
  ground_truth_appearance: string;
  ground_truth_in_catalog: boolean;
  candidate_pool_article_ids: string[];
  candidate_pool_size: number;
  ground_truth_in_candidate_pool: boolean;
  is_valid_for_evaluation: boolean;
  invalid_reason: string;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(payload.detail ?? `Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function getSetup(): Promise<ExperimentSetup | null> {
  try {
    return await apiFetch<ExperimentSetup>("/experiment/setup");
  } catch {
    return null;
  }
}

export async function getCFRecommendations(userId: string): Promise<CFRecommendationResponse> {
  return apiFetch<CFRecommendationResponse>(`/recommendations/cf/${userId}`);
}

export async function runAgenticRecommendations(
  userId: string,
  userRequest: string,
): Promise<AgenticRunResponse> {
  return apiFetch<AgenticRunResponse>("/recommendations/agentic/run", {
    method: "POST",
    body: JSON.stringify({ user_id: userId, user_request: userRequest }),
  });
}

export async function getComparison(userId: string): Promise<ComparisonResponse> {
  return apiFetch<ComparisonResponse>(`/comparison/${userId}`);
}

export async function getMetrics(): Promise<MetricsResponse> {
  return apiFetch<MetricsResponse>("/metrics");
}

export async function getEvaluationDebug(userId: string): Promise<EvaluationDebugResponse> {
  return apiFetch<EvaluationDebugResponse>(`/debug/evaluation/${userId}`);
}

export async function getEvaluationBase(userId: string): Promise<EvaluationBaseRow> {
  return apiFetch<EvaluationBaseRow>(`/debug/evaluation-base/${userId}`);
}
