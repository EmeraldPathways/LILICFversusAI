"use client";

import { useEffect, useMemo, useState } from "react";

import {
  getWorkflowCases,
  type ArtifactDemoMethodItem,
  type ArtifactDemoValueCount,
  type ArtifactDemoWorkflowCase,
} from "@/lib/api";

type ArtifactDemoTabsProps = {
  workflowCases: ArtifactDemoWorkflowCase[];
};

type TabId = "svd" | "agentic" | "hybrid";

const tabs: Array<{ id: TabId; label: string }> = [
  { id: "svd", label: "SVD" },
  { id: "agentic", label: "3-Agent" },
  { id: "hybrid", label: "Hybrid" },
];

function formatNumber(value: number | null | undefined, digits = 3) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "Not available";
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(digits);
}

function formatBoolean(value: boolean | null | undefined) {
  if (value === null || value === undefined) {
    return "Not available";
  }
  return value ? "Yes" : "No";
}

function compactValueCounts(items: ArtifactDemoValueCount[]) {
  if (!items.length) {
    return "Not available";
  }
  return items.map((item) => `${item.value} (${item.count})`).join(", ");
}

function MetadataDefinition({
  label,
  value,
}: {
  label: string;
  value: string | null | undefined;
}) {
  return (
    <div className="artifact-definition">
      <span className="artifact-definition-label">{label}</span>
      <span className="artifact-definition-value">{value || "Not available"}</span>
    </div>
  );
}

function ScorePill({
  label,
  value,
}: {
  label: string;
  value: number | null | undefined;
}) {
  return (
    <div className="artifact-score-pill">
      <span>{label}</span>
      <strong>{formatNumber(value)}</strong>
    </div>
  );
}

function PreferenceChipList({
  label,
  values,
}: {
  label: string;
  values: string[];
}) {
  return (
    <article className="artifact-profile-panel">
      <span className="artifact-profile-label">{label}</span>
      <div className="artifact-chip-row">
        {values.length ? (
          values.map((value) => (
            <span key={`${label}-${value}`} className="artifact-chip">
              {value}
            </span>
          ))
        ) : (
          <span className="artifact-chip artifact-chip-muted">Not available</span>
        )}
      </div>
    </article>
  );
}

function UserSummaryPanel({
  workflowCase,
  method,
  compact = false,
}: {
  workflowCase: ArtifactDemoWorkflowCase;
  method: TabId;
  compact?: boolean;
}) {
  const methodHit =
    method === "svd"
      ? workflowCase.method_hits.svd
      : method === "agentic"
        ? workflowCase.method_hits.agentic
        : workflowCase.method_hits.hybrid;

  const methodLabel = method === "svd" ? "SVD" : method === "agentic" ? "3-Agent" : "Hybrid";

  return (
    <article className={compact ? "artifact-summary-card artifact-summary-card-compact" : "card artifact-shell"}>
      <span className="eyebrow">{compact ? "Selected User" : "Selected Real Demo User"}</span>
      <strong className="artifact-user-name">{workflowCase.demo_user.label}</strong>
      <div className={compact ? "artifact-compact-grid" : "artifact-context-grid"}>
        <MetadataDefinition label="Customer ID" value={workflowCase.demo_user.customer_id_short} />
        <MetadataDefinition
          label="Training History"
          value={String(workflowCase.leave_one_out.training_history_count)}
        />
        <MetadataDefinition label="Ground Truth" value={workflowCase.leave_one_out.ground_truth_article_id} />
        <MetadataDefinition
          label="Candidate Pool"
          value={String(workflowCase.leave_one_out.candidate_pool_size)}
        />
      </div>
      <div className="artifact-badge-row">
        <span className="artifact-badge">
          Ground truth in pool: {formatBoolean(workflowCase.leave_one_out.ground_truth_in_candidate_pool)}
        </span>
        <span className={methodHit ? "artifact-badge artifact-badge-hit" : "artifact-badge"}>
          {methodLabel} {methodHit ? "Hit at Top-10" : "Miss at Top-10"}
        </span>
      </div>
    </article>
  );
}

