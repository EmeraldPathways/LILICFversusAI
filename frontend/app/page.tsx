import Link from "next/link";

import { MetricCard } from "@/components/MetricCard";
import { getMetrics, getSetup } from "@/lib/api";

export default async function HomePage() {
  const [setup, metrics] = await Promise.all([getSetup(), getMetrics()]);

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
          value={String(metrics?.evaluated_users ?? "0")}
          detail="Users compared across both models"
        />
      </section>

      <section className="card">
        <strong>Dashboard Sections</strong>
        <div className="grid two" style={{ marginTop: 16 }}>
          {[
            ["/research-setup", "Research setup and experiment framing"],
            ["/data-processing", "Sample summary and metadata distributions"],
            ["/user-intention", "LLM-inferred user intent and preference profile"],
            ["/comparison", "Side-by-side CF and Agentic recommendations"],
            ["/evaluation", "Comparative proxy metrics and business meaning"],
          ].map(([href, text]) => (
            <Link key={href} href={href} className="card" style={{ background: "var(--card-strong)" }}>
              {text}
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}

