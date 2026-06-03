import { AgenticExplorer } from "@/components/AgenticExplorer";
import { getSetup } from "@/lib/api";

export default async function AgenticPage() {
  const setup = await getSetup();
  const userIds = setup?.summary?.evaluated_user_ids ?? setup?.summary?.sample_user_ids ?? [];

  return <AgenticExplorer setup={setup} userIds={userIds} />;
}
