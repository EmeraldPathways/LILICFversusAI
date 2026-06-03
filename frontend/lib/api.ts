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
};

export type ExperimentSetup = {
  dataset: string;
  sample_size: number;
  split_method: string;
  benchmark: string;
  proposed_framework: string;
  evaluation_metrics: string[];
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
  user_id: string;
  ground_truth_article_id: string;
  hit_at_5: boolean;
  training_history_count: number;
  training_history_preview: TrainingHistoryItem[];
  recommendations: RecommendationItem[];
};

export type AgenticRunResponse = {
  user_id: string;
  user_request: string;
  ground_truth_article_id: string;
  hit_at_5: boolean;
  training_history_count: number;
  training_history_preview: TrainingHistoryItem[];
  preference_profile: UserPreferenceProfile;
  candidate_evidence_set: CandidateEvidenceItem[];
  final_recommendations: FinalRecommendationItem[];
  process_trace: AgentProcessStage[];
};

export type ComparisonModelOutput = {
  hit_at_5: boolean;
  recommendations: Array<Record<string, unknown>>;
};

export type ComparisonResponse = {
  user_id: string;
  ground_truth_article_id: string;
  training_history_count: number;
  training_history_preview: TrainingHistoryItem[];
  cf: ComparisonModelOutput;
  agentic: ComparisonModelOutput;
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
