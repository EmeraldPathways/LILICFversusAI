# Hybrid SVD + 3-Agent Audit Report

## Why Hybrid Was Added

The standalone 3-agent method underperformed SVD in the saved 1,000-user offline evaluation.
The hybrid experiment tests whether agentic evidence can help as a reranking signal on top of SVD rather than replacing SVD.

## Method Description

- SVD remains the main behavioural relevance signal.
- The standalone 3-agent score is used as a metadata evidence signal.
- A small diversity bonus is applied during iterative Top-10 selection.

## Hybrid Scoring Formula

```text
hybrid_score = 0.70 * normalized_svd_score
             + 0.25 * normalized_agentic_score
             + 0.05 * diversity_bonus
```

## Validation Checks

- users_evaluated: 1000
- users_with_svd_metrics: 1000
- users_with_agentic_metrics: 1000
- users_with_hybrid_metrics: 1000
- svd_top_10_count_check: 1000
- agentic_top_10_count_check: 1000
- hybrid_top_10_count_check: 1000
- svd_recommendations_inside_candidate_pool_check: 1000
- agentic_recommendations_inside_candidate_pool_check: 1000
- hybrid_recommendations_inside_candidate_pool_check: 1000
- missing_metadata_for_diversity_count: 0
- metric_calculation_errors: []

## Final Metrics

- SVD HitRate@10: 0.500000
- SVD NDCG@10: 0.295493
- SVD ILD@10: 0.751933
- Standalone 3-Agent HitRate@10: 0.274000
- Standalone 3-Agent NDCG@10: 0.155365
- Standalone 3-Agent ILD@10: 0.543800
- Hybrid HitRate@10: 0.498000
- Hybrid NDCG@10: 0.304552
- Hybrid ILD@10: 0.694481

## Bootstrap Confidence Intervals

- svd_hit_rate_at_10: mean=0.500116, 95% CI [0.467975, 0.529000]
- agentic_hit_rate_at_10: mean=0.274028, 95% CI [0.247000, 0.303000]
- hybrid_hit_rate_at_10: mean=0.497798, 95% CI [0.466975, 0.527000]
- svd_ndcg_at_10: mean=0.295371, 95% CI [0.272764, 0.317322]
- agentic_ndcg_at_10: mean=0.155690, 95% CI [0.138165, 0.173654]
- hybrid_ndcg_at_10: mean=0.304259, 95% CI [0.281050, 0.326226]
- svd_ild_at_10: mean=0.752100, 95% CI [0.747293, 0.756876]
- agentic_ild_at_10: mean=0.544017, 95% CI [0.537007, 0.550698]
- hybrid_ild_at_10: mean=0.694626, 95% CI [0.688822, 0.700097]
- difference_hybrid_minus_svd_hit_rate_at_10: mean=-0.002318, 95% CI [-0.023000, 0.018025]
- difference_hybrid_minus_svd_ndcg_at_10: mean=0.008888, 95% CI [-0.000764, 0.018136]
- difference_hybrid_minus_svd_ild_at_10: mean=-0.057473, 95% CI [-0.062550, -0.052856]
- difference_hybrid_minus_agentic_hit_rate_at_10: mean=0.223770, 95% CI [0.192975, 0.254025]
- difference_hybrid_minus_agentic_ndcg_at_10: mean=0.148568, 95% CI [0.124614, 0.169055]
- difference_hybrid_minus_agentic_ild_at_10: mean=0.150609, 95% CI [0.143954, 0.157482]

## Did Hybrid Improve?

- Hybrid improved over SVD on offline relevance: False
- Hybrid improved over standalone 3-agent on offline relevance: True

## Honest Interpretation

- The saved offline metrics do not show the hybrid outperforming SVD on relevance.
- SVD remains the strongest offline relevance baseline in this experiment.
- The hybrid outperforms standalone 3-agent on offline relevance.
- The hybrid improves diversity over standalone 3-agent.

## Limitations

- These are offline metrics only.
- They do not establish customer engagement, CTR, CVR, or business impact.
- The hybrid uses a fixed heuristic formula and was not tuned in this step.
