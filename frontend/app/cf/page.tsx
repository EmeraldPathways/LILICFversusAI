import { CFExplorer } from "@/components/CFExplorer";
import { getSetup } from "@/lib/api";

export default async function CFPage() {
  const setup = await getSetup();
  const userIds = setup?.summary?.evaluated_user_ids ?? setup?.summary?.sample_user_ids ?? [];

  return <CFExplorer setup={setup} userIds={userIds} />;
}
