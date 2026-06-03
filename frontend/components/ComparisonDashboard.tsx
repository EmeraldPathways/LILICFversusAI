"use client";

import { useState } from "react";

import {
  type ComparisonResponse,
  type ExperimentSetup,
  getComparison,
} from "@/lib/api";

type ComparisonDashboardProps = {
  setup: ExperimentSetup | null;
  userIds: string[];
};

export function ComparisonDashboard({ setup, userIds }: ComparisonDashboardProps) {
  const [selectedUserId, setSelectedUserId] = useState(userIds[0] ?? "");
  const [result, setResult] = useState<ComparisonResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleCompare() {
    if (!selectedUserId) {
      setError("No evaluated user is available yet. Run the backend experiment first.");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      setResult(await getComparison(selectedUserId));
    } catch (compareError) {
      setError(compareError instanceof Error ? compareError.message : "Unable to load the comparison.");
    } finally {
      setIsLoading(false);
    }
  }

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
              CF: {result.cf.hit_at_5 ? "Hit" : "Miss"}
            </div>
            <div className={result.agentic.hit_at_5 ? "hit-badge hit" : "hit-badge miss"}>
              Agentic: {result.agentic.hit_at_5 ? "Hit" : "Miss"}
            </div>
          </div>
        ) : (
          <p className="empty-state">Run the comparison to inspect both Top 5 lists side by side.</p>
        )}
      </section>

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
