# Handoff Next Stage

## 1. Project Purpose

This repository contains a formal offline H&M recommender experiment comparing three methods on the same leave-one-out next-item task:

1. SVD Matrix Factorisation baseline
2. Standalone 3-Agent recommender
3. Hybrid SVD + 3-Agent reranker

The current experiment is an offline ranking evaluation, not a live product deployment or live customer engagement study.

## 2. Current Correct Repo Path

`D:\GOOGLE DRIVE\EMERALD PATHWAYS\WEB WORK\AI CODING\VS CODE\personal\LILI FINAL PAPER DEMO`

## 3. Current Branch

`formal-experiment-seed99-robustness`

## 4. Important Path Warning

There was a previous path mismatch during earlier work.

- Wrong folder: `D:\GOOGLE DRIVE\EMERALD PATHWAYS\WEB WORK\AI CODING\VS CODE\personal\LILI RESEARCH PROPOSAL`
- Correct folder: `D:\GOOGLE DRIVE\EMERALD PATHWAYS\WEB WORK\AI CODING\VS CODE\personal\LILI FINAL PAPER DEMO`

Future work must happen in `LILI FINAL PAPER DEMO`, not in `LILI RESEARCH PROPOSAL`.

## 5. Current Git Status Summary

Current branch head:

- `8d965b1 Add safe seed99 artifact naming for formal experiment`

Current modified tracked files that are not part of the seed99 safety commit and are still present in the working tree:

- `backend/app/api/metrics.py`
- `backend/app/api/recommendations.py`
- `backend/app/api/users.py`
- `backend/app/models/schemas.py`
- `backend/tests/test_api.py`
- `frontend/app/comparison/page.tsx`
- `frontend/app/data-processing/page.tsx`
- `frontend/app/evaluation/page.tsx`
- `frontend/app/research-setup/page.tsx`
- `frontend/components/AgentProcessPanel.tsx`
- `frontend/components/ComparisonExplorer.tsx`
- `frontend/components/ModelComparisonTable.tsx`
- `frontend/lib/api.ts`

Current untracked log files:

- `backend-dev.err.log`
- `backend-dev.log`
- `backend-experiment.err.log`
- `backend-experiment.log`
- `frontend-dev.err.log`
- `frontend-dev.log`

There is also a locked `.tmp/pytest` folder under the repo that produced earlier temp cleanup warnings. It is not part of the seed99 checkpoint and should remain unstaged.

## 6. Recent Safety Commit Details

Safety commit on the current branch:

- Commit: `8d965b1`
- Message: `Add safe seed99 artifact naming for formal experiment`

This commit contains:

- `artifact_prefix` support in processed artifact path resolution
- overwrite protection through `allow_overwrite` / `ensure_output_path`
- seed-specific prefixed naming support for future `seed99_robustness_*` outputs
- `backend/tests/test_output_naming.py`

Files included in that commit:

- `backend/app/config.py`
- `backend/app/services/data_service.py`
- `backend/app/services/cf_service.py`
- `backend/app/services/agentic_service.py`
- `backend/app/services/hybrid_service.py`
- `backend/app/services/evaluation_service.py`
- `backend/tests/test_output_naming.py`

## 7. Formal Experiment Design

The formal offline experiment uses:

- leave-one-out evaluation
- 1,000 valid users
- 100-item candidate pool per user
- Top-10 recommendations
- shared user-level evaluation base
- offline metrics with bootstrap confidence intervals

## 8. Three Methods

### SVD

The SVD baseline exists in `backend/app/services/cf_service.py` through `build_svd_top10_baseline(...)`.

### Standalone 3-Agent

The standalone 3-Agent Top-10 experiment logic exists in `backend/app/services/agentic_service.py` through `build_top10_formal_experiment(...)` and `_build_top10_formal_experiment(...)`.

### Hybrid

The hybrid reranker exists in `backend/app/services/hybrid_service.py` through `build_hybrid_svd_agentic_reranker(...)`.

## 9. Hybrid Formula

The hybrid formula remains:

```text
0.70 * normalized_svd_score
+ 0.25 * normalized_agentic_score
+ 0.05 * diversity_bonus
```

This was confirmed in `backend/app/services/hybrid_service.py`. It has not been changed in the seed99 safety work.

## 10. Evaluation Protocol

Current formal offline evaluation includes:

- HitRate@10
- NDCG@10
- ILD@10
- bootstrap 95% confidence interval reporting

These are implemented in `backend/app/services/evaluation_service.py`.

