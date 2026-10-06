# Latest implementation update

The baseline review below describes the earlier prototype. Since that review, Supabase migration has completed, public DSE quotes/history/announcements have been connected, daily protected ingestion has completed its first successful run, and 23,961 verified historical observations for 50 companies were added separately from the preserved legacy records. Actual coverage is October 2024–October 2026, not five years. A price-plus-official-announcement ML experiment using 2,467 events has completed; research candidates for two and forty trading sessions are saved. Newspaper corpus, fundamentals, broad market features, calibrated forecasts, prospective shadow validation and shared-project key rotation remain pending. See [the detailed experiment](price-news-experiment-20261006.md).

---

# DhanVest proposition and implementation review

Review date: 6 October 2026, Asia/Dhaka. Scope: supplied pitch, proposal, assessment, Q&A, execution plan, demo HTML, repository code and read-only live database observations. This reviews alignment; it does not certify legal compliance, market statistics, model accuracy, or business traction. Original documents, imported records and Git history were preserved.

## Main conclusion

The project matches the beginning of the proposed intelligence platform: a working stock-research interface, initial database and explanation/scoring code. It is an early Solution prototype, consistent with the Session 3 assessment. It is not yet the complete Stage 1 product described in the investment proposal, and there is no evidence here of PMF or the regulated Stage 2 business. The legacy `backend/scraper.py` is a random-walk simulator that writes SQLite demo records, not an actual DSE collector. Do not treat its generated prices or fundamentals as market evidence.

The missing core is dependable data and validated intelligence, rather than a lack of additional dashboard styling.

The intended live platform remains the target. The supplied assessment describes the current stage, not a ceiling on what should be built. `/research` preserves access to existing research and `/v2` provides a separate development workspace for the live product. V2 currently connects to the existing database; market/news automation and validated forecasts are not yet connected.

## Sources inspected

- DhanVest_AI_Pitch_Deck-1.pptx: 13 slides; PDF counterpart also extracted, 13 pages. Slides 3–4 describe hybrid models, verification, back-tests and explanations; slide 10 provides the rollout; slides 11–13 cover financial targets, team and raise.
- DhanVest_AI_Series_A_Proposal-1.docx: especially sections 1, 4, 8/8A, 9 and 10.
- session3_Assesment-Report.docx: Problem, Solution and PMF criteria.
- DhanVestAI-Code-Readme.md and older DhanVestAI Code Readme.md: MVP implementation and illustrative-data disclosure.
- DhanVest_Q_A_and_Naming_ANSWERED-1.md: positioning, verification, data rights, confidence, regulation, team, funding and traction claims.
- DhanVest_Execution_Plan-1.csv: all 58 task rows and their definitions of done.
- dhanvest-mvp-1.html: hand-set STOCKS data, factors, headlines, confidence heuristic and browser Anthropic call.

The proposal -1/-2 files are byte-identical, Q&A -1/-2 are byte-identical, and demo HTML -1/-2 are byte-identical. Both copies remain intact. There is no need to treat each duplicate as a different requirement version.

## Product promise versus evidence

| Proposed capability | Current evidence | Gap to close |
|---|---|---|
| Centralized, explainable company research | Stock list, database records, stored scores, Bangla summary, chart, watchlist | Add authenticated user flows, financial reports, sources, updated quotes and company events |
| Live market intelligence | Database reachable, nine stocks and 2,160 price rows | No connected live/EOD provider; original dates were generated from undated CSV imports |
| Business-health evaluation | Stored factor scores preserved | Imported P/E, ROE and debt values are null; old quality/value scores were fixed at 50 and cannot establish health |
| Verified, probabilistic signals | Transparent factor rules and chronological model-evaluation tooling | Actual training data, calibrated probabilities, independent test periods, baseline comparison and published performance |
| Bangla/English news intelligence | Timestamp/entity/duplicate validation groundwork | Feed rights/access, article ingestion, entity matching, syndicated-story clustering, sentiment/materiality, disclosure cross-checks |
| AI explanations | Server-only optional LLM, rule-based Bangla explanation, cache code | Provider configuration and live cache schema, bilingual/batched outputs and stronger evidence validation |
| Portfolio health, IPO tracker, fund comparisons | Proposed in section 4.1 | Not implemented |
| Consumer platform adoption | Working web prototype | No demonstrated retention, willingness to pay, interviews or analytics in supplied evidence |
| Licensed funds, SIPs and MFS distribution | Stage 2 concept | No evidence of licence, signed partners, custody/accounting/onboarding or implemented investment transactions |

## Why the copied MVP looked more complete

