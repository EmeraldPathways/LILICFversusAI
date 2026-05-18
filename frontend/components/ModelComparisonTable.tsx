import type { MetricsResponse } from "@/lib/api";

function formatValue(value: number | null | undefined) {
  return typeof value === "number" ? value.toFixed(3) : "n/a";
}

export function ModelComparisonTable({ metrics }: { metrics: MetricsResponse }) {
  return (
    <section className="card">
      <strong>Comparative Result Table</strong>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Model</th>
              <th>Hit Rate@10</th>
              <th>Preference Alignment</th>
              <th>Diversity</th>
              <th>Explanation Quality</th>
              <th>Feedback Adaptability</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Collaborative Filtering</td>
              <td>{formatValue(metrics.collaborative_filtering.hit_rate_at_10)}</td>
              <td>{formatValue(metrics.collaborative_filtering.preference_alignment)}</td>
              <td>{formatValue(metrics.collaborative_filtering.diversity)}</td>
              <td>{formatValue(metrics.collaborative_filtering.explanation_quality)}</td>
              <td>{formatValue(metrics.collaborative_filtering.feedback_adaptability)}</td>
            </tr>
            <tr>
              <td>Agentic AI Framework</td>
              <td>{formatValue(metrics.agentic_ai_framework.hit_rate_at_10)}</td>
              <td>{formatValue(metrics.agentic_ai_framework.preference_alignment)}</td>
              <td>{formatValue(metrics.agentic_ai_framework.diversity)}</td>
              <td>{formatValue(metrics.agentic_ai_framework.explanation_quality)}</td>
              <td>{formatValue(metrics.agentic_ai_framework.feedback_adaptability)}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  );
}

