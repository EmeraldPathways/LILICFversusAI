# Frontend-Visible vs Backend-Saved Visibility Audit

## Scope

This report classifies the current `/artifact-demo` implementation into two buckets:

- **Frontend-visible**: data that is explicitly rendered on the current `/artifact-demo` page.
- **Backend-saved but not clearly frontend-visible**: data that is stored, loaded, or returned by the backend but is not explicitly rendered on the current `/artifact-demo` page.

The classification is based on the current frontend rendering code, the walkthrough API contract, the walkthrough service, and the saved artefact inventory. No files were modified during the audit (`frontend/app/artifact-demo/page.tsx`; `frontend/components/ArtifactDemoTabs.tsx`; `frontend/lib/api.ts`; `backend/app/api/demo.py`; `backend/app/services/artifact_demo_service.py`; `backend/app/models/schemas.py`).

---

## 1. Walkthrough Case Top-Level Fields

Source-backed shape: `ArtifactDemoWorkflowCase` in `frontend/lib/api.ts` and `backend/app/models/schemas.py`, populated by `ArtifactDemoService._build_case()` in `backend/app/services/artifact_demo_service.py`.

| Frontend-visible | Backend-saved but not clearly frontend-visible |
|---|---|
| `demo_user.label` - shown in the case selector and user summary (`frontend/components/ArtifactDemoTabs.tsx`) | top-level `label` - populated separately in the payload but not rendered independently from `demo_user.label` (`backend/app/services/artifact_demo_service.py`) |
| `demo_user.customer_id_short` - shown in the selector and summary (`frontend/components/ArtifactDemoTabs.tsx`) | `demo_user.customer_id` - used for selection and lookup, but the full value is not shown directly (`frontend/components/ArtifactDemoTabs.tsx`; `backend/app/services/artifact_demo_service.py`) |
| `leave_one_out.training_history_count` - shown in summary cards (`frontend/components/ArtifactDemoTabs.tsx`) | |
| `leave_one_out.ground_truth_article_id` - shown in the summary and SVD section (`frontend/components/ArtifactDemoTabs.tsx`) | |
| `leave_one_out.candidate_pool_size` - shown in the summary (`frontend/components/ArtifactDemoTabs.tsx`) | |
| `leave_one_out.ground_truth_in_candidate_pool` - shown as a visible status value/badge (`frontend/components/ArtifactDemoTabs.tsx`) | |
| `method_hits.svd`, `method_hits.agentic`, `method_hits.hybrid` - shown as visible hit/miss status values (`frontend/components/ArtifactDemoTabs.tsx`) | |
| `ground_truth.article_id`, `ground_truth.product_type_name`, `ground_truth.product_group_name`, `ground_truth.colour_group_name` - shown in the SVD signal card (`frontend/components/ArtifactDemoTabs.tsx`; `backend/app/services/artifact_demo_service.py`) | `ground_truth.garment_group_name` - present in the response but not rendered in the SVD signal card (`backend/app/models/schemas.py`; `backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`) |
| | `ground_truth.graphical_appearance_name` - present in the response but not rendered in the current SVD signal card (`backend/app/models/schemas.py`; `backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`) |

---

## 2. Preference Agent Fields

Source-backed shape: `ArtifactDemoPreferenceSummary` in `frontend/lib/api.ts` and `backend/app/models/schemas.py`, populated in `ArtifactDemoService._build_case()`.

| Frontend-visible | Backend-saved but not clearly frontend-visible |
|---|---|
| `inferred_intent` - shown as the section subtitle (`frontend/components/ArtifactDemoTabs.tsx`) | `availability.has_preference_summary` - returned by the backend but not rendered (`backend/app/services/artifact_demo_service.py`; `backend/app/models/schemas.py`) |
| `preferred_product_types[]` - shown as tags (`frontend/components/ArtifactDemoTabs.tsx`) | `availability.has_history_summary` - returned by the backend but not rendered (`backend/app/services/artifact_demo_service.py`; `backend/app/models/schemas.py`) |
| `preferred_categories[]` - shown as tags (`frontend/components/ArtifactDemoTabs.tsx`) | |
| `preferred_colours[]` - shown as tags (`frontend/components/ArtifactDemoTabs.tsx`) | |
| `preferred_appearance[]` - shown as tags (`frontend/components/ArtifactDemoTabs.tsx`) | |
| chart slots for `frequent_product_types[]`, `frequent_product_groups[]`, `frequent_colours[]`, and `frequent_graphical_appearances[]` are part of the rendered UI (`frontend/components/ArtifactDemoTabs.tsx`) | The current walkthrough service calls `_build_case(..., history_rows=[])`, so non-empty history-derived chart content cannot be confirmed from the current service path without additional backend wiring (`backend/app/services/artifact_demo_service.py`) |