The build guide explicitly says its market figures are realistic but illustrative, hand-set to stabilize the demonstration. The demo HTML contains ten hand-set companies, fundamentals and headline strings. These are not a connected news feed or five-year dataset. Its generated confidence meter is a heuristic, not measured prediction accuracy.

Its verification wording also goes beyond its evidence: a generic statement that every number traces to public filings is not an individual citation, publication timestamp or verification record. The new implementation must add provenance, not silently relabel that demo as live verified research.

The demo can remain a labelled presentation artifact. Do not merge its illustrative fundamentals or headlines into production market-data tables. Keep the database-derived product and a demonstration snapshot distinct.

## Restoration of existing product value

All 2,160 original price rows and nine stored factor-score rows remain in the database. Each stock has 240 imported observations. The previous verification gate hid their practical value. That regression was corrected by displaying the imported price sequence, previous-record percentage change, volume, stored composite/factor scores and saved Bangla analysis, with their provenance limitations explicit.

Example observed on the existing GP records: last stored close 313.40 BDT, previous close 323.30 BDT, change -3.06%, stored composite 81.99. These are values from the preserved dataset; they are not today's quote or a validated forecast. The chart uses import observation order when dates are unverified, rather than presenting invented dates as real trading sessions.

Verified-factor values and archived scores remain separate API fields. Restoring archived outputs does not reinstate the previous arbitrary ML boost as a production algorithm. New Bangla summaries explain the stored movement without invoking an external AI service.

## Document changes needed before investor use

1. **Make one consistent product promise.** The guide says the AI explains the present; the proposal permits probabilistic, back-tested decision support. These fit together if the UI separates observed movement, factor assessment and a future model's probability/horizon/back-test evidence. A saved score is not the probability that a stock will rise.
2. **Correct verified/live claims.** The demo is illustrative, the current database is historical and the active feed is absent. Statements such as cross-verifying every claim, nightly scoring and a proprietary cleaned corpus should be roadmap claims until implemented and measured.
3. **Correct the investor return calculation.** Section 9 compares enterprise value of US$18–22m with the US$3m raise to claim 5–7x investor return. With 20–25% ownership, assuming enterprise value equals equity value, zero dilution and no other distributions, the stake is US$3.6–5.5m, or about 1.2–1.83x on US$3m. Debt, cash, dilution and preferred terms must be included before an actual return model is stated.
4. **Reconcile fund/advisory revenue.** At year-end AUM Tk400 crore and 120 BDT/USD, AUM is about US$33.33m. A 1.25% annual fee implies about US$0.417m before expenses, versus US$1.18m fund/advisory revenue in FY5. An explicit bridge for average AUM, advisory fees, fee rates and additional revenue is needed. Year-end AUM should not automatically be charged for the full year.
5. **Separate target metrics from observed traction.** CAC, conversion, LTV, retained users, willingness to pay and institutional demand are assumptions here. The Q&A calls the financial model market-validated, but the assessment says demand validation is not established. Use assumption-based projections until cohort evidence exists.
6. **Resolve team/institution wording.** Pitch slide 12 identifies BRAC University education, while Q&A and website use an ICE University of Dhaka venture framing. These can coexist only with an accurate explanation of founder/team affiliations and permission to imply institutional backing.
7. **Get the regulatory statements checked.** The proposal asserts that Stage 1 needs no licence and cites an alternative-investment fund-manager capital benchmark for an AMC roadmap. This review has not verified those legal claims, applicable rules or liability assertions. Keep them as items for a written, jurisdiction-specific legal opinion rather than claiming regulator-proof status.
8. **Date and source market statistics.** No fresh verification of BO accounts, market capitalization, AUM, comparable funding or grant availability was performed in this alignment review. Avoid treating supplied dated figures as current facts.
9. **Match fundraising to evidenced stage.** The proposal presents a US$3m Series A, while the execution plan's later task is a seed raise on metrics. Resolve this sequencing and demonstrate paid retention/B2B demand before presenting the model as a proven commercial business.

## Recommended build sequence for V2

### Gate 1: usable research with preserved data

Keep the current stock details, archived analysis and charts working. Add schema support without deleting imported history. Rotate the previously exposed key. Add source/date/model labels and a visible system status. Gate: users can inspect all existing records and every view distinguishes stored observations, verified snapshots and future predictions.

### Gate 2: real market and fundamentals

Select an allowed DSE feed and archive; validate coverage, actual trading dates, OHLCV, corporate actions and price adjustments. Preserve unadjusted/adjusted values separately. Add real company sectors and financial reporting/availability dates. Ingest idempotently, record job runs and failures, schedule EOD updates and display as-of/freshness. Gate: authentic recent data arrives automatically for seven trading sessions with documented failures and no fabricated dates.

