import { ChartCard } from "@/components/ChartCard";
import { MetricCard } from "@/components/MetricCard";
import { ModelComparisonTable } from "@/components/ModelComparisonTable";
import { getMetrics } from "@/lib/api";

export default async function EvaluationPage() {
  const metrics = await getMetrics();

  if (!metrics) {
    return <section className="card muted">Run the backend experiment to generate evaluation metrics.</section>;
  }

  const metricChart = [
    { label: "Hit Rate@10", value: metrics.agentic_ai_framework.hit_rate_at_10 },
    { label: "Preference Alignment", value: metrics.agentic_ai_framework.preference_alignment },
    { label: "Diversity", value: metrics.agentic_ai_framework.diversity },
  ];

  return (
    <div className="stack">
      <section className="grid three">
        <MetricCard
          label="CTR Proxy"
          value={metrics.business_mapping.hit_rate_at_10}
          detail="Mapped from Hit Rate@10"
        />
        <MetricCard
          label="CVR Proxy"
          value={metrics.business_mapping.preference_alignment}
          detail="Mapped from Preference Alignment"
        />
        <MetricCard
          label="Engagement Proxy"
          value={metrics.business_mapping.diversity}
          detail="Mapped from Diversity"
        />
      </section>
      <ModelComparisonTable metrics={metrics} />
      <section className="grid two">
        <ChartCard title="Agentic AI Metric Profile" data={metricChart} />
        <article className="card">
          <strong>Interpretation</strong>
          <p className="muted">
            If the agentic framework improves hit rate, it indicates stronger click potential. If
            it improves preference alignment, it indicates stronger conversion potential. If it
            improves diversity, it indicates broader engagement potential.
          </p>
        </article>
      </section>
    </div>
  );
}