---

## 3. Evidence Agent Fields

Source-backed shape: `ArtifactDemoEvidencePanel` in `frontend/lib/api.ts` and `backend/app/models/schemas.py`, populated in `ArtifactDemoService._build_case()`. The visible evidence cards are rendered from preview items taken from `agentic_top10` in `ArtifactDemoTabs.tsx`.

| Frontend-visible | Backend-saved but not clearly frontend-visible |
|---|---|
| evidence-card metadata fields `product_type_name`, `product_group_name`, `colour_group_name`, `graphical_appearance_name` - shown in evidence cards (`frontend/components/ArtifactDemoTabs.tsx`) | `evidence_agent.headline` - present in the payload but not rendered as a separate Evidence Agent field (`backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`) |
| `matched_evidence[]` - shown as chips in evidence cards (`frontend/components/ArtifactDemoTabs.tsx`) | `evidence_agent.availability.has_item_metadata` - returned but not rendered (`backend/app/services/artifact_demo_service.py`; `backend/app/models/schemas.py`) |
| `reason` / recommendation explanation text - shown in evidence cards (`frontend/components/ArtifactDemoTabs.tsx`) | `evidence_agent.availability.has_matched_evidence` - returned but not rendered (`backend/app/services/artifact_demo_service.py`; `backend/app/models/schemas.py`) |
| | `evidence_agent.item_metadata.article_id` - present in the response but not visibly shown as a labeled field (`backend/app/models/schemas.py`; `frontend/components/ArtifactDemoTabs.tsx`) |
| | `evidence_agent.item_metadata.garment_group_name` - present in the response but not shown in the visible four-field evidence card metadata grid (`backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`) |
| | `evidence_agent.item_metadata.prod_name` - present in the shape, but the service sets it to `None` for this panel and the UI does not render it here (`backend/app/services/artifact_demo_service.py`; `backend/app/models/schemas.py`) |

---

## 4. Decision Agent Fields

Source-backed shape: `ArtifactDemoDecisionPanel` in `frontend/lib/api.ts` and `backend/app/models/schemas.py`, populated in `ArtifactDemoService._build_case()`.

| Frontend-visible | Backend-saved but not clearly frontend-visible |
|---|---|
| no separate Decision Agent payload panel is rendered as its own field block | `decision_agent.headline` (`backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`) |
| | `decision_agent.selected_article_id` (`backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`) |
| | `decision_agent.selected_rank` (`backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`) |
| | `decision_agent.selected_score` (`backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`) |

The current 3-Agent tab renders the recommendation list from `agentic_top10`, not a separate visible panel based on `decision_agent` (`frontend/components/ArtifactDemoTabs.tsx`).

---

## 5. SVD Top-10 Recommendation Items

Source-backed shape: `ArtifactDemoMethodItem`, mapped by `_map_method_items()` for `svd_top10`.

| Frontend-visible | Backend-saved but not clearly frontend-visible |
|---|---|
| `article_id`, `rank`, `score`, `product_type_name`, `product_group_name`, `colour_group_name`, `graphical_appearance_name` - rendered in SVD recommendation cards (`frontend/components/ArtifactDemoTabs.tsx`; `backend/app/services/artifact_demo_service.py`) | `is_ground_truth` - included in mapped items but not shown on SVD cards (`backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`) |
| | `garment_group_name` - included in mapped items but not rendered in the SVD card metadata grid (`backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`) |
| | `reason`, `matched_evidence`, `hybrid_score`, `normalized_svd_score`, `normalized_agentic_score`, `diversity_bonus` - part of the general item shape but not used as visible SVD card fields (`backend/app/services/artifact_demo_service.py`; `backend/app/models/schemas.py`; `frontend/components/ArtifactDemoTabs.tsx`) |

---

## 6. 3-Agent Top-10 Recommendation Items

Source-backed shape: `ArtifactDemoMethodItem`, mapped by `_map_method_items()` for `agentic_top10`.

| Frontend-visible | Backend-saved but not clearly frontend-visible |
|---|---|
| `article_id`, `rank`, `score`, `product_type_name`, `product_group_name`, `colour_group_name`, `graphical_appearance_name`, `reason`, `matched_evidence[]` - rendered in the 3-Agent recommendation cards (`frontend/components/ArtifactDemoTabs.tsx`; `backend/app/services/artifact_demo_service.py`) | `is_ground_truth` - included in mapped items but not shown on the 3-Agent cards (`backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`) |
| | `garment_group_name` - included in mapped items but not rendered in the visible card metadata (`backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`) |
| | `hybrid_score`, `normalized_svd_score`, `normalized_agentic_score`, `diversity_bonus` - part of the general item shape but not visible on the 3-Agent cards (`backend/app/services/artifact_demo_service.py`; `backend/app/models/schemas.py`) |