Confirmed current code capabilities:

- SVD logic exists
- standalone 3-Agent Top-10 logic exists
- Hybrid formula remains `0.70 / 0.25 / 0.05`
- HitRate@10, NDCG@10, ILD@10 exist
- bootstrap CI logic exists
- `artifact_prefix` support exists
- seed99 prefixed output naming exists
- overwrite protection exists

## 11. Previous Non-Prefixed 1,000-User Results

The following previous non-prefixed 1,000-user outputs exist in `backend/app/data/processed/`:

- `metric_summary_top10_1000_three_methods.json`
- `bootstrap_ci_report_top10_1000_three_methods.json`
- `svd_recommendations_top10_1000.json`
- `agentic_recommendations_top10_1000.json`
- `hybrid_svd_agentic_recommendations_top10_1000.json`
- `per_user_metrics_top10_1000_three_methods.json`
- `final_experiment_report_svd_agentic_hybrid.md`
- `hybrid_result_interpretation_check.md`
- `diagnostic_report_svd_vs_agentic_1000.md`

These appear to be the previous main 1,000-user result set and should not be overwritten.

## 12. Seed99 Robustness Results

As of this handoff, no `seed99_robustness_*` output artifacts were found in `backend/app/data/processed/`.

Missing seed99-prefixed outputs include:

- `seed99_robustness_metric_summary_top10_1000_three_methods.json`
- `seed99_robustness_bootstrap_ci_report_top10_1000_three_methods.json`
- `seed99_robustness_svd_recommendations_top10_1000.json`
- `seed99_robustness_agentic_recommendations_top10_1000.json`
- `seed99_robustness_hybrid_svd_agentic_recommendations_top10_1000.json`
- `seed99_robustness_per_user_metrics_top10_1000_three_methods.json`
- `seed99_robustness_validation_report_top10_1000_three_methods.json`
- `seed99_robustness_experiment_report_top10_1000.md`

This means the seed99 robustness run has not yet been executed in this repo state.

## 13. Files Currently Present in `backend/app/data/processed`

Notable current processed artifacts include:

- evaluation base tables for `100`, `1000`, and `all_valid`
- SVD Top-10 recommendations for `100` and `1000`
- standalone 3-Agent Top-10 recommendations for `100` and `1000`
- hybrid Top-10 recommendations for `1000`
- per-user metrics for `100`, `1000`, and `1000_three_methods`
- metric summaries for `100`, `1000`, and `1000_three_methods`
- bootstrap CI reports for `1000` and `1000_three_methods`
- validation reports and audit reports
- `final_experiment_report_svd_agentic_hybrid.md`
- `hybrid_result_interpretation_check.md`
- `diagnostic_report_svd_vs_agentic_1000.md`

Important note:

- `backend/app/data/processed/*` is ignored by Git via `.gitignore`
- these files exist locally but are not intended to be committed casually

## 14. What Has Been Confirmed Stable

- Correct repo path is `LILI FINAL PAPER DEMO`
- Correct working branch is `formal-experiment-seed99-robustness`
- Safety commit `8d965b1` exists on this branch
- Seed99 output naming support exists in code
- Prefixed writes can avoid overwriting existing non-prefixed 1,000-user outputs
- Overwrite protection is present for prefixed output generation
- Focused tests passed for:
  - `backend/tests/test_output_naming.py`
  - `backend/tests/test_formal_evaluation_service.py`
  - `backend/tests/test_hybrid_service.py`
- The focused tests were run successfully using an external temp directory outside the repo because the in-repo `.tmp/pytest` path was locked

## 15. What Is Still Unresolved

- The seed99 robustness experiment has not been run yet
- No seed99-prefixed outputs exist yet
- The working tree still has unrelated modified tracked UI/API files
- There are untracked runtime log files
- The locked `.tmp/pytest` directory can still produce warning noise in `git status --short`

## 16. Exact Next Recommended Action

Run the seed99 robustness sample from this repo state using the current branch and pass:

- `artifact_prefix="seed99_robustness"`
- the required seed / subset settings for the second independent 1,000-valid-user sample

Before doing that:

- do not change ranking logic
- do not change hybrid weights
- do not change metric definitions
- do not change bootstrap logic

After the run:

- verify all expected `seed99_robustness_*` outputs exist
- validate that previous non-prefixed outputs remain untouched
- inspect metric summary and bootstrap CI reports carefully before making any claims

## 17. What Must Not Be Changed

