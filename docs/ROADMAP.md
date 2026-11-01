# Roadmap: from PoC to a multi-household product

Goal: a user logs in and sees **their own spending**: accounts, budgets and
analysis. Sharing with a household (members, split weights, who owes whom) is an
optional layer on top. Sized for ~10 users at first, so the effort goes into
a correct data model and tenant isolation, not infrastructure.

## 1. What stops being hardcoded

| PoC (hardcoded) | Becomes |
|---|---|
| Amex CSV format | Importer plugins + a generic CSV mapper |
| Axel and Ebba | Household members (any number) |
| `Delad` / `Utlägg` / `Excludera` | An allocation per transaction: shared, personal, outlay, excluded |
| An even 50/50 split | Split weights per household (50/50, 60/40, by income) |
| `CATEGORY_KEYWORDS` | Default categories and rules + each household's own |
| `targets = {...}` in the plot function | A budgets table per household, category and month |
| One CSV per month on disk | Imports and transactions in a database, with deduplication |

## 2. Core data model

**User first, household optional.** Data belongs to users; a household is a way
to share some of it. Someone using the app alone never has to create one.

```
User ──< Account              (owner_id, household_id nullable, currency)
User ──< Membership >── Household
                 role: owner | member
                 split_weight: 1      # relative: 1/1 = 50/50, 3/2 = 60/40

Account ──< Import            (file name, hash, importer used, period, counts)
Account ──< Transaction
Transaction:
    account_id, import_id
    booked_on: date
    description_raw, description_clean
    amount_minor: int, currency           # whole öre, never floats
    allocation: shared | personal | outlay | excluded
    member_id (nullable)                  # whose it is, iff personal
    category, category_manual             # a category name in the account's scope
    dedupe_hash (unique per account)

Scope = a User (their unshared accounts) or a Household (accounts shared into it)
Scope ──< Category             (name, default_key; defaults copied on first use)
Scope ──< CategoryRule         (pattern → category name)
Scope ──< Budget               (category name, month or null = every month)
Household ──< Settlement       (period, result snapshot, closed_at)   (Phase 4)
```

Key decisions:
- **One access rule.** A user sees an account if they own it, or it's shared into a
  household they're a member of; transactions and imports follow their account.
  `backend/app/access.py` is the only place that decides this, and anything not
  visible answers 404. `tests/test_isolation.py` is the most important test file.
- **Sharing is per account.** The owner shares an account into a household (or
  stops sharing). Leaving a household unshares your accounts from it.
- **Owners manage, members allocate.** Only the account owner imports, adds,
  deletes or reshares; any household member can change allocation, category and
  who a transaction belongs to, so Ebba can mark exceptions on Axel's card.
- **Defaults follow sharing.** New spending on an unshared account is personal to
  the owner; on a shared account it's shared until someone says otherwise.
- **Members can be added before they sign up.** Adding an unknown email creates a
  pending member (a `User` without `auth_subject`) who can be split with at once;
  their first sign-in with that verified email takes over the row.
- **Categories follow the account's scope.** A shared account uses the household's
  categories and rules, an unshared one its owner's; sharing re-runs the rules.
  Transactions store the category *name* rather than a foreign key, so "Groceries"
  adds up across your own and your households' accounts in "My view".
- **Who paid comes from the account owner** (Phase 4 uses this for "who owes whom").
- **Settlement for N members:** each member's share = their personal spending +
  weight × shared spending. Outlays are reported separately.
- **Closing a month** stores a `Settlement` snapshot, so later edits don't quietly
  change history.

## 3. Importers

```python
class Importer(Protocol):            # spending_core/importers/
    id: str
    name: str
    def detect(self, table: Table) -> float: ...  # confidence 0–1
    def parse(self, table: Table) -> list[ParsedTransaction]: ...
```

`read_table` turns any CSV export into a `Table` first: it handles UTF-8 or
Windows-1252, `,` / `;` / tab delimiters, and skips preamble lines above the header.
An upload is read with, in order: the config sent with it, the account's saved
config if its columns still match, a built-in importer that recognizes the file,
or a mapping guessed from the header names and content.

- **Built-in importers:** `AmexSE` first, then the big Swedish banks, using real
  (anonymized) exports as test fixtures.
- **Generic CSV mapper:** the user picks which columns hold date, description and
  amount, plus the decimal separator and sign convention. The mapping is saved per
  account, so the next upload is automatic.
- **Deduplication:** a hash of (account, date, amount, normalized description, how
  many times that combination appears in the file). Uploading the same file twice
  adds nothing.
- **Later:** bank APIs through an open-banking aggregator (e.g. Tink or Enable
  Banking), only once CSV import is solid; it brings licensing and approval work.

## 4. Categorization pipeline

For each transaction, the first match wins:

1. The scope's own rules (e.g. "ICA MAXI → Groceries"); the longest matching text wins
2. Global default rules (the keyword lists in `spending_core.categorize`, versioned with the code)
3. *(Optional, later)* an LLM fallback for whatever is still unmatched, with results cached
4. Otherwise "Other"

When a user re-categorizes a transaction, offer *"Always do this for ICA MAXI?"*
and create a rule if they accept, so categorization improves per scope over time.
New and changed rules apply to existing transactions too, except ones a person
categorized by hand.

## 5. Budgets and analysis

