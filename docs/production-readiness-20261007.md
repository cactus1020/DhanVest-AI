# DhanVest readiness assessment — 7 October 2026

**Decision: suitable for a supervised research/learning-beta demonstration and an honest prototype pitch. Not approved for an unrestricted production launch, real-money trading, or accuracy/profit claims.**

## What can be demonstrated

- DSE public equity snapshots, historical closing charts, saved research and source dates.
- A persistent virtual portfolio starting at BDT 1,000,000 with market-price simulation, whole-share buy/sell, disclosed 0.25% simulated fees, holdings, cash and trade receipts.
- Stock search, buy/sell affordability hints, explicit confirmation, CSV export, automatic refresh and mobile layouts.
- Actual price-only versus price-plus-announcement research comparisons. The models remain experimental; displayed validation scores are not a live signal's confidence.
- Daily price ingestion and a new protected daily announcement collector recording actual first-seen times and distinct content versions. First announcement run: 50 companies, 31 observed versions, no failed companies. This is DSE disclosure ingestion, not newspaper/social-rumor ingestion.

## Checks completed

- 66 software tests passed. Tests cover anonymous/cross-origin rejection, authenticated owner selection, server-controlled prices, stale/closed/invalid-timestamp quotes, idempotent retry and unavailable valuations. Credential validation errors no longer echo submitted passwords.
- Disposable PostgreSQL integration assertions passed: starting balance, buy/sell fees, average-cost holdings, duplicate request replay, overspend/oversell rejection and private-table permissions. Test rows were rolled back.
- Live Supabase authentication and production portfolio endpoints were tested with one dedicated synthetic QA user. Initial balance was BDT 1m; repeated portfolio reads preserved it; anonymous access returned 401. No existing users/settings were changed, and no live trades were submitted.
- Browser flow with isolated synthetic fixtures: sign-in, initial funding, stock search, buy 10 shares, sell 4 shares, cash/fees/P&L, six remaining shares, oversell disabled, sign-out and second-user isolation. The browser trading fixture does not establish live exchange execution or production order throughput.
- Mobile layout inspected at 390×844; desktop layout also inspected. Tables scroll inside their sections; controls and metrics fit the mobile layout.

## Release blockers and limits

| Priority | Issue | Required evidence or work |
|---|---|---|
| Critical | Public Git history contains the privileged legacy Supabase service-role key currently used by the backend | Migrate safely to a new server secret and disable the exposed legacy access path after checking dependencies. A history cleanup alone does not invalidate a leaked key. No project-wide keys/settings were changed in this work. |
| High | Public signup/email delivery and recovery have not passed an end-to-end owned-mailbox test | Verify email confirmation destinations, deliverability, password recovery and production SMTP limits. The QA user was individually preconfirmed; global email confirmation was not disabled. |
| High | Signup/auth abuse controls and session lifecycle need a production design | Add durable rate/bot controls, account recovery and audited session handling. Current token is stored in sessionStorage and local sign-out clears it; full session revocation/renewal is not implemented. CSP and sanitized errors reduce exposure but do not make sessionStorage risk-free. |
| High | DSE public website feed has no measured latency/SLA or licensed exchange-grade availability | Validate data-use terms and provider agreements; monitor stale data, source outages and corporate-action adjustments. Snapshot fetch time is not proof of exchange quote freshness. |
| High | News-informed production predictions remain disabled | Acquire usable historical newspaper corpus and five-year verified prices, use chronological holdouts and calibration, then collect prospective shadow predictions/outcomes before a controlled release. |
| Medium | Trading is a simplified practice simulator | Implement actual settlement timing, corporate actions/dividends, depth/slippage and order rules before claiming equivalence with real DSE execution. |
| Medium | Sustained operation, concurrency and recovery not yet proven | Run controlled load/concurrent-order tests, backup/restore drills, multiple unattended ingestion days and alerting. Current passing tests and one successful job are not uptime or scaling proof. |

The private research prediction/outcome ledger has been added and a resolver calculates outcomes using verified future trading sessions. No public predictions have been enabled; the ledger alone is not an accuracy record. Newspaper ingestion and automated retraining are still pending.

## Suggested pitch wording

“DhanVest is a Bangladesh stock-research and investing-learning beta. Users can explore dated DSE market data and practice with a BDT 1m virtual portfolio. We are evaluating models that combine historical prices with company announcements and are building a point-in-time news dataset. Prediction accuracy, production robustness and real-market execution remain under validation.”

Avoid “80–90% accurate,” “guaranteed profit,” “licensed broker,” “real-time exchange-grade,” “news predicts causes,” or “production-ready” claims without corresponding evidence. Current public data covers roughly two years, not five; announcements are not the full newspaper corpus the product ultimately needs.

References: [Supabase API-key privileges and compromised keys](https://supabase.com/docs/guides/getting-started/api-keys), [Supabase password/email confirmation](https://supabase.com/docs/guides/auth/passwords), [Vercel daily cron timing limits](https://vercel.com/docs/cron-jobs/usage-and-pricing). The daily collector is configured around 17:00 Dhaka; scheduling precision is plan-dependent and this is not continuous real-time news monitoring.