---

## 7. Hybrid Top-10 Recommendation Items

Source-backed shape: `ArtifactDemoMethodItem`, mapped by `_map_method_items()` for `hybrid_top10`.

| Frontend-visible | Backend-saved but not clearly frontend-visible |
|---|---|
| `article_id`, `rank`, `is_ground_truth`, `hybrid_score`, `normalized_svd_score`, `normalized_agentic_score`, `diversity_bonus`, `product_type_name`, `product_group_name`, `colour_group_name`, `graphical_appearance_name`, `reason` - rendered in Hybrid recommendation cards (`frontend/components/ArtifactDemoTabs.tsx`; `backend/app/services/artifact_demo_service.py`) | `garment_group_name` - included in mapped items but not rendered in the current Hybrid card metadata (`backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`) |
| the derived badge based on `hybridAuditArticleId === item.article_id` is visible on Hybrid cards (`frontend/components/ArtifactDemoTabs.tsx`) | `matched_evidence` - present in the generic item shape but not used as a visible Hybrid card field (`backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`) |

---

## 8. Hybrid Explainability Audit Panel

Source-backed shape: `ArtifactDemoExplanationPanel` in `frontend/lib/api.ts` and `backend/app/models/schemas.py`, populated in `ArtifactDemoService._build_case()` and `_select_explanation_row()`.

| Frontend-visible | Backend-saved but not clearly frontend-visible |
|---|---|
| `article_id`, `groundedness_status`, `hybrid_rank`, `svd_rank`, `rank_shift`, `is_ground_truth` - rendered as visible metadata values (`frontend/components/ArtifactDemoTabs.tsx`; `backend/app/services/artifact_demo_service.py`) | `warnings[]` - returned by the backend but not iterated or displayed in the current audit panel (`backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`) |
| visible "Preference Trace" status derived from whether `matched_preference_fields.length` is non-zero (`frontend/components/ArtifactDemoTabs.tsx`) | `availability.has_explanation_text` - returned but not used directly by the UI (`backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`) |
| `item_metadata.prod_name`, `item_metadata.product_type_name`, `item_metadata.product_group_name`, `item_metadata.colour_group_name`, `item_metadata.graphical_appearance_name` - rendered in the audit panel (`frontend/components/ArtifactDemoTabs.tsx`; `backend/app/services/artifact_demo_service.py`) | `availability.has_score_breakdown` - returned but not used directly by the UI (`backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`) |
| `matched_preference_fields[]` - rendered as chips (`frontend/components/ArtifactDemoTabs.tsx`) | `availability.has_rank_shift` - returned but not used directly by the UI (`backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`) |
| `explanation_text` - rendered when present (`frontend/components/ArtifactDemoTabs.tsx`) | `availability.has_item_metadata` - returned but not used directly by the UI (`backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`) |
| `score_components.normalized_svd_score`, `score_components.normalized_agentic_score`, `score_components.diversity_bonus`, `score_components.hybrid_score` - rendered across the Hybrid signal and formula cards (`frontend/components/ArtifactDemoTabs.tsx`) | `availability.prod_name_available` - returned but not shown as its own visible field (`backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`) |
| | `item_metadata.garment_group_name` - present in the explanation payload but not rendered in the current audit panel (`backend/app/services/artifact_demo_service.py`; `backend/app/models/schemas.py`; `frontend/components/ArtifactDemoTabs.tsx`) |

---

## 9. Saved Artefact Files Used by the Demo vs Saved Only in the Backend

The walkthrough service explicitly reads six files: evaluation base JSON, SVD recommendations JSON, agentic recommendations JSON, Hybrid recommendations JSON, per-user metrics JSON, and explainability examples CSV (`backend/app/services/artifact_demo_service.py`).

### Frontend-visible or frontend-derived via the walkthrough

| File | Current classification |
|---|---|
| `seed99_robustness_evaluation_base_table_top10_1000.json` | Frontend-visible through summary, ground-truth, and leave-one-out fields (`backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`) |
| `seed99_robustness_svd_recommendations_top10_1000.json` | Frontend-visible through the SVD tab (`backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`) |
| `seed99_robustness_agentic_recommendations_top10_1000.json` | Frontend-visible through the 3-Agent evidence and recommendation sections (`backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`) |
| `seed99_robustness_hybrid_svd_agentic_recommendations_top10_1000.json` | Frontend-visible through the Hybrid tab (`backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`) |
| `seed99_full_retry_explainability_examples.csv` | Frontend-visible through the Hybrid explainability audit section (`backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`) |
| `seed99_robustness_per_user_metrics_top10_1000_three_methods.json` | Backend-read and only indirectly frontend-derived when `rank_shift` falls back to per-user metric ranks; the raw file contents are not directly rendered (`backend/app/services/artifact_demo_service.py`) |

