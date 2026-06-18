"use client";

import { useEffect, useState } from "react";

import { MetricCard } from "@/components/MetricCard";
import type {
  ArtifactDemoMethodItem,
  ArtifactDemoWorkflowCase,
  ExplainabilityPageResponse,
} from "@/lib/api";

type ArtifactDemoTabsProps = {
  explainability: ExplainabilityPageResponse | null;
  workflowCases: ArtifactDemoWorkflowCase[];
};

type TabId =
  | "system-workflow"
  | "user-walkthrough"
  | "experiment-results"
  | "explainability-evidence"
  | "technical-validation";

const tabs: Array<{ id: TabId; label: string }> = [
  { id: "system-workflow", label: "System Workflow" },
  { id: "user-walkthrough", label: "User Walkthrough" },
  { id: "experiment-results", label: "Experiment Results" },
  { id: "explainability-evidence", label: "Explainability Evidence" },
  { id: "technical-validation", label: "Technical Validation" },
];

const experimentRuns = [
  {
    label: "Run 1",
    description: "Previous 1,000-user formal ranking run.",
    metrics: [
      { method: "SVD Matrix Factorisation", hitRate: 0.5, ndcg: 0.295493, ild: 0.751933 },
      { method: "Standalone 3-Agent", hitRate: 0.274, ndcg: 0.155365, ild: 0.5438 },
      { method: "Hybrid SVD + 3-Agent", hitRate: 0.498, ndcg: 0.304552, ild: 0.694481 },
    ],
  },
  {
    label: "Seed99 Robustness Run",
    description: "Second independent 1,000-user run using saved seed99 artifacts.",
    metrics: [
      { method: "SVD Matrix Factorisation", hitRate: 0.505, ndcg: 0.296245, ild: 0.755089 },
      { method: "Standalone 3-Agent", hitRate: 0.269, ndcg: 0.154352, ild: 0.539319 },
      { method: "Hybrid SVD + 3-Agent", hitRate: 0.526, ndcg: 0.312443, ild: 0.692919 },
    ],
  },
];

const experimentInterpretations = [
  "SVD remains the strong formal behavioural baseline.",
  "Standalone 3-Agent remains the comparison and ablation method rather than the final artifact.",
  "Hybrid consistently outperforms Standalone 3-Agent on ranking quality.",
  "Hybrid remains competitive with SVD on ranking quality, but that does not justify replacement claims.",
  "Hybrid reduces intra-list diversity compared with SVD, so the diversity trade-off must remain explicit.",
];

const technicalChecks = [
  "Explainability-specific backend tests: 4 passed",
  "Full backend tests: 34 passed",
  "100-user explainability performance check completed successfully",
  "Full 1,000-user explainability audit completed successfully in about 252.8 seconds",
  "This demo uses saved offline artifacts and does not rerun recommendations",
  "Formal seed99 source artifacts remained unchanged during explainability work",
  "SVD logic, Standalone 3-Agent logic, Hybrid reranking logic, hybrid formula, and ranking metrics were not modified",
];

const artifactPaths = [
  "backend/app/data/processed/explainability/seed99_full_retry_explainability_summary.json",
  "backend/app/data/processed/explainability/seed99_full_retry_explainability_audit.json",
  "backend/app/data/processed/explainability/seed99_full_retry_explainability_examples.csv",
  "backend/app/data/processed/explainability/seed99_full_retry_rank_shift_analysis.csv",
  "backend/app/data/processed/explainability/seed99_full_retry_case_studies.md",
];

const nonClaims = [
  "No CTR claims",
  "No CVR claims",
  "No conversion claims",
  "No live customer engagement claims",
  "No add-to-cart claims",
  "No dwell-time claims",
  "No live feedback-adaptation claims",
];

