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

## Imports
Uploading is two calls with the same file: `POST /accounts/{id}/imports/preview`
shows how the file was read (`source`: detected, guessed, saved...), the rows,
and which are duplicates; `POST /accounts/{id}/imports` stores the new rows.
Both take an optional `config` form field (a JSON `ImportConfig`) to override
how the file is read; a confirmed import saves it on the account, so the next
upload needs no config. Raw files are never stored, only their hash.
The importers themselves live in `spending_core.importers`.

## Categories and budgets
Categories, rules and budgets belong to a scope: yours (for your unshared
accounts) or, with `?household_id=`, a household's (for the accounts shared into
it). A scope gets a copy of the default categories on first use. Transactions
store the category by name, so the same name adds up across scopes in "My view".
- `/categories`: list, add, rename (transactions, rules and budgets follow), delete
  (its transactions are categorized again). The fallback ("Other") can't be deleted.
- `/category-rules`: "text in the description → category". A scope's rules come
  before the default keywords and the longest match wins. Adding or deleting a rule
  re-runs the rules on transactions nobody categorized by hand
  (`transactions.category_manual`).
- `/budgets?month=YYYY-MM`: targets (every month, or one month's override) against
  spending: shared spending for a household, your own share for you.

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
- `app/imports.py`: upload → preview → confirm
- `app/categories.py`: categories, rules and budgets per scope
- `app/routes/`: endpoints, one module per resource
- `app/settings.py`: configuration from env / `.env`
