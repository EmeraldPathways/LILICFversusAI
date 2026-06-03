"use client";

import { useEffect, useState } from "react";

import {
  type AgenticRunResponse,
  type ComparisonResponse,
  type EvaluationBaseRow,
  type EvaluationDebugResponse,
  type ExperimentSetup,
  getComparison,
  getEvaluationBase,
  getEvaluationDebug,
} from "@/lib/api";
import { EvaluationDebugPanel } from "@/components/EvaluationDebugPanel";
import {
  readPersistedComparisonResult,
  readPersistedAgenticResult,
  readSelectedUserId,
  writePersistedComparisonResult,
  writeSelectedUserId,
} from "@/lib/persistedState";

type ComparisonDashboardProps = {
  setup: ExperimentSetup | null;
  userIds: string[];
};

function toComparisonResult(
  comparison: ComparisonResponse,
  storedAgenticResult: AgenticRunResponse | null,
) {
  if (!storedAgenticResult || storedAgenticResult.customer_id !== comparison.user_id) {
    return comparison;
  }

  return {
    ...comparison,
    agentic: {
      ...comparison.agentic,
      hit_at_5: storedAgenticResult.hit_at_5,
      hit_label: storedAgenticResult.hit_label,
      explanation: storedAgenticResult.explanation,
      hit_result: storedAgenticResult.hit_result,
      recommendations: storedAgenticResult.top_5_recommendations.map((item) => ({
        article_id: item.article_id,
        product_type_name: item.product_type_name,
        product_group_name: item.product_group_name,
        colour_group_name: item.colour_group_name,
        graphical_appearance_name: item.graphical_appearance_name,
        recommendation_reason: item.recommendation_reason,
        match_score: item.match_score,
      })),
    },
  };
}