function RecommendationCard({
  item,
  mode,
  hybridAuditArticleId,
}: {
  item: ArtifactDemoMethodItem;
  mode: TabId;
  hybridAuditArticleId?: string | null;
}) {
  const primaryScore = mode === "hybrid" ? item.hybrid_score ?? item.score : item.score;
  const hasHybridAudit = mode === "hybrid" && hybridAuditArticleId === item.article_id;

  return (
    <article className={hasHybridAudit ? "artifact-rec-card artifact-rec-card-selected" : "artifact-rec-card"}>
      <div className="artifact-rec-topline">
        <span className="artifact-rank">Rank {item.rank ?? "NA"}</span>
        {item.is_ground_truth ? <span className="artifact-badge artifact-badge-hit">Ground Truth</span> : null}
      </div>
      <h4 className="artifact-rec-title">{item.article_id}</h4>
      <div className="artifact-score-row">
        <ScorePill
          label={mode === "svd" ? "SVD score" : mode === "agentic" ? "Agentic score" : "Hybrid score"}
          value={primaryScore}
        />
        {mode === "hybrid" ? (
          <>
            <ScorePill label="SVD score" value={item.normalized_svd_score} />
            <ScorePill label="Agentic score" value={item.normalized_agentic_score} />
            <ScorePill label="Diversity bonus" value={item.diversity_bonus} />
          </>
        ) : null}
      </div>
      <div className="artifact-meta-grid">
        <MetadataDefinition label="Type" value={item.product_type_name} />
        <MetadataDefinition label="Group" value={item.product_group_name} />
        <MetadataDefinition label="Colour" value={item.colour_group_name} />
        <MetadataDefinition label="Appearance" value={item.graphical_appearance_name} />
      </div>
      {mode === "agentic" && item.matched_evidence.length ? (
        <div className="artifact-chip-row artifact-chip-row-spaced">
          {item.matched_evidence.map((evidence) => (
            <span key={`${item.article_id}-${evidence}`} className="artifact-chip">
              {evidence}
            </span>
          ))}
        </div>
      ) : null}
      {mode !== "svd" && item.reason ? <p className="muted artifact-card-copy">{item.reason}</p> : null}
      {mode === "hybrid" ? (
        <span className={hasHybridAudit ? "artifact-badge artifact-badge-hybrid" : "artifact-badge artifact-badge-muted"}>
          {hasHybridAudit ? "Explanation available" : "Hybrid-ranked item"}
        </span>
      ) : null}
    </article>
  );
}

function RecommendationSection({
  title,
  intro,
  items,
  mode,
  hybridAuditArticleId,
}: {
  title: string;
  intro?: string;
  items: ArtifactDemoMethodItem[];
  mode: TabId;
  hybridAuditArticleId?: string | null;
}) {
  return (
    <section className="card artifact-shell">
      <div className="artifact-section-head">
        <span className="eyebrow">{title}</span>
        {intro ? <p className="muted artifact-copy-small">{intro}</p> : null}
      </div>
      <div className="artifact-rec-grid">
        {items.length ? (
          items.map((item) => (
            <RecommendationCard
              key={`${mode}-${item.article_id}-${item.rank ?? 0}`}
              item={item}
              mode={mode}
              hybridAuditArticleId={hybridAuditArticleId}
            />
          ))
        ) : (
          <div className="muted">Saved recommendations unavailable.</div>
        )}
      </div>
    </section>
  );
}

function FlowNode({
  title,
  body,
  layer,
  source,
  accent = false,
}: {
  title: string;
  body: string;
  layer: string;
  source?: string;
  accent?: boolean;
}) {
  return (
    <article className={accent ? "artifact-flow-node-box artifact-flow-node-box-accent" : "artifact-flow-node-box"}>
      <div className="artifact-flow-node-head">
        <span className="artifact-flow-layer">{layer}</span>
        {source ? <span className="artifact-flow-source">{source}</span> : null}
      </div>
      <span className="artifact-flow-label">{title}</span>
      <p>{body}</p>
    </article>
  );
}