### Gate 3: source-linked news and disclosures

Connect official company disclosures first, then permitted Bangla/English publisher feeds. Store publication, first-observed and availability times, source, entity mapping and verification state. Separate unverified claims from confirmed disclosures. Gate: users can open the exact source for each company event; summaries distinguish evidence from unverified claims and syndicated articles are clustered.

### Gate 4: validated prediction module

Use the same time periods to compare price-only, fundamentals/market-context and news-augmented models. Keep a locked final test period, purge overlapping future labels, use point-in-time corporate membership/fundamentals/news and compare a majority/no-change baseline. Assess calibration, coverage and costs; record model/data versions. Show forecast horizon, probability and historical test evidence only when earned. Gate: reproducible real-data results and a shadow-run record, not synthetic test success.

### Gate 5: prove customer value

Authentication and synchronized watchlists, Bangla localization, privacy-conscious product analytics, investor interviews and design partners. Portfolio and alerts should follow actual research workflows. PWA before native apps is the execution plan's lower-cost sequence. Gate: observed returning users, explanation usage, paid willingness/retention or a concrete B2B pilot. Growth/paid features follow evidence rather than presentation targets.

### Stage 2 gate

Treat asset management, execution, client money, SIP/MFS and fund operations as a separate regulated product workstream with the needed partners, personnel and legal decisions. This audit did not implement those operations or change any account permissions.

## Execution-plan review of all 58 tasks

“Not evidenced” means no supporting material was found in this package; it does not prove the team has never done the work. “Implemented” refers to the specific scope stated, not the entire live-product roadmap. Existing task Status cells were not changed.

