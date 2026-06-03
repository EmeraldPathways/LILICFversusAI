"use client";

import { useEffect, useState } from "react";

import {
  type CFRecommendationResponse,
  type EvaluationDebugResponse,
  type ExperimentSetup,
  getEvaluationDebug,
  getCFRecommendations,
} from "@/lib/api";
import { EvaluationDebugPanel } from "@/components/EvaluationDebugPanel";
import {
  readPersistedCFResult,
  readSelectedUserId,
  writePersistedCFResult,
  writeSelectedUserId,
} from "@/lib/persistedState";

type CFExplorerProps = {
  setup: ExperimentSetup | null;
  userIds: string[];
};

export function CFExplorer({ setup, userIds }: CFExplorerProps) {
  const [selectedUserId, setSelectedUserId] = useState(userIds[0] ?? "");
  const [result, setResult] = useState<CFRecommendationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [debug, setDebug] = useState<EvaluationDebugResponse | null>(null);
  const [debugError, setDebugError] = useState<string | null>(null);
  const [isDebugLoading, setIsDebugLoading] = useState(false);

  useEffect(() => {
    const storedUserId = readSelectedUserId();
    if (storedUserId && userIds.includes(storedUserId)) {
      setSelectedUserId(storedUserId);
    }

    const storedResult = readPersistedCFResult();
    if (storedResult && userIds.includes(storedResult.customer_id)) {
      setSelectedUserId(storedResult.customer_id);
      setResult(storedResult);
    }
  }, [userIds]);

  useEffect(() => {
    if (selectedUserId) {
      writeSelectedUserId(selectedUserId);
    }
  }, [selectedUserId]);

  useEffect(() => {
    if (result && result.customer_id !== selectedUserId) {
      const storedResult = readPersistedCFResult();
      if (storedResult?.customer_id === selectedUserId) {
        setResult(storedResult);
        return;
      }

      setResult(null);
    }
  }, [result, selectedUserId]);

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

  async function handleLoad() {
    if (!selectedUserId) {
      setError("No evaluated user is available yet. Run the backend experiment first.");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const response = await getCFRecommendations(selectedUserId);
      setResult(response);
      writePersistedCFResult(response);
      writeSelectedUserId(selectedUserId);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load CF recommendations.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="page-stack">
      <section className="hero-panel compact">
        <div className="hero-copy">
          <span className="eyebrow">CF Baseline</span>
          <h2>Collaborative Filtering Top 5</h2>
          <p>
            This baseline uses transaction behavior only. It does not inspect article descriptions,
            explanations, or explicit user request constraints.
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
          <button className="primary-button" onClick={handleLoad} disabled={isLoading}>
            {isLoading ? "Loading CF..." : "Load CF Recommendations"}
          </button>
          <div className="summary-chip">
            <span>Evaluated Users</span>
            <strong>{setup?.summary?.evaluated_users ?? 0}</strong>
          </div>
        </div>
      </section>

      {error ? <div className="error-banner">{error}</div> : null}

      <section className="panel">
        <div className="panel-header">
          <div>
            <span className="eyebrow">Protocol</span>
            <h3>Leave-One-Out Evaluation</h3>
          </div>
          {result ? (
            <div className={result.hit_at_5 ? "hit-badge hit" : "hit-badge miss"}>
              CF Hit@5: {result.hit_at_5 ? "Hit" : "Miss"}
            </div>
          ) : null}
        </div>
        <p className="body-copy">
          For each user, earlier purchases form the training history and the final purchase is the
          held-out next item. The baseline succeeds only if the held-out item appears in the Top 5.
        </p>
        {result ? (
          <div className="evaluation-grid">
            <div className="summary-chip">
              <span>Ground Truth</span>
              <strong>{result.ground_truth_article_id}</strong>
            </div>
            <div className="summary-chip">
              <span>Training History</span>
              <strong>{result.training_history_count} purchases</strong>
            </div>
          </div>
        ) : null}
        {result ? <p className="body-copy">{result.explanation}</p> : null}
      </section>

      <EvaluationDebugPanel debug={debug} error={debugError} isLoading={isDebugLoading} />

      <section className="panel">
        <div className="panel-header">
          <div>
            <span className="eyebrow">Training History</span>
            <h3>Observed Purchases</h3>
          </div>
        </div>
        {result ? (
          <div className="history-grid">
            {result.training_history_preview.map((item) => (
              <article key={`${item.article_id}-${item.transaction_date}`} className="history-card">
                <div className="history-date">{item.transaction_date}</div>
                <strong>{item.product_name}</strong>
                <p>
                  {item.product_type} · {item.product_group}
                </p>
                <p>
                  {item.colour} · {item.appearance}
                </p>
              </article>
            ))}
          </div>
        ) : (
          <p className="empty-state">Load a user to inspect the CF training history.</p>
        )}
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <span className="eyebrow">CF Output</span>
            <h3>Top 5 Recommendations</h3>
          </div>
        </div>
        {result ? (
          <div className="candidate-grid">
            {result.top_5_recommendations.map((item, index) => (
              <article key={item.article_id} className="candidate-card simple-card">
                <div className="candidate-body">
                  <div className="candidate-head">
                    <div>
                      <div className="meta-label">Rank #{index + 1}</div>
                      <h4>
                        {item.product_type} · {item.article_id}
                      </h4>
                    </div>
                    <div className="match-pill">Score {item.score}</div>
                  </div>
                  <dl className="detail-grid">
                    <div>
                      <dt>Group</dt>
                      <dd>{item.product_group}</dd>
                    </div>
                    <div>
                      <dt>Colour</dt>
                      <dd>{item.colour}</dd>
                    </div>
                    <div>
                      <dt>Appearance</dt>
                      <dd>{item.appearance}</dd>
                    </div>
                  </dl>
                  <p className="body-copy">{item.product_name}</p>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <p className="empty-state">Load a user to inspect the CF Top 5.</p>
        )}
      </section>
    </div>
  );
}
