# Portfolio Simulator — Architecture & Technology Decisions

This document records the architectural decisions made while building the
Portfolio Simulator. Each section describes **what** was chosen, and — more
importantly — **why** that choice was made for *this* project. The goal is to
give a future maintainer (or a future me) enough context to either extend the
system confidently or re-evaluate a decision when requirements change.

---

## 1. Project goals and constraints

The Portfolio Simulator is a **source-agnostic portfolio backtesting and
analytics tool**. It is a rewrite of an earlier prototype (Regalo) into
production-quality code. Concrete goals:

- Let a small set of known users (friends, family, a few colleagues) build,
  backtest, compare and optimize investment portfolios from a browser, 24/7,
  without installing anything.
- Be **free or nearly free** to run. This is a personal project, not a SaaS.
- Keep the door open for **multiple market-data providers** (Yahoo today,
  Refinitiv / Bloomberg later) without rewriting the analytics.
- Remain **fully usable locally** with zero cloud dependencies — I should be
  able to clone the repo, run one command, and have a working app with
  persistent storage.
- Prioritize **simple, readable code** over clever abstractions. The user base
  is small; the architecture must match that reality.

These constraints shape every decision below: small scale, low budget,
local-first, cloud-optional, and optimized for one developer's cognitive load.

---

## 2. Language and build system

### Python 3.11+

**Why Python.** The entire financial-analytics ecosystem (pandas, numpy, scipy,
statsmodels, yfinance, PyPortfolioOpt, cvxpy, etc.) is Python-first. Rewriting
those in another language would be a multi-year effort for zero benefit. I also
already have deep Python fluency, so iteration speed is highest here.

**Why 3.11+.** The codebase uses modern typing features (`str | None`,
`from __future__ import annotations`, `dict[str, ...]` generics) that are
cleaner in 3.10+, and 3.11 brings meaningful interpreter performance gains. I
pinned `>=3.11` in `pyproject.toml` so I don't accidentally run on an older
interpreter locally.

### Hatchling + pyproject.toml (PEP 621)

**Why hatchling.** It's the default modern Python build backend, has zero
boilerplate for simple packages, and plays well with `pip install -e .` for
local development. I didn't need anything poetry offers (lock files,
virtualenv management) because Streamlit Cloud uses `requirements.txt`, so a
second source of truth would just create drift.

**Why `src/` layout.** `src/portfolio_simulator/` instead of a flat
`portfolio_simulator/` at the repo root. The src-layout forces you to install
the package before importing it, which catches "works on my machine because of
CWD" bugs that a flat layout lets through. The one-time cost — Streamlit Cloud
doesn't automatically add `src/` to `sys.path` — is paid once in
`ui/app.py` via a small `sys.path.insert(...)` shim.

### requirements.txt alongside pyproject.toml

Streamlit Community Cloud installs from `requirements.txt`, not from
`pyproject.toml`. I keep both in sync manually. It's mildly annoying but
beats the alternatives (pinning a `pip install .` command in a custom start
script, or using a tool like `pip-compile` that adds a build step).

---

## 3. UI framework — Streamlit

**Chosen:** Streamlit (`>=1.30`), rendered as a multi-page app controlled from
`src/portfolio_simulator/ui/app.py` with one view module per page.

**Alternatives considered:**

| Option | Why not |
|---|---|
| **Dash / Plotly** | More flexible but forces me to write callbacks and manage state by hand. Too much plumbing for a small app. |
| **Gradio** | Great for ML demos, poor for multi-page data-dense apps with custom widgets. |
| **FastAPI + React** | The "real" answer for a production SaaS. For ~5 users it's a massive overbuild — two languages, two deploys, auth plumbing, CORS, bundler configuration. Not worth it. |
| **Jupyter notebooks** | No shareable UI for non-technical users. |

**Why Streamlit wins here:**

1. **Pure Python, top-to-bottom.** Every view is a single `render()` function.
   I can write analytics, charts, and UI in the same file without context-
   switching between a frontend and backend language.
2. **First-class DataFrame / Plotly rendering.** `st.dataframe` and
   `st.plotly_chart` handle the most important outputs with zero wiring.
