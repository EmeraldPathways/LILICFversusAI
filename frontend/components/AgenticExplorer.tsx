"use client";

import { useEffect, useState } from "react";

import {
  type AgenticRunResponse,
  type EvaluationDebugResponse,
  type ExperimentSetup,
  type FinalRecommendationItem,
  type TrainingHistoryItem,
  type WeightedPreferenceItem,
  getEvaluationDebug,
  runAgenticRecommendations,
} from "@/lib/api";
import { EvaluationDebugPanel } from "@/components/EvaluationDebugPanel";
import {
  readPersistedAgenticResult,
  readSelectedUserId,
  writePersistedAgenticResult,
  writeSelectedUserId,
} from "@/lib/persistedState";

type AgenticExplorerProps = {
  setup: ExperimentSetup | null;
  userIds: string[];
};

function percent(weight: number) {
  return `${Math.round(weight * 100)}%`;
}

function PreferenceList({
  title,
  items,
}: {
  title: string;
  items: WeightedPreferenceItem[];
}) {
  return (
    <article className="panel preference-chart">
      <h3>{title}</h3>
      <div className="meter-list">
        {items.map((item) => (
          <div key={item.value} className="meter-row">
            <div className="meter-label">
              <span>{item.value}</span>
              <span>{percent(item.weight)}</span>
            </div>
            <div className="meter-track">
              <div className="meter-fill" style={{ width: `${Math.max(item.weight * 100, 6)}%` }} />
            </div>
          </div>
        ))}
      </div>
    </article>
  );
}