function formatNumber(value: unknown, digits = 3) {
  if (typeof value !== "number") {
    return "n/a";
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(digits);
}

function formatRate(value: number | undefined) {
  return value === undefined ? "n/a" : value.toFixed(4);
}

function formatList(value: unknown) {
  if (!Array.isArray(value) || value.length === 0) {
    return "n/a";
  }
  return value.map(String).join(", ");
}

function compactMethodLabel(label: string) {
  if (label.includes("Matrix")) return "SVD Baseline";
  if (label.includes("Standalone")) return "Standalone 3-Agent";
  return "Hybrid";
}

function renderRecommendationRows(items: ArtifactDemoMethodItem[]) {
  if (!items.length) {
    return (
      <tr>
        <td colSpan={5} className="muted">
          Saved recommendations unavailable.
        </td>
      </tr>
    );
  }

  return items.map((item) => (
    <tr key={`${item.article_id}-${item.rank ?? 0}`}>
      <td>
        <strong>{item.article_id}</strong>
        {item.is_ground_truth ? <span className="artifact-hit">Ground Truth Hit</span> : null}
      </td>
      <td>{item.rank ?? "n/a"}</td>
      <td>{item.product_type_name ?? "n/a"}</td>
      <td>{formatNumber(item.score)}</td>
      <td>{item.reason ?? item.product_group_name ?? "n/a"}</td>
    </tr>
  ));
}

export function ArtifactDemoTabs({ explainability, workflowCases }: ArtifactDemoTabsProps) {
  const [activeTab, setActiveTab] = useState<TabId>("system-workflow");
  const [pendingCaseId, setPendingCaseId] = useState(workflowCases[0]?.customer_id ?? "");
  const [selectedCaseId, setSelectedCaseId] = useState(workflowCases[0]?.customer_id ?? "");

  useEffect(() => {
    if (!workflowCases.length) {
      setPendingCaseId("");
      setSelectedCaseId("");
      return;
    }
    setPendingCaseId((current) => current || workflowCases[0].customer_id);
    setSelectedCaseId((current) => current || workflowCases[0].customer_id);
  }, [workflowCases]);

  const selectedCase =
    workflowCases.find((item) => item.customer_id === selectedCaseId) ?? workflowCases[0] ?? null;
  const explainabilityMetrics = explainability?.summary.summary_metrics;

  return (
    <div className="stack">
      <section className="card artifact-intro">
        <span className="eyebrow">Supervisor-Facing Artifact</span>
        <h2 className="section-title">Hybrid SVD + 3-Agent Recommendation Demo</h2>
        <p className="muted">
          This route presents the final dissertation artifact as a saved offline demonstration of
          the Hybrid SVD + 3-Agent recommender on the H&amp;M dataset.
        </p>
        <div className="artifact-tabbar" role="tablist" aria-label="Artifact demo sections">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.id}
              className={activeTab === tab.id ? "artifact-tab artifact-tab-active" : "artifact-tab"}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </section>

      {activeTab === "system-workflow" ? (
        <div className="stack">
          <section className="card artifact-hero">
            <span className="eyebrow">What Was Built</span>
            <h3 className="artifact-title">Hybrid SVD + 3-Agent Recommendation Workflow</h3>
            <p className="muted">
              This artifact demonstrates a Hybrid SVD + 3-Agent recommendation workflow using the
              H&amp;M dataset. SVD provides behavioural recommendation signals, the 3-Agent layer
              provides preference and item evidence, and the Hybrid reranker combines these signals
              to produce explainable Top-10 recommendations.
            </p>
          </section>

          <section className="artifact-workflow">
            <article className="card artifact-flow-card">
              <span className="eyebrow">Behavioural Branch</span>
              <div className="artifact-flow-node">User Purchase History</div>
              <div className="artifact-flow-arrow">↓</div>
              <div className="artifact-flow-node">SVD Baseline</div>
              <div className="artifact-flow-arrow">↓</div>
              <div className="artifact-flow-node artifact-flow-node-accent">SVD Score</div>
            </article>
            <article className="card artifact-flow-card artifact-flow-card-strong">
              <span className="eyebrow">Agentic Branch</span>
              <div className="artifact-flow-node">User Purchase History + Candidate Item Metadata</div>
              <div className="artifact-flow-arrow">↓</div>
              <div className="artifact-flow-branch">
                <div className="artifact-flow-mini">Preference Agent</div>
                <div className="artifact-flow-mini">Evidence / Item Agent</div>
                <div className="artifact-flow-mini">Decision Agent</div>
              </div>
              <div className="artifact-flow-arrow">↓</div>
              <div className="artifact-flow-node artifact-flow-node-accent">Agentic Score + Evidence</div>
            </article>
            <article className="card artifact-flow-card">
              <span className="eyebrow">Final Artifact</span>
              <div className="artifact-flow-node">SVD Score + Agentic Score + Diversity Bonus</div>
              <div className="artifact-flow-arrow">↓</div>
              <div className="artifact-flow-node">Hybrid SVD + 3-Agent Reranker</div>
              <div className="artifact-flow-arrow">↓</div>
              <div className="artifact-flow-node artifact-flow-node-final">
                Explainable Top-10 Recommendations
              </div>
            </article>
          </section>

          <section className="grid three">
            <article className="card">
              <span className="eyebrow">Method Role</span>
              <strong>SVD Matrix Factorisation</strong>
              <p className="muted">
                Formal collaborative filtering baseline and the main behavioural signal.
              </p>
            </article>
            <article className="card">
              <span className="eyebrow">Method Role</span>
              <strong>Standalone 3-Agent</strong>
              <p className="muted">
                Agentic comparison and ablation method using Preference, Evidence, and Decision
                agents.
              </p>
            </article>
            <article className="card">
              <span className="eyebrow">Method Role</span>
              <strong>Hybrid SVD + 3-Agent</strong>
              <p className="muted">
                Final artifact method combining SVD score, agentic score, and diversity bonus.
              </p>
            </article>
          </section>

          <section className="grid three">
            <article className="card artifact-agent-card">
              <span className="eyebrow">Preference Agent</span>
              <p className="muted">
                Extracts user preference signals from historical training items.
              </p>
            </article>
            <article className="card artifact-agent-card">
              <span className="eyebrow">Evidence / Item Agent</span>
              <p className="muted">
                Retrieves candidate-item metadata evidence from the saved candidate pool.
              </p>
            </article>
            <article className="card artifact-agent-card">
              <span className="eyebrow">Decision Agent</span>
              <p className="muted">
                Ranks candidate items using preference and evidence signals, contributing to the
                agentic score.
              </p>
            </article>
          </section>

          <section className="grid two">
            <article className="card artifact-formula-card">
              <span className="eyebrow">Hybrid Formula</span>
              <pre className="trace-pre artifact-formula">
{`hybrid_score =
0.70 * normalized_svd_score +
0.25 * normalized_agentic_score +
0.05 * diversity_bonus`}
              </pre>
            </article>
            <article className="card">
              <span className="eyebrow">Limitation</span>
              <p className="muted">
                Hybrid is an augmentation and explainability layer over SVD, not a full
                replacement.
              </p>
            </article>
          </section>
        </div>
      ) : null}

      {activeTab === "user-walkthrough" ? (
        <div className="stack">
          <section className="card">
            <span className="eyebrow">Guided Walkthrough</span>
            <h3 className="section-title">One Saved User Through the Hybrid Workflow</h3>
            <p className="muted">
              These selected users show how the final artifact operates at user level. Quantitative
              evidence remains in the full 1,000-user experiment and explainability tabs.
            </p>
          </section>

          <section className="card artifact-controlbar">
            <label className="artifact-control">
              <span className="eyebrow">Demo User</span>
              <select
                value={pendingCaseId}
                onChange={(event) => setPendingCaseId(event.target.value)}
                disabled={!workflowCases.length}
              >
                {workflowCases.map((item) => (
                  <option key={item.customer_id} value={item.customer_id}>
                    {item.label} · {item.customer_id_short}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className="artifact-load-button"
              disabled={!pendingCaseId}
              onClick={() => setSelectedCaseId(pendingCaseId)}
            >
              Load Saved Walkthrough
            </button>
          </section>

          {!selectedCase ? (
            <section className="card muted">
              Saved walkthrough cases are unavailable. Ensure the formal artifact files exist first.
            </section>
          ) : (
            <>
              <section className="grid two">
                <article className="card">
                  <span className="eyebrow">Selected Case</span>
                  <h3 className="section-title">{selectedCase.label}</h3>
                  <p className="muted">
                    Category: {selectedCase.category}
                    <br />
                    Customer ID: {selectedCase.customer_id}
                    <br />
                    Candidate Pool Size: {selectedCase.candidate_pool_size}
                  </p>
                </article>
                <article className="card">
                  <span className="eyebrow">Held-Out Ground Truth</span>
                  <p className="muted">
                    Article: {String(selectedCase.ground_truth.article_id ?? "n/a")}
                    <br />
                    Product Type: {String(selectedCase.ground_truth.product_type_name ?? "n/a")}
                    <br />
                    Product Group: {String(selectedCase.ground_truth.product_group_name ?? "n/a")}
                    <br />
                    Colour: {String(selectedCase.ground_truth.colour_group_name ?? "n/a")}
                  </p>
                </article>
              </section>

              <section className="artifact-agent-panels">
                <article className="card artifact-agent-panel">
                  <span className="eyebrow">Preference Agent</span>
                  <h4>Saved user preference profile</h4>
                  <p className="muted">
                    Intent: {String(selectedCase.preference_agent.inferred_intent ?? "n/a")}
                  </p>
                  <div className="artifact-pill-row">
                    <span className="pill">
                      Categories: {formatList(selectedCase.preference_agent.preferred_categories)}
                    </span>
                    <span className="pill">
                      Types: {formatList(selectedCase.preference_agent.preferred_product_types)}
                    </span>
                    <span className="pill">
                      Colours: {formatList(selectedCase.preference_agent.preferred_colours)}
                    </span>
                  </div>
                </article>
                <article className="card artifact-agent-panel artifact-agent-panel-strong">
                  <span className="eyebrow">Evidence / Item Agent</span>
                  <h4>Saved evidence used for ranking</h4>
                  <p className="muted">{String(selectedCase.evidence_agent.headline ?? "n/a")}</p>
                  <div className="artifact-pill-row">
                    {Array.isArray(selectedCase.evidence_agent.matched_evidence) &&
                    selectedCase.evidence_agent.matched_evidence.length ? (
                      selectedCase.evidence_agent.matched_evidence.map((item) => (
                        <span className="pill" key={String(item)}>
                          {String(item)}
                        </span>
                      ))
                    ) : (
                      <span className="pill">No explicit matched evidence saved</span>
                    )}
                  </div>
                </article>
                <article className="card artifact-agent-panel">
                  <span className="eyebrow">Decision Agent</span>
                  <h4>Final saved ranking decision</h4>
                  <p className="muted">{String(selectedCase.decision_agent.headline ?? "n/a")}</p>
                  <p className="muted">
                    Selected Article: {String(selectedCase.decision_agent.selected_article_id ?? "n/a")}
                    <br />
                    Selected Rank: {String(selectedCase.decision_agent.selected_rank ?? "n/a")}
                    <br />
                    Hybrid Score: {formatNumber(selectedCase.decision_agent.selected_score)}
                  </p>
                </article>
              </section>

              <section className="grid two">
                <article className="card">
                  <span className="eyebrow">Training History Summary</span>
                  <p className="muted">
                    Interactions: {String(selectedCase.training_history_summary.interaction_count ?? "n/a")}
                    <br />
                    Preview IDs: {formatList(selectedCase.training_history_summary.article_ids_preview)}
                    <br />
                    Top Product Types: {formatList(selectedCase.training_history_summary.top_product_types)}
                    <br />
                    Top Product Groups: {formatList(selectedCase.training_history_summary.top_product_groups)}
                  </p>
                </article>
                <article className="card">
                  <span className="eyebrow">Hybrid Explanation</span>
                  <p className="muted">
                    {String(selectedCase.hybrid_selected_explanation.explanation_text ?? "No saved explanation text.")}
                  </p>
                  <p className="muted">
                    Rank Shift: {String(selectedCase.rank_shift ?? "n/a")}
                    <br />
                    Hybrid Rank: {String(selectedCase.hybrid_selected_explanation.hybrid_rank ?? "n/a")}
                    <br />
                    SVD Rank: {String(selectedCase.hybrid_selected_explanation.svd_rank ?? "n/a")}
                  </p>
                </article>
              </section>

              <section className="grid three">
                <MetricCard
                  label="Normalized SVD Score"
                  value={formatNumber(selectedCase.hybrid_score_components.normalized_svd_score)}
                />
                <MetricCard
                  label="Normalized Agentic Score"
                  value={formatNumber(selectedCase.hybrid_score_components.normalized_agentic_score)}
                />
                <MetricCard
                  label="Hybrid Score"
                  value={formatNumber(selectedCase.hybrid_score_components.hybrid_score)}
                  detail={`Diversity bonus: ${formatNumber(selectedCase.hybrid_score_components.diversity_bonus)}`}
                />
              </section>

              <section className="grid three">
                <article className="card">
                  <span className="eyebrow">SVD Baseline Top-10</span>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Article</th>
                          <th>Rank</th>
                          <th>Type</th>
                          <th>Score</th>
                          <th>Context</th>
                        </tr>
                      </thead>
                      <tbody>{renderRecommendationRows(selectedCase.svd_top10)}</tbody>
                    </table>
                  </div>
                </article>
                <article className="card">
                  <span className="eyebrow">Standalone 3-Agent Top-10</span>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Article</th>
                          <th>Rank</th>
                          <th>Type</th>
                          <th>Score</th>
                          <th>Reason</th>
                        </tr>
                      </thead>
                      <tbody>{renderRecommendationRows(selectedCase.agentic_top10)}</tbody>
                    </table>
                  </div>
                </article>
                <article className="card">
                  <span className="eyebrow">Hybrid Top-10</span>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Article</th>
                          <th>Rank</th>
                          <th>Type</th>
                          <th>Score</th>
                          <th>Reason</th>
                        </tr>
                      </thead>
                      <tbody>{renderRecommendationRows(selectedCase.hybrid_top10)}</tbody>
                    </table>
                  </div>
                </article>
              </section>
            </>
          )}
        </div>
      ) : null}

      {activeTab === "experiment-results" ? (
        <div className="stack">
          <section className="card">
            <span className="eyebrow">Formal Ranking Evidence</span>
            <h3 className="section-title">Two Saved 1,000-User Offline Runs</h3>
            <p className="muted">
              Global ranking metrics are isolated here. These are offline leave-one-out Top-10
              results, not live customer engagement or conversion outcomes.
            </p>
          </section>

          {experimentRuns.map((run) => (
            <section className="card" key={run.label}>
              <span className="eyebrow">{run.label}</span>
              <p className="muted">{run.description}</p>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Method</th>
                      <th>HitRate@10</th>
                      <th>NDCG@10</th>
                      <th>ILD@10</th>
                    </tr>
                  </thead>
                  <tbody>
                    {run.metrics.map((metric) => (
                      <tr key={`${run.label}-${metric.method}`}>
                        <td>{metric.method}</td>
                        <td>{metric.hitRate.toFixed(6)}</td>
                        <td>{metric.ndcg.toFixed(6)}</td>
                        <td>{metric.ild.toFixed(6)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ))}

          <section className="grid two">
            {experimentInterpretations.map((item) => (
              <article className="card" key={item}>
                <span className="eyebrow">Interpretation</span>
                <p className="muted">{item}</p>
              </article>
            ))}
          </section>
        </div>
      ) : null}

      {activeTab === "explainability-evidence" ? (
        <div className="stack">
          {!explainability || !explainabilityMetrics ? (
            <section className="card muted">
              Explainability evidence is unavailable. Run the saved audit path first.
            </section>
          ) : (
            <>
              <section className="card">
                <span className="eyebrow">Seed99 Explainability Audit</span>
                <h3 className="section-title">Offline Evidence Coverage at 1,000 Users</h3>
                <p className="muted">{explainability.summary.interpretation.safe_claim}</p>
              </section>

              <section className="grid three">
                <MetricCard
                  label="Users Included"
                  value={String(explainability.summary.run_context.users_included)}
                />
                <MetricCard
                  label="Recommendations Explained"
                  value={String(explainability.summary.run_context.recommendations_explained)}
                />
                <MetricCard
                  label="Evidence Coverage"
                  value={formatRate(explainabilityMetrics.evidence_coverage_rate)}
                />
                <MetricCard
                  label="Preference Trace"
                  value={formatRate(explainabilityMetrics.preference_trace_rate)}
                />
                <MetricCard
                  label="Score Component Coverage"
                  value={formatRate(explainabilityMetrics.score_component_coverage_rate)}
                />
                <MetricCard
                  label="Groundedness"
                  value={formatRate(explainabilityMetrics.groundedness_rate)}
                />
                <MetricCard
                  label="Rank-Shift Coverage"
                  value={formatRate(explainabilityMetrics.rank_shift_coverage_rate)}
                />
                <MetricCard
                  label="Ungrounded Claim Count"
                  value={String(explainabilityMetrics.ungrounded_claim_count)}
                />
                <MetricCard
                  label="Average Rank Shift"
                  value={formatNumber(explainabilityMetrics.average_rank_shift_for_ground_truth_hits, 6)}
                />
              </section>

              <section className="grid two">
                <article className="card">
                  <span className="eyebrow">Interpretation</span>
                  <p className="muted">
                    Hybrid provides source-grounded explanation evidence at scale, but this remains
                    an offline metric-based explainability audit rather than a human evaluation or
                    live A/B test.
                  </p>
                </article>
                <article className="card">
                  <span className="eyebrow">Trade-off Warning</span>
                  <p className="muted">
                    Hybrid improves explainability and remains competitive on ranking quality, but
                    it reduces intra-list diversity compared with SVD.
                  </p>
                </article>
              </section>

              {explainability.warnings.length ? (
                <section className="card">
                  <span className="eyebrow">Warnings</span>
                  {explainability.warnings.map((warning) => (
                    <p className="muted" key={warning}>
                      {warning}
                    </p>
                  ))}
                </section>
              ) : null}
            </>
          )}
        </div>
      ) : null}

      {activeTab === "technical-validation" ? (
        <div className="stack">
          <section className="card">
            <span className="eyebrow">Technical Validation</span>
            <h3 className="section-title">Read-Only Artifact Confidence</h3>
            <p className="muted">
              This artifact route uses saved offline outputs. It does not rerun recommendations,
              modify formal experiment artifacts, or change the dissertation algorithms.
            </p>
          </section>

          <section className="grid two">
            <article className="card">
              <span className="eyebrow">Validation Checks</span>
              {technicalChecks.map((item) => (
                <p className="muted" key={item}>
                  {item}
                </p>
              ))}
            </article>
            <article className="card">
              <span className="eyebrow">Non-Claims</span>
              {nonClaims.map((item) => (
                <p className="muted" key={item}>
                  {item}
                </p>
              ))}
            </article>
          </section>

          <section className="card">
            <span className="eyebrow">Important Artifact Paths</span>
            {artifactPaths.map((path) => (
              <p className="muted artifact-path" key={path}>
                {path}
              </p>
            ))}
          </section>
        </div>
      ) : null}
    </div>
  );
}
