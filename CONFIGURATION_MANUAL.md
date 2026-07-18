# Configuration Manual

## Purpose

This manual is a reproducible runbook for the dissertation artefact in this repository. It is written so that another student or examiner can set up the environment, reproduce the formal Seed99 experiment artifacts, generate the explainability replay artifacts used by the demo, launch the backend and frontend, and access the final read-only artefact page.

This repository is not a live production recommender. The final `/artifact-demo` page is a read-only replay of saved offline outputs. It does not rerun the experiment on page load.

## Repository Root

Use this repository root:

```text
D:\GOOGLE DRIVE\EMERALD PATHWAYS\WEB WORK\AI CODING\VS CODE\personal\LILI FINAL PAPER DEMO
```

## Runtime Versions

The locally verified runtime versions in this checkout are:

- Python: `3.13.2`
- Node.js: `24.14.1`
- npm: `11.11.0`

Important frontend package versions from `frontend/package.json`:

- Next.js: `15.5.18`
- React: `19.0.0`
- React DOM: `19.0.0`
- TypeScript: `5.8.3`

Important backend package versions from `backend/requirements.txt`:

- `fastapi==0.115.12`
- `uvicorn[standard]==0.34.2`
- `pandas==2.2.3`
- `numpy==2.2.5`
- `openai==1.78.1`
- `pytest==8.3.5`
- `scipy==1.17.1`
- `scikit-learn==1.9.0`

## Dataset Source

The project is based on the H&M Personalized Fashion Recommendations dataset. The expected download source is the Kaggle H&M competition page:

```text
https://www.kaggle.com/competitions/h-and-m-personalized-fashion-recommendations
```

After downloading and extracting the dataset, place the raw CSV files inside:

```text
backend/app/data/raw/
```

## Required Raw Files

The formal pipeline expects these files:

- `backend/app/data/raw/transactions_train.csv`
- `backend/app/data/raw/articles.csv`
- `backend/app/data/raw/customers.csv`

The supervisor feedback specifically mentions `transactions_train.csv` and `articles.csv`, but the code also validates the presence of `customers.csv`. If `customers.csv` is missing, the data build step will fail.

## Backend Setup

From the repository root:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

If you prefer not to activate the environment, use the explicit interpreter path in all backend commands:

```powershell
.\.venv\Scripts\python.exe
```

## Frontend Setup

From the repository root:

```powershell
cd frontend
npm.cmd install
```

## Environment Configuration

The backend settings load from a `.env` file. Create:

```text
backend/.env
```

Use this template:

```dotenv
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4.1-mini
FRONTEND_ORIGIN=http://localhost:3009,http://127.0.0.1:3009

# Optional overrides
# BACKEND_DATA_DIR=D:\path\to\alternate\data\folder
# SAMPLE_SIZE=20000
# TOP_N=10
# CANDIDATE_POOL_SIZE=100
# MIN_USER_INTERACTIONS=3
# MIN_PRODUCT_INTERACTIONS=2
# MAX_EVAL_USERS=50
# LLM_TIMEOUT_SECONDS=40
```

Do not place the real API key in the dissertation document. Use a placeholder such as:

```text
OPENAI_API_KEY=sk-REDACTED
```

Notes:

- `OPENAI_API_KEY` is required for the agentic intention and explanation services.
- `TOP_N` defaults to `10`.
- `CANDIDATE_POOL_SIZE` defaults to `100`.
- If `BACKEND_DATA_DIR` is not set, the code uses `backend/app/data/raw/` and `backend/app/data/processed/`.

## Exact Placement of Raw Data

The code resolves these paths directly:

- transactions path: `backend/app/data/raw/transactions_train.csv`
- articles path: `backend/app/data/raw/articles.csv`
- customers path: `backend/app/data/raw/customers.csv`

No additional renaming is required.

## Reproducing the Seed99 Formal Experiment

### Important Note

The repository does not expose the full three-method Seed99 pipeline as a single packaged CLI command. The exact reproducible run is a sequence of service calls. The command block below reproduces the saved `seed99_robustness_*` formal experiment artifacts from the current codebase.

### Exact Seed99 Run Command

Run this from the repository root:

```powershell
cd backend
@'
from app.config import get_settings
from app.services.data_service import DataService
from app.services.cf_service import CollaborativeFilteringService
from app.services.agentic_service import AgenticRecommendationService
from app.services.hybrid_service import HybridRecommendationService
from app.services.evaluation_service import EvaluationService

settings = get_settings()
data_service = DataService(settings)
cf_service = CollaborativeFilteringService(settings)
agentic_service = AgenticRecommendationService(settings)
hybrid_service = HybridRecommendationService(settings, cf_service, agentic_service)
evaluation_service = EvaluationService(settings)

data_service.build_processed_interactions_with_articles()
data_service.build_leave_one_out_evaluation_base()
data_service.build_svd_top10_subset(
    sample_size=1000,
    random_seed=99,
    candidate_pool_size=100,
    artifact_prefix="seed99_robustness",
)
cf_service.build_svd_top10_baseline(
    subset_size=1000,
    random_state=99,
    artifact_prefix="seed99_robustness",
)
agentic_service._build_top10_formal_experiment(
    subset_size=1000,
    artifact_prefix="seed99_robustness",
)
hybrid_service.build_hybrid_svd_agentic_reranker(
    subset_size=1000,
    random_state=99,
    artifact_prefix="seed99_robustness",
)
evaluation_service.compute_three_method_top10_metrics_from_saved_artifacts(
    subset_size=1000,
    bootstrap_samples=1000,
    random_seed=42,
    artifact_prefix="seed99_robustness",
)
'@ | .\.venv\Scripts\python.exe -
```

### What This Command Produces

The formal run writes saved artifacts to:

```text
backend/app/data/processed/
```

Expected key outputs include:

- `seed99_robustness_evaluation_base_table_top10_1000.json`
- `seed99_robustness_svd_recommendations_top10_1000.json`
- `seed99_robustness_agentic_recommendations_top10_1000.json`
- `seed99_robustness_hybrid_svd_agentic_recommendations_top10_1000.json`
- `seed99_robustness_per_user_metrics_top10_1000_three_methods.json`
- `seed99_robustness_metric_summary_top10_1000_three_methods.json`
- `seed99_robustness_bootstrap_ci_report_top10_1000_three_methods.json`
- `seed99_robustness_validation_report_top10_1000_three_methods.json`
- `seed99_robustness_experiment_report_top10_1000.md`

## Bootstrap Confidence Interval Procedure

The bootstrap confidence interval logic is implemented in `backend/app/services/evaluation_service.py`.

For the three-method Seed99 comparison, the procedure is:

1. Read the saved per-user SVD, standalone 3-Agent, and Hybrid recommendation results.
2. Compute per-user values for:
   - HitRate@10
   - NDCG@10
   - ILD@10
3. Draw `1000` bootstrap resamples with replacement from the full set of per-user rows.
4. For each resample, compute:
   - method-level mean metrics for SVD, standalone 3-Agent, and Hybrid
   - pairwise differences:
     - Hybrid minus SVD
     - Hybrid minus standalone 3-Agent
5. Estimate the 95% confidence interval using the empirical 2.5th and 97.5th percentiles.

The Seed99 run above uses:

- `bootstrap_samples=1000`
- `random_seed=42`

The resulting report is saved as:

```text
backend/app/data/processed/seed99_robustness_bootstrap_ci_report_top10_1000_three_methods.json
```

## Explainability Replay Artifacts for `/artifact-demo`

The final `/artifact-demo` page also expects explainability replay artifacts. After the Seed99 formal experiment is complete, run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m backend.scripts.run_explainability_audit --artifact-prefix seed99_robustness --sample-size 1000 --output-prefix seed99_full_retry
```

This writes explainability artifacts to:

```text
backend/app/data/processed/explainability/
```

Important outputs include:

- `seed99_full_retry_explainability_summary.json`
- `seed99_full_retry_explainability_audit.json`
- `seed99_full_retry_explainability_examples.csv`
- `seed99_full_retry_rank_shift_analysis.csv`
- `seed99_full_retry_case_studies.md`

## Backend Launch Command

Exact FastAPI launch command:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8009
```

Repo-root helper:

```powershell
start-backend.cmd
```

Health check:

```text
http://127.0.0.1:8009/health
```

## Frontend Launch Commands

### Development Mode

```powershell
cd frontend
$env:PORT='3009'
$env:NEXT_PUBLIC_API_BASE_URL='http://127.0.0.1:8009'
npm.cmd run dev
```

### Production-Style Local Run Used for the Artefact

```powershell
cd frontend
$env:NEXT_PUBLIC_API_BASE_URL='http://127.0.0.1:8009'
npm.cmd run build
npm.cmd run start:artifact-demo
```

Repo-root helper:

```powershell
start-frontend.cmd
```

The helper script performs:

1. `npm.cmd run build`
2. `npm.cmd run start:artifact-demo`

with `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8009`.

## How to Access the Demo

Once the backend and frontend are both running, open:

```text
http://127.0.0.1:3009/artifact-demo
```

The backend walkthrough route that feeds this page is:

```text
GET /demo/workflow-cases?artifact_prefix=seed99_robustness&explainability_prefix=seed99_full_retry
```

## Read-Only Replay Confirmation

The `/artifact-demo` page is a read-only replay of saved offline outputs.

It does:

