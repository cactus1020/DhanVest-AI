# DhanVest AI

An early-stage DSE research prototype with transparent factor scores and Bangla
explanations. It does not establish future returns or provide buy/sell advice.

## Run locally

From the repository root, install `requirements-dev.txt` for development and
tests (or just `requirements.txt` for the API). Copy `.env.example` to `.env` and
set fresh, server-only Supabase credentials. Then run:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/research` for research and `/early-access` for the
marketing page and waitlist. `/api/health` checks the database connection and
required schema. The app starts even without credentials and returns a clear
503 error instead of failing at import time. A reachable database with missing
migration fields reports `degraded`; stock names still load, while unverified
legacy records do not produce scores.

## Live database recovery

The existing deployment is `dhanvest-ai-live` on Vercel. Its former database
hostname, `bvuaggdosiqsqszlmtto.supabase.co`, did not resolve during the outage
check. The page itself returned HTTP 200. This proves the database endpoint was
unreachable, but does not identify whether the project was paused or deleted.
After the user restored the project, authenticated reads confirmed nine stocks,
2,160 daily records and nine score records. The supplied server credential is
configured as a sensitive variable in Vercel Preview and Production. The source
metadata and waitlist migration remains pending; no historical rows were deleted.

1. Authenticate the Supabase CLI or sign in to the owning Supabase account.
   Find the original project and restore it if available. Otherwise use an
   active replacement project; do not invent historical market data.
2. Revoke/rotate both the Supabase service-role key and Gemini credential that
   were previously embedded in frontend code and Git history. Removing them
   from current files does not revoke them. Do not reuse those credentials.
3. For a new database run `supabase-setup.sql`, then run
   `migrations/001_trusted_data_and_waitlist.sql`. For the existing database,
   apply the migration. It keeps legacy data unverified, adds source/reporting
   metadata and a private waitlist, and removes direct public table access.
   The migration aborts if duplicate stock/date rows exist; resolve them using
   the original source before rerunning it.
4. Set `SUPABASE_URL` and the **new** `SUPABASE_SERVICE_ROLE_KEY` in Vercel's
   server environment for both Preview and Production. Optional AI explanations
   require a **new** `GEMINI_API_KEY` and an available `GEMINI_MODEL` ID. Keys
   belong in server configuration, never in HTML or JavaScript.
5. Deploy from `frontend` with `vercel deploy`; verify `/api/health`, research
   loading, and an actual waitlist write before promoting with `vercel --prod`.

See `docs/dashboard-and-news-model-plan.md` for the proposed mobile/desktop
improvements, historical-data acquisition, news-aware research and background
update pipeline. These new features are a proposal, not implemented capabilities.

The existing Vercel project uses the `frontend` folder as its deployment source.
Its FastAPI entrypoint is `frontend/app.py`; it includes lean runtime requirements
and its own Vercel configuration. `frontend/landing.html` mirrors the root
marketing page for this deployment; keep the two copies in sync when editing.
Repository-root deployment is also supported by `app.py` and `vercel.json`.

## Market data and scores

The bundled `real_dse_data.csv` has nine symbols and 2,160 rows but no dates.
It is deliberately rejected by import and training. Obtain genuinely dated
source data before importing it:

```powershell
python -m backend.seed_supabase path/to/dated.csv --source-url https://SOURCE/ARCHIVE --confirm-verified
python -m backend.scoring
```

Required CSV columns: `symbol,date,close,volume`. Dates must be real DSE trading
dates in `YYYY-MM-DD` format. Optional columns: `name,sector,pe_ratio,roe,
debt_to_equity,fundamentals_date`. Fundamentals require their own reporting date;
do not forward-fill future reports into earlier market records. Verify against
the stated source before using `--confirm-verified`. Imports upsert by stock/date
and never clear the database.

Quality: 60% of ROE normalized to 30%, plus 40% of debt-to-equity normalized from
0 to 2. Value: P/E compared with the median of at least three fresh companies in
the same known sector. Momentum: 60-session return normalized from -10% to +20%.
Liquidity: average volume over 20 sessions normalized to 200,000 shares. All
factors are clamped to 0–100. These are documented heuristics, not validated
investment recommendations.

Base weights are quality 32%, value 28%, momentum 25%, liquidity 15%. Missing
inputs remain null; available weights are renormalized, with coverage and actual
weights shown. Fundamentals older than 180 days are unavailable. Market snapshots
older than seven days are labeled historical. The old ML prediction boost and
cached explanations are not used. API history reads paginate rather than
silently accepting only the first 1,000 rows.

Bangla explanations use factor rules by default. Optional Gemini calls run only
on the server, use the displayed facts, and cache by data/model signature.
Obvious advice, forecasts, invented numbers and invalid responses fall back to
the deterministic explanation. This filter is not a guarantee of factual
correctness. The UI discloses whether the explanation came from rules or AI.

## Model research and verification

See `MODEL_CARD.md`. The replacement research script uses three chronological
folds and purges training labels reaching the test period. It reports a
majority-class baseline as well as accuracy and balanced accuracy. No accuracy
or performance claim is established until genuinely dated source data is tested.

```powershell
python -m backend.train_model path/to/dated.csv --source-url https://SOURCE/ARCHIVE --confirm-verified
python -m unittest discover -s tests -v
node --check frontend/assets/research.js
node --check frontend/assets/waitlist.js
```

Synthetic test fixtures verify implementation behavior only. No production
database writes or paid AI calls occur during these tests.


### Dashboard improvements and news groundwork

The research dashboard now includes company search, sector filtering, sorting by score or input coverage, browser-local watchlists, refresh, and verified-price charts. Chart ranges represent up to 20, 60 and 250 trading observations, rather than claiming complete calendar-month/year coverage. The displayed dates and observation count describe the actual history. The original legacy dashboard and database rows remain preserved.

`GET /api/stocks/{stock_id}/history` returns only validated, source-verified historical prices. Legacy rows are omitted from charts until their real dates and sources are established.

`backend/news_events.py` accepts a permitted JSONL news export and prepares point-in-time article counts, separately for official announcements, publisher reports and unverified claims. This is groundwork; it is not an active feed or trained news model. Explicit company symbols, timezone-aware publication and first-seen timestamps, HTTPS source URLs and consistent duplicate records are required. Historical archives retrieved today must retain today's first-seen time; do not fabricate past observation times to enable backtesting. Same-URL duplicates are removed; syndicated stories on different URLs still require upstream clustering.

Example: `python -m backend.news_events licensed-news.jsonl --symbols GP,SQURPHARMA --output validated-news.jsonl --confirm-rights`. The output must not already exist. The tool validates the complete input before creating output and never changes the live database. `event_features(events, symbol, as_of)` includes only events observed by the prediction cutoff. Counts are not sentiment, causal impact, or probability estimates.

Still required for live news and model training: a permitted feed and authentic dated market archive, the database migration, ingestion scheduling with monitoring, entity resolution, duplicate-story clustering, and out-of-time evaluation against the price-only baseline. Official DSE feeds and daily collectors are now active; public news-based predictions remain disabled. Newspaper ingestion is pending.


### Preserved research and V2 workspace

`/research` and the original `/dashboard.html` display the existing database's saved research again. Verified scores remain separate from `saved_scores`, and `stored_data` includes the last imported price, preceding-record change, volume and record count. The read-only `stored_summary_bn` explains these observations without an external AI call. Old saved explanations remain available as clearly labelled historical output.

The history endpoint accepts `?include_stored=true`: when no verified dates exist, it returns `mode: stored_sequence`, uses observation numbers and labels date/source uncertainty. It does not turn the generated import dates into real trading dates. Verified history remains the default endpoint behavior.

`/v2` is a separate development workspace for the intended live platform, with database status, company price metrics, research, stored charts and disclosure/news source links. It combines preserved records with DSE quotes, historical charts and announcements. Validated production forecasts are not enabled. Current implementation gaps and all 58 execution-plan tasks are reviewed in [the proposition alignment review](docs/proposition-alignment-review.md).


### DSE integration and first price/news experiment completed

As of 6 October 2026 the required schema migration has been applied. Unrelated shop/tuition tables were not changed. Legacy daily_data still has 2,160 rows and factor_scores still has nine saved rows. New market_history contains 23,961 date-validated DSE observations for 50 equities. Actual archive coverage is 6 October 2024 through 6 October 2026, despite the five-year request; out-of-range source rows were excluded. Explicit verified Saturday sessions are documented in docs/dse-special-sessions.md.

V2 reads the public DSE quote snapshot (360 PUBLIC-board equities in the tested session), market session status, one-year stock history and company announcements. It shows source time and retrieval time and distinguishes no-trade quotes. This is website-sourced data; exchange latency and commercial redistribution licensing are not certified. The protected market-sync cron is configured daily at 10:30 UTC (16:30 Dhaka); platform timing can vary. CRON_SECRET is server-only. A completed live run processed 50 equities. Seven consecutive unattended trading-session runs have not yet been demonstrated.

The first real price-plus-announcement ML comparison uses 2,467 official events. Two-session and forty-session research candidates are saved locally under ignored data/news-model-candidates-20261006, alongside provenance metadata. Mean balanced accuracy over three purged chronological tests is 50.5% price-only versus 49.9% news-augmented for two sessions, and 53.2% versus 54.7% for forty sessions. These are exploratory results, not calibrated probabilities or proven trading performance. Newspaper archives, macroeconomic features, corporate-action adjustment, complete historical publication/revision evidence, final holdout and live shadow testing remain pending. See docs/price-news-experiment-20261006.md. The candidate models are not exposed as production forecasts.

Supabase credential migration/revocation remains pending. The exposed legacy key must be invalidated after a scoped dependency check; no unrelated projects or global auth settings were changed. Original user documents and Git history remain preserved.

### Practice beta and readiness — 7 October 2026

`/v2/practice` supports authenticated virtual portfolios with BDT 1m initial funding, simulated buy/sell fees, holdings, P/L and receipts. Stock search, affordability hints, explicit trade review, retry verification, CSV export and mobile layouts are included. See [paper trading](docs/paper-trading.md) for simplified settlement and session limits. Credentials in invalid requests are redacted and cross-origin auth/order forms are rejected.

The private daily announcement collector records actual first-seen timestamps and distinct revisions without backdating news availability. First run captured 31 versions across 50 companies. Protected `/api/jobs/news-sync` is scheduled daily at 11:00 UTC (around 17:00 Dhaka, plan timing varies). `python -m scripts.export_prospective_news --output data/<unique-name>.jsonl` exports private point-in-time data for research. Newspaper coverage is not yet included.

Migrations 004–007 add virtual portfolios, prospective-news records, private research prediction/outcome ledgers and restricted receipt permissions. `python -m scripts.resolve_shadow_predictions` resolves eligible private outcomes using future verified trading sessions. It does not create forecasts, promote models or submit trades.

66 software tests, rollback-only PostgreSQL checks, a dedicated live QA account login/funding smoke test, and isolated browser buy/sell/isolation checks passed. This supports a supervised prototype pitch; it does not certify public production readiness. Email delivery/recovery, key revocation, durable abuse protection, sustained operation and live model validation are still required. See the [readiness assessment](docs/production-readiness-20261007.md).

### Confirmation redirect repaired — 8 October 2026

Supabase's production Site URL and allowlist now point to `/v2/practice`. Signup and resend requests specify that exact URL. Confirmation callbacks open the saved portfolio and remove tokens from the address bar; expired links have recovery guidance. Users whose old email opens localhost should sign in directly or use **Resend confirmation email** with the same address. No new account is necessary. The updated suite passes 69 Python tests and three callback tests. See [confirmation troubleshooting and verification scope](docs/auth-confirmation.md).

### Dated fundamentals and newspaper training — 8 October 2026

Both research pages now show sourced annual EPS, NAV/share, profit, reviewed ROE/debt, reporting period and P/E using the displayed closing session. Separate financial versions preserve old market rows and saved scores. Value is available for 32 stocks; Quality for two with individually reviewed reports. GP has 100% factor-input coverage. Annual statements have a disclosed 548-day eligibility limit; missing ratios stay unavailable. The protected financial collector runs weekly on Sunday around 18:00 Dhaka, with timing subject to the hosting plan.

731 Financial Express archive dates yielded 2,798 initial company/sector headline matches. Entity review against the official catalogue removed 1,207 outside-universe company stories and corrected 54 mappings. Two research candidates were trained on 1,591 reviewed newspaper headlines, 2,467 disclosures and the existing 23,961 price observations. Same-window mean balanced accuracy for price/disclosures/combined is 50.83% / 49.65% / 51.39% at two sessions and 52.99% / 54.77% / 54.32% at forty sessions. This does not establish consistent news benefit or production prediction accuracy. Full-text licensing, broader publishers, adjusted prices, holdout/calibration and prospective validation remain pending.

76 Python tests and three callback tests pass. Live price and financial refresh jobs have been verified once. Data, report PDFs and model binaries stay under ignored `data/`; public source includes only implementation and a small result summary. See [the dated source/experiment report](docs/fundamentals-and-newspaper-experiment-20261008.md).
