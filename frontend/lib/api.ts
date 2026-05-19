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

export type UserIntent = {
  user_id: string;
  inferred_intent: string;
  preferred_categories: string[];
  preferred_product_types: string[];
  preferred_colours: string[];
  preferred_appearance: string[];
  shopping_context: string;
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

export type AgenticRecommendationItem = RecommendationItem & {
  reason: string;
  intent_match: number;
  preference_alignment: number;
  product_relevance: number;
  diversity: number;
  behavioural_signal: number;
};

export type RecommendationComparison = {
  user_id: string;
  cf_recommendations: RecommendationItem[];
  agentic_recommendations: AgenticRecommendationItem[];
  agentic_process: AgentProcessStage[];
};

export type AgentProcessStage = {
  agent: string;
  title: string;
  summary: string;
  payload: Record<string, unknown>;
};

export type ModelMetrics = {
  hit_rate_at_10: number;
  preference_alignment: number;
  diversity: number;
  explanation_quality?: number | null;
  feedback_adaptability?: number | null;
};

export type MetricsResponse = {
  collaborative_filtering: ModelMetrics;
  agentic_ai_framework: ModelMetrics;
  business_mapping: Record<string, string>;
  evaluated_users: number;
  generated_at: string;
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

export async function getMetrics(): Promise<MetricsResponse | null> {
  try {
    return await apiFetch<MetricsResponse>("/metrics");
  } catch {
    return null;
  }
}

export async function getUserIntent(userId: string): Promise<UserIntent> {
  return apiFetch<UserIntent>(`/users/${userId}/intent`);
}

export async function getRecommendationComparison(userId: string): Promise<RecommendationComparison> {
  return apiFetch<RecommendationComparison>(`/recommendations/compare/${userId}`);
}

export async function sendFeedback(
  userId: string,
  articleId: string,
  feedbackType: "click" | "add_to_cart" | "ignore" | "purchase",
): Promise<{ message: string; updated_weights: Record<string, number> }> {
  return apiFetch(`/users/${userId}/feedback`, {
    method: "POST",
    body: JSON.stringify({
      article_id: articleId,
      feedback_type: feedbackType,
    }),
  });
}