3. **Free hosting that's purpose-built for it.** Streamlit Community Cloud
   deploys directly from GitHub, gives HTTPS, and requires no Docker file or
   server config. This is the decisive factor for the deployment budget.
4. **Session state + widget model** is sufficient for a small app. I don't need
   a Redux-style store.

**Known trade-offs accepted:**

- Streamlit reruns the whole script on every widget interaction. This is fine
  for the current workloads, but it makes caching and state management load-
  bearing (see §6 and §8).
- Streamlit Cloud free apps sleep after ~15 minutes of inactivity and cold-
  start in ~30 seconds. For a personal tool used by a handful of people, this
  is not a problem.
- HTML/CSS customization is limited. I lean on brand-color badges and emoji
  rather than fighting the theme.

---

## 4. Hosting — Streamlit Community Cloud

**Chosen:** Streamlit Community Cloud (free tier).

**Why.** It is the only hosting option that matches the constraints exactly:

- **Free** — no credit card required, no per-minute billing.
- **Purpose-built** — native Streamlit support, no Docker to maintain.
- **GitHub-integrated** — `git push main` triggers auto-deploy; no CI/CD to
  set up.
- **HTTPS-by-default** — no Cloudflare/Caddy/nginx configuration needed.
- **Secrets manager** — `st.secrets` is populated from a TOML blob I paste
  into the Streamlit Cloud UI, so credentials never live in the repo.

**Alternatives considered:**

- **Fly.io / Render.com free tier:** More flexible, but I'd have to write a
  Dockerfile, configure a health check, and manage a Postgres add-on. Extra
  cognitive load for no win.
- **Vercel / Netlify:** Not designed for long-running Python processes.
- **Self-hosted on a Raspberry Pi:** Fun, but requires dynamic DNS, TLS
  certificates, uptime monitoring. Not worth the maintenance.

**Deployment shim.** Because the package lives in `src/portfolio_simulator/`
and Streamlit Cloud runs `streamlit run src/portfolio_simulator/ui/app.py`
without `pip install -e .`, the package's parent directory isn't on
`sys.path`. I fixed this once in `app.py`:

```python
import sys
from pathlib import Path
_SRC_DIR = Path(__file__).resolve().parents[2]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
```

This is ugly but honest — it's a single three-line wart that buys an otherwise-
standard `src/` layout.

---

## 5. Authentication — streamlit-authenticator

**Chosen:** `streamlit-authenticator>=0.3` with bcrypt-hashed passwords and a
whitelist stored in `st.secrets`.

**Why.** Requirements were:

