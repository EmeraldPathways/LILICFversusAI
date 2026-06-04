# Project Guide

## Overview

This project is a research-style fashion recommendation dashboard built on the H&M Personalized Fashion Recommendations dataset.

The live application compares two recommendation methods on the same leave-one-out next-item task:

- `Collaborative Filtering (CF)` baseline
- `3-Agent Agentic AI` recommendation pipeline

The current system is built around one canonical evaluation source of truth:

- `backend/app/data/processed/evaluation_base_table.json`

For the live presentation flow, the app is intentionally locked to one saved evaluation subset:

- `backend/app/data/processed/completed_evaluation_users.json`

Only rows with:

- `included_in_metrics = true`

are exposed in the frontend dropdown and used for the presentation comparison and default metrics view.

That base table defines, per user:

- training history
- held-out ground-truth next purchase
- shared candidate pool
- evaluation validity

Both CF and Agentic AI are expected to rank over that same candidate pool.

The current live presentation subset contains exactly `10` users.

## Current App Structure

- `backend/`
  - FastAPI API
  - preprocessing and leave-one-out experiment setup
  - canonical evaluation base table generation
  - CF recommendation logic
  - 3-agent recommendation logic
  - offline evaluation and metrics
- `frontend/`
  - Next.js App Router dashboard
  - three pages:
    - `Agentic AI`
    - `CF`
    - `Comparison`
- `three-agent-demo/`
  - separate Vite demo project
  - not part of the live app flow
  - currently independent from the main frontend/backend app

## Current Evaluation Design

The project uses leave-one-out next-item evaluation.

For each eligible customer:

1. Sort the transaction sequence by `transaction_date`
2. Use all earlier purchases as training history
3. Use the final purchase as `ground_truth_article_id`
4. Build one shared candidate pool
5. Run both CF and Agentic AI over the same candidate pool
6. Measure `Hit@5`

The backend writes a canonical evaluation row for each customer into:

- `evaluation_base_table.csv`
- `evaluation_base_table.json`

Important row fields:

- `customer_id`
- `train_article_ids`
- `ground_truth_article_id`
- `candidate_pool_article_ids`
- `candidate_pool_size`
- `ground_truth_in_candidate_pool`
- `is_valid_for_evaluation`
- `invalid_reason`

## Normalization Rules

The current implementation treats identifiers consistently:

- `article_id` is normalized to string everywhere
- leading zeros are preserved
- `customer_id` is normalized to string everywhere

This normalization is expected across:

- raw transactions
- processed interactions
- train/test data
- evaluation base table
- candidate pools
- CF outputs
- Agentic outputs
- Hit@5 checks

## What The Backend Does

### 1. Preprocesses real H&M data

The backend expects these raw CSV files in `backend/app/data/raw/`:

- `transactions_train.csv`
- `articles.csv`
- `customers.csv`

During preprocessing, the backend:

- loads transactions and article metadata
- joins transactions to article metadata by `article_id`
- normalizes the product schema
- generates placeholder image URLs from `article_id`
- filters sparse users and sparse products
- samples a manageable working subset

Normalized product fields used by the app:

- `article_id`
- `product_type`
- `product_group`
- `colour`
- `appearance`
- `product_name`
- `product_description`
- `image_url`
- `transaction_date`

### 2. Builds canonical evaluation artifacts

The backend writes processed files into `backend/app/data/processed/`.

Important files:

- `interactions_sample.csv`
- `train.csv`
- `test.csv`
- `evaluation_base_table.csv`
- `evaluation_base_table.json`
- `evaluation_validation_report.json`
- `experiment_summary.json`
- `cf_recommendations.json`
- `agentic_recommendations.json`
- `agentic_trace.json`
- `metrics.json`
- `invalid_evaluation_users.json`
- `completed_evaluation_users.json`
- `comparable_user_audit.json`
- `experiment_state.json`

### 3. Builds one shared candidate pool per user

The current candidate-pool rules are:

