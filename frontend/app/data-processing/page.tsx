import { ChartCard } from "@/components/ChartCard";
import { MetricCard } from "@/components/MetricCard";
import { getSetup } from "@/lib/api";

export default async function DataProcessingPage() {
  const setup = await getSetup();
  const summary = setup?.summary;

  return (
    <div className="stack">
      <section className="card">
        <span className="eyebrow">Preprocessing</span>
        <h2 className="section-title">Interaction Sample and Metadata Profile</h2>
        <p className="muted">
          Transactions are merged with article metadata, filtered for usable interactions, sampled,
          and split into historical train data and future test data.
        </p>
      </section>

      <section className="grid three">
        <MetricCard label="Interactions" value={String(summary?.sample_size ?? 0)} />
        <MetricCard label="Users" value={String(summary?.distinct_users ?? 0)} />
        <MetricCard label="Products" value={String(summary?.distinct_products ?? 0)} />
      </section>

      <section className="grid two">
        <MetricCard label="Train Size" value={String(summary?.train_size ?? 0)} />
        <MetricCard
          label="Split Boundary"
          value={summary?.split_boundary_date ?? "Not available"}
          detail="Last date included in training data"
        />
      </section>

      <section className="grid two">
        <ChartCard title="Top Product Groups" data={summary?.top_product_groups ?? []} />
        <ChartCard title="Top Colours" data={summary?.top_colours ?? []} color="#c46e3b" />
      </section>

      <section className="grid two">
        <ChartCard title="Top Appearances" data={summary?.top_appearances ?? []} color="#4d7b94" />
        <article className="card">
          <strong>Why this page matters</strong>
          <p className="muted">
            The dashboard makes the experiment traceable: viewers can see the size of the offline
            sample and whether the core metadata dimensions used by the agentic layer are present.
          </p>
        </article>
      </section>
    </div>
  );
}

