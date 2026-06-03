"use client";

import { type EvaluationDebugResponse } from "@/lib/api";

type EvaluationDebugPanelProps = {
  debug: EvaluationDebugResponse | null;
  error: string | null;
  isLoading: boolean;
};

function MethodSummary({
  label,
  method,
}: {
  label: string;
  method: EvaluationDebugResponse["cf"] | EvaluationDebugResponse["agentic"];
}) {
  return (
    <article className="summary-chip">
      <span>{label}</span>
      <strong>{method.hit_label}</strong>
      <small>{method.top_5_article_ids.join(", ") || "No Top 5 available"}</small>
    </article>
  );
}

export function EvaluationDebugPanel({
  debug,
  error,
  isLoading,
}: EvaluationDebugPanelProps) {
  const validation = debug?.validation ?? null;

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <span className="eyebrow">Evaluation Debug</span>
          <h3>Validation Layer</h3>
        </div>
        {debug ? (
          <div className={validation?.is_valid ?? true ? "hit-badge hit" : "hit-badge miss"}>
            {validation ? (validation.is_valid ? "Valid" : "Excluded") : "Legacy Debug"}
          </div>
        ) : null}
      </div>

      {isLoading ? <p className="empty-state">Loading evaluation debug data...</p> : null}
      {error ? <div className="error-banner">{error}</div> : null}
      {!isLoading && !error && !debug ? (
        <p className="empty-state">Select an evaluated user to inspect validation state and candidate-pool checks.</p>
      ) : null}

      {debug ? (
        <>
          <div className="evaluation-grid">
            <div className="summary-chip">
              <span>Ground Truth</span>
              <strong>{debug.ground_truth_article_ids.join(", ")}</strong>
            </div>
            <div className="summary-chip">
              <span>Evaluation Mode</span>
              <strong>{validation?.evaluation_mode ?? "legacy"}</strong>
            </div>
            <div className="summary-chip">
              <span>Candidate Pool</span>
              <strong>{validation?.candidate_pool_size ?? "unknown"} items</strong>
            </div>
            <div className="summary-chip">
              <span>Catalog Check</span>
              <strong>
                {debug.ground_truth_exists_in_processed_product_catalog ? "Ground truth present" : "Missing"}
              </strong>
            </div>
          </div>

          <p className="body-copy">
            Validation reasons: {validation ? (validation.reasons.length ? validation.reasons.join(", ") : "none") : "not available from current backend payload"}
          </p>
          <p className="body-copy">
            Candidate pool preview:{" "}
            {validation?.candidate_pool_article_ids_preview.join(", ") || "No candidate pool preview available"}
          </p>

          <div className="evaluation-grid">
            <MethodSummary label="CF" method={debug.cf} />
            <MethodSummary label="Agentic" method={debug.agentic} />
          </div>
        </>
      ) : null}
    </section>
  );
}
