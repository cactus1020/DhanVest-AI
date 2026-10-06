# Price and news model experiment on 6 October 2026

## Dataset and actual scope

50 current liquid equities selected using existing coverage and session volume. 23,961 authentic source price observations from the DSE public archive. Requested five years, but actual date-matching coverage begins 6 October 2024 and ends 6 October 2026; unavailable older dates were not fabricated. Three exceptional Saturday sessions were verified and explicitly allowed. 2,467 official company-announcement events were collected. Newspaper articles, macroeconomic headlines and social rumors are not yet included.

Legacy daily_data and saved factor_scores were preserved. New price records were written to the separate market_history table. Local datasets and backups are ignored by Git/deployment.

## What the machine learning model receives

Numeric past-return, moving-average and volume features, the prior seven days of company-linked headline text through train-fold-only TF-IDF, announcement counts, and positive/negative keyword counts derived from disclosure bodies. Keyword counts are crude features, not validated financial sentiment. Headlines do not capture all financial facts contained in an announcement.

Two targets were compared: direction over two trading sessions and forty trading sessions. Forty trading sessions approximate, but do not equal, two calendar months. The prediction cutoff is 14:30 Dhaka; archive announcements with only a date are conservatively made usable the next day. Archived text may have revisions, so this is an explicitly acknowledged reconstruction rather than a proven point-in-time news archive.

Numeric transformations and text vocabulary are fitted on training rows only. Each of three expanding chronological tests purges training labels that reach into the test period. Price-only and price-plus-news use identical periods and the same classifier family. Accuracy, balanced accuracy, Brier score and majority baseline are recorded in the local JSON report.

## Results

{
  "2_trading_sessions": {
    "price_only_balanced_accuracy": 0.5046658011288564,
    "price_plus_news_balanced_accuracy": 0.49941290430372254,
    "folds": 3
  },
  "40_trading_sessions": {
    "price_only_balanced_accuracy": 0.5322144987402401,
    "price_plus_news_balanced_accuracy": 0.5474867323817968,
    "folds": 3
  }
}

Balanced accuracy equally weights the two movement classes; it is not a promise or calibrated probability. In the two-session experiment, news did not improve performance consistently. Forty-session results show a modest exploratory improvement, but do not establish a trading edge or reliably high prediction accuracy.

## Why this is not a production predictor yet

Current-universe selection creates selection/survivorship bias. Corporate-action adjustment has not been established. Publication-time/revision evidence is incomplete. Tests are exploratory folds, without a future live shadow record or an untouched final holdout. Transaction costs, confidence calibration and newspaper/news/macroeconomic coverage still need work. No forecast was published as a reliable live prediction on the basis of this experiment.

## Next model work

Obtain a permitted, historical Bangla/English news archive with original publication and revision timestamps. Link entities and sectors, cluster syndicated stories, extract financial-event facts and distinguish verified reports from unverified claims. Compare the richer model with these baselines, reserve a final test period, calibrate probabilities and run a logged live shadow phase before enabling customer-facing forecasts. A weak or non-improving model stays out of production.
