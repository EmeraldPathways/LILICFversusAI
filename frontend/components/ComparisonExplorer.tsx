"use client";

import { useEffect, useState } from "react";

import { RecommendationTable } from "@/components/RecommendationTable";
import type { RecommendationComparison } from "@/lib/api";
import { getRecommendationComparison } from "@/lib/api";

type ComparisonExplorerProps = {
  userIds: string[];
};

export function ComparisonExplorer({ userIds }: ComparisonExplorerProps) {
  const [selectedUser, setSelectedUser] = useState(userIds[0] ?? "");
  const [comparison, setComparison] = useState<RecommendationComparison | null>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    if (!selectedUser) {
      return;
    }
    getRecommendationComparison(selectedUser)
      .then((data) => {
        setComparison(data);
        setError("");
      })
      .catch((fetchError) => {
        setComparison(null);
        setError(fetchError instanceof Error ? fetchError.message : "Unable to fetch recommendations.");
      });
  }, [selectedUser]);

  if (!userIds.length) {
    return <section className="card muted">Run the backend experiment to populate sample users.</section>;
  }

  return (
    <div className="stack">
      <div className="controls">
        <select value={selectedUser} onChange={(event) => setSelectedUser(event.target.value)}>
          {userIds.map((userId) => (
            <option key={userId} value={userId}>
              {userId}
            </option>
          ))}
        </select>
      </div>
      {error ? <section className="card muted">{error}</section> : null}
      {comparison ? (
        <div className="grid two">
          <RecommendationTable
            title="Collaborative Filtering Benchmark"
            userId={comparison.user_id}
            items={comparison.cf_recommendations}
          />
          <RecommendationTable
            title="Agentic AI Recommendation Framework"
            userId={comparison.user_id}
            items={comparison.agentic_recommendations}
            showReasons
          />
        </div>
      ) : null}
    </div>
  );
}

