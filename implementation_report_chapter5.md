# Chapter 5 - Implementation Report: H&M Hybrid SVD + 3-Agent Recommendation Artefact

## Section A. Executive Implementation Summary

The implemented artefact is a read-only dissertation demonstration built around saved recommendation and explainability outputs rather than live recommendation generation. The current supervisor-facing route is `/artifact-demo`, and the page is populated from precomputed SVD, standalone 3-Agent, Hybrid, evaluation, and explainability artefacts loaded by a dedicated walkthrough endpoint rather than by rerunning experiments at request time (`README.md`; `frontend/app/artifact-demo/page.tsx`; `backend/app/api/demo.py`; `backend/app/services/artifact_demo_service.py`).

The implemented walkthrough is organised into three method views: SVD, 3-Agent, and Hybrid. These views present per-user recommendation cases, method-specific context, and a Hybrid explainability audit for a small set of saved demo users. The implementation therefore supports a reproducible, offline artefact presentation rather than a live recommender or an autonomous multi-agent production system (`README.md`; `PROJECT.md`; `frontend/components/ArtifactDemoTabs.tsx`; `backend/app/services/artifact_demo_service.py`).

## Section B. Frontend Implementation

The frontend is a Next.js App Router application. The main dissertation artefact route is `frontend/app/artifact-demo/page.tsx`, which is an async server component that calls `getWorkflowCases()` and renders `ArtifactDemoTabs` with the returned `cases` payload (`frontend/package.json`; `frontend/app/artifact-demo/page.tsx`; `frontend/lib/api.ts`).

`ArtifactDemoTabs` implements the visible artefact surface. It maintains the active tab state, selected demo user, and a client-side recovery fetch if the initial server render has no cases. The component renders a one-page interface with exactly three tabs: `svd`, `agentic`, and `hybrid` (`frontend/components/ArtifactDemoTabs.tsx`; `PROJECT.md`).

The SVD tab renders an SVD method header, a compact user summary panel, a behavioural interaction card, and an SVD Top-10 recommendation section. The visible SVD metadata includes the held-out ground-truth article and article descriptors such as `product_type_name`, `product_group_name`, and `colour_group_name`, along with recommendation ranks and scores (`frontend/components/ArtifactDemoTabs.tsx`; `backend/app/models/schemas.py`).

The 3-Agent tab renders three header cards for the Preference Agent, Evidence Agent, and Decision Agent, followed by a user summary panel, a user preference section, a candidate evidence section, and a final recommendation section. The preference section visibly surfaces `inferred_intent`, `preferred_product_types`, `preferred_categories`, `preferred_colours`, and `preferred_appearance` as labels or chips. It also renders four `PreferenceBarChart` components for `frequent_product_types`, `frequent_product_groups`, `frequent_colours`, and `frequent_graphical_appearances`; however, in the current walkthrough service path, `_build_case()` is called with `history_rows=[]`, so those frequency arrays are built from an empty history input unless other backend wiring changes this behaviour (`frontend/components/ArtifactDemoTabs.tsx`; `backend/app/services/artifact_demo_service.py`; `backend/app/models/schemas.py`).

The Hybrid tab renders a six-step flow diagram, a compact user summary panel, three signal cards, a Hybrid Top-10 recommendation section, an explainability audit card, and an explicit limitation card. The formula card visibly displays `0.70 x normalized_svd_score`, `0.25 x normalized_agentic_score`, and `0.05 x diversity_bonus`, and the audit card renders fields for selected article, groundedness, Hybrid rank, SVD rank, rank shift, hit status, preference trace, product name, article metadata chips, matched preference fields, and explanation text when present (`frontend/components/ArtifactDemoTabs.tsx`; `frontend/lib/api.ts`; `handoff_next_stage.md`; `PROJECT.md`).

