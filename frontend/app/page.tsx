import { AgenticExplorer } from "@/components/AgenticExplorer";
import { getSetup } from "@/lib/api";

export default async function AgenticPage() {
  const setup = await getSetup();
  const userIds =
    setup?.selected_user_ids ??
    setup?.completed_comparable_user_ids ??
    setup?.available_user_ids ??
    setup?.summary?.selected_user_ids ??
    setup?.summary?.completed_comparable_user_ids ??
    setup?.summary?.evaluated_user_ids ??
    setup?.summary?.sample_user_ids ??
    [];

  return <AgenticExplorer setup={setup} userIds={userIds} />;
}
