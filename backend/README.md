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

## Auth
Sign-in is handled by Supabase; the API only verifies the access token sent as
`Authorization: Bearer <jwt>` and creates a `User` row the first time it sees a
token's `sub`. Set `SUPABASE_URL` in `.env` (and `SUPABASE_JWT_SECRET` if the
project still signs tokens with the legacy shared secret). Every endpoint except
`/` requires a token.

Who can see what is decided in one place, `app/access.py`: your own accounts,
plus accounts shared into households you belong to. `tests/test_isolation.py`
checks that nothing else leaks.

## Run
```bash
fastapi dev app/main.py     # auto-reload, http://localhost:8000
fastapi run app/main.py     # production mode: no reload, listens on 0.0.0.0
```

## Layout
- `app/models.py`: database tables
- `app/schemas.py`: request/response models
- `app/auth.py`: token verification, current user
- `app/access.py`: what the current user may see
- `app/crud.py`: database access
- `app/routes/`: endpoints, one module per resource
- `app/settings.py`: configuration from env / `.env`
