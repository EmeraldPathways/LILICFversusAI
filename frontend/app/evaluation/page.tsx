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
  const hitRateDelta =
    metrics.agentic_ai_framework.hit_rate_at_10 - metrics.collaborative_filtering.hit_rate_at_10;
  const alignmentDelta =
    metrics.agentic_ai_framework.preference_alignment -
    metrics.collaborative_filtering.preference_alignment;
  const diversityDelta =
    metrics.agentic_ai_framework.diversity - metrics.collaborative_filtering.diversity;

  return (
    <div className="stack">
      <section className="card">
        <span className="eyebrow">Research Result</span>
        <h2 className="section-title">Offline Comparative Evaluation</h2>
        <p className="muted">
          This stage reports an offline comparative experiment on the H&amp;M public dataset. The
          benchmark is traditional collaborative filtering, while the proposed model is an agentic
          AI recommendation framework that transparentises user-need understanding through user
          shopping intention understanding, product retrieval, recommendation reasoning,
          recommendation explanation, and feedback adaptation.
        </p>
        <p className="muted">
          Both methods generate Top-N recommendations under the same sampled data environment and
          are then compared against future user behaviour through Hit Rate@10, Preference
          Alignment, and Diversity. The current run covers {metrics.evaluated_users} evaluated
          users, so the interpretation should be treated as prototype evidence rather than a final
          paper result.
        </p>
      </section>
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
          <strong>Research Interpretation</strong>
          <p className="muted">
            In this paper framing, Hit Rate@10 is treated as a proxy for potential CTR impact,
            Preference Alignment as a proxy for potential CVR impact, and Diversity as a proxy for
            potential customer-engagement depth. These are inferential links rather than direct
            live-market measurements.
          </p>
          <p className="muted">
            In the current run, the strongest result is Preference Alignment: the agentic framework
            is {alignmentDelta > 0 ? "higher" : "not higher"} than collaborative filtering by{" "}
            {Math.abs(alignmentDelta).toFixed(3)}. This is the clearest support for the claim that
            the agentic layer improves the recommendation system&apos;s explicit understanding of user
            needs.
          </p>
          <p className="muted">
            No CTR-related improvement is demonstrated in this experiment because the two models
            produced the same Hit Rate@10 result ({metrics.agentic_ai_framework.hit_rate_at_10.toFixed(3)} vs{" "}
            {metrics.collaborative_filtering.hit_rate_at_10.toFixed(3)}). Diversity is{" "}
            {diversityDelta < 0 ? "lower" : "higher"} for the agentic framework by{" "}
            {Math.abs(diversityDelta).toFixed(3)}, so the engagement-depth claim is not supported
            by this specific run.
          </p>
          <p className="muted">
            The intended research relationship remains: agentic AI ability shapes how the system
            interprets user needs, which may influence shopping-behaviour response and customer
            engagement. A larger evaluated cohort is still needed before claiming stable business
            implications.
          </p>
        </article>
      </section>
    </div>
  );
}