The visible demo-user selector is populated from saved walkthrough cases. `getWorkflowCases()` calls `/demo/workflow-cases?artifact_prefix=seed99_robustness&explainability_prefix=seed99_full_retry`, and the TypeScript response shape expects `artifact_prefix`, `explainability_prefix`, and `cases`, where each case includes `svd_top10`, `agentic_top10`, `hybrid_top10`, `preference_agent`, `leave_one_out`, `ground_truth`, `method_hits`, and `hybrid_explainability` data (`frontend/lib/api.ts`; `backend/app/models/schemas.py`; `backend/app/api/demo.py`).

Evaluation metrics tables are not rendered on the `/artifact-demo` page. The current artefact surface focuses on per-user walkthrough content rather than aggregate tables such as HitRate@10, NDCG@10, or ILD@10 (`frontend/components/ArtifactDemoTabs.tsx`; `PROJECT.md`; `handoff_next_stage.md`).

## Section C. Backend Implementation

The route supporting the dissertation artefact is `GET /demo/workflow-cases` in `backend/app/api/demo.py`. It accepts `artifact_prefix` and `explainability_prefix`, depends on `ExperimentService` for settings access, instantiates `ArtifactDemoService` with those settings, and returns the loaded walkthrough payload (`backend/app/api/demo.py`).

`ArtifactDemoService` is the read-only adapter for the artefact walkthrough. Its `load_workflow_cases()` method resolves six saved artefact paths: evaluation base, SVD recommendations, agentic recommendations, Hybrid recommendations, per-user metrics, and explainability examples CSV. It validates that those files exist, loads the JSON and CSV inputs, normalises customer IDs, intersects the user sets available across the recommendation and evaluation artefacts, prioritises users that have explainability rows, and returns up to five cases (`backend/app/services/artifact_demo_service.py`; `PROJECT.md`).

The current walkthrough payload is assembled from saved files rather than runtime experiment execution. `load_workflow_cases()` reads from disk with `read_text()` and `pd.read_csv()`, builds lookup tables, and maps the saved rows into the frontend-facing schema. In this code path it does not call recommendation-generation methods, retraining logic, or experiment-running endpoints (`backend/app/services/artifact_demo_service.py`; `README.md`; `PROJECT.md`).

Within `_build_case()`, the backend constructs the response sections used by the frontend: `demo_user`, `leave_one_out`, `ground_truth`, `method_hits`, `preference_agent`, `evidence_agent`, `decision_agent`, `svd_top10`, `agentic_top10`, `hybrid_top10`, and `hybrid_explainability`. `_select_explanation_row()` chooses a preferred explainability row for the selected user, `_map_method_items()` maps recommendation entries into a consistent item shape, and `_build_explanation_warnings()` records missing product-name or explanation-text cases (`backend/app/services/artifact_demo_service.py`; `backend/app/models/schemas.py`).

## Section D. Data Processing and Offline Workflow

The repository documentation describes an offline pipeline based on H&M raw data files placed in `backend/app/data/raw/`, including `transactions_train.csv`, `articles.csv`, and `customers.csv`. The processed outputs referenced by the artefact include joined interaction data, evaluation-base artefacts, recommendation artefacts, metric artefacts, and explainability artefacts stored under `backend/app/data/processed/` and `backend/app/data/processed/explainability/` (`README.md`; `PROJECT.md`; directory listings under `backend/app/data/processed/`).

The current walkthrough service directly consumes the saved offline outputs for the seed99 robustness run. The concrete filenames referenced in code are `seed99_robustness_evaluation_base_table_top10_1000.json`, `seed99_robustness_svd_recommendations_top10_1000.json`, `seed99_robustness_agentic_recommendations_top10_1000.json`, `seed99_robustness_hybrid_svd_agentic_recommendations_top10_1000.json`, `seed99_robustness_per_user_metrics_top10_1000_three_methods.json`, and `seed99_full_retry_explainability_examples.csv` (`backend/app/services/artifact_demo_service.py`; `backend/app/data/processed/`; `backend/app/data/processed/explainability/`).

