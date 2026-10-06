# DhanVest research model

Status: **unvalidated; excluded from production scores**.

The old Random Forest artifact was trained on an undated CSV using a random
train/test split. Its reported accuracy does not establish out-of-time performance.
The current bundled CSV has nine symbols and 2,160 rows but no trading dates;
training and import now reject it. Dates must not be reconstructed by row number.

The replacement evaluation uses dated, source-verified data sorted per symbol.
Features: close, volume, daily return, 5/20-session moving-average ratio and
5-session average volume. Target: positive close-price change over five sessions.
Three expanding chronological folds purge training labels that reach the test
period. Each fold reports accuracy, balanced accuracy, majority-class baseline,
dates and sample sizes. No performance figure is available until genuine dated
data is evaluated. Test fixtures are synthetic and validate code, not the model.

Limitations include limited stock coverage, corporate actions, market regimes,
survivorship bias and transaction costs. Classification accuracy is not a measure
of net investment returns. Never use the artifact as a buy/sell recommendation.

Production uses documented heuristic factors with no ML boost. Missing data is
null, factor coverage and effective weights are disclosed, and old snapshots
are labeled. Bangla explanations use fixed rules based on displayed scores by
default. An optional server-side Gemini service uses the same inputs, caches by
data/model signature and rejects obvious advice, forecasts and invented numbers.
This validation is not a guarantee of factual correctness. Failed or unavailable
AI output falls back to factor rules; the frontend discloses the method.


## Price and news research update on 6 October 2026

An actual DSE archive and official-event comparison has now been run, documented in docs/price-news-experiment-20261006.md. The experiment combines numeric price features with fold-fitted TF-IDF announcement titles and event/keyword counts. Research candidates exist for 2 and 40 trading sessions, with provenance metadata. News did not consistently improve the short horizon; longer-horizon improvement is modest. Newspaper text, macro inputs, probability calibration, adjusted-price validation and a prospective shadow record remain missing. No candidate has passed the production forecast gate.
