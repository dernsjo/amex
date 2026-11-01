# amex
Monthly spend analysis, with optional expense splitting in a household.

| Directory | What |
|---|---|
| `core/` | `spending_core`: framework-free domain logic (Amex parsing, categorization, settlement). Shared by everything below. |
| `backend/` | FastAPI + SQLAlchemy API, Alembic migrations |
| `frontend/` | Vite + React + TypeScript UI |
| `src/` | The original Streamlit PoC (now uses `spending_core`) |
| `docs/ROADMAP.md` | The plan from PoC to a multi-household product |

## Setup (Python)
Python 3.11+. One virtualenv at the repo root covers the core, backend and PoC.

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r backend/requirements-dev.txt   # run from the repo root
```

## Tests
```bash
pytest core
cd backend && pytest
cd frontend && npm run typecheck
```

## Auth (Supabase)
Create a project at supabase.com (EU region), then:
- `backend/.env`: `SUPABASE_URL` (see `backend/.env.example`)
- `frontend/.env.local`: `VITE_SUPABASE_URL` and `VITE_SUPABASE_KEY` (the publishable/anon key)
- In Supabase, Authentication → URL Configuration: add `http://localhost:5173` as a redirect URL

Sign-in is by magic link to your email.

## Run
Backend (see `backend/README.md` for Postgres):
```bash
cd backend
alembic upgrade head
fastapi dev app/main.py              # http://localhost:8000, docs at /docs
```

Frontend:
```bash
cd frontend
npm install
npm run dev                          # http://localhost:5173
```

Streamlit PoC:
```bash
streamlit run src/calculate_debt.py
```

## Notebooks
Notebook output is stripped on commit; see
https://gist.github.com/33eyes/431e3d432f73371509d176d0dfb95b6e
