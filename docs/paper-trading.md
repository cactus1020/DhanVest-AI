# Virtual DSE practice portfolios

Route: `/v2/practice`. Supabase email/password authentication verifies each request on the server. No project-wide authentication settings are modified. Existing email confirmation requirements remain in force. Sessions stay in browser sessionStorage; refresh tokens and service credentials are not exposed. Sign-out clears the local session; account recovery and server-wide session revocation are future work.

Each authenticated user receives one persistent account with BDT 1,000,000 virtual starting cash. Creating/opening the portfolio again never resets or tops up the balance. All funds are virtual. Trading cannot reach a broker or the actual exchange.

Server-side quotes come from the DSE public equity feed. Whole-share market orders are allowed only when the source says today's session is open and the fetched snapshot is at most 120 seconds old. Upstream quote latency cannot be inferred from fetch time; public quotes may lag. Fills use last-traded price rather than bid/ask depth. A clearly disclosed simulated fee of 0.25% applies to each side. Settlement is instant; no margin, short selling, order-book/slippage, corporate-action accounting or real exchange settlement is implemented yet.

The SQL transaction locks the account before checking cash and holdings, updates cash and average-cost holdings together, and records immutable trade receipts. Idempotency keys prevent retries from creating a second fill. All tables and the order RPC are private to the server role. User IDs, prices and fee values are never accepted as order inputs. Accounts/trades persist across sign-out and deployment. An unavailable valuation remains null rather than reporting fabricated profit.

Migration: `migrations/004_paper_trading.sql`. Only three DhanVest-prefixed tables and one DhanVest function are added. Other applications, tables, auth settings and keys remain unchanged.

Portfolio P/L measures trading decisions, not standalone prediction accuracy. The price/news candidates are still experimental. A future prediction ledger must persist prediction version, timestamp, horizon, baseline and subsequent outcome before publishing model hit rates. Paper performance is not evidence of equivalent real-money performance.