- SVD ranking logic
- standalone 3-Agent ranking logic
- hybrid formula / weights
- metric definitions
- bootstrap logic
- prior non-prefixed 1,000-user outputs

Also do not confuse the wrong folder (`LILI RESEARCH PROPOSAL`) with the correct one (`LILI FINAL PAPER DEMO`).

## 18. What Should Not Be Committed

- raw H&M CSVs in `backend/app/data/raw/`
- processed artifacts in `backend/app/data/processed/`
- runtime logs
- `.tmp/pytest`
- cache folders
- virtualenv files
- unrelated UI/API tracked changes unless that is a separate intentional task

Current processed files are ignored by Git and should remain treated as generated local artifacts.

## 19. When To Commit / Push

Do not push immediately after running seed99.

Recommended order:

1. Run the seed99 robustness experiment
2. Validate all `seed99_robustness_*` outputs
3. Review metric summary and bootstrap CI outputs
4. Confirm no unintended code or artifact path regressions
5. Commit intentional code changes only if any new code changes were actually made
6. Push only after explicit review/approval

## 20. Instructions For The Next Assistant / Next Codex Session

- Start in `D:\GOOGLE DRIVE\EMERALD PATHWAYS\WEB WORK\AI CODING\VS CODE\personal\LILI FINAL PAPER DEMO`
- Confirm branch is `formal-experiment-seed99-robustness`
- Do not operate in `LILI RESEARCH PROPOSAL`
- Treat `8d965b1` as the seed99 naming safety checkpoint
- Assume no `seed99_robustness_*` outputs exist yet unless you verify otherwise
- Preserve all non-prefixed 1,000-user outputs
- Use the existing formal experiment code paths, not legacy demo logic
- If tests are needed again, use an external temp directory outside the repo
- Do not stage unrelated UI/API files unless the user explicitly asks

Interpretation guardrails:

- Do not claim Hybrid beats SVD unless confidence intervals support it
- Do not claim agentic AI improves live customer engagement
- Do not claim CTR or CVR improved
- Do not claim feedback adaptation was validated
- Do not claim users perceived explanations as useful

Allowed careful framing:

- SVD is the strong offline baseline
- Standalone 3-Agent is an ablation, not a failure to hide
- Hybrid is an augmentation / reranking layer
- Results are offline ranking quality and explainability-related, not proof of live customer engagement

## 21. Seed99 Robustness Run Completed

- seed99 run completed: yes
- users_evaluated = 1000
- validation passed = yes

Seed99 metrics:

- SVD: HitRate@10 `0.505000`, NDCG@10 `0.296245`, ILD@10 `0.755089`
- Standalone 3-Agent: HitRate@10 `0.269000`, NDCG@10 `0.154352`, ILD@10 `0.539319`
- Hybrid: HitRate@10 `0.526000`, NDCG@10 `0.312443`, ILD@10 `0.692919`

Key pairwise CI interpretation:

- Hybrid minus SVD HitRate@10 CI: `[-0.001000, 0.042000]`
- Hybrid minus SVD NDCG@10 CI: `[0.007190, 0.025000]`
- Hybrid minus SVD ILD@10 CI: `[-0.066816, -0.057555]`
- Hybrid minus Standalone 3-Agent HitRate@10 CI: `[0.225950, 0.286000]`
- Hybrid minus Standalone 3-Agent NDCG@10 CI: `[0.133920, 0.180924]`
- Hybrid minus Standalone 3-Agent ILD@10 CI: `[0.146976, 0.160104]`

Careful final interpretation:

The seed99 robustness run broadly confirms the previous 1,000-user findings. SVD remains much stronger than the standalone 3-agent recommender. The Hybrid method remains much stronger than standalone 3-agent. In seed99, Hybrid improves NDCG@10 over SVD, but it does not clearly improve HitRate@10 because the confidence interval crosses zero. Hybrid remains less diverse than SVD. Therefore, the dissertation should frame the Hybrid method as an augmentation and reranking layer that can improve ranking position quality and provide evidence-based explainability, not as a full replacement for SVD.

Guardrails:

- Do not claim live customer engagement improvement.
- Do not claim CTR/CVR improvement.
- Do not claim feedback adaptation was validated.
- Do not claim Hybrid universally beats SVD.
- Do not hide the standalone 3-agent ablation result.

## 22. Explainability Evidence Layer

The repository now includes a separate explainability evidence layer for the Hybrid SVD + 3-Agent reranker.

