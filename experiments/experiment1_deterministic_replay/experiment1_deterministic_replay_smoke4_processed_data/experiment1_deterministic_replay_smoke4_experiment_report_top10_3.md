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

- users_evaluated: 3
- users_with_svd_metrics: 3
- users_with_agentic_metrics: 3
- users_with_hybrid_metrics: 3
- svd_top_10_count_check: 3
- agentic_top_10_count_check: 3
- hybrid_top_10_count_check: 3
- svd_recommendations_inside_candidate_pool_check: 3
- agentic_recommendations_inside_candidate_pool_check: 3
- hybrid_recommendations_inside_candidate_pool_check: 3
- missing_metadata_for_diversity_count: 0
- metric_calculation_errors: []

## Final Metrics

- SVD HitRate@10: 1.000000
- SVD NDCG@10: 0.567439
- SVD ILD@10: 0.723457
- Standalone 3-Agent HitRate@10: 0.333333
- Standalone 3-Agent NDCG@10: 0.105155
- Standalone 3-Agent ILD@10: 0.493827
- Hybrid HitRate@10: 0.666667
- Hybrid NDCG@10: 0.444444
- Hybrid ILD@10: 0.641975

## Bootstrap Confidence Intervals

- svd_hit_rate_at_10: mean=1.000000, 95% CI [1.000000, 1.000000]
- agentic_hit_rate_at_10: mean=0.341333, 95% CI [0.000000, 1.000000]
- hybrid_hit_rate_at_10: mean=0.661000, 95% CI [0.000000, 1.000000]
- svd_ndcg_at_10: mean=0.558655, 95% CI [0.315465, 1.000000]
- agentic_ndcg_at_10: mean=0.107679, 95% CI [0.000000, 0.315465]
- hybrid_ndcg_at_10: mean=0.433444, 95% CI [0.000000, 1.000000]
- svd_ild_at_10: mean=0.722509, 95% CI [0.644444, 0.762963]
- agentic_ild_at_10: mean=0.491761, 95% CI [0.303704, 0.600000]
- hybrid_ild_at_10: mean=0.640363, 95% CI [0.585185, 0.718519]
- difference_hybrid_minus_svd_hit_rate_at_10: mean=-0.339000, 95% CI [-1.000000, 0.000000]
- difference_hybrid_minus_svd_ndcg_at_10: mean=-0.125211, 95% CI [-0.315465, 0.000000]
- difference_hybrid_minus_svd_ild_at_10: mean=-0.082146, 95% CI [-0.140741, -0.044444]
- difference_hybrid_minus_agentic_hit_rate_at_10: mean=0.319667, 95% CI [0.000000, 1.000000]
- difference_hybrid_minus_agentic_ndcg_at_10: mean=0.325766, 95% CI [0.000000, 1.000000]
- difference_hybrid_minus_agentic_ild_at_10: mean=0.148602, 95% CI [0.022222, 0.281481]

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
