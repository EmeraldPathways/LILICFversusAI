# Project Guide

## Overview

This project is a research-style fashion recommendation dashboard built on the H&M Personalized Fashion Recommendations dataset.

The live application compares two recommendation methods on the same held-out next-purchase task:

- `Collaborative Filtering (CF)` baseline
- `3-Agent Agentic AI` recommendation pipeline

The goal is to test whether the user's actual next purchased item appears in the model's Top 5 recommendations.

The evaluation setup is:

- use each eligible user's transaction sequence
- hold out the last purchase as ground truth
- use earlier purchases as training history
- generate Top 5 recommendations
- measure `Hit@5`

## Current App Structure

- `backend/`
  - FastAPI API
  - data preprocessing
  - leave-one-out split generation
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
  - not used by the live app
  - currently untracked and standalone

## What The Live App Does

### 1. Preprocesses real H&M data

The backend expects these raw CSV files in `backend/app/data/raw/`:

- `transactions_train.csv`
- `articles.csv`
- `customers.csv`

During preprocessing, the backend:

- loads the H&M transactions and article metadata
- joins transactions to article metadata by `article_id`
- normalizes product fields into a simpler recommendation schema
- adds placeholder image URLs using `article_id`
- filters sparse users and sparse products
- samples a manageable working subset

The normalized product fields used by the app are:

- `article_id`
- `product_type`
- `product_group`
- `colour`
- `appearance`
- `product_name`
- `product_description`
- `image_url`
- `transaction_date`

### 2. Builds a leave-one-out next-item experiment

For each eligible user:

- the final purchase is moved to `test`
- all earlier purchases remain in `train`
- users with fewer than 2 purchases are excluded from evaluation

This is the basis for both CF and Agentic AI evaluation.

### 3. Runs two recommendation methods

#### Collaborative Filtering

The CF method:

- uses only interaction behavior from the training history
- builds a user-item interaction matrix
- recommends unseen items
- returns Top 5 recommendations

#### 3-Agent Agentic AI

The agentic method runs three stages in order:

1. `Preference Agent`
   - reads the selected user's training history
   - joins that history with product metadata
   - estimates weighted product preferences
   - treats history as soft preference evidence
   - only creates hard constraints from explicit request text such as `only black` or `only dresses`

2. `Evidence Agent`
   - builds a candidate set from the processed catalog
   - checks products against preference signals
   - records which fields matched
   - generates evidence summaries for each candidate

3. `Decision Agent`
   - applies any explicit hard constraints
   - ranks candidates using a transparent weighted scoring rule
   - returns the final Top 5 recommendations

The current scoring weights are:

- `product_type_name`: `0.30`
- `product_group_name`: `0.25`
- `colour_group_name`: `0.20`
- `graphical_appearance_name`: `0.15`
- `product_description` keyword similarity: `0.10`

### 4. Evaluates both methods with Hit@5

After recommendations are generated, the backend checks whether the held-out next purchase appears in each Top 5 list.

This produces:

- per-user `hit_at_5`
- aggregated offline metrics

## Frontend Pages

The live app has exactly three pages.

### Agentic AI

Route:

- `/`

Purpose:

- run the 3-agent workflow for a selected user
- optionally provide a current request
- inspect the full agent trace

What it shows:

- selected user
- optional request input
- training history count and preview
- ground-truth next purchase
- Preference Agent output
- Evidence Agent candidate set
- Decision Agent final recommendations
- Agentic `Hit@5`

### CF

Route:

- `/cf`

Purpose:

- inspect the collaborative filtering baseline for the same evaluation task

What it shows:

- selected user
- training history summary
- ground-truth next purchase
- Top 5 CF recommendations
- CF `Hit@5`

### Comparison

Route:

- `/comparison`

Purpose:

- compare the two methods side by side on the same user

What it shows:

- selected user
- ground-truth next purchase
- training history preview
- CF Top 5
- Agentic AI Top 5
- CF `Hit@5`
- Agentic `Hit@5`

## Main Backend Endpoints

### Health

- `GET /health`

Simple health check.

### Experiment

- `POST /experiment/run`
  - preprocesses the data
  - creates the leave-one-out split
  - generates CF outputs
  - generates Agentic outputs
  - writes evaluation metrics

- `GET /experiment/setup`
  - returns dataset summary
  - returns experiment description
  - returns the curated user IDs exposed in the UI

### Recommendations

- `GET /recommendations/cf/{user_id}`
  - returns CF Top 5
  - returns training history preview
  - returns ground-truth next item
  - returns `hit_at_5`

- `POST /recommendations/agentic/run`
  - input:
    - `user_id`
    - `user_request`
  - returns:
    - preference profile
    - candidate evidence set
    - final recommendations
    - process trace
    - ground-truth next item
    - `hit_at_5`

### Comparison

- `GET /comparison/{user_id}`
  - returns both CF and Agentic outputs for the same user

### Metrics

- `GET /metrics`
  - returns aggregated offline evaluation metrics

## Data Artifacts Written By The Backend

Processed files are written into `backend/app/data/processed/`.

Important files:

- `interactions_sample.csv`
- `train.csv`
- `test.csv`
- `experiment_summary.json`
- `cf_recommendations.json`
- `agentic_recommendations.json`
- `agentic_trace.json`
- `metrics.json`
- `experiment_state.json`

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
- `LLM_TIMEOUT_SECONDS`

Frontend variables:

- `NEXT_PUBLIC_API_BASE_URL`

Local defaults:

- backend: `http://localhost:8000`
- frontend: `http://localhost:3000`

## How To Run The Project

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

### Recommended first run

1. Place the raw H&M CSV files in `backend/app/data/raw/`
2. Start the backend
3. Call `POST /experiment/run`
4. Start the frontend
5. Open:
   - `http://localhost:3000/`
   - `http://localhost:3000/cf`
   - `http://localhost:3000/comparison`

## Current Design Decisions

- The live app uses `real H&M data`, not mock data
- The UI only exposes a small curated set of users to avoid broken evaluation states in the demo
- The agentic method uses OpenAI only in the agentic workflow
- The frontend and backend are separate services
- The local Vite demo is not part of production flow

## Do We Still Need `three-agent-demo/`?

Not for the live app.

`three-agent-demo/` is not imported by `frontend/` or `backend/`, and nothing in the current application depends on it.

You should keep it only if you still want one of these:

- a standalone mock demo reference
- a place to copy UI ideas from
- an isolated prototype that is separate from the real-data app

You can safely remove it if:

- you are fully committed to the current `frontend/` + `backend/` app
- you no longer need the Vite prototype
- you want the repository to contain only the real project

Recommended practical choice:

- keep it temporarily if you still compare designs
- delete or archive it once you are sure the live app has absorbed what you need

## Important Caveat

The root `README.md` is older than the current implementation and still describes earlier pages and endpoints in places. `PROJECT.md` should be treated as the current working guide for the live 3-page application.