1. Restrict access to a small whitelist of users.
2. Per-user portfolio isolation (one user cannot see another's portfolios).
3. No external auth provider (free tier only).
4. Minimal code and no SMTP / email verification.

`streamlit-authenticator` is the de-facto community standard:

- Password hashing with **bcrypt** (industry-standard).
- **Cookie-based sessions** with a signing key, so a refresh doesn't log you
  out.
- **Whitelist in `st.secrets`** — I edit a TOML blob in the Streamlit Cloud
  dashboard to add/remove users. No user-signup flow to build, no email server
  to run.
- **Zero UI work** — `authenticator.login()` renders a drop-in login form.

**Alternatives considered:**

- **OAuth (Google / GitHub):** Overkill and leaks the user's identity to a
  third party. No benefit when the user list is a personal whitelist.
- **Supabase Auth:** Tempting because I'm already using Supabase for the
  database. But it requires JavaScript SDK plumbing that fights Streamlit's
  Python-only model.
- **Custom JWT + bcrypt:** Re-implementing what streamlit-authenticator
  already does. Not worth it.

**Known rough edges and fixes:**

1. `st.secrets` is read-only, but `streamlit-authenticator` mutates the
   credentials dict internally (to track failed login attempts). Shallow
   `dict(st.secrets["credentials"])` isn't enough — nested entries remain
   read-only. Fix: a `_to_mutable()` recursive deep-copy helper in
   `src/portfolio_simulator/ui/auth.py`.
2. `@st.cache_resource` on the authenticator factory triggers a
   `CachedWidgetWarning`, because the Authenticate constructor instantiates a
   cookie-manager component which is treated as a widget. Fix: store the
   authenticator in `st.session_state["_authenticator"]` instead of caching
   it. State still persists for the session; we just don't cache across
   sessions.

Both fixes are documented as comments in `auth.py` so the next person doesn't
"clean them up".

### Auth toggle for local dev

A `PSIM_REQUIRE_AUTH` environment variable (or the presence of a
`[credentials]` block in `st.secrets`) enables the auth gate. When it's off,
the app sets `st.session_state["user_id"] = "local"` and skips the login
screen entirely. This means local dev is zero-friction: `streamlit run ...`
Just Works with no secrets file.

---

## 6. Data persistence — dual-mode SQLite + Supabase PostgreSQL

This is the most nuanced decision in the app. The store layer needs to:

1. Persist portfolios across sessions.
2. Keep per-user data isolated on the hosted instance.
3. Require **zero** setup for local dev.
4. Cost nothing.

### The dual-mode design

There are **two** implementations of the same `PortfolioStore` interface:

- `src/portfolio_simulator/services/portfolio_store.py` — SQLite, used locally
  at `~/.portfolio_simulator/portfolios.db`.
- `src/portfolio_simulator/services/pg_portfolio_store.py` — PostgreSQL, used
  on Streamlit Cloud via Supabase.

A factory in `services/__init__.py` returns one or the other based on whether
`settings.database_url` is set:

```python
def get_portfolio_store():
    if settings.database_url:
        return PgPortfolioStore(settings.database_url)
    return PortfolioStore(settings.db_path)
```

Every view calls `get_portfolio_store()` and never constructs a store
directly. That keeps the swap invisible to the UI layer.

**Why two stores instead of one abstraction.** I could have used SQLAlchemy
Core and written one query layer that runs on both SQLite and Postgres. I
chose two concrete implementations because:

- The code in each is ~80 lines of straightforward parameterized SQL.
- SQLAlchemy would pull in a large dependency and an ORM model layer for two
  tables.
- The dialects diverge in ways I actually care about (JSON vs JSONB, SERIAL
  vs AUTOINCREMENT, `ON CONFLICT` syntax) — abstracting them costs more than
  duplicating them.

**Why SQLite locally.** Single file, no server to run, no credentials to
manage, backups are `cp portfolios.db`. For a one-person local database it's
impossible to beat.

**Why Supabase for the cloud database.**

- **Free tier:** 500 MB of Postgres — roughly 5,000× the storage I'll ever
  need for small JSON portfolio blobs. No credit card.
- **Real Postgres:** not a Postgres-like ORM abstraction. I can connect with
  `psycopg2` and use standard SQL.
- **Hosted and backed up** by Supabase — one less thing to run.
- **Good web dashboard** for inspecting the `portfolios` table during
  debugging.

**Alternatives considered:**

| Option | Why not |
|---|---|
| **Neon (serverless Postgres)** | Similar free tier. Supabase has a nicer dashboard and bundles auth/storage if I ever want them. |
| **PlanetScale (MySQL)** | Free tier ended. Also MySQL, which I like less for JSON workloads. |
| **Firebase / Firestore** | Document store, not SQL. The analytics side of this app thinks in DataFrames; SQL is a better impedance match. |
| **Streamlit Cloud's filesystem** | Ephemeral — writes are lost on redeploy. Hard no. |
| **GitHub as a database** | I seriously considered committing portfolio JSON to a private repo. Rejected: concurrent writes are a nightmare and it leaks the edit history. |

### Per-user isolation

Both stores carry a `user_id TEXT NOT NULL DEFAULT 'local'` column on the
`portfolios` table. Every query filters by `WHERE user_id = ?` and the unique
constraint is `UNIQUE(user_id, name)` so two users can both have a portfolio
called "Balanced".

The default value `'local'` is load-bearing — it means existing local SQLite
files from before the auth work continue to function without a migration.
The SQLite store also has a one-time `_migrate()` method that ALTERs the
table if an older schema is detected.

### The Supabase IPv6 / connection pooler trap

The direct Supabase connection string (`db.<project>.supabase.co:5432`) is
**IPv6-only**. Streamlit Cloud's outbound network does not support IPv6, so
`psycopg2.connect()` times out with an opaque error.

The fix is to use Supabase's **Session pooler** endpoint
(`aws-0-<region>.pooler.supabase.com:5432`, username
`postgres.<project_ref>`), which speaks IPv4. **Not** the Transaction pooler
on port 6543 — that one doesn't support prepared statements, which psycopg2
uses under the hood.

`PgPortfolioStore.__init__` auto-injects `sslmode=require` into the URL if
missing and wraps connection failures with a friendly error message pointing
at this exact issue. This was painful to debug; the comment in the code is
there to save the next me from repeating it.

---

## 7. Configuration — pydantic-settings

**Chosen:** `pydantic-settings>=2.0` with a single `Settings` class in
`src/portfolio_simulator/config.py`.

**Why:**

- **Typed, validated config** with zero boilerplate. Field types double as
  documentation.
- **Layered sources**: env vars (`PSIM_*`), `.env` files, and `st.secrets`
  fallback, all with one consistent API.
- **Same philosophy as pydantic models** used in the domain layer — one
  library to learn.

The `_load_settings()` helper pulls `database_url` and `require_auth` out of
`st.secrets` when they aren't set via env vars. This lets both local dev
(env vars / `.env`) and cloud dev (Streamlit secrets) feed the same
`settings` singleton without knowing about each other.

---

## 8. Caching strategy

There are **three** independent caches in the app, each solving a different
problem.

### 8.1 Market-data cache — two-tier (memory LRU + SQLite parquet blobs)

Lives in `src/portfolio_simulator/cache/`. Every call to a data provider
goes through `DataService`, which:

1. Checks an **in-memory LRU** for the `(ticker, start, end)` slice — near-
   instant return on a warm hit.
2. Falls back to a **SQLite blob table** that stores each ticker's full price
   history as a **parquet-serialized DataFrame** — one row per ticker. This
   survives across processes and across container restarts (locally).
3. Falls through to the provider (yfinance) only if both tiers miss.

**Why two tiers.** Memory is fast but dies with the process. SQLite parquet
is slower but persists. Together they give sub-millisecond latency on the
common path without re-hitting Yahoo every rerun, which Streamlit would
otherwise do 100 times per session.

**Why parquet instead of per-row rows.** Per-ticker price history is naturally
a DataFrame. Serializing it as parquet via `pyarrow` gives fast round-tripping
and typed columns (dates as dates, floats as floats), and keeps one row per
ticker in the table instead of millions.

**Why SQLite for the blob store even on Streamlit Cloud.** The cloud
filesystem is ephemeral, so the cache rebuilds on wake. That's fine — cache
misses just fall through to yfinance, which is free and fast enough. The
alternative — caching price data in Supabase — would waste the 500 MB
Postgres quota on data that's freely re-fetchable.

### 8.2 Service-level — `@st.cache_resource`

`get_portfolio_store()` and `get_data_service(provider_name)` are decorated
with `@st.cache_resource`. Streamlit otherwise rebuilds these on every script
rerun (which happens on every widget interaction), and:

- Rebuilding `PgPortfolioStore` means opening a new psycopg2 connection
  every click — slow, wasteful, and a source of connection-pool exhaustion.
- Rebuilding `DataService` discards the in-memory LRU every click.

`@st.cache_resource` is the right decorator here (not `@st.cache_data`)
because these objects are **stateful connections**, not pure data snapshots.

### 8.3 Session-level — `st.session_state`

Used for objects that:

- Depend on widgets (so can't go in `@st.cache_resource` — see the
  `CachedWidgetWarning` discussion in §5).
- Need to survive a script rerun within a single session.

Examples: the authenticator instance, the currently-selected portfolio, the
latest backtest result (so the Monte Carlo tab in the Optimizer view can find
it), the `pending_asset` in the Portfolio Builder.

**Rule of thumb I've settled on:**

- Expensive, read-only, cross-session → `@st.cache_data`
- Stateful connection-like objects → `@st.cache_resource`
- Anything widget-derived or session-scoped → `st.session_state`

---

## 9. Data providers — plug-in Provider protocol

`src/portfolio_simulator/providers/` defines a `Provider` protocol and one
concrete implementation (`YahooProvider` via `yfinance`). The UI sidebar
shows a "Data Source" selector built from `PROVIDER_META` in
`ui/components/provider_selector.py`, with Yahoo available today and
Reuters / Bloomberg listed as "coming soon".

**Why a Protocol, not an ABC.** `typing.Protocol` gives structural typing: a
future provider just needs to implement the method signatures; it doesn't
have to inherit. This matches the "source-agnostic" project goal without
forcing a class hierarchy on third-party code.

**Why yfinance for the first provider.**

- **Free** and requires no API key.
- **Wide asset coverage**: stocks, ETFs, indices, crypto, FX.
- **Good-enough data quality** for portfolio backtesting at daily resolution.
  Not good enough for production trading — acknowledged and documented in
  the app's "How Backtest works" expander.
- Matches the "zero setup for local dev" constraint perfectly.

**Why show the active provider as a brand-colored badge in the sidebar.**
Users were confused about where asset tickers were coming from and whether
prices were real or synthetic. A permanently visible "Yahoo! Finance" badge
in the provider's brand purple makes the source obvious. Originally I tried
to render the official logo via `st.image(url)`, but hotlinked Wikipedia
Commons images sometimes fail to load on Streamlit Cloud and leave a
broken-image icon. A styled HTML `<div>` with the brand color is reliable,
offline-friendly, and good-looking enough.

---

## 10. Analytics, visualization, and export libraries

| Concern | Library | Why |
|---|---|---|
| Tabular data | **pandas** | Industry standard. Every finance library speaks DataFrames. |
| Numerics | **numpy** | pandas dependency anyway; direct use for vectorized math. |
| Optimization | **scipy** | Used for the efficient-frontier quadratic optimizer. Self-contained, no need for cvxpy's heavier stack. |
| Charts | **plotly** | Interactive by default (zoom, hover, legend toggles), renders cleanly in Streamlit via `st.plotly_chart`. matplotlib is static and not as nice in a web context. |
| Parquet serialization | **pyarrow** | Required for pandas' parquet IO, also powers the cache blobs. |
| Excel export | **openpyxl** | Required by pandas' `ExcelWriter` for `.xlsx`. Chose xlsx over CSV for the "View & export raw data" feature because users wanted multi-sheet workbooks (portfolio value + returns + asset prices in one file). |
| Asset autocomplete | **streamlit-searchbox** | Drop-in debounced search widget. Writing one from scratch would take longer than the savings. |
| Trading calendar | **exchange-calendars** | Needed to know valid trading days per exchange for rebalancing logic. Maintained and covers all majors. |

**What I deliberately did _not_ add:**

- **PyPortfolioOpt / cvxpy** — overkill for a from-scratch Markowitz frontier.
  The direct `scipy.optimize` version is ~50 lines and I fully understand it.
- **SQLAlchemy** — see §6.
- **Backtrader / zipline** — heavy, opinionated engines designed for
  event-driven trading strategy research. The app's backtest model is much
  simpler: rebalance-and-hold with costs. A focused in-house engine is
  smaller, faster, and easier to extend.

---

## 11. Domain model — immutable dataclasses

`src/portfolio_simulator/domain/` contains frozen dataclasses for
`Portfolio`, `Asset`, `SimulationConfig`, `BacktestResult`, etc., plus
`enums.py` for `RebalanceStrategy`, `InvestmentStrategy`, etc.

**Why frozen dataclasses over pydantic models for the domain layer.**

- The domain objects are constructed by **internal** code, not parsed from
  external JSON. Pydantic's validation and coercion are unnecessary overhead
  here.
- Immutability (`frozen=True`) makes state changes explicit: to "mutate" a
  portfolio you construct a new one. This composes well with Streamlit's
  rerun-based model, where accidental mutation of shared state is a classic
  bug.
- Dataclasses are stdlib — no version compatibility concerns.

Pydantic is reserved for `Settings` (§7), where the "parse and validate from
an external source" behavior is exactly what I want.

---

## 12. UI layering

```
ui/
├── app.py                  # Router, auth gate, sidebar
├── auth.py                 # streamlit-authenticator wrapper
├── components/             # Reusable widgets (provider_selector, data_export, metric_cards)
└── views/                  # One file per page (portfolio_builder, backtest, comparison, optimizer)
```

Each view is a single `render()` function. The router in `app.py` picks the
right one based on the sidebar's page selector. Shared concerns
(authentication, provider selector, user id) live in `app.py` and are read
from `st.session_state` inside views — that way views stay decoupled from the
auth system and can be tested in isolation.

**Why per-view files instead of a mega-module.** At current size (4 pages),
one file per page is still comfortable to navigate. The split also happens to
match how I think about features ("the Backtest page") when reaching for a
file to edit.

**Info expanders pattern.** Every view has a short `st.caption(...)` under
the header giving a one-sentence elevator pitch, plus a collapsed
`st.expander("How X works")` containing a detailed explanation with sections
for **What it does**, **How it works**, **Caveats**. This keeps the UI
uncluttered for experienced users while giving new users a path to "why
should I trust these numbers". Content lives in the view file next to the
code it describes, not in a separate docs site, so it stays in sync.

---

## 13. Testing — pytest

`tests/` is run with `pytest`. Markers include `slow` for tests that hit
external APIs (yfinance); those can be deselected with `-m "not slow"` for
fast local iteration.

**Why pytest over unittest.** Fixtures, parametrization, and terser assert
syntax. Standard choice.

**Where coverage is deep:** analytics (returns, metrics, efficient frontier,
Monte Carlo) and domain model construction. Those are the parts where a bug
silently produces wrong numbers — exactly where regression tests are worth
writing.

**Where coverage is shallow:** UI views. Streamlit's script-rerun model makes
view tests awkward; I rely on manual smoke testing instead. Not proud of it
but honest about the trade-off.

---

## 14. Secrets and configuration files

| File | Purpose | Gitignored? |
|---|---|---|
| `.env` | Local env vars for `pydantic-settings` | yes (via `.env`) |
| `.streamlit/config.toml` | Theme / server config | no — safe to commit |
| `.streamlit/secrets.toml` | Local mirror of Streamlit Cloud secrets | **yes** — contains credentials |
| `.streamlit/secrets.toml.example` | Template showing the shape | no — committed |

Streamlit Cloud secrets are edited in the web UI and injected as
`st.secrets` at runtime; they never touch the repo.

`data/` (SQLite market-data cache) is gitignored. So is `Capture.JPG` — a
throwaway screenshot the user shared during UX iteration that has no reason
to live in version control.

---

## 15. What I deliberately left for later

These are explicit non-goals for v1, noted here so "why didn't you do X"
questions have answers:

- **User preference persistence** — saving each user's default start date,
  initial investment, benchmark etc. into Supabase. Planned as Step 7 of the
  deployment plan, currently deferred. Current behavior: Streamlit's
  per-session widget state only.
- **Multi-currency portfolios** — Yahoo returns prices in listing currency;
  mixing USD and EUR assets in one portfolio will give nonsense. Needs an
  FX conversion layer. Out of scope for now because all my test portfolios
  are single-currency.
- **Real logos for data providers** — see §9 rationale. Would require
  bundling SVG assets.
- **Reuters / Bloomberg providers** — the `PROVIDER_META` scaffold is in
  place but neither is implemented. Will add if I ever get data access.
- **Background jobs / scheduled refresh** — Streamlit Cloud doesn't support
  cron-style workers. Cache rebuilds on demand instead.
- **CI/CD pipeline** — Streamlit Cloud auto-deploys on push to `main`.
  A GitHub Actions workflow to run pytest before deploy would be a nice
  addition but isn't critical at current scale.

---

## 16. Summary — the one-paragraph version

The Portfolio Simulator is a **Streamlit app** written in **Python 3.11+**,
deployed free on **Streamlit Community Cloud**, with **streamlit-authenticator**
gating access behind a whitelist stored in `st.secrets`. Portfolios are
persisted in **SQLite** locally and in **Supabase PostgreSQL** in the cloud,
with per-user isolation via a `user_id` column and a factory function that
picks the right store based on configuration. Market data flows through a
**pluggable Provider protocol** (Yahoo / yfinance today, Reuters / Bloomberg
scaffolded) and is cached in a **two-tier memory + SQLite-parquet** cache.
Analytics are built on **pandas / numpy / scipy**, charts on **plotly**,
exports via **openpyxl**. Configuration is managed with **pydantic-settings**.
The design prioritizes local-first development, zero cloud cost, readable code
over clever abstractions, and a small-scale user base over premature SaaS
scaffolding.
