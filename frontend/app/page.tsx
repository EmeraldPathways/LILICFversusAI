import { MetricCard } from "@/components/MetricCard";
import { getSetup } from "@/lib/api";

export default async function HomePage() {
  const setup = await getSetup();

  return (
    <div className="stack">
      <section className="grid two">
        <article className="card">
          <span className="eyebrow">Demo Positioning</span>
          <h2 className="section-title">Decision Layer, Not Chatbot</h2>
          <p className="muted">
            The proposed method adds intention understanding, targeted retrieval, reasoning,
            explanations, and feedback adaptation above a standard recommendation workflow.
          </p>
        </article>
        <article className="card">
          <span className="eyebrow">Experimental Goal</span>
          <h2 className="section-title">Offline Comparative Evaluation</h2>
          <p className="muted">
            Both models generate Top-N recommendations on the same cohort, then proxy metrics map
            the results to CTR, CVR, and engagement depth.
          </p>
        </article>
      </section>

      <section className="grid three">
        <MetricCard
          label="Dataset"
          value={setup?.dataset ?? "Awaiting backend"}
          detail="H&M Personalized Fashion Recommendations"
        />
        <MetricCard
          label="Sample Size"
          value={String(setup?.summary?.sample_size ?? setup?.sample_size ?? "20,000")}
          detail="Processed interaction sample"
        />
        <MetricCard
          label="Evaluated Users"
          value={String(setup?.summary?.evaluated_users ?? "0")}
          detail="Users compared across both models"
        />
      </section>
    </div>
  );
}
