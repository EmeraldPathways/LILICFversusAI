import { ComparisonExplorer } from "@/components/ComparisonExplorer";
import { getSetup } from "@/lib/api";

export default async function ComparisonPage() {
  const setup = await getSetup();
  const userIds = setup?.summary?.evaluated_user_ids ?? setup?.summary?.sample_user_ids ?? [];

  return (
    <div className="stack">
      <section className="card">
        <span className="eyebrow">Model Comparison</span>
        <h2 className="section-title">Collaborative Filtering vs Agentic AI</h2>
        <p className="muted">
          The benchmark returns similarity-based products. The agentic model returns products with
          explicit reasons, exposes the five-agent pipeline, and supports simulated feedback
          adaptation.
        </p>
      </section>
      <ComparisonExplorer userIds={userIds} />
    </div>
  );
}
