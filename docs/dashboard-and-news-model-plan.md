# Dashboard and news-aware model: proposed next steps

Status: proposal for discussion, not an approved feature rollout. Existing data,
pages and deployment history must be preserved. News ingestion, five-year model
training and continuous prediction have not been implemented.

## Current foundation

- Supabase has nine stocks, 2,160 daily records and nine legacy score records.
- The legacy CSV has no real trading dates, and its importer invented dates.
  Restoring the database does not make these historical timestamps trustworthy.
- The API now loads stock metadata without trusting those legacy scores.
- Missing fundamentals remain null. Coverage is available factor weight, not
  predictive confidence. The old ML score boost is excluded.
- Server-only credentials are configured in Vercel Preview and Production.
- Verified-data metadata, the waitlist and AI cache still need the SQL migration.
- The classifier is research-only; there is no validated production forecast.

## Dashboard priorities

Keep the existing design language and original dashboard. Reduce the large hero
area inside the research product, retaining it on the marketing page.

First release:

1. Stock/company search, sector filtering and an explicit sort control.
2. Watchlist, initially device-local with that limitation disclosed; authenticated
   cross-device sync later.
3. Price and percentage-change overview, trading status, last update, data source
   and clear end-of-day/delayed/live labels.
4. Accessible price/volume chart with 1M, 6M, 1Y and 5Y ranges only when that
   coverage exists. News-event markers open the article source and timestamp.
5. News/disclosure cards with separate official disclosure, publisher report and
   unverified-claim labels. Do not certify a claim merely because it is popular.
6. Bangla/English labels, explanations of factors, usable loading/error/empty
   states and accessible keyboard/focus/touch interactions.

Desktop: searchable stock list next to a chart/details panel. Mobile: separate
list and stock-detail views, visible back navigation and large touch targets.
Do not force users through a long nested scrolling list and detail card.

Acceptance checks: 360px layout without horizontal overflow; keyboard usability;
clear timestamps and unavailable inputs; realistic loading tests on slower
connections. Preserve the existing original dashboard route.

Later: two-stock comparison, saved filters, announcement/volume alerts and a
performance page. Automated trading and personalized buy/sell instructions are
outside this proposal.

## Historical dataset

Start with 50–100 suitably liquid DSE companies and five years of authentic,
dated OHLCV. Expand only after quality checks. For example, 100 companies × five
years × approximately 240 sessions would be about 120,000 price rows; this is
an illustrative estimate, not a verified session count or acquired dataset.

Store exchange-specific prices, trading calendars, corporate actions, index and
sector context, and fundamentals with their publication/availability timestamps.
Do not pool CSE execution prices into a DSE price series. Include suspensions,
new listings and delisted companies when available to reduce selection bias.
Preserve raw sourced records and produce versioned cleaned datasets rather than
overwriting history. Investigate floor-price/circuit-limit regimes and adjustments
for dividends, splits and rights issues before labeling returns.

Data-provider historical coverage, licensing, permitted storage, price adjustment
method and intraday entitlements remain to be confirmed. Five years of authentic
prices have not yet been acquired.

## News and rumors

Sources to evaluate: official exchange/company disclosures first; publisher
financial reporting next; GDELT as a supplementary discovery/metadata source.
GDELT is not a comprehensive archive of every Bangladesh financial article or
every rumor. Publisher/API access and historical snapshots must be checked.

Each item should preserve publication time, first-seen time, capture time,
version/hash, source URL, company/sector mapping, event type, language, and
verification status as it was known at the decision time. Keep later corrections
as later versions rather than silently rewriting what the model knew earlier.

Extract events such as earnings surprises, dividends, factory interruptions,
export incentives, input costs, financing and regulatory announcements. Test
features for tone, relevance, novelty and source diversity. Deduplicate syndicated
copies of the same story before using article volume as an attention signal.

Unverified claims should be a separate experimental feature set. Later
confirmation must not be inserted into earlier features. An article describing a
price move after it happened is not evidence that the article predicted it.

Association is not causation: an event and a price increase occurring together
does not prove the event caused the move. Broader market moves, liquidity and
other contemporaneous events need consideration.

## Model experiments

Compare identical out-of-time evaluation windows for:

- A simple majority/direction baseline.
- Price/volume features only.
- Price/volume plus fundamentals and market/sector context.
- Those inputs plus news features.
- A separate experiment adding unverified public claims.

Start with relatively simple tabular classifiers. Use a language model to extract
structured information from the provided article, not to invent a future price.
Bangla financial entity/event extraction needs its own labeled evaluation sample.

Define the prediction horizon and target before training. A first experiment can
use five trading sessions, with up/down/small-change classes and thresholds
reflecting realistic costs. Use chronological, purged walk-forward folds, an
untouched final test period and probability calibration on separate validation
data. Do not randomly shuffle time series or tune on the final holdout.

Report baseline comparison, balanced accuracy, probability calibration, sample
sizes, sector/date coverage and cost-aware return evaluation. No larger dataset
or news source guarantees improvement. Evaluate in paper/shadow mode before
publishing any experimental directional forecast.

Future dashboard probability cards must disclose horizon, model version,
evaluation period and limitations. An abstention/insufficient-evidence state is
required. Data coverage, source verification and probability are different things.

## Automated operation

Begin with daily end-of-day updates. Real-time prices require an actual intraday
feed; refreshing the page does not turn end-of-day data into live quotes.

Proposed background pipeline:

Sources → collection → raw storage → validation/deduplication → company/event
mapping → as-of feature snapshots → scoring/inference → stored latest results
→ API → dashboard.

News collection every 15–30 minutes is a proposed cadence subject to source
limits. Recompute affected stock snapshots after new eligible data. Run historical
imports and model training in background workers, not dashboard HTTP requests.
Precompute results so the API does not download five years of history on each
page view. Preserve model versions, retries, run logs, watermarks and stale-data
warnings. An incomplete job must not publish a partial snapshot as current.

Retraining should be periodic and controlled by minimum data and evaluation
criteria. A newly trained model must beat the appropriate baseline and pass
checks before replacing the deployed model. Keep the old model for rollback.

## Recommended sequence

1. Complete the non-destructive SQL migration and verify secure connectivity.
2. Improve search/navigation/watchlist and transparent empty/data states.
3. Audit and acquire historical DSE coverage; build repeatable daily ingestion.
4. Build a sourced news timeline and historical event corpus.
5. Compare news-aware experiments with the price-only baseline.
6. Run shadow evaluation; only then consider experimental prediction cards and
   source-specific alerts.

## Primary sources consulted

- GDELT datasets and archive access: https://gdeltproject.org/data.html
- GDELT DOC API: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
- scikit-learn chronological splits and gaps:
  https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html
- CSE official company announcements: https://www.cse.com.bd/index.php?mCode=002
- The Financial Express stock reporting:
  https://thefinancialexpress.com.bd/category/stock
- The Business Standard stock reporting:
  https://www.tbsnews.net/economy/stocks?page=1

The official DSE archive page could not be accessed during this research; its
current downloadable coverage and acquisition route have not been verified.
