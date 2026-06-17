# Port `LILI FINAL PAPER DEMO` to the `three-agent-demo` UI

## Summary

Replace the current light multi-page frontend with a near-identical Next.js version of the dark single-page `three-agent-demo` UI, but wire it to this project's existing FastAPI data and experiment flow.

The new homepage becomes the primary demo surface:
- dark theme
- explicit 3-agent framing
- single user selector + run/view workflow
- main focus on Preference Agent, Evidence Agent, and Decision Agent
- benchmark/SVD shown as a secondary comparison section, not the primary experience

No backend API changes are required for the first pass. The frontend should adapt existing responses into the `three-agent-demo` presentation model.

## Implementation Changes

### 1. Replace the current shell with a single-page dark 3-agent experience

Adopt the structure and visual language of `three-agent-demo`:
- dark slate background and panel styling
- hero/header matching the 3-agent demo layout closely
- three stage explainer cards near the top
- one main page instead of the current 6-page research navigation
- typography, spacing, card layout, and interaction states should intentionally mirror the demo

Practical frontend shape:
- keep Next.js/App Router, but collapse the primary experience into `frontend/app/page.tsx`
- remove the current top navigation from the main experience
- keep metadata/title aligned with the project but update copy to clearly present the 3-agent workflow
- rewrite `frontend/app/globals.css` to a dark theme or replace most page-level styling with component-local classes that reproduce the `three-agent-demo` look

### 2. Map this project's real backend data into the 3-agent UI model

Create a thin adapter layer in the frontend that converts existing API responses into the three visual sections:

- Preference Agent
  - source: `getUserIntent(userId)`
  - map intent summary, preferred categories/types/colours/appearance into the preference profile panel
  - show graceful empty states when preference detail is sparse

- Evidence Agent
  - source: `getRecommendationComparison(userId).agentic_process`
  - use saved retrieval/process stages as the evidence panel content
  - if the formal experiment returns limited trace detail, render a best-effort evidence view from:
    - stage summaries/payloads when present
    - otherwise top agentic recommendation attributes and reasons as evidence proxies
  - this avoids backend changes while still preserving the 3-agent feel

- Decision Agent
  - source: `getRecommendationComparison(userId).agentic_recommendations`
  - render final ranked recommendation cards in the dark demo style
  - include reason text, rank, score, and product metadata

- Secondary benchmark section
  - source: `getRecommendationComparison(userId).cf_recommendations`
  - show the SVD/baseline output in a smaller lower-priority panel below the 3-agent sections
  - keep it clearly labeled as benchmark output, not the main story

### 3. Match the interaction model to this project's setup

Keep the interaction backend-driven rather than mock-workflow-driven:
- primary control is selected user
- page loads candidate user IDs from `getSetup()`
- selecting a user and pressing the main CTA fetches:
  - setup-derived context if needed
  - user intent
  - comparison payload
- the CTA label should stay 3-agent-oriented, but behavior is "load this user's saved formal experiment outputs," not "generate from mock local agents"

Recommended interaction behavior:
- top controls: user selector + CTA
- no free-text prompt in v1
- if no experiment artifacts exist, show a clear empty state instructing the user to run the backend experiment first
- preserve `NEXT_PUBLIC_API_BASE_URL` support and the formal mode default already used by `frontend/lib/api.ts`

## Public Interfaces / Data Contracts

No backend endpoint changes are required.

Frontend contract usage remains:
- `GET /experiment/setup?mode=svd_top10_experiment`
- `GET /users/{user_id}/intent?mode=svd_top10_experiment`
- `GET /recommendations/compare/{user_id}?mode=svd_top10_experiment`

Frontend additions:
- add a local adapter/mapping layer that converts current API types into UI-specific view models for:
  - preference panel
  - evidence panel
  - recommendation panel
  - secondary benchmark panel

## Test Plan

### Functional checks
- Homepage loads in the dark 3-agent layout and no longer shows the old 6-page navigation.
- User selector is populated from setup/evaluated users.
- Selecting a valid user loads:
  - preference data
  - evidence/trace content
  - agentic recommendations
  - benchmark recommendations
- Empty-state messaging appears correctly when experiment artifacts are missing.
- The page still works when `agentic_process` is empty by falling back to recommendation-based evidence display.

### Visual checks
- Page visually matches `three-agent-demo` closely:
  - dark background
  - 3-agent hero and stage cards
  - panel density and layout
  - recommendation card treatment
- Mobile layout remains usable and readable.

### Integration checks
- Frontend still respects `NEXT_PUBLIC_API_BASE_URL`.
- Frontend still targets formal experiment mode by default.
- Existing backend on `8003` and frontend on `3003` render the new page correctly against live data.

## Assumptions and Defaults

- "Follow that UI perfectly" means near-identical layout and visual direction, not preserving the existing 6-page research IA.
- The new dark 3-agent page becomes the primary interface for this project.
- Benchmark/SVD remains available, but as a secondary panel.
- No backend schema changes are introduced in v1; evidence rendering will adapt to whatever `agentic_process` currently provides.
- The source of truth for the target look is `three-agent-demo`, while the source of truth for data is this project's FastAPI API and saved formal experiment artifacts.