| # | Task | Review status | Evidence or next condition |
|---|---|---|---|
| 1 | Wire the waitlist form to a real database | Partial | Server form exists; live waitlist table is still missing. |
| 2 | Audit repo for exposed secrets | Partial | Browser secrets removed; previously exposed key still needs rotation. |
| 3 | Remove dhanvest.db from git history | Preserved intentionally | Database is ignored for new files; existing file/history has not been purged because preservation was requested. |
| 4 | Fix the prediction language on the live site | Implemented | Public research copy separates past movement, saved scores and future prediction. |
| 5 | Add a persistent risk disclaimer to every page | Implemented | Risk footer exists on public marketing/research/dashboard/V2 views. |
| 6 | Change the currency glyph from Rs to Taka | Implemented in deployed UI | Taka used on deployed pages; original supplied demo artifacts are unchanged. |
| 7 | Run honest out-of-sample validation on the existing model | Partial | Purged chronological evaluator exists; authentic dated dataset and real performance report are missing. |
| 8 | Write the model card documenting the model honestly | Implemented with limitations | MODEL_CARD.md states unvalidated status; no proven out-of-sample result. |
| 9 | Expand price history to 5+ years | Missing | Existing 2,160 records have no independently verified trading-date provenance; no five-year archive. |
| 10 | Expand coverage from 10 to all listed companies | Missing | Nine stocks, sector General in existing database. |
| 11 | Build the automated daily data ingestion job | Missing | No active daily price provider or scheduler. |
| 12 | Add data quality checks to the pipeline | Partial | CSV dates, duplicates, finite prices/volume and source checks implemented; jump/corporate-action monitoring not complete. |
| 13 | Verify and correct every statistic in the pitch materials | Needs verification | Pitch statistics remain unverified; internal arithmetic issues documented below. |
| 14 | Collect quarterly fundamentals for the full universe | Missing | Stored sample has null P/E, ROE and debt-to-equity. |
| 15 | Write the 12-question user survey | Not evidenced | Requires founder/team evidence or work outside the current code and supplied package. |
| 16 | Get 300 survey responses | Not evidenced | Requires founder/team evidence or work outside the current code and supplied package. |
| 17 | Conduct 50 one-to-one user interviews | Not evidenced | Requires founder/team evidence or work outside the current code and supplied package. |
| 18 | Write the user research synthesis document | Not evidenced | Requires founder/team evidence or work outside the current code and supplied package. |
| 19 | Recruit 20 design partners from the interviews | Not evidenced | Requires founder/team evidence or work outside the current code and supplied package. |
| 20 | Rebuild the factor engine on the full universe | Partial | Shared four-factor implementation exists; full universe, fundamentals and nightly scoring missing. |
| 21 | Run a rigorous back-test of the factor scores | Missing | No real-data factor performance study, cost/survivorship treatment or published whitepaper. |
| 22 | Move all AI generation server-side and cache it | Partial | AI server route, validation and cache code exist; live cache schema and nightly bilingual batch missing. |
| 23 | Add a prompt-output validation layer | Implemented with limits | Advice/markup/invented-numeric checks tested; this is not comprehensive factual verification. |
| 24 | Build user accounts and authentication | Missing | No deployed user account/authentication flow. |
| 25 | Build the watchlist feature | Partial | Watchlist persists in browser; accounts and cross-device synchronization missing. |
| 26 | Add analytics instrumentation | Missing | No verified analytics implementation or measured DAU/WAU. |
| 27 | Define and start tracking your one core metric | Not evidenced | Core metric and weekly review records not found. |
| 28 | Make the site fully mobile-responsive | Partial | 390px browser layout checked; low-end Android/4G field testing not performed. |
| 29 | Optimise for slow connections | Not measured | No 3G load-time benchmark or cache-performance evidence. |
| 30 | Add full Bangla UI localisation | Partial | Bangla explanations and some labels; full language toggle/localization missing. |
| 31 | Launch the education hub | Not evidenced | Requires founder/team evidence or work outside the current code and supplied package. |
| 32 | Publish the weekly market wrap | Not evidenced | Requires founder/team evidence or work outside the current code and supplied package. |
| 33 | Start the YouTube channel | Not evidenced | Requires founder/team evidence or work outside the current code and supplied package. |
| 34 | Build the Facebook content calendar | Not evidenced | Requires founder/team evidence or work outside the current code and supplied package. |
| 35 | Join and contribute to DSE investor communities | Not evidenced | Requires founder/team evidence or work outside the current code and supplied package. |
| 36 | Run the campus ambassador program | Not evidenced | Requires founder/team evidence or work outside the current code and supplied package. |
| 37 | Reach 500 registered users | Not evidenced | Requires founder/team evidence or work outside the current code and supplied package. |
| 38 | Measure and publish your retention curve | Not evidenced | Requires founder/team evidence or work outside the current code and supplied package. |
| 39 | Interview 20 users who churned | Not evidenced | Requires founder/team evidence or work outside the current code and supplied package. |
| 40 | Apply to Accelerating Bangladesh | Not evidenced | Requires founder/team evidence or work outside the current code and supplied package. |
| 41 | Apply to the Bangabandhu Innovation Grant | Not evidenced | Requires founder/team evidence or work outside the current code and supplied package. |
| 42 | Apply to Accelerate Bangladesh investment readiness | Not evidenced | Requires founder/team evidence or work outside the current code and supplied package. |
| 43 | Build the investor data room | Not evidenced | Requires founder/team evidence or work outside the current code and supplied package. |
| 44 | Register the company legally | Not evidenced | Requires founder/team evidence or work outside the current code and supplied package. |
| 45 | Agree and document the founder equity split | Not evidenced | Requires founder/team evidence or work outside the current code and supplied package. |
| 46 | Get a written legal opinion on Stage 1 | Not evidenced | Requires founder/team evidence or work outside the current code and supplied package. |
| 47 | Draft terms of service and privacy policy | Not found | No complete published terms/privacy policy identified. |
| 48 | Write the DhanVest vision document | Not evidenced | Requires founder/team evidence or work outside the current code and supplied package. |
| 49 | Set up weekly team metrics review | Not evidenced | Requires founder/team evidence or work outside the current code and supplied package. |
| 50 | Launch on Product Hunt and local tech media | Not evidenced | Requires founder/team evidence or work outside the current code and supplied package. |
| 51 | Ship the mobile app as a PWA first | Missing | No installable PWA, offline cache or push implementation. |
| 52 | Add push notifications for watchlist alerts | Missing | No scheduled watchlist push alerts. |
| 53 | Launch the paid tier | Not implemented in app | No billing flow or evidence of paid retention. |
| 54 | Sign the first B2B pilot | Not evidenced | No signed pilot agreement found in supplied package. |
| 55 | Publish the back-test whitepaper publicly | Missing | No back-test whitepaper on authentic data. |
| 56 | Build native mobile apps | Missing | No native Android/iOS application code found. |
| 57 | Begin BSEC licence groundwork | Not evidenced | Requires founder/team evidence or work outside the current code and supplied package. |
| 58 | Raise a seed round on proven metrics | Not evidenced | Requires founder/team evidence or work outside the current code and supplied package. |

## Current limits and evidence

The restored /research and /v2 use the existing Supabase connection and server-held credentials. Live database reads confirmed nine stocks, 2,160 original observations and nine saved scores. No database mutation, history rewrite, company deletion, paid feed subscription or news/model-training run was performed during this review. Unit tests use synthetic/mock fixtures; they establish software behavior, not financial model performance. Supabase waitlist and cache/verification schema migrations remain pending.
