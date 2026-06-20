# Dissertation Artefact Demo Refactor Plan

## Summary
- Current repo state for implementation: branch `UI-Update`; existing uncommitted change in `PROJECT.md` only. Leave it untouched.
- Refactor the existing `/artifact-demo` route into the phase-1 supervisor-facing artefact entry point rather than creating a new route.
- Keep legacy pages/routes reachable, but remove older `Comparison`, `Evaluation`, and standalone `Explainability Evidence` links from the primary nav so `/artifact-demo` is the main visible entry.
- Use only saved offline artifacts already present:
  - `seed99_robustness_evaluation_base_table_top10_1000.json`
  - `seed99_robustness_svd_recommendations_top10_1000.json`
  - `seed99_robustness_agentic_recommendations_top10_1000.json`
  - `seed99_robustness_hybrid_svd_agentic_recommendations_top10_1000.json`
  - `seed99_robustness_per_user_metrics_top10_1000_three_methods.json`
  - `backend/app/data/processed/explainability/seed99_full_retry_explainability_examples.csv`
  - `backend/app/data/processed/explainability/seed99_full_retry_explainability_audit.json`
- Scope for this phase: only the three runnable method tabs `SVD`, `3-Agent`, and `Hybrid`. Do not show full experiment results or global 1,000-user metrics inside `/artifact-demo`.

## Implementation Changes
- Update app shell branding in `frontend/app/layout.tsx`:
  - Change title/description/header copy from `Agentic AI Recommendation Framework` to the dissertation artefact framing.
  - Keep the dark visual style and existing spacing/typography direction.
  - Remove copy that implies CTR/CVR/engagement outcomes.
- Update primary nav in `frontend/components/TopNav.tsx`:
  - Keep `Artefact Demo` as the main route label.
  - Remove old primary-nav links for `Comparison`, `Evaluation`, and `Explainability Evidence`.
  - Leave old routes working; do not delete route files in this phase.
- Refactor `frontend/components/ArtifactDemoTabs.tsx` into a three-tab method UI:
  - Replace the current five-tab structure with `SVD`, `3-Agent`, `Hybrid`.
  - Add the shared page header text exactly per the brief, including the offline-only limitation note.
  - Use one shared demo-user selector across the page and keep the selected user synchronized across all three tabs.
  - Remove the current `Experiment Results`, `Explainability Evidence`, and `Technical Validation` sections from this route.
  - Remove image placeholder blocks entirely; use metadata-only recommendation cards/tables.
  - Remove raw debug JSON and old aggregate comparison cards from the visible method UI.
- Extend the existing read-only backend payload instead of adding a new endpoint:
  - Keep `GET /demo/workflow-cases`.
  - Expand `ArtifactDemoService`, `backend/app/models/schemas.py`, and `frontend/lib/api.ts` types so each case exposes:
    - neutral demo label (`Demo User 1` … `Demo User 5`)
    - `train_count`
    - `ground_truth_in_candidate_pool`
    - `candidate_pool_size`
    - ground-truth metadata fields already available in evaluation artifacts
    - SVD Top-10 item rows with rank, score, and item metadata
    - 3-Agent Top-10 item rows with rank, score, item metadata, `matched_evidence`, and saved reason if present
    - Hybrid Top-10 item rows with rank, `hybrid_score`, `normalized_svd_score`, `normalized_agentic_score`, `diversity_bonus`, item metadata, and saved reason if present
    - selected explainability row data for the Hybrid tab: matched preference fields, groundedness counts/status, rank shift, warning fields such as missing `prod_name`
  - Keep the service read-only and sourced only from saved files.
  - Change case selection to deterministic neutral demo users with complete artifact coverage; target 5 users by default.
- Tab content decisions:
  - `SVD`: show method role, leave-one-out context, hit/miss badge based on ground-truth presence in the saved SVD Top-10, and SVD Top-10 metadata rows.
  - `3-Agent`: keep the three-agent structure, show real preference summary from saved profile when present, otherwise derive from saved history summary fields already in the response; show evidence metadata and Top-10 rows without claiming live OpenAI reasoning.
  - `Hybrid`: make this the visually strongest tab; include the fixed workflow diagram, fixed hybrid formula text, Hybrid Top-10 rows with score components, and a read-only explainability panel with the required limitation wording.
- Wording rules to enforce during implementation:
  - Use `SVD Matrix Factorisation Baseline`, `Standalone 3-Agent Recommender`, `Hybrid SVD + 3-Agent Reranker`.
  - Replace old CF/Top-5/Hit@5 language everywhere in `/artifact-demo` and shared artefact shell copy.
  - If a field is absent in saved artifacts, render `Not available` explicitly.

## Public API / Type Changes
- `GET /demo/workflow-cases` remains the only artefact data endpoint for this phase.
- Extend `ArtifactDemoMethodItem` with optional method-specific fields needed by the UI:
  - `matched_evidence?: string[]`
  - `normalized_svd_score?: number | null`
  - `normalized_agentic_score?: number | null`
  - `diversity_bonus?: number | null`
- Extend `ArtifactDemoWorkflowCase` with explicit leave-one-out context fields rather than burying them in generic records:
  - `train_count: number`
  - `ground_truth_in_candidate_pool: boolean | null`
  - `ground_truth_hit_svd: boolean`
  - `ground_truth_hit_agentic: boolean`
  - `ground_truth_hit_hybrid: boolean`
  - `explanation_available: boolean`
  - `grounded_claim_count?: number | null`
  - `ungrounded_claim_count?: number | null`
- Keep existing older frontend API types/routes intact unless needed for compile safety; do not change recommender or metric endpoints.

## Test Plan
- Backend:
  - Update `backend/tests/test_api.py` assertions for `/demo/workflow-cases` to cover the new explicit fields and Hybrid score-component payload.
  - Add assertions that the endpoint still fails cleanly when required artifacts are missing.
  - If selection logic changes materially, add a focused `ArtifactDemoService` test or extend the existing API fixture coverage to verify neutral labels and deterministic case ordering.
- Frontend:
  - `npx tsc --noEmit`
  - `npm run build`
  - Manual check of `/artifact-demo`:
    - only three visible tabs
    - no experiment/global metrics shown
    - no image placeholders
    - no raw JSON
    - `Not available` shown for absent fields such as missing `prod_name`
    - old pages absent from primary nav but still routable directly
- Regression guard:
  - No edits to `backend/app/services/cf_service.py`, `agentic_service.py`, `hybrid_service.py`, evaluation logic, or saved processed artifacts except read-only consumption.

## Assumptions
- Use the existing `/artifact-demo` route and existing `/demo/workflow-cases` endpoint; do not add a second demo endpoint unless an unexpected payload mismatch makes extension impractical.
- Use 5 real demo users, not 10, because the brief allows `5–10` and 5 keeps the artefact tighter for supervisor review.
- Keep old standalone routes in the repo for later phases; this phase only removes them from the main navigation.
- `prod_name` is genuinely unavailable in the saved explainability source and should be shown as `Not available`, not backfilled.
- Explainability content in `/artifact-demo` is limited to per-user Hybrid evidence only; the full audit stays off the main artefact route in this phase.
