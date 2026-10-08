# Dated financial facts and newspaper experiment — 8 October 2026

## Implemented financial research

The existing 50 companies were checked against DSE company profiles. There are 377 annual observations for 49 companies; one company has no usable annual series. Two additional reviewed versions add issuer-reported ROE and debt/equity, and one supplemental Telecom peer adds a sector benchmark. The separate private `dhanvest_fundamentals` table contains 380 versions. Legacy daily data, archived scores and original stock records are preserved.

Both `/research` and `/v2` now show EPS, NAV/share, annual net profit, ROE, debt/equity, price-based P/E, reporting period and source definitions. The exchange's current name/sector is applied only to the research response. Financial facts are not backfilled into old market prices or historical model features.

GP's 2025 annual report, PDF page 100 / printed page 98, Table 1, reports ROE 49% and debt/equity 1.21 times. BAT Bangladesh's 2025 report, PDF page 65 / printed page 63, reports ROE 10.55% and debt/equity **17.62%**, converted to **0.1762 times**. These pages were extracted and visually reviewed. Issuer definitions may differ; the quality score remains a heuristic, not an audited rating.

Annual statements remain scoring-eligible for 548 days (approximately 18 months) from their period end, to accommodate annual reporting cycles; quarterly/legacy inputs retain the 180-day limit. Fetching a document never resets its reporting date. P/E uses the same closing price shown by the research API divided by reported annual EPS. It is unavailable for zero/negative earnings or too few eligible sector peers. The supplemental BSCPLC observation is used for the Telecom median; no additional stock or market rows were inserted for it.

Verified live result before the scheduled refresh: **32 Value scores, 2 Quality scores**. GP has 100% factor input coverage; SQURPHARMA 68%; BATBC 72%. Coverage is availability of factor weights, not forecast accuracy. Other companies' ROE/debt remain unavailable until individually sourced/validated reports are added.

Protected `/api/jobs/fundamentals-sync` is configured weekly on Sunday, around 18:00 Dhaka. Refresh adds immutable versions and ignores duplicates; it does not overwrite reviewed ratios or old prices. Pending/failed source symbols are prioritized next run. New annual periods require new ratio verification, so a future report may temporarily reduce coverage.

Sources: [DSE GP company profile](https://www.dse.com.bd/company/GP), [GP annual report](https://cdn01da.grameenphone.com/sites/default/files/2026-03/Annual%20Report%202025%20of%20GP.pdf#page=100), [BAT Bangladesh annual report](https://www.batbangladesh.com/content/dam/endmarkets/bd/en/download/investors-and-reporting/financial-statements/2026/Annual_Report_2025.pdf#page=65).

## Historical newspaper + price training completed

The Financial Express stock/corporate daily archive was checked for all **731 dates from 6 October 2024 through 6 October 2026**, with zero collection failures. There were **2,798 initial matching headlines**, with publisher URL, publication day, actual first-seen timestamp and mapping reasons. Entity review against the official 633-instrument catalogue excluded **1,207 company-specific stories outside the covered universe** and corrected **54 mappings**, leaving **1,591 reviewed headlines** for final training. Known two-letter tickers and spaced bank abbreviations are now matched. Full articles are not stored or republished. Exact company matches stay company-specific; only remaining broad sector headlines map to the sector's covered companies. The catalogue is saved privately and reproduces the training dataset exactly. Rule-based matching still needs richer entity/sector review and does not prove exhaustive news coverage.

They were combined with **2,467 DSE announcement events** and **23,961 verified price observations for 50 stocks**. Features include price returns, moving-average trend, volume, headline TF-IDF and keyword/event counts. Counts are not validated sentiment or causal attribution. TF-IDF and numeric transformations are fit only on each training window.

Historical date-only availability is conservatively reconstructed to the following day; first-seen dates remain the actual retrieval time. The decision cutoff is 16:30 Dhaka, after close. All events in this experiment are eligible from midnight on the reconstructed day, so moving the initial implementation's 14:30 cutoff to 16:30 does not change this dataset's features or metrics. Archive revisions and the original time of observation cannot be proven. Research explicitly acknowledges this limitation. Today's fundamentals are excluded from historical training because their original availability is not established.

Identical three chronological test windows, with labels crossing into a test window purged:

| Future trading sessions | Price only | Price + DSE disclosures | Price + disclosures + newspaper headlines |
|---|---:|---:|---:|
| 2 | 50.83% | 49.65% | 51.39% |
| 40 | 52.99% | 54.77% | 54.32% |

These are **mean balanced accuracies**, not calibrated confidence. The binary target is **up vs not-up**, with down and flat together. Newspaper headlines improve the two-session mean but worsen the forty-session result relative to disclosures alone. No 80–90% accuracy or consistent news benefit has been demonstrated.

Two full-data research candidates are saved privately: 22,911 training rows for the two-session candidate and 21,011 for the forty-session candidate. Model files, headline datasets, PDFs and raw financial exports stay under ignored `data/`; public GitHub contains code and the small result summary only. No public prediction endpoint or automatic model promotion is enabled.

Reproduce using `python -m scripts.collect_fundamentals`, `python -m scripts.collect_newspaper_archive --profiles data/fundamentals-20261008/profiles.json`, `python -m scripts.review_newspaper_mapping --catalogue data/newspaper-archive-reviewed-20261008-audit/catalogue.json --folder data/<new-reviewed-folder>` and `python -m scripts.train_newspaper_candidates --newspaper-news data/<new-reviewed-folder>/events.jsonl --folder data/<new-run-folder>`. Existing output files are preserved. Current models still require corporate-action adjustments, broader publishers/licensed full text, an untouched holdout, calibration, cost/portfolio evaluation and prospective shadow testing. This is a completed headline-based research pipeline, not a complete licensed newspaper service or production forecasting system.

Verification: 76 Python tests and three browser-callback tests passed; live financial scoring was checked. Protected production price refresh completed for 50 stocks for 8 October 2026, and financial refresh completed for 50 stocks plus the supplemental peer with 378 exchange observations. These runs preserve the two reviewed ratio versions and existing records. Sustained unattended weekly operation is not yet proven.

Publisher archive example: [Financial Express stock/corporate archive](https://today.thefinancialexpress.com.bd/stock-corporate?date=18-07-2025). Commercial reuse/redistribution rights remain under validation.
