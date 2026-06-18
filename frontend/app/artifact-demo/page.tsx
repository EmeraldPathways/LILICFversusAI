import { ArtifactDemoTabs } from "@/components/ArtifactDemoTabs";
import { getExplainabilityEvidence, getWorkflowCases } from "@/lib/api";

export default async function ArtifactDemoPage() {
  const [workflowPayload, explainability] = await Promise.all([
    getWorkflowCases(),
    getExplainabilityEvidence({
      artifactPrefix: "seed99_robustness",
      outputPrefix: "seed99_full_retry",
    }),
  ]);

  return (
    <ArtifactDemoTabs
      workflowCases={workflowPayload?.cases ?? []}
      explainability={explainability}
    />
  );
}
