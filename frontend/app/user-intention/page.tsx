import { UserIntentExplorer } from "@/components/UserIntentExplorer";
import { getSetup } from "@/lib/api";

export default async function UserIntentionPage() {
  const setup = await getSetup();
  const userIds = setup?.summary?.sample_user_ids ?? [];

  return (
    <div className="stack">
      <section className="card">
        <span className="eyebrow">Agent 1</span>
        <h2 className="section-title">User Shopping Intention Understanding</h2>
        <p className="muted">
          This view exposes the LLM-backed user profile used to guide candidate retrieval,
          reasoning, and explanation generation.
        </p>
      </section>
      <UserIntentExplorer userIds={userIds} />
    </div>
  );
}