- always include `ground_truth_article_id` if it exists in catalog
- exclude training items
- exclude duplicates
- exclude items missing from catalog
- use a fixed seed for reproducibility
- default target size is controlled by `CANDIDATE_POOL_SIZE`

Both recommenders should use the same stored `candidate_pool_article_ids` from the evaluation base table.

## Recommendation Methods

### Collaborative Filtering

The CF method currently:

- builds a global user-item interaction matrix from training interactions
- uses the selected user's `train_article_ids` from the evaluation base table
- scores only items in the shared candidate pool
- excludes items already present in training history
- returns Top 5 from the shared candidate pool

### 3-Agent Agentic AI

The agentic pipeline currently runs:

1. `Preference Agent`
   - reads only the selected user's training history
   - joins training items to product metadata
   - infers soft preferences from history
   - creates hard constraints only from explicit request text

2. `Evidence Agent`
   - builds candidate evidence only for the shared candidate pool
   - does not search outside that pool during normal evaluation

3. `Decision Agent`
   - ranks only the candidate evidence set
   - applies explicit hard constraints when present
   - returns Top 5 from the shared candidate pool

Current scoring weights:

- `product_type_name`: `0.30`
- `product_group_name`: `0.25`
- `colour_group_name`: `0.20`
- `graphical_appearance_name`: `0.15`
- `product_description` keyword similarity: `0.10`

## Shared Hit@5 Logic

Both methods use one shared hit function.

The hit result includes:

- `hit_at_5`
- `hit_label`
- `matched_article_id`
- `matched_rank`
- `explanation`

This is intended to answer whether a miss is:

- a real ranking miss
- or an invalid evaluation setup

In the UI, a displayed `Miss` means:

- the method returned a valid Top 5 list
- but the held-out ground-truth item was not found in that Top 5

It does **not** mean the recommender failed to run.

## Validation Behavior

Each method response can include a validation block proving:

- the evaluation base row was used
- the candidate pool came from the same source
- the ground truth is in the candidate pool
- Top 5 items stay inside the candidate pool
- Top 5 items do not leak from training history
- article ID formatting checks passed

If a user row is invalid for evaluation:

- recommendations should not be generated honestly for that user
- the response should return `invalid_reason`

Invalid users are excluded from aggregate offline metrics.

## Frontend Pages

The live app has exactly three pages.

### Agentic AI

Route:

- `/`

Purpose:

- run the 3-agent workflow for a selected user
- optionally provide a current request
- inspect the preference profile, candidate evidence, and final Top 5

What it shows:

- selected user
- optional request input
- training history summary
- ground-truth next purchase
- Preference Agent output
- Evidence Agent output
- Decision Agent Top 5
- agentic hit result
- evaluation debug panel

### CF

Route:

- `/cf`

Purpose:

- inspect the CF baseline for the same evaluation task

What it shows:

- selected user
- training history summary
- ground-truth next purchase
- CF Top 5
- CF hit result
- evaluation debug panel

### Comparison

Route:

- `/comparison`

Purpose:

- compare CF and Agentic AI side by side on the same evaluation base row

What it shows:

- presentation subset note for the locked 10 users
- aggregate Hit@5 summary for the presentation subset
- evaluation base row
- ground-truth next purchase
- CF Top 5
- Agentic AI Top 5
- both hit results
- method run status and Top 5 generation status
- consistency warnings when:
  - candidate pool sizes differ
  - a recommender returns an item outside the candidate pool
  - a recommender returns a training item
  - ground truth is missing from the candidate pool

Current wording on this page distinguishes:

- `Hit`
- `Valid Miss`
- `Not Available`

so a valid ranking miss is not confused with a failed run.

## Frontend Persistence

The frontend persists navigation context in local storage.

Current persisted state:

- selected user ID
- latest agentic result
- latest CF result
- latest comparison result

This is why moving between pages can preserve the last loaded result instead of resetting immediately.

## Main Backend Endpoints

### Health

- `GET /health`

Simple health check.

