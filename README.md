# Agentic AI Recommendation Demo

Academic demo comparing a collaborative filtering benchmark against an agentic AI recommendation framework on the H&M Personalized Fashion Recommendations dataset.

## Stack

- Backend: FastAPI + pandas
- Frontend: Next.js App Router + TypeScript
- Storage: local CSV/JSON artifacts
- LLM integration: OpenAI API for user-intent interpretation and recommendation explanations

## Project Layout

- `backend/` FastAPI API, experiment pipeline, tests, and local data folders
- `frontend/` Next.js dashboard with five research/demo pages

## Dataset Placement

Drop these files into `backend/app/data/raw/` before running the experiment:

- `transactions_train.csv`
- `articles.csv`
- `customers.csv`

The raw dataset is not committed to git.

## Backend Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Frontend Setup

```bash
cd frontend
npm.cmd install
npm.cmd run dev
```

## Environment

Backend expects:

- `OPENAI_API_KEY`
- Optional `OPENAI_MODEL` defaulting to `gpt-4.1-mini`
- Optional `FRONTEND_ORIGIN` defaulting to `http://localhost:3000`

## Main Endpoints

- `POST /experiment/run`
- `GET /experiment/setup`
- `GET /users/{user_id}/intent`
- `GET /recommendations/compare/{user_id}`
- `GET /metrics`
- `POST /users/{user_id}/feedback`

## Demo Flow

1. Place the H&M CSV files in `backend/app/data/raw/`
2. Start the FastAPI backend
3. Run `POST /experiment/run`
4. Start the Next.js frontend
5. Review the research setup, processing summary, user intent view, model comparison, and evaluation dashboard

