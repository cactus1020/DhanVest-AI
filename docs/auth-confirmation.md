# Confirmation emails open the production site

The reported failure was caused by the linked Supabase project's Site URL being `http://localhost:3000`, with no production redirect allowed. Its Site URL and redirect allowlist now point to `https://dhanvest.covers.bd/v2/practice`.

Signup and resend requests also supply this exact production URL. Browser callback code consumes the returned access token, clears authentication parameters from the address bar, discards stale trade-retry state and opens the user's saved portfolio. An expired or already-used link shows recovery guidance rather than an empty page. A rejected session does not display confirmation success.

Users with an old email should try signing in on the live practice page first: verification may already have succeeded before the old link redirected them to localhost. If still unconfirmed, enter the same email and select **Resend confirmation email**, wait at least one minute between requests, then use the newest email. Creating another account is unnecessary. Old emails retain their original redirect URL.

Verification on 8 October 2026:

- 69 Python tests and three JavaScript callback tests passed.
- Live page, callback asset and `/api/account/resend` route were confirmed deployed.
- Supabase configuration comparison reports no remaining differences from the repaired redirect configuration.
- A link generated for the existing dedicated QA account, without sending email, redirected to the production practice route. The returned verified session opened that QA user's existing portfolio.

The QA check uses a generated magic-link session. Actual signup email delivery and clicking a confirmation email inside a real inbox still require an owned-mailbox check; no message was sent by these verification scripts. Supabase's existing email-confirmation requirement remains enabled.