The explainability layer is also documented and implemented as an offline audit over saved Hybrid outputs rather than as a live recommender feature. Project documentation points to `backend/app/services/explainability_service.py`, the CLI runner `python -m backend.scripts.run_explainability_audit`, the backend endpoint `GET /metrics/explainability`, and the frontend route `/explainability-evidence` as the explainability evidence path (`PROJECT.md`; `handoff_next_stage.md`; `frontend/lib/api.ts`).

## Section E. Saved Outputs and Artefact Structure

The main saved artefact categories used by the current implementation are recommendation outputs, evaluation outputs, metric outputs, validation outputs, and explainability outputs (`backend/app/data/processed/`; `backend/app/data/processed/explainability/`; `backend/app/services/artifact_demo_service.py`).

Recommendation outputs include the seed99 robustness SVD, agentic, and Hybrid Top-10 recommendation files. These are frontend-visible because the walkthrough service maps them into `svd_top10`, `agentic_top10`, and `hybrid_top10`, which are rendered on the three tabs (`backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`).

Evaluation outputs include the seed99 robustness evaluation base and per-user metrics files. These are partly frontend-visible through derived fields such as training history count, candidate pool size, ground-truth metadata, method hit status, and fallback rank-shift calculation, but the raw tables themselves are backend-saved artefacts rather than frontend tables (`backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`).

Explainability outputs include `seed99_full_retry_explainability_examples.csv` and summary or audit files under `backend/app/data/processed/explainability/`. The examples CSV is directly consumed by the walkthrough service and partly surfaced in the Hybrid audit section, while the summary and audit files support the separate explainability evidence path rather than the main `/artifact-demo` tab surface (`backend/app/services/artifact_demo_service.py`; `backend/app/data/processed/explainability/`; `PROJECT.md`; `handoff_next_stage.md`).

Validation artefacts such as `seed99_robustness_agentic_top10_validation_report_1000.json`, `seed99_robustness_svd_baseline_validation_report_top10_1000.json`, `seed99_robustness_hybrid_svd_agentic_validation_report_top10_1000.json`, and `seed99_robustness_validation_report_top10_1000_three_methods.json` are present in the processed output directory. These support implementation integrity and reporting, but they are not directly rendered on the `/artifact-demo` page (`backend/app/data/processed/`; `PROJECT.md`).

## Section F. Validation and Implementation Safety Evidence

The backend response contract is defined with Pydantic models in `backend/app/models/schemas.py`, including `ArtifactDemoWorkflowCase`, `ArtifactDemoMethodItem`, `ArtifactDemoExplanationPanel`, and related nested models. The frontend mirrors the same structure in TypeScript types inside `frontend/lib/api.ts`. This is clear evidence of typed response modelling across the walkthrough path (`backend/app/models/schemas.py`; `frontend/lib/api.ts`).

The repository documentation records frontend verification commands for type-checking and production build: `npx.cmd tsc --noEmit` and `npm.cmd run build`. The same documentation also records a backend pytest command for the test suite. These items are evidence of validation practices in the project, although this report does not claim that every test file was re-run during this read-only inspection (`PROJECT.md`).

The current implementation also includes explicit fallback handling for missing explanation fields. In `ArtifactDemoService`, `_build_explanation_warnings()` adds warnings when `prod_name` or `explanation_text` are unavailable, and the schema includes an availability block with `prod_name_available`. The frontend visibly renders a limitation statement that the artefact is offline and does not claim CTR, CVR, conversion, live customer engagement, add-to-cart behaviour, dwell time, or live feedback adaptation (`backend/app/services/artifact_demo_service.py`; `backend/app/models/schemas.py`; `frontend/components/ArtifactDemoTabs.tsx`; `README.md`).

## Section G. Tools and Languages

The codebase and configuration files directly support Python, FastAPI, Uvicorn, pandas, NumPy, pydantic, pydantic-settings, HTTPX, OpenAI, pytest, SciPy, and scikit-learn on the backend, and TypeScript, Next.js, React, and Recharts on the frontend (`backend/requirements.txt`; `backend/app/main.py`; `frontend/package.json`).