export function ComparisonDashboard({ setup, userIds }: ComparisonDashboardProps) {
  const [selectedUserId, setSelectedUserId] = useState(userIds[0] ?? "");
  const [result, setResult] = useState<ComparisonResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [debug, setDebug] = useState<EvaluationDebugResponse | null>(null);
  const [debugError, setDebugError] = useState<string | null>(null);
  const [isDebugLoading, setIsDebugLoading] = useState(false);
  const [evaluationBase, setEvaluationBase] = useState<EvaluationBaseRow | null>(null);
  const [evaluationBaseError, setEvaluationBaseError] = useState<string | null>(null);
  const [isEvaluationBaseLoading, setIsEvaluationBaseLoading] = useState(false);

  useEffect(() => {
    const storedUserId = readSelectedUserId();
    if (storedUserId && userIds.includes(storedUserId)) {
      setSelectedUserId(storedUserId);
    }

    const storedComparison = readPersistedComparisonResult();
    if (storedComparison && userIds.includes(storedComparison.user_id)) {
      setSelectedUserId(storedComparison.user_id);
      setResult(toComparisonResult(storedComparison, readPersistedAgenticResult()));
    }
  }, [userIds]);

  useEffect(() => {
    if (selectedUserId) {
      writeSelectedUserId(selectedUserId);
    }
  }, [selectedUserId]);

  useEffect(() => {
    if (!selectedUserId) {
      setDebug(null);
      setDebugError(null);
      return;
    }

    let cancelled = false;

    async function loadDebug() {
      setIsDebugLoading(true);
      setDebugError(null);
      try {
        const payload = await getEvaluationDebug(selectedUserId);
        if (!cancelled) {
          setDebug(payload);
        }
      } catch (loadError) {
        if (!cancelled) {
          setDebug(null);
          setDebugError(
            loadError instanceof Error ? loadError.message : "Unable to load evaluation debug data.",
          );
        }
      } finally {
        if (!cancelled) {
          setIsDebugLoading(false);
        }
      }
    }

    void loadDebug();

    return () => {
      cancelled = true;
    };
  }, [selectedUserId]);

  useEffect(() => {
    if (!selectedUserId) {
      setEvaluationBase(null);
      setEvaluationBaseError(null);
      return;
    }

    let cancelled = false;

    async function loadEvaluationBase() {
      setIsEvaluationBaseLoading(true);
      setEvaluationBaseError(null);
      try {
        const payload = await getEvaluationBase(selectedUserId);
        if (!cancelled) {
          setEvaluationBase(payload);
        }
      } catch (loadError) {
        if (!cancelled) {
          setEvaluationBase(null);
          setEvaluationBaseError(
            loadError instanceof Error ? loadError.message : "Unable to load evaluation base data.",
          );
        }
      } finally {
        if (!cancelled) {
          setIsEvaluationBaseLoading(false);
        }
      }
    }

    void loadEvaluationBase();

    return () => {
      cancelled = true;
    };
  }, [selectedUserId]);

  useEffect(() => {
    const storedAgenticResult = readPersistedAgenticResult();
    if (!storedAgenticResult || storedAgenticResult.customer_id !== selectedUserId || result) {
      return;
    }

    let cancelled = false;

    async function hydrateComparison() {
      setIsLoading(true);
      setError(null);
      try {
        const comparison = await getComparison(selectedUserId);
        if (!cancelled) {
          const hydrated = toComparisonResult(comparison, storedAgenticResult);
          setResult(hydrated);
          writePersistedComparisonResult(hydrated);
        }
      } catch (compareError) {
        if (!cancelled) {
          setError(
            compareError instanceof Error ? compareError.message : "Unable to load the comparison.",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void hydrateComparison();

    return () => {
      cancelled = true;
    };
  }, [result, selectedUserId]);

  async function handleCompare() {
    if (!selectedUserId) {
      setError("No evaluated user is available yet. Run the backend experiment first.");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const comparison = await getComparison(selectedUserId);
      const hydrated = toComparisonResult(comparison, readPersistedAgenticResult());
      setResult(hydrated);
      writePersistedComparisonResult(hydrated);
    } catch (compareError) {
      setError(compareError instanceof Error ? compareError.message : "Unable to load the comparison.");
    } finally {
      setIsLoading(false);
    }
  }

  const comparisonWarnings = result && evaluationBase ? [
    result.cf.candidate_pool_size !== result.agentic.candidate_pool_size
      ? "CF and Agentic candidate pool sizes differ."
      : null,
    !result.cf.validation.top_5_all_inside_candidate_pool || !result.agentic.validation.top_5_all_inside_candidate_pool
      ? "A method recommended an item outside the shared candidate pool."
      : null,
    result.cf.validation.top_5_contains_training_items || result.agentic.validation.top_5_contains_training_items
      ? "A method recommended an item from the training history."
      : null,
    !evaluationBase.ground_truth_in_candidate_pool
      ? "Ground truth is not in the candidate pool."
      : null,
  ].filter(Boolean) : [];

  return (
    <div className="page-stack">
      <section className="hero-panel compact">
        <div className="hero-copy">
          <span className="eyebrow">Comparison</span>
          <h2>CF vs 3-Agent Agentic AI</h2>
          <p>
            Both methods are evaluated against the same held-out next purchase. Hit@5 checks whether
            each method can place the real next item inside its Top 5 list.
          </p>
        </div>
        <div className="hero-side">
          <label className="field">
            <span>Evaluated User</span>
            <select value={selectedUserId} onChange={(event) => setSelectedUserId(event.target.value)}>
              {userIds.map((userId) => (
                <option key={userId} value={userId}>
                  {userId}
                </option>
              ))}
            </select>
          </label>
          <button className="primary-button" onClick={handleCompare} disabled={isLoading}>
            {isLoading ? "Comparing..." : "Run Comparison"}
          </button>
          <div className="summary-chip">
            <span>Metric</span>
            <strong>{setup?.evaluation_metrics?.join(", ") ?? "Hit@5"}</strong>
          </div>
        </div>
      </section>

      {error ? <div className="error-banner">{error}</div> : null}

      <section className="panel">
        <div className="panel-header">
          <div>
            <span className="eyebrow">Ground Truth</span>
            <h3>Held-Out Next Purchase</h3>
          </div>
        </div>
        {result ? (
          <>
            <div className="evaluation-grid">
              <div className="summary-chip">
                <span>Article</span>
                <strong>{result.ground_truth_article_id}</strong>
              </div>
              <div className="summary-chip">
                <span>History Size</span>
                <strong>{result.training_history_count}</strong>
              </div>
              <div className={result.cf.hit_at_5 ? "hit-badge hit" : "hit-badge miss"}>
                CF: {result.cf.hit_label}
              </div>
              <div className={result.agentic.hit_at_5 ? "hit-badge hit" : "hit-badge miss"}>
                Agentic: {result.agentic.hit_label}
              </div>
            </div>
            <p className="body-copy">CF: {result.cf.explanation}</p>
            <p className="body-copy">Agentic: {result.agentic.explanation}</p>
          </>
        ) : (
          <p className="empty-state">Run the comparison to inspect both Top 5 lists side by side.</p>
        )}
      </section>

      <EvaluationDebugPanel debug={debug} error={debugError} isLoading={isDebugLoading} />

      <section className="panel">
        <div className="panel-header">
          <div>
            <span className="eyebrow">Evaluation Base</span>
            <h3>Canonical Leave-One-Out Row</h3>
          </div>
          {evaluationBase ? (
            <div className={evaluationBase.is_valid_for_evaluation ? "hit-badge hit" : "hit-badge miss"}>
              {evaluationBase.is_valid_for_evaluation ? "Valid" : "Invalid"}
            </div>
          ) : null}
        </div>
        {evaluationBaseError ? <div className="error-banner">{evaluationBaseError}</div> : null}
        {isEvaluationBaseLoading ? <p className="empty-state">Loading evaluation base row...</p> : null}
        {evaluationBase ? (
          <>
            <div className="evaluation-grid">
              <div className="summary-chip">
                <span>Train Count</span>
                <strong>{evaluationBase.train_count}</strong>
              </div>
              <div className="summary-chip">
                <span>Ground Truth</span>
                <strong>{evaluationBase.ground_truth_article_id}</strong>
              </div>
              <div className="summary-chip">
                <span>Candidate Pool</span>
                <strong>{evaluationBase.candidate_pool_size}</strong>
              </div>
              <div className="summary-chip">
                <span>Ground Truth In Pool</span>
                <strong>{evaluationBase.ground_truth_in_candidate_pool ? "Yes" : "No"}</strong>
              </div>
            </div>
            <div className="tag-row">
              <span className="tag subdued-tag">{evaluationBase.ground_truth_product_type}</span>
              <span className="tag subdued-tag">{evaluationBase.ground_truth_product_group}</span>
              <span className="tag subdued-tag">{evaluationBase.ground_truth_colour}</span>
              <span className="tag subdued-tag">{evaluationBase.ground_truth_appearance}</span>
            </div>
            <p className="body-copy">
              Invalid reason: {evaluationBase.invalid_reason || "none"}
            </p>
          </>
        ) : null}
      </section>

      {comparisonWarnings.length > 0 ? (
        <section className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">Warnings</span>
              <h3>Evaluation Consistency Checks</h3>
            </div>
          </div>
          <div className="stack-list">
            {comparisonWarnings.map((warning) => (
              <p key={warning} className="body-copy">{warning}</p>
            ))}
          </div>
        </section>
      ) : null}

      {result ? (
        <section className="comparison-grid">
          <article className="panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">Collaborative Filtering</span>
                <h3>CF Top 5</h3>
              </div>
            </div>
            <div className="stack-list">
              {result.cf.recommendations.map((item, index) => {
                const recommendation = item as {
                  article_id: string;
                  product_type?: string;
                  product_group?: string;
                  colour?: string;
                  appearance?: string;
                  product_name?: string;
                  score?: number;
                };

                return (
                  <article key={recommendation.article_id} className="list-card">
                    <div className="candidate-head">
                      <div>
                        <div className="meta-label">Rank #{index + 1}</div>
                        <h4>
                          {(recommendation.product_type ?? "Product")} · {recommendation.article_id}
                        </h4>
                      </div>
                      <div className="match-pill">Score {recommendation.score ?? 0}</div>
                    </div>
                    <p className="body-copy">
                      {recommendation.product_name ?? "Transaction-behavior recommendation"}
                    </p>
                    <p className="body-copy">Validation: {result.cf.validation.top_5_all_inside_candidate_pool ? "inside shared pool" : "outside shared pool"}</p>
                    <div className="tag-row">
                      {recommendation.product_group ? (
                        <span className="tag subdued-tag">{recommendation.product_group}</span>
                      ) : null}
                      {recommendation.colour ? (
                        <span className="tag subdued-tag">{recommendation.colour}</span>
                      ) : null}
                      {recommendation.appearance ? (
                        <span className="tag subdued-tag">{recommendation.appearance}</span>
                      ) : null}
                    </div>
                  </article>
                );
              })}
            </div>
          </article>

          <article className="panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">Agentic AI</span>
                <h3>3-Agent Top 5</h3>
              </div>
            </div>
            <div className="stack-list">
              {result.agentic.recommendations.map((item, index) => {
                const recommendation = item as {
                  article_id: string;
                  product_type_name?: string;
                  product_group_name?: string;
                  colour_group_name?: string;
                  graphical_appearance_name?: string;
                  recommendation_reason?: string;
                  match_score?: number;
                };

                return (
                  <article key={recommendation.article_id} className="list-card">
                    <div className="candidate-head">
                      <div>
                        <div className="meta-label">Rank #{index + 1}</div>
                        <h4>
                          {(recommendation.product_type_name ?? "Product")} · {recommendation.article_id}
                        </h4>
                      </div>
                      <div className="match-pill">Score {recommendation.match_score ?? 0}</div>
                    </div>
                    <p className="body-copy">
                      {recommendation.recommendation_reason ?? "Agentic ranking explanation"}
                    </p>
                    <p className="body-copy">Validation: {result.agentic.validation.top_5_all_inside_candidate_pool ? "inside shared pool" : "outside shared pool"}</p>
                    <div className="tag-row">
                      {recommendation.product_group_name ? (
                        <span className="tag subdued-tag">{recommendation.product_group_name}</span>
                      ) : null}
                      {recommendation.colour_group_name ? (
                        <span className="tag subdued-tag">{recommendation.colour_group_name}</span>
                      ) : null}
                      {recommendation.graphical_appearance_name ? (
                        <span className="tag subdued-tag">
                          {recommendation.graphical_appearance_name}
                        </span>
                      ) : null}
                    </div>
                  </article>
                );
              })}
            </div>
          </article>
        </section>
      ) : null}
    </div>
  );
}