### Experiment

- `POST /experiment/run`
  - preprocesses data
  - builds or refreshes the evaluation base table
  - evaluates only valid users
  - runs CF over the base table
  - runs Agentic AI over the base table
  - writes recommendation outputs and metrics

- `GET /experiment/setup`
  - returns dataset summary
  - returns experiment description
  - returns the locked presentation user IDs exposed in the UI
  - current response includes:
    - `presentation_mode`
    - `user_selection_method`
    - `selected_user_ids`
    - `valid_evaluation_users`
    - `presentation_user_count`

### Recommendations

- `GET /recommendations/cf/{user_id}`
  - returns base-table-driven CF result
  - returns Top 5 from the shared candidate pool
  - returns hit result
  - returns validation block

- `POST /recommendations/agentic/run`
  - input:
    - `user_id`
    - `user_request`
  - returns:
    - preference profile
    - candidate evidence set
    - Top 5 from the shared candidate pool
    - hit result
    - validation block

### Comparison

- `GET /comparison/{user_id}`
  - only allows users from the locked presentation subset
  - returns:
    - evaluation base row
    - CF result
    - Agentic result
    - both Top 5 lists
    - both hit results
    - validation blocks
  - if the user is outside the locked set, returns:
    - `error`
    - `allowed_user_ids`

### Debug

- `GET /debug/evaluation/{user_id}`
  - returns detailed evaluation trace for that user

- `GET /debug/evaluation-base/{user_id}`
  - returns the exact canonical evaluation base row for that user

- `GET /debug/presentation-users`
  - returns the locked presentation subset
  - source: `completed_evaluation_users.json`
  - filter: `included_in_metrics=true`

### Metrics

- `GET /metrics`
  - returns presentation metrics for the locked 10-user subset by default
  - current live values are:
    - CF: `0 / 10 = 0.00`
    - 3-Agent: `2 / 10 = 0.20`
  - also includes:
    - `presentation_mode`
    - `user_scope`
    - `legacy_20_user_metrics`

## Environment Variables

Backend variables:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `FRONTEND_ORIGIN`
- `BACKEND_DATA_DIR`
- `SAMPLE_SIZE`
- `TOP_N`
- `CANDIDATE_POOL_SIZE`
- `MIN_USER_INTERACTIONS`
- `MIN_PRODUCT_INTERACTIONS`
- `MAX_EVAL_USERS`
- `MAX_VALID_EVAL_USERS`
- `LLM_TIMEOUT_SECONDS`
- `GROUND_TRUTH_MODE`
- `EVALUATION_MODE`
- `EVALUATION_SEED`

Frontend variables:

- `NEXT_PUBLIC_API_BASE_URL`

Local defaults:

- backend: `http://localhost:8000`
- frontend: `http://localhost:3000`

## How To Run

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm.cmd install
npm.cmd run dev
```

### Recommended local run

1. Place raw H&M CSV files in `backend/app/data/raw/`
2. Start backend
3. Call `POST /experiment/run`
4. Start frontend
5. Open:
   - `http://localhost:3000/`
   - `http://localhost:3000/cf`
   - `http://localhost:3000/comparison`

## Current Design Decisions

- the live app uses real H&M data, not mock data
- the evaluation base table is the single source of truth
- the live frontend is locked to the saved 10-user presentation subset
- the presentation subset is loaded from `completed_evaluation_users.json`
- only rows with `included_in_metrics=true` are shown in dropdowns
- the comparison page reads saved CF and Agentic outputs for that subset
- default frontend metrics are the 10-user presentation metrics, not the legacy 20-user aggregate
- invalid users are excluded from aggregate Hit@5 metrics
- the two recommenders are compared only on the same shared candidate pool
- recommendation algorithms are kept honest; misses are allowed
- the frontend and backend are separate services
- `three-agent-demo/` is not part of the live production flow

## Important Caveat

The root `README.md` may lag behind the implementation. `PROJECT.md` should be treated as the current working guide for the live application.