export function ArtifactDemoTabs({ workflowCases }: ArtifactDemoTabsProps) {
  const [cases, setCases] = useState(workflowCases);
  const [isLoadingCases, setIsLoadingCases] = useState(workflowCases.length === 0);
  const [activeTab, setActiveTab] = useState<TabId>("hybrid");
  const [selectedCaseId, setSelectedCaseId] = useState(workflowCases[0]?.demo_user.customer_id ?? "");

  useEffect(() => {
    setCases(workflowCases);
    setIsLoadingCases(false);
  }, [workflowCases]);

  useEffect(() => {
    if (workflowCases.length) {
      return;
    }

    let cancelled = false;

    async function loadCases() {
      setIsLoadingCases(true);
      const payload = await getWorkflowCases();
      if (cancelled) {
        return;
      }
      setCases(payload?.cases ?? []);
      setIsLoadingCases(false);
    }

    void loadCases();

    return () => {
      cancelled = true;
    };
  }, [workflowCases]);

  useEffect(() => {
    if (!cases.length) {
      setSelectedCaseId("");
      return;
    }
    setSelectedCaseId((current) => {
      if (current && cases.some((item) => item.demo_user.customer_id === current)) {
        return current;
      }
      return cases[0].demo_user.customer_id;
    });
  }, [cases]);

  const selectedCase = useMemo(
    () => cases.find((item) => item.demo_user.customer_id === selectedCaseId) ?? cases[0] ?? null,
    [selectedCaseId, cases],
  );

  const evidencePreviewItems = selectedCase?.agentic_top10.slice(0, 9) ?? [];
  const matchedPreferenceFields = selectedCase?.hybrid_explainability.matched_preference_fields ?? [];
  const selectedHybridAuditItem = useMemo(() => {
    if (!selectedCase) {
      return null;
    }
    return (
      selectedCase.hybrid_top10.find(
        (item) => item.article_id === selectedCase.hybrid_explainability.article_id,
      ) ?? selectedCase.hybrid_top10[0] ?? null
    );
  }, [selectedCase]);
  const selectedSvdItem = useMemo(() => {
    if (!selectedCase || !selectedHybridAuditItem) {
      return null;
    }
    return selectedCase.svd_top10.find((item) => item.article_id === selectedHybridAuditItem.article_id) ?? null;
  }, [selectedCase, selectedHybridAuditItem]);
  const selectedAgenticItem = useMemo(() => {
    if (!selectedCase || !selectedHybridAuditItem) {
      return null;
    }
    return (
      selectedCase.agentic_top10.find((item) => item.article_id === selectedHybridAuditItem.article_id) ??
      null
    );
  }, [selectedCase, selectedHybridAuditItem]);

  return (
    <div className="artifact-page artifact-one-page">
      <section className="card artifact-shell artifact-hero-redesign">
        <div className="artifact-hero-grid">
          <div className="artifact-hero-copy">
            <span className="eyebrow">Phase 1 Dissertation Artefact</span>
            <h2 className="section-title artifact-title-main">H&amp;M Next-Item Recommendation Artefact</h2>
            <p className="muted artifact-copy">
              A runnable offline recommender-system demo showing SVD, a structured 3-Agent workflow,
              and a Hybrid SVD + 3-Agent reranker using real saved H&amp;M experiment artifacts.
            </p>
            <p className="muted artifact-copy">
              This artefact demonstrates three method modes: SVD baseline as behavioural collaborative
              filtering signal, 3-Agent as the preference-evidence-decision workflow, and Hybrid as the
              final reranking and explainability-oriented method.
            </p>
            <p className="muted artifact-copy artifact-copy-small">
              Offline evaluation only. No CTR, CVR, conversion, live customer engagement, add-to-cart,
              dwell time, or live feedback adaptation is claimed.
            </p>
          </div>
          {selectedCase ? <UserSummaryPanel workflowCase={selectedCase} method={activeTab} compact /> : null}
        </div>
        <div className="artifact-tabbar" role="tablist" aria-label="Artefact methods">
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

      <section className="card artifact-shell artifact-controls artifact-controls-redesign">
        <div>
          <span className="eyebrow">Demo User Selection</span>
          <p className="muted artifact-copy-small">
            These users are selected from saved formal experiment artifacts to demonstrate the artefact
            workflow. The full quantitative evaluation is reported separately in the dissertation.
          </p>
        </div>
        <label className="artifact-select-wrap">
          <span className="artifact-label">Selected User</span>
          <select
            value={selectedCaseId}
            onChange={(event) => setSelectedCaseId(event.target.value)}
            disabled={!cases.length}
          >
            {cases.map((item) => (
              <option key={item.demo_user.customer_id} value={item.demo_user.customer_id}>
                {item.demo_user.label} - {item.demo_user.customer_id_short}
              </option>
            ))}
          </select>
        </label>
      </section>

      {!selectedCase && isLoadingCases ? (
        <section className="card artifact-shell muted">Loading saved artifact cases...</section>
      ) : null}

      {!selectedCase && !isLoadingCases ? (
        <section className="card artifact-shell muted">
          Saved artefact cases are unavailable. Check that the formal seed99 saved artifacts are present.
        </section>
      ) : null}

      {selectedCase && activeTab === "svd" ? (
        <div className="stack">
          <section className="card artifact-shell artifact-method-header">
            <span className="eyebrow">SVD Baseline</span>
            <h3 className="section-title">SVD Matrix Factorisation Baseline</h3>
            <p className="muted artifact-copy">
              SVD is the formal collaborative filtering baseline. It uses user-item purchase interactions
              to produce behavioural recommendation scores for candidate items.
            </p>
          </section>

          <section className="grid two">
            <UserSummaryPanel workflowCase={selectedCase} method="svd" />
            <article className="card artifact-shell artifact-signal-card">
              <span className="eyebrow">SVD Signal</span>
              <p className="muted artifact-copy-small">
                SVD uses behavioural interaction patterns only. It does not inspect item explanations or
                agentic evidence.
              </p>
              <div className="artifact-meta-grid artifact-meta-grid-tight">
                <MetadataDefinition label="Ground Truth Article" value={selectedCase.ground_truth.article_id} />
                <MetadataDefinition label="Type" value={selectedCase.ground_truth.product_type_name} />
                <MetadataDefinition label="Group" value={selectedCase.ground_truth.product_group_name} />
                <MetadataDefinition label="Colour" value={selectedCase.ground_truth.colour_group_name} />
              </div>
            </article>
          </section>

          <RecommendationSection title="SVD Top-10 Recommendations" items={selectedCase.svd_top10} mode="svd" />
        </div>
      ) : null}

      {selectedCase && activeTab === "agentic" ? (
        <div className="stack">
          <section className="card artifact-shell artifact-method-header">
            <span className="eyebrow">Standalone 3-Agent</span>
            <h3 className="section-title">Standalone 3-Agent Recommender</h3>
            <p className="muted artifact-copy">
              The standalone 3-Agent recommender uses user history and item metadata to rank candidate
              items without SVD. It is evaluated as the agentic comparison / ablation method.
            </p>
          </section>

          <section className="grid three artifact-agent-rail">
            <article className="card artifact-shell artifact-agent-card-dark">
              <span className="eyebrow">1. Preference Agent</span>
              <p className="muted">Extracts preferences from real H&amp;M purchase history.</p>
            </article>
            <article className="card artifact-shell artifact-agent-card-dark">
              <span className="eyebrow">2. Evidence / Item Agent</span>
              <p className="muted">Builds candidate item evidence from catalogue metadata.</p>
            </article>
            <article className="card artifact-shell artifact-agent-card-dark">
              <span className="eyebrow">3. Decision Agent</span>
              <p className="muted">Ranks candidate items using preference and evidence signals.</p>
            </article>
          </section>

          <section className="card artifact-shell">
            <div className="artifact-profile-header">
              <div>
                <span className="eyebrow">Preference Agent</span>
                <h3 className="section-title">User Preference Profile</h3>
              </div>
              <div className="artifact-profile-stat">
                <span>Transactions Analysed</span>
                <strong>{selectedCase.leave_one_out.training_history_count}</strong>
              </div>
            </div>
            <p className="muted artifact-copy-small">
              {selectedCase.preference_agent.inferred_intent
                ? `Preference Agent summary: ${selectedCase.preference_agent.inferred_intent}.`
                : "Preference summary not available in the saved artifacts."}
            </p>
            <div className="artifact-chip-row artifact-chip-row-spaced">
              <span className="artifact-chip">{selectedCase.demo_user.label}</span>
              <span className="artifact-chip">Short ID {selectedCase.demo_user.customer_id_short}</span>
              <span className="artifact-chip">Candidate pool {selectedCase.leave_one_out.candidate_pool_size}</span>
            </div>
            <div className="artifact-profile-grid">
              <PreferenceChipList
                label="Preferred Product Types"
                values={selectedCase.preference_agent.preferred_product_types}
              />
              <PreferenceChipList
                label="Preferred Product Groups"
                values={selectedCase.preference_agent.preferred_categories}
              />
              <PreferenceChipList
                label="Preferred Colours"
                values={selectedCase.preference_agent.preferred_colours}
              />
              <PreferenceChipList
                label="Preferred Appearances"
                values={selectedCase.preference_agent.preferred_appearance}
              />
            </div>
            <div className="artifact-profile-summary-grid">
              <article className="artifact-summary-strip">
                <span className="artifact-profile-label">Frequent Product Types</span>
                <p>{compactValueCounts(selectedCase.preference_agent.frequent_product_types)}</p>
              </article>
              <article className="artifact-summary-strip">
                <span className="artifact-profile-label">Frequent Product Groups</span>
                <p>{compactValueCounts(selectedCase.preference_agent.frequent_product_groups)}</p>
              </article>
              <article className="artifact-summary-strip">
                <span className="artifact-profile-label">Frequent Colours</span>
                <p>{compactValueCounts(selectedCase.preference_agent.frequent_colours)}</p>
              </article>
              <article className="artifact-summary-strip">
                <span className="artifact-profile-label">Frequent Appearances</span>
                <p>{compactValueCounts(selectedCase.preference_agent.frequent_graphical_appearances)}</p>
              </article>
            </div>
          </section>

          <section className="card artifact-shell">
            <div className="artifact-section-head">
              <span className="eyebrow">Evidence Agent</span>
              <h3 className="section-title">Candidate Evidence Set</h3>
              <p className="muted artifact-copy-small">
                Retrieved candidate evidence by matching saved preference signals against product metadata.
              </p>
            </div>
            <div className="artifact-evidence-grid">
              {evidencePreviewItems.length ? (
                evidencePreviewItems.map((item) => (
                  <article
                    key={`evidence-${item.article_id}-${item.rank ?? 0}`}
                    className="artifact-evidence-card"
                  >
                    <div className="artifact-rec-topline">
                      <span className="artifact-rank">{item.article_id}</span>
                      <span className="artifact-badge">
                        {item.matched_evidence.length} {item.matched_evidence.length === 1 ? "match" : "matches"}
                      </span>
                    </div>
                    <div className="artifact-meta-grid artifact-meta-grid-tight">
                      <MetadataDefinition label="Type" value={item.product_type_name} />
                      <MetadataDefinition label="Group" value={item.product_group_name} />
                      <MetadataDefinition label="Colour" value={item.colour_group_name} />
                      <MetadataDefinition label="Appearance" value={item.graphical_appearance_name} />
                    </div>
                    {item.matched_evidence.length ? (
                      <div className="artifact-chip-row artifact-chip-row-spaced">
                        {item.matched_evidence.map((evidence) => (
                          <span key={`${item.article_id}-${evidence}`} className="artifact-chip">
                            {evidence}
                          </span>
                        ))}
                      </div>
                    ) : null}
                    {item.reason ? <p className="muted artifact-card-copy">{item.reason}</p> : null}
                  </article>
                ))
              ) : (
                <div className="muted">Not available</div>
              )}
            </div>
          </section>

          <section className="card artifact-shell">
            <div className="artifact-section-head">
              <span className="eyebrow">Decision Agent</span>
              <h3 className="section-title">Final Recommendations</h3>
              <p className="muted artifact-copy-small">
                Ranked the evidence set with transparent weighted scoring and returned the top 10 items.
              </p>
            </div>
            <div className="artifact-decision-summary">
              <ScorePill label="Selected rank" value={selectedCase.decision_agent.selected_rank} />
              <ScorePill label="Selected score" value={selectedCase.decision_agent.selected_score} />
              <MetadataDefinition label="Selected article" value={selectedCase.decision_agent.selected_article_id} />
            </div>
            {selectedCase.decision_agent.headline ? (
              <p className="muted artifact-copy-small">{selectedCase.decision_agent.headline}</p>
            ) : null}
            <div className="artifact-rec-grid">
              {selectedCase.agentic_top10.map((item) => (
                <RecommendationCard key={`agentic-${item.article_id}-${item.rank ?? 0}`} item={item} mode="agentic" />
              ))}
            </div>
          </section>
        </div>
      ) : null}

      {selectedCase && activeTab === "hybrid" ? (
        <div className="stack">
          <section className="card artifact-shell">
            <div className="artifact-section-head">
              <h3 className="section-title">End-to-End Hybrid Recommendation Path</h3>
              <p className="muted artifact-copy-small">
                How the selected user moves from history data to explainable Hybrid Top-10 recommendations.
              </p>
            </div>
            <div className="artifact-flow-grid artifact-flow-grid-six">
              <FlowNode
                layer="Layer 1"
                title="Input"
                body="Selected H&M user, training history, held-out item, and 100-item candidate pool."
                source="Evaluation Base"
              />
              <FlowNode
                layer="Layer 2"
                title="SVD Signal"
                body="Saved SVD score ranks candidate items using behavioural collaborative filtering."
                accent
                source="SVD Artifact"
              />
              <FlowNode
                layer="Layer 3"
                title="3-Agent Signal"
                body="Preference, evidence, and decision signals score items using user history and metadata."
                source="3-Agent Artifact"
              />
              <FlowNode
                layer="Layer 4"
                title="Hybrid Reranker"
                body="Combines SVD score, agentic score, and diversity bonus."
                accent
                source="Hybrid Formula"
              />
              <FlowNode
                layer="Layer 5"
                title="Hybrid Top-10"
                body="Outputs the final ranked Top-10 recommendation list."
                source="Hybrid Artifact"
              />
              <FlowNode
                layer="Layer 6"
                title="Explainability Audit"
                body="Checks groundedness, evidence traceability, rank shift, and score components."
                source="Explainability Artifact"
              />
            </div>
          </section>

          <section className="card artifact-shell artifact-user-pill-card">
            <div className="artifact-section-head">
              <h3 className="section-title">H&amp;M User Selection</h3>
            </div>
            <div className="artifact-user-selection-grid">
              <div className="artifact-kv-pill-grid">
                <span className="artifact-kv-pill">
                  <strong>Demo User</strong>
                  <span>{selectedCase.demo_user.label}</span>
                </span>
                <span className="artifact-kv-pill">
                  <strong>Customer ID</strong>
                  <span>{selectedCase.demo_user.customer_id_short}</span>
                </span>
                <span className="artifact-kv-pill">
                  <strong>Training History</strong>
                  <span>{selectedCase.leave_one_out.training_history_count}</span>
                </span>
                <span className="artifact-kv-pill">
                  <strong>Ground Truth</strong>
                  <span>{selectedCase.leave_one_out.ground_truth_article_id || "Not available"}</span>
                </span>
                <span className="artifact-kv-pill">
                  <strong>Candidate Pool</strong>
                  <span>{selectedCase.leave_one_out.candidate_pool_size}</span>
                </span>
                <span className="artifact-kv-pill">
                  <strong>Ground Truth In Pool</strong>
                  <span>{formatBoolean(selectedCase.leave_one_out.ground_truth_in_candidate_pool)}</span>
                </span>
                <span className="artifact-kv-pill artifact-kv-pill-hit">
                  <strong>Hybrid Hit@10</strong>
                  <span>{selectedCase.method_hits.hybrid ? "Yes" : "No"}</span>
                </span>
              </div>
              <label className="artifact-select-wrap artifact-inline-select-wrap">
                <span className="artifact-label">Selected User</span>
                <select
                  value={selectedCaseId}
                  onChange={(event) => setSelectedCaseId(event.target.value)}
                  disabled={!cases.length}
                >
                  {cases.map((item) => (
                    <option key={item.demo_user.customer_id} value={item.demo_user.customer_id}>
                      {item.demo_user.label} - {item.demo_user.customer_id_short}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </section>

          <section className="artifact-hybrid-signal-grid">
            <article className="card artifact-shell">
              <div className="artifact-section-head">
                <h3 className="section-title">SVD Behavioural Signal</h3>
                <p className="muted artifact-copy-small">
                  This signal comes from saved SVD recommendations and reflects behavioural collaborative filtering relevance.
                </p>
              </div>
              <div className="artifact-score-stack artifact-score-stack-compact">
                <ScorePill label="SVD Rank" value={selectedCase.hybrid_explainability.svd_rank} />
                <ScorePill
                  label="Normalized SVD"
                  value={selectedCase.hybrid_explainability.score_components.normalized_svd_score}
                />
                <ScorePill label="SVD Score" value={selectedSvdItem?.score} />
              </div>
              <div className="artifact-chip-row artifact-chip-row-spaced">
                <span className="artifact-chip">
                  Ground truth in pool: {formatBoolean(selectedCase.leave_one_out.ground_truth_in_candidate_pool)}
                </span>
                {selectedSvdItem?.product_type_name ? (
                  <span className="artifact-chip">{selectedSvdItem.product_type_name}</span>
                ) : null}
                {selectedSvdItem?.product_group_name ? (
                  <span className="artifact-chip">{selectedSvdItem.product_group_name}</span>
                ) : null}
                {!selectedSvdItem ? <span className="artifact-chip artifact-chip-muted">Not available</span> : null}
              </div>
            </article>

            <article className="card artifact-shell">
              <div className="artifact-section-head">
                <h3 className="section-title">3-Agent Evidence Signal</h3>
                <p className="muted artifact-copy-small">
                  This signal comes from the structured 3-Agent workflow: Preference Agent, Evidence Agent, and Decision Agent.
                </p>
              </div>
              <div className="artifact-score-stack artifact-score-stack-compact">
                <ScorePill
                  label="Normalized Agentic"
                  value={selectedCase.hybrid_explainability.score_components.normalized_agentic_score}
                />
                <ScorePill label="Agentic Score" value={selectedAgenticItem?.score} />
              </div>
              <div className="artifact-chip-row artifact-chip-row-spaced">
                {selectedCase.hybrid_explainability.item_metadata.product_type_name ? (
                  <span className="artifact-chip">{selectedCase.hybrid_explainability.item_metadata.product_type_name}</span>
                ) : null}
                {selectedCase.hybrid_explainability.item_metadata.product_group_name ? (
                  <span className="artifact-chip">{selectedCase.hybrid_explainability.item_metadata.product_group_name}</span>
                ) : null}
                {selectedCase.hybrid_explainability.item_metadata.colour_group_name ? (
                  <span className="artifact-chip">{selectedCase.hybrid_explainability.item_metadata.colour_group_name}</span>
                ) : null}
                {selectedCase.hybrid_explainability.item_metadata.graphical_appearance_name ? (
                  <span className="artifact-chip">{selectedCase.hybrid_explainability.item_metadata.graphical_appearance_name}</span>
                ) : null}
                {matchedPreferenceFields.length ? (
                  matchedPreferenceFields.map((field, index) => (
                    <span key={`matched-${index}`} className="artifact-chip">
                      {String(field.field ?? field.item_value ?? "match")}
                    </span>
                  ))
                ) : (
                  <span className="artifact-chip artifact-chip-muted">Not available</span>
                )}
              </div>
              {selectedAgenticItem?.reason ? (
                <p className="muted artifact-copy-small artifact-signal-footnote">{selectedAgenticItem.reason}</p>
              ) : null}
            </article>

            <article className="card artifact-shell artifact-formula-card-dark">
              <div className="artifact-section-head">
                <h3 className="section-title">Hybrid Formula</h3>
              </div>
              <div className="artifact-formula-stack">
                <strong>hybrid_score =</strong>
                <span>0.70 x normalized_svd_score</span>
                <span>0.25 x normalized_agentic_score</span>
                <span>0.05 x diversity_bonus</span>
              </div>
              <div className="artifact-score-stack artifact-score-stack-compact">
                <ScorePill
                  label="Normalized SVD"
                  value={selectedCase.hybrid_explainability.score_components.normalized_svd_score}
                />
                <ScorePill
                  label="Normalized Agentic"
                  value={selectedCase.hybrid_explainability.score_components.normalized_agentic_score}
                />
                <ScorePill
                  label="Diversity Bonus"
                  value={selectedCase.hybrid_explainability.score_components.diversity_bonus}
                />
                <ScorePill
                  label="Hybrid Score"
                  value={selectedCase.hybrid_explainability.score_components.hybrid_score}
                />
              </div>
            </article>
          </section>

          <RecommendationSection
            title="Hybrid Top-10 Recommendations"
            intro="Final ranked recommendations produced by combining behavioural relevance, agentic evidence, and diversity adjustment."
            items={selectedCase.hybrid_top10}
            mode="hybrid"
            hybridAuditArticleId={selectedCase.hybrid_explainability.article_id}
          />

          <section className="grid two artifact-hybrid-audit-grid">
            <article className="card artifact-shell">
              <div className="artifact-section-head">
                <h3 className="section-title">Explainability Audit</h3>
                <p className="muted artifact-copy-small">
                  Read-only explanation evidence for the selected Hybrid recommendation.
                </p>
                <p className="muted artifact-copy-small">
                  The explainability layer is a read-only audit of Hybrid recommendations. It does not
                  generate new recommendations and does not change ranking metrics.
                </p>
              </div>
              <div className="artifact-meta-grid">
                <MetadataDefinition label="Selected Article" value={selectedCase.hybrid_explainability.article_id} />
                <MetadataDefinition label="Groundedness" value={selectedCase.hybrid_explainability.groundedness_status} />
                <MetadataDefinition
                  label="Hybrid Rank"
                  value={
                    selectedCase.hybrid_explainability.hybrid_rank !== null &&
                    selectedCase.hybrid_explainability.hybrid_rank !== undefined
                      ? String(selectedCase.hybrid_explainability.hybrid_rank)
                      : "Not available"
                  }
                />
                <MetadataDefinition
                  label="SVD Rank"
                  value={
                    selectedCase.hybrid_explainability.svd_rank !== null &&
                    selectedCase.hybrid_explainability.svd_rank !== undefined
                      ? String(selectedCase.hybrid_explainability.svd_rank)
                      : "Not available"
                  }
                />
                <MetadataDefinition
                  label="Rank Shift"
                  value={
                    selectedCase.hybrid_explainability.rank_shift !== null &&
                    selectedCase.hybrid_explainability.rank_shift !== undefined
                      ? String(selectedCase.hybrid_explainability.rank_shift)
                      : "Not available"
                  }
                />
                <MetadataDefinition
                  label="Hit Status"
                  value={selectedCase.hybrid_explainability.is_ground_truth ? "Ground-truth hit" : "Not available"}
                />
                <MetadataDefinition
                  label="Preference Trace"
                  value={matchedPreferenceFields.length ? "Available" : "Not available"}
                />
                <MetadataDefinition
                  label="Product Name"
                  value={selectedCase.hybrid_explainability.item_metadata.prod_name}
                />
              </div>
              <div className="artifact-chip-row artifact-chip-row-spaced">
                {selectedCase.hybrid_explainability.item_metadata.product_type_name ? (
                  <span className="artifact-chip">{selectedCase.hybrid_explainability.item_metadata.product_type_name}</span>
                ) : null}
                {selectedCase.hybrid_explainability.item_metadata.product_group_name ? (
                  <span className="artifact-chip">{selectedCase.hybrid_explainability.item_metadata.product_group_name}</span>
                ) : null}
                {selectedCase.hybrid_explainability.item_metadata.colour_group_name ? (
                  <span className="artifact-chip">{selectedCase.hybrid_explainability.item_metadata.colour_group_name}</span>
                ) : null}
                {selectedCase.hybrid_explainability.item_metadata.graphical_appearance_name ? (
                  <span className="artifact-chip">{selectedCase.hybrid_explainability.item_metadata.graphical_appearance_name}</span>
                ) : null}
                {matchedPreferenceFields.length ? (
                  matchedPreferenceFields.map((field, index) => (
                    <span key={`${selectedCase.hybrid_explainability.article_id}-${index}`} className="artifact-chip">
                      {String(field.field ?? field.item_value ?? "match")}
                    </span>
                  ))
                ) : (
                  <span className="artifact-chip artifact-chip-muted">Matched preference fields not available</span>
                )}
              </div>
              {selectedCase.hybrid_explainability.explanation_text ? (
                <p className="muted artifact-card-copy artifact-card-copy-roomy">
                  {selectedCase.hybrid_explainability.explanation_text}
                </p>
              ) : null}
            </article>
          </section>

          <section className="card artifact-shell artifact-limitation-card">
            <p className="muted artifact-copy-small">
              This is an offline recommendation artefact. It demonstrates ranking behaviour and
              source-grounded explanation evidence using saved H&amp;M experiment artifacts. It does not
              claim CTR, CVR, conversion, live customer engagement, add-to-cart, dwell time, or live
              feedback adaptation.
            </p>
          </section>
        </div>
      ) : null}
    </div>
  );
}
