import { ComparisonDashboard } from "@/components/ComparisonDashboard";
import { getSetup } from "@/lib/api";

export default async function ComparisonPage() {
  const setup = await getSetup();
  const userIds = setup?.summary?.evaluated_user_ids ?? setup?.summary?.sample_user_ids ?? [];

  return <ComparisonDashboard setup={setup} userIds={userIds} />;
}