- read saved experiment artifacts from `backend/app/data/processed/`
- read saved explainability artifacts from `backend/app/data/processed/explainability/`
- render a deterministic walkthrough for selected saved users

It does not:

- rerun the formal experiment when the page loads
- regenerate recommendations live
- retrain SVD
- regenerate the Hybrid ranking live
- run a live user study

## Pytest Commands

Full backend test suite from the repository root:

```powershell
python -m pytest backend/tests
```

Windows-safe low-cache variant used in this repo when cache locking causes issues:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend/tests -q -p no:cacheprovider
```

Targeted tests:

```powershell
python -m pytest backend/tests/test_data_service.py
python -m pytest backend/tests/test_cf_service.py
python -m pytest backend/tests/test_agentic_service.py
python -m pytest backend/tests/test_formal_evaluation_service.py
```

## Saved Artefact Locations

### Raw Data

```text
backend/app/data/raw/
```

### Processed Formal Experiment Outputs

```text
backend/app/data/processed/
```

Examples:

- `processed_interactions_with_articles.csv`
- `evaluation_base_table_svd_top10_all_valid.json`
- `seed99_robustness_*`

### Explainability Outputs

```text
backend/app/data/processed/explainability/
```

Examples:

- `seed99_full_retry_explainability_examples.csv`
- `seed99_full_retry_explainability_summary.json`

## Common Errors and Troubleshooting

### 1. Missing Raw Dataset Files

Symptom:

- the data build step fails with a message about missing raw files

Cause:

- one or more required CSV files are not present in `backend/app/data/raw/`

Fix:

- confirm all of these exist:
  - `transactions_train.csv`
  - `articles.csv`
  - `customers.csv`

### 2. `OPENAI_API_KEY is required`

Symptom:

- agentic intention or explanation steps fail because no API key is available

Cause:

- `backend/.env` is missing `OPENAI_API_KEY`

Fix:

- add a valid key to `backend/.env`
- do not expose the real key in screenshots or dissertation appendices

### 3. PowerShell Blocks `npm`

Symptom:

- `npm -v` or `npm` fails because PowerShell script execution is disabled

Fix:

- use `npm.cmd` instead of `npm`

Example:

```powershell
npm.cmd install
npm.cmd run build
```

### 4. Frontend Cannot Reach the Backend

Symptom:

- the frontend loads but data fetches fail

Cause:

- `NEXT_PUBLIC_API_BASE_URL` was not set correctly before starting Next.js

Fix:

```powershell
$env:NEXT_PUBLIC_API_BASE_URL='http://127.0.0.1:8009'
```

Then restart the frontend.

### 5. Port Conflicts

Symptom:

- backend or frontend fails to bind to `8009` or `3009`

Fix:

- stop the existing process already using the port
- then restart:
  - backend on `8009`
  - frontend on `3009`

### 6. Missing `.next/types/...`

Symptom:

- `npx.cmd tsc --noEmit` reports missing `.next/types/...`

Fix:

```powershell
cd frontend
npm.cmd run build
```

Then rerun the type check.

### 7. Page Shows Old Layout After Restart

Symptom:

- the browser still shows an earlier UI after a restart

Fix:

- do one hard refresh in the browser

### 8. Shared `.next` State Conflicts

Symptom:

- unexpected frontend behaviour when another Next.js process for the same repo is already running

Fix:

- stop the other repo process first
- then restart only the intended `3009` instance

### 9. Pytest Cache or Lock Noise on Windows

Symptom:

- `.tmp/pytest` produces warnings or locking issues

Fix:

- use:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend/tests -q -p no:cacheprovider
```

### 10. `/artifact-demo` Fails Because Explainability Artifacts Are Missing

Symptom:

- the walkthrough API or page cannot find saved explainability outputs

Fix:

- run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m backend.scripts.run_explainability_audit --artifact-prefix seed99_robustness --sample-size 1000 --output-prefix seed99_full_retry
```

### 11. Running `uvicorn` From the Wrong Directory

Symptom:

- `app.main:app` does not resolve correctly

Fix:

- start the backend from `backend/`, not from another directory

Correct command:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8009
```

## Minimal Reproduction Checklist

1. Download the H&M dataset from Kaggle.
2. Place `transactions_train.csv`, `articles.csv`, and `customers.csv` in `backend/app/data/raw/`.
3. Create `backend/.env` with a valid `OPENAI_API_KEY`.
4. Create the backend virtual environment and install `backend/requirements.txt`.
5. Install frontend dependencies with `npm.cmd install`.
6. Run the Seed99 formal experiment command block.
7. Run the explainability audit command with `--output-prefix seed99_full_retry`.
8. Start the backend on `127.0.0.1:8009`.
9. Start the frontend on `127.0.0.1:3009`.
10. Open `http://127.0.0.1:3009/artifact-demo`.