## Section H. Dissertation-Safe Writing Notes

### 1. What Is Safe to Claim in Chapter 5

It is safe to describe the artefact as an offline, read-only dissertation demonstration that reads saved SVD, standalone 3-Agent, Hybrid, evaluation, and explainability outputs and presents them through a supervisor-facing walkthrough route. It is also safe to state that the current frontend visibly implements three method views - SVD, 3-Agent, and Hybrid - and that the backend walkthrough endpoint assembles deterministic cases from saved files rather than rerunning experiments (`README.md`; `frontend/components/ArtifactDemoTabs.tsx`; `backend/app/api/demo.py`; `backend/app/services/artifact_demo_service.py`).

It is also safe to state that the implementation includes a separate explainability evidence layer based on saved Hybrid artefacts, a typed backend/frontend payload contract, and explicit UI limitation language about the offline scope of the artefact (`PROJECT.md`; `handoff_next_stage.md`; `backend/app/models/schemas.py`; `frontend/lib/api.ts`; `frontend/components/ArtifactDemoTabs.tsx`).

### 2. What Is NOT Safe to Claim in Chapter 5

It is not safe to describe the artefact as a live recommender, a production-facing autonomous multi-agent system, or a system that measures live customer engagement outcomes such as CTR, CVR, conversion, add-to-cart behaviour, dwell time, or adaptive feedback learning. It is also not safe to claim that all frontend-visible preference charts currently reflect populated frequency data from the walkthrough service, because the present `ArtifactDemoService` code builds those chart arrays from an empty `history_rows` input in this route path (`README.md`; `frontend/components/ArtifactDemoTabs.tsx`; `backend/app/services/artifact_demo_service.py`).

It is also not safe to claim that aggregate evaluation tables are rendered on `/artifact-demo`, because the current tab surface is a per-user walkthrough rather than an aggregate metrics dashboard (`frontend/components/ArtifactDemoTabs.tsx`; `PROJECT.md`; `handoff_next_stage.md`).

---

## Concise File Inventory of Most Important Implementation Files Inspected

1. `implementation_report_chapter5.md`
2. `README.md`
3. `PROJECT.md`
4. `handoff_next_stage.md`
5. `frontend/app/artifact-demo/page.tsx`
6. `frontend/components/ArtifactDemoTabs.tsx`
7. `frontend/lib/api.ts`
8. `frontend/package.json`
9. `backend/app/api/demo.py`
10. `backend/app/services/artifact_demo_service.py`
11. `backend/app/models/schemas.py`
12. `backend/app/main.py`
13. `backend/requirements.txt`
14. `backend/app/data/processed/`
15. `backend/app/data/processed/explainability/`

## Known Uncertainties

1. This report does not claim direct line-by-line verification of `backend/app/services/hybrid_service.py`, `backend/app/services/explainability_service.py`, `backend/app/services/evaluation_service.py`, `backend/app/services/agentic_service.py`, `backend/app/services/cf_service.py`, or `backend/app/services/data_service.py`. Where those parts of the system are discussed, the wording is limited to what is supported by inspected documentation, saved artefact paths, and the currently inspected walkthrough code (`PROJECT.md`; `handoff_next_stage.md`; `backend/app/services/artifact_demo_service.py`).

2. The separate `/explainability-evidence` surface and `GET /metrics/explainability` path are documented in project files and referenced in frontend API code, but this report does not claim a full direct audit of the explainability page component itself (`PROJECT.md`; `handoff_next_stage.md`; `frontend/lib/api.ts`).

3. The presence of validation and metrics artefacts in `backend/app/data/processed/` is directly observable from the current directory listing, but this report does not claim that every saved JSON or CSV file was opened and read in full during this pass (`backend/app/data/processed/`; `backend/app/data/processed/explainability/`).