This layer does not change the recommendation algorithms or formal ranking metrics. Instead, it audits whether the Hybrid SVD + 3-Agent reranker exposes source-grounded evidence from user history, item metadata, score components and reranking movement. This supports the interpretation of Hybrid as an explainability-oriented augmentation layer over SVD, while preserving the limitation that the study is offline and cannot establish live customer engagement or conversion gains.

### Backend additions

- Service: `backend/app/services/explainability_service.py`
- CLI: `python -m backend.scripts.run_explainability_audit --artifact-prefix seed99_robustness --sample-size 100 --output-prefix seed99`
- API endpoint: `GET /metrics/explainability`
- Frontend route: `/explainability-evidence`

### Explainability artifacts

All explainability outputs are written under:

- `backend/app/data/processed/explainability/`

Generated files:

- `seed99_explainability_summary.json`
- `seed99_explainability_audit.json`
- `seed99_explainability_examples.csv`
- `seed99_rank_shift_analysis.csv`
- `seed99_case_studies.md`

Additional validated output sets now exist:

- `seed99_perf_check_*` for the post-optimisation 100-user verification run
- `seed99_full_retry_*` for the completed full 1,000-user explainability audit

### Explainability metrics

- `evidence_coverage_rate`: share of Hybrid explanation rows with at least one usable core metadata field
- `preference_trace_rate`: share of rows with at least one user-history metadata match
- `score_component_coverage_rate`: share of rows where all saved Hybrid score components are present
- `groundedness_rate`: grounded structured claims divided by all structured claims
- `rank_shift_coverage_rate`: share of rows where both SVD and Hybrid rank positions are observable
- `ungrounded_claim_count`: number of unsupported structured claims
- `average_rank_shift_for_ground_truth_hits`: average promotion/demotion of the held-out item where observable

### Interpretation guardrails

- This is not a live user study.
- Do not claim CTR, CVR, customer engagement, conversion, add-to-cart, dwell time, or live feedback adaptation improvement.
- The explainability layer is an offline evidence audit over saved artifacts.
- The diversity trade-off must remain explicit:
  `Hybrid improves explainability and remains competitive on ranking quality, but it reduces intra-list diversity compared with SVD.`

## 23. Explainability Audit Performance And Full-Scale Result

The full 1,000-user explainability audit originally timed out because the explainability service repeatedly filtered the full `processed_interactions_with_articles.csv` table inside the per-user loop when building user-history summaries.

That bottleneck has now been removed inside the read-only explainability path only. The optimisation:

- selects the relevant users from saved Hybrid artifacts first
- collects only the needed training and recommendation article IDs
- reads only required columns from the processed CSV
- filters relevant rows in chunks
- precomputes metadata and user-history summaries once before the per-user loop

This optimisation does **not** modify:

- SVD recommendation logic
- Standalone 3-Agent logic
- Hybrid recommendation logic
- Hybrid formula
- formal ranking metrics
- candidate pool logic
- saved formal experiment artifacts

### 100-user explainability verification

The post-optimisation 100-user explainability performance check reproduced the prior key metrics exactly:

- `users_included = 100`
- `recommendations_explained = 1000`
- `evidence_coverage_rate = 1.000`
- `preference_trace_rate = 1.000`
- `score_component_coverage_rate = 1.000`
- `groundedness_rate = 1.000`
- `rank_shift_coverage_rate = 0.682`
- `ungrounded_claim_count = 0`
- `average_rank_shift_for_ground_truth_hits = 0.212766`

### Full 1,000-user explainability audit

The full explainability audit now completes successfully for:

- command:
  `python -m backend.scripts.run_explainability_audit --artifact-prefix seed99_robustness --sample-size 1000 --output-prefix seed99_full_retry`
- runtime observed in Codex: about `252.8` seconds

Full 1,000-user explainability metrics:

- `users_included = 1000`
- `recommendations_explained = 10000`
- `evidence_coverage_rate = 1.0000`
- `preference_trace_rate = 0.9954`
- `score_component_coverage_rate = 1.0000`
- `groundedness_rate = 1.0000`
- `rank_shift_coverage_rate = 0.6974`
- `ungrounded_claim_count = 0`
- `average_rank_shift_for_ground_truth_hits = 0.274725`

Warnings:

- `prod_name` remains unavailable in the processed source and is reported as missing rather than fabricated.

Validation outcome:

- full backend tests passed after the optimisation
- explainability service tests passed after the optimisation
- 100-user explainability outputs remained semantically consistent
- the four checked `seed99_robustness_*` formal source artifacts remained unchanged by size and timestamp
