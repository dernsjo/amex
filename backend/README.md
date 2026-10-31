# Backend

FastAPI + SQLAlchemy 2.0. Domain logic lives in `../core` (`spending_core`); this
package only handles HTTP and persistence.

## Database
Without configuration the API uses a SQLite file at `backend/expenses.db`.

For Postgres (recommended, and what will be used in production):
```bash
docker compose up -d                 # from the repo root
cp .env.example .env                 # points DATABASE_URL at the container
```

Schema changes go through Alembic:
```bash
alembic upgrade head                                  # apply migrations
alembic revision --autogenerate -m "describe change"  # after editing app/models.py
```
`tests/test_migrations.py` fails if models and migrations drift apart.

## Run
```bash
fastapi dev app/main.py     # auto-reload, http://localhost:8000
fastapi run app/main.py     # production mode: no reload, listens on 0.0.0.0
```

## Layout
- `app/models.py`: database tables
- `app/schemas.py`: request/response models
- `app/crud.py`: database access
- `app/routes.py`: endpoints
- `app/settings.py`: configuration from env / `.env`