### Backend-saved but not clearly frontend-visible on `/artifact-demo`

This bucket includes:

- CSV mirrors of files where the JSON version is the one actually read by the walkthrough service.
- validation reports, bootstrap CI reports, metric summaries, candidate pool reports, and experiment reports in `backend/app/data/processed/`.
- non-prefixed historical outputs and 100-user subset outputs not used by the current `/artifact-demo` service path.
- explainability summary, audit, case-study, and rank-shift files under `backend/app/data/processed/explainability/` that are not read by `ArtifactDemoService.load_workflow_cases()`.

Representative examples:

| File | Why backend-saved only for `/artifact-demo` |
|---|---|
| `seed99_robustness_metric_summary_top10_1000_three_methods.json` | saved aggregate metrics, not rendered on `/artifact-demo` (`backend/app/data/processed/`; `frontend/components/ArtifactDemoTabs.tsx`) |
| `seed99_robustness_bootstrap_ci_report_top10_1000_three_methods.json` | saved CI report, not read by the walkthrough service (`backend/app/data/processed/`; `backend/app/services/artifact_demo_service.py`) |
| `seed99_robustness_validation_report_top10_1000_three_methods.json` | saved validation report, not rendered on `/artifact-demo` (`backend/app/data/processed/`) |
| `seed99_full_retry_explainability_summary.json` | used for the explainability evidence path, not for the main `/artifact-demo` walkthrough (`frontend/lib/api.ts`; `backend/app/data/processed/explainability/`) |
| `seed99_full_retry_explainability_audit.json` | saved backend audit artefact, not read by `load_workflow_cases()` (`backend/app/data/processed/explainability/`; `backend/app/services/artifact_demo_service.py`) |

---

## 10. API Endpoints: Used by `/artifact-demo` vs Not Used by `/artifact-demo`

| Endpoint | Used by `/artifact-demo`? | Evidence |
|---|---|---|
| `GET /demo/workflow-cases` | Yes | called by `getWorkflowCases()` and used by `frontend/app/artifact-demo/page.tsx` (`frontend/lib/api.ts`; `frontend/app/artifact-demo/page.tsx`) |
| `GET /metrics` | No | helper exists in `frontend/lib/api.ts`, but the artefact demo route does not call it (`frontend/lib/api.ts`; `frontend/app/artifact-demo/page.tsx`; `frontend/components/ArtifactDemoTabs.tsx`) |
| `GET /metrics/explainability` | No | helper exists in `frontend/lib/api.ts`, but the artefact demo route does not call it (`frontend/lib/api.ts`; `frontend/app/artifact-demo/page.tsx`; `frontend/components/ArtifactDemoTabs.tsx`) |
| `GET /experiment/setup` | No | helper exists, not used by `/artifact-demo` (`frontend/lib/api.ts`; `frontend/app/artifact-demo/page.tsx`) |
| `GET /users/{user_id}/intent` | No | helper exists, not used by `/artifact-demo` (`frontend/lib/api.ts`; `frontend/app/artifact-demo/page.tsx`) |
| `GET /recommendations/compare/{user_id}` | No | helper exists, not used by `/artifact-demo` (`frontend/lib/api.ts`; `frontend/app/artifact-demo/page.tsx`) |
| `POST /users/{user_id}/feedback` | No | helper exists, not used by `/artifact-demo` (`frontend/lib/api.ts`; `frontend/app/artifact-demo/page.tsx`) |
| `POST /experiment/run` | No | not part of the read-only walkthrough route (`README.md`; `backend/app/api/demo.py`) |

---

## Known Uncertainties

1. The preference chart components are definitely rendered in the frontend, but the current walkthrough service passes `history_rows=[]` into `_build_case()`. That means the presence of non-empty history-derived frequency bars cannot be confirmed from the current service path alone (`backend/app/services/artifact_demo_service.py`; `frontend/components/ArtifactDemoTabs.tsx`).
2. This audit is intentionally about `/artifact-demo`. It does not classify what may be visible on separate routes such as `/explainability-evidence` (`PROJECT.md`; `handoff_next_stage.md`; `frontend/lib/api.ts`).
3. The saved-file classification is based on the current walkthrough service read-path and current directory inventory, not on whether another tool, page, or script elsewhere in the repo may consume the same files (`backend/app/services/artifact_demo_service.py`; `backend/app/data/processed/`; `backend/app/data/processed/explainability/`).