function HistoryPreview({ items }: { items: TrainingHistoryItem[] }) {
  return (
    <div className="history-grid">
      {items.map((item) => (
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
  );
}

function DecisionCard({ item }: { item: FinalRecommendationItem }) {
  return (
    <article className="candidate-card recommendation-card">
      <img src={item.image_url} alt={item.article_id} />
      <div className="candidate-body">
        <div className="candidate-head">
          <div>
            <div className="meta-label">Rank #{item.rank}</div>
            <h4>{item.product_type_name}</h4>
          </div>
          <div className="score-pill">
            <span>Match Score</span>
            <strong>{item.match_score}</strong>
          </div>
        </div>
        <p className="body-copy recommendation-code">{item.article_id}</p>
        <dl className="detail-grid">
          <div>
            <dt>Group</dt>
            <dd>{item.product_group_name}</dd>
          </div>
          <div>
            <dt>Colour</dt>
            <dd>{item.colour_group_name}</dd>
          </div>
          <div>
            <dt>Appearance</dt>
            <dd>{item.graphical_appearance_name}</dd>
          </div>
          <div>
            <dt>Constraint Status</dt>
            <dd>{item.constraint_status}</dd>
          </div>
        </dl>
        <div className="tag-row">
          {item.matched_evidence.map((entry) => (
            <span key={entry} className="tag subdued-tag">
              {entry}
            </span>
          ))}
        </div>
        <p className="body-copy">{item.recommendation_reason}</p>
      </div>
    </article>
  );
}

export function AgenticExplorer({ setup, userIds }: AgenticExplorerProps) {
  const [selectedUserId, setSelectedUserId] = useState(userIds[0] ?? "");
  const [userRequest, setUserRequest] = useState("");
  const [result, setResult] = useState<AgenticRunResponse | null>(null);
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

    const storedResult = readPersistedAgenticResult();
    if (storedResult && userIds.includes(storedResult.customer_id)) {
      setSelectedUserId(storedResult.customer_id);
      setResult(storedResult);
      setUserRequest(storedResult.user_request);
    }
  }, [userIds]);

  useEffect(() => {
    if (selectedUserId) {
      writeSelectedUserId(selectedUserId);
    }
  }, [selectedUserId]);

  useEffect(() => {
    if (result && result.customer_id !== selectedUserId) {
      const storedResult = readPersistedAgenticResult();
      if (storedResult?.customer_id === selectedUserId) {
        setResult(storedResult);
        setUserRequest(storedResult.user_request);
        return;
      }

      setResult(null);
      setUserRequest("");
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

  async function handleRun() {
    if (!selectedUserId) {
      setError("No evaluated user is available yet. Run the backend experiment first.");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const response = await runAgenticRecommendations(selectedUserId, userRequest);
      setResult(response);
      writePersistedAgenticResult(response);
      writeSelectedUserId(selectedUserId);
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "Unable to run the agentic workflow.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="page-stack">
      <section className="hero-panel">
        <div className="hero-copy">
          <span className="eyebrow">Agentic AI</span>
          <h2>3-Agent Fashion Recommendation Demo</h2>
          <p>
            Preference Agent extracts soft preferences from real H&amp;M purchase history, Evidence
            Agent builds catalog evidence, and Decision Agent applies explicit constraints and ranks
            the final Top 5.
          </p>
          <div className="summary-strip">
            <div className="summary-chip">
              <span>Dataset</span>
              <strong>{setup?.dataset ?? "Awaiting backend"}</strong>
            </div>
            <div className="summary-chip">
              <span>Split</span>
              <strong>{setup?.split_method ?? "Leave-one-out"}</strong>
            </div>
            <div className="summary-chip">
              <span>Evaluated Users</span>
              <strong>{setup?.summary?.evaluated_users ?? 0}</strong>
            </div>
          </div>
        </div>

        <div className="hero-side">
          <label className="field">
            <span>Real H&amp;M User</span>
            <select value={selectedUserId} onChange={(event) => setSelectedUserId(event.target.value)}>
              {userIds.map((userId) => (
                <option key={userId} value={userId}>
                  {userId}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Current User Request</span>
            <input
              value={userRequest}
              onChange={(event) => setUserRequest(event.target.value)}
              placeholder='Optional: "I only want black dresses"'
            />
          </label>
          <button className="primary-button" onClick={handleRun} disabled={isLoading}>
            {isLoading ? "Running Agents..." : "Run 3-Agent Recommendation"}
          </button>
        </div>
      </section>

      <section className="agent-strip">
        <article className="agent-card cyan">
          <span>1. Preference Agent</span>
          <p>Analyze transaction history and produce a weighted soft-preference profile.</p>
        </article>
        <article className="agent-card emerald">
          <span>2. Evidence Agent</span>
          <p>Retrieve product candidates from real article metadata and expose matched evidence.</p>
        </article>
        <article className="agent-card violet">
          <span>3. Decision Agent</span>
          <p>Apply explicit hard constraints, score each candidate, and return the Top 5.</p>
        </article>
      </section>

      {error ? <div className="error-banner">{error}</div> : null}

      <section className="panel">
        <div className="panel-header">
          <div>
            <span className="eyebrow">Evaluation Context</span>
            <h3>Leave-One-Out Next-Item Test</h3>
          </div>
          {result ? (
            <div className={result.hit_at_5 ? "hit-badge hit" : "hit-badge miss"}>
              Agentic Hit@5: {result.hit_at_5 ? "Hit" : "Miss"}
            </div>
          ) : null}
        </div>
        <p className="body-copy">
          The last purchase is the ground-truth next item, and all earlier purchases are used as
          training history. The workflow is evaluated on whether the real next item appears in the
          returned Top 5.
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
            <span className="eyebrow cyan-text">Preference Agent</span>
            <h3>User Preference Profile</h3>
          </div>
          {result ? <div className="stat-box">{result.training_history_count}</div> : null}
        </div>
        {result ? (
          <>
            <p className="body-copy">{result.preference_profile.preference_summary}</p>
            <div className="tag-row">
              {result.preference_profile.soft_preferences.map((item) => (
                <span key={item} className="tag info-tag">
                  {item}
                </span>
              ))}
              {Object.entries(result.preference_profile.hard_constraints).length === 0 ? (
                <span className="tag neutral-tag">No hard constraints detected</span>
              ) : (
                Object.entries(result.preference_profile.hard_constraints).map(([key, value]) => (
                  <span key={key} className="tag warning-tag">
                    {key}: {value}
                  </span>
                ))
              )}
            </div>
            <HistoryPreview items={result.training_history_preview} />
            <div className="preference-grid">
              <PreferenceList
                title="Preferred Product Types"
                items={result.preference_profile.preferred_product_type_name_values}
              />
              <PreferenceList
                title="Preferred Product Groups"
                items={result.preference_profile.preferred_product_group_name_values}
              />
              <PreferenceList
                title="Preferred Colours"
                items={result.preference_profile.preferred_colour_group_name_values}
              />
              <PreferenceList
                title="Preferred Appearances"
                items={result.preference_profile.preferred_graphical_appearance_name_values}
              />
            </div>
          </>
        ) : (
          <p className="empty-state">Run the workflow to generate the Preference Agent output.</p>
        )}
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <span className="eyebrow emerald-text">Evidence Agent</span>
            <h3>Candidate Evidence Set</h3>
          </div>
        </div>
        {result ? (
          <div className="candidate-grid">
            {result.candidate_evidence_set.map((candidate) => (
              <article key={candidate.article_id} className="candidate-card">
                <img src={candidate.image_url} alt={candidate.article_id} />
                <div className="candidate-body">
                  <div className="candidate-head">
                    <div>
                      <div className="meta-label">{candidate.article_id}</div>
                      <h4>{candidate.product_type_name}</h4>
                    </div>
                    <div className="match-pill">{candidate.match_count} matches</div>
                  </div>
                  <p className="body-copy">{candidate.product_description}</p>
                  <dl className="detail-grid">
                    <div>
                      <dt>Group</dt>
                      <dd>{candidate.product_group_name}</dd>
                    </div>
                    <div>
                      <dt>Colour</dt>
                      <dd>{candidate.colour_group_name}</dd>
                    </div>
                    <div>
                      <dt>Appearance</dt>
                      <dd>{candidate.graphical_appearance_name}</dd>
                    </div>
                  </dl>
                  <div className="tag-row">
                    {candidate.matched_preference_fields.map((entry) => (
                      <span key={entry} className="tag subdued-tag">
                        {entry}
                      </span>
                    ))}
                  </div>
                  <p className="body-copy">{candidate.evidence_summary}</p>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <p className="empty-state">Run the workflow to generate the Evidence Agent candidate set.</p>
        )}
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <span className="eyebrow violet-text">Decision Agent</span>
            <h3>Final Recommendations</h3>
          </div>
        </div>
        {result ? (
          <div className="decision-grid">
            {result.top_5_recommendations.map((item) => (
              <DecisionCard key={item.article_id} item={item} />
            ))}
          </div>
        ) : (
          <p className="empty-state">Run the workflow to generate Decision Agent recommendations.</p>
        )}
      </section>
    </div>
  );
}