- **Budgets:** a target per category for every month, with optional overrides per
  month, for a household (against shared spending) or for yourself (against your
  own share: personal spending plus your weighted part of shared spending).
- **Analysis endpoints** (plain SQL `GROUP BY`; no data warehouse needed at this scale):
  - `GET /households/{id}/summary?month=`: spending by category against target, by member, settlement preview
  - `GET /households/{id}/trends?from=&to=`: totals per month and category
  - `GET /households/{id}/settlements`: history of closed months
- **Dashboard:** month picker, spending against target per category (the existing
  target bar chart), a trend line, a "who owes whom" card, the largest transactions.

## 6. Tech stack

- **Backend:** FastAPI, SQLAlchemy 2.0, Alembic, Postgres, pydantic-settings
- **Auth: don't build it yourself.** Use a hosted provider (Clerk, Auth0 or Supabase
  Auth); the backend only verifies the JWT. Password reset, magic links and Google
  login come for free. Household invitations are our own `Invite` table holding a token.
- **Frontend:** Vite, React, TypeScript, React Router, TanStack Query, an API client
  generated from the OpenAPI schema (e.g. `openapi-typescript`), a component library
  (shadcn/ui or Mantine), Recharts
- **Deployment:** Docker Compose for local development. For hosting, one container
  plus managed Postgres on Render, Fly.io or Railway, **in an EU region**.
- **Avoid for now:** microservices, Kubernetes, message queues. A single FastAPI app
  handles 10 users, and 1,000 too.

## 7. Privacy (other people's financial data)

- Host in the EU; encryption at rest (managed DB) and HTTPS only.
- "Export my data" and "Delete my household" early on: GDPR requires both, and
  they're cheap to build from the start.
- Store raw uploaded files only if needed; otherwise parse and discard.
- Secrets in environment variables, automatic backups, never production data in local dev.

## 8. Phases

### Phase 0: Foundations ✅ (branch `phase-0-foundations`)
- [x] Extract a framework-free `core/` package (`spending_core`): parsing,
      categorization, N-member settlement, with tests
- [x] Postgres via Docker Compose, Alembic migrations, settings from env
- [x] CRA → Vite + TypeScript
- [x] Fix review bugs: split logic, Unicode minus, 100-row limit, 404 on empty list,
      client-side settlement round trip
- [x] Streamlit PoC uses `spending_core`, so logic can't drift
- [ ] Verify migrations against Postgres (Docker wasn't running)
- [ ] Confirm the raw Amex date format with a real export (assumed `MM/DD/YYYY` or ISO)
- [ ] CI (GitHub Actions) running `pytest core`, backend tests and `npm run typecheck`

### Phase 1: Multi-tenant model and auth (branch `phase-1-multi-tenant`)
- [x] User-owned accounts, optional households, memberships with split weights,
      imports and the transaction model above (Alembic migrations; the PoC tables are dropped)
- [x] Supabase Auth: the backend verifies the JWT (JWKS, or the legacy shared
      secret) and creates a `User` on first request; magic-link sign-in in the frontend
- [x] Access dependencies in `access.py`; household routes (create, members,
      weights, leave), accounts with sharing, transactions, per-account imports
- [x] Deduplication on import (`spending_core.dedupe_hashes`), since the model needs it anyway
- [x] Tenant-isolation tests
- [x] Supabase project created; both members signed in and see the same household
- ~~Load the PoC data as household #1~~ (dropped: not worth importing)
- [ ] Verify the migrations against Postgres (Docker still wasn't running)

### Phase 2: Imports (branch `phase-2-imports`)
- [x] Importer interface, `AmexSE`, generic CSV mapper with guessed and saved mappings
- [x] Upload → preview → confirm flow, deduplication, "this file was already imported" warning
- [x] Import history per account, with undo
- [ ] Built-in importers for the big Swedish banks, from real anonymized exports
      (the generic mapper covers them until then)
- [ ] Confirm the raw Amex date format with a real export (carried over from Phase 0)

### Phase 3: Categories and budgets (branch `phase-3-categories-budgets`)
- [x] Categories per scope (you or a household), seeded from the defaults; add, rename, delete
- [x] Rules per scope ahead of the default keywords; rules apply to existing
      transactions except hand-picked ones
- [x] Learning from corrections: "Always put PRESSBYRÅN in Eating out?" after a change
- [x] Budgets per scope and category, every month or one month; target vs spent per month
- [x] Budget and category management UI

### Phase 4: Analysis and settlement
- Summary and trend endpoints + dashboard
- N-member settlement with split weights; closing a month

### Phase 5: Private beta (~10 users)
- Invitations, onboarding (create household → add account → first import)
- Data export and deletion, error tracking (Sentry), backups
- Deploy; invite 2–3 households using different banks to find importer gaps

### Later
Bank API connections, LLM categorization, recurring-payment detection, PWA or
mobile app, notifications when a budget is exceeded.

## 9. Open questions (change the design)

1. ~~**Can one person belong to several households?**~~ Decided in Phase 1: the app
   is user-first and households are optional. A user can be in several; the UI
   has a "My view" / household switcher.
2. **Is the split always weighted per household, or sometimes per transaction or
   category?** E.g. groceries 50/50 but rent by income.
3. **Free and private for friends, or possibly paid later?** Affects the auth
   provider, terms of service and how strict the privacy setup needs to be.
