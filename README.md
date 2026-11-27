# Financial Tracker

Flask and SQLite personal finance API with username accounts, revocable cookie sessions, CSRF protection, and SQLite-backed login limits.

## Setup

Use Python 3.14 and install dependencies with `pip install -r requirements.txt`. Set `FINANCIAL_DATABASE` to an absolute database path (default: `financial.db` next to `database.py`) and `FINANCIAL_SECRET_KEY` to a persistent, unpredictable random secret of at least 32 characters. Keep the secret outside Git; changing it invalidates sessions. For example, generate one privately with `python -c "import secrets; print(secrets.token_urlsafe(48))"` and store it in a secure environment variable. Never use the example test secret in production.

The app checks the schema read-only at startup and refuses an unmigrated database. It does not create or migrate a database on WSGI import or on requests. For a **new, explicitly selected** database, run `python migrate.py --database PATH`, then `python migrate_v2.py --database PATH`, then `python migrate_v3.py --database PATH`, and finally `python migrate_v4.py --database PATH`. For an existing database, follow the migration procedure below first. Then `python app.py` runs with debug disabled; WSGI entry point is `app:app`.

Session cookies default to `Secure`, `HttpOnly`, and `SameSite=Lax`, with a 12-hour lifetime. Use HTTPS in production. For a local HTTP-only development environment, use a local app factory configuration with `SESSION_COOKIE_SECURE=False`; never use that override in production. Flask's signed cookie is not encrypted; it contains a random session identifier and CSRF token, not financial data or passwords. Only a hash of the identifier is stored server-side. Logout deletes that server-side session, so a copied cookie can no longer authenticate. Sessions created before schema v2 must log in again. The server enforces the same 12-hour absolute expiry. There is currently no password-change or reset endpoint; future implementations must revoke all user sessions atomically with the password change. `revoke_user_sessions` is a building block, not a substitute for that atomic workflow.

## API and frontend integration

All API responses are JSON except successful DELETE (`204`, empty body). The root `GET /` remains public. The transaction and balance routes require a session; an unauthenticated request returns `401 {"error":"Authentication required"}`. Financial data is always scoped to the authenticated user. A `user_id` field in transaction JSON is rejected.

Cookie and CSRF flow for Medet's frontend:

1. Send `GET /api/auth/csrf` with cookies; retain the returned `csrf_token` in memory.
2. Send `X-CSRF-Token: <token>` and the session cookie on every POST, PUT, PATCH, or DELETE, including registration, login, and logout. A missing, wrong, or stale token returns `403`.
3. Login and logout clear the old session. Fetch a fresh token after each before the next changing request. Never place tokens in URLs.
4. For a separate frontend origin, configure exact allowed origins and credentialed CORS only after choosing deployment origins; this project does not currently enable CORS. Cookie `SameSite` and HTTPS settings must be reviewed for that topology. Frontend should use `credentials: 'include'` when appropriate.

Authentication endpoints:

- `POST /api/auth/register`: JSON `{"username":"alice","password":"..."}`; `201 {"message":"User registered"}`. Usernames normalize to lowercase, must contain 3–32 ASCII letters, digits, or underscores. Passwords must contain 12–256 characters. Duplicate username returns `409`; invalid input returns `400`. Registration does not log the user in.
- `POST /api/auth/login`: same fields; `200 {"message":"Logged in"}`; incorrect credentials return `401`. Malformed input returns `400`. Excess attempts return `429` with `Retry-After` seconds; unavailable security storage returns `503`.
- `POST /api/auth/logout`: `200 {"message":"Logged out"}` and clears the session.
- `GET /api/auth/me`: `200` with `id` and `username`, or `401`.
- `GET /api/auth/csrf`: `200 {"csrf_token":"..."}` and sets or uses the session cookie.

Transaction endpoints:

- `GET /api/transactions`: `200`, array of `id`, `type`, `amount`, `category`, `description`, `date`. Order is unspecified.
- `POST /api/transactions`: JSON object with `type` (`income` or `expense`), `amount` (positive integer up to 9223372036854775807), and valid `date` (`YYYY-MM-DD`). Optional `category` and `description` are null or strings of at most 100 and 1000 characters. Success: `201 {"message":"Transaction created"}`.
- `PUT /api/transactions/<id>`: same validation as POST, replaces all fields; omitted optional fields become null. Success: `200 {"message":"Transaction updated"}`.
- `DELETE /api/transactions/<id>`: success `204` with no body.
- `GET /api/balance`: `200`, for example `{"income":120,"expense":20,"balance":100}`.

PUT and DELETE return `404 {"error":"Transaction not found"}` for both missing and other users' IDs. PUT validates input before checking existence. Body size is limited to 16 KiB; invalid JSON or fields return `400`, unsupported content type `415`, too large body `413`, and database errors `503`. Error responses contain an `error` string. Amounts are integers; currency and minor units are not defined.

## Existing database migration

Do not migrate the real `financial.db` without explicit owner approval. Stop all writers, create and verify a SQLite backup, and rehearse on a temporary copy. Then explicitly run `python migrate.py --database PATH` for version 0 followed by `python migrate_v2.py --database PATH` for version 1, only after approval. For an existing version 1 database, run only the second command. Each migration is transactional and versioned; existing rows retain their IDs and values and get `user_id = NULL`. They remain invisible to every account and are never automatically assigned. Startup refuses a schema that has not been migrated.

The optional local administrative command `python claim_legacy.py --database PATH --user-id ID --expected-count COUNT --confirm` assigns **all** unassigned rows to that existing user. Before using it, independently inspect the database in read-only mode, verify the target user and the count, back up, and obtain the owner's explicit authorization. The command aborts if the count has changed. There is no web endpoint for claiming rows.

## Tests

`python -m pytest` runs against isolated temporary databases. Tests initialize or migrate only temporary paths and set the test database before importing the WSGI app. They check cross-user access, session and CSRF behavior, migration and rollback, and existing transaction validation.

## Login limits and production

By default, validly formatted login attempts (successful or failed) are limited to 30 per client IP and 5 per normalized username in a rolling 60-second window. Attempts are reserved atomically in SQLite before password verification; the limits apply across workers sharing the same database. Limits are short-lived, but an attacker can temporarily exhaust the username limit. Expired attempts are removed during later login attempts. App-factory settings `LOGIN_WINDOW`, `LOGIN_IP_LIMIT`, and `LOGIN_USER_LIMIT` are positive integers; tune them for the deployment. Rate-limit and session database errors reject requests rather than granting access. A distributed attack still needs upstream protection, and registration currently has no rate limit.

By default `X-Forwarded-For` is ignored. Only when the app is reachable exclusively through a known chain of trusted reverse proxies, set `FINANCIAL_TRUSTED_PROXY_HOPS` to the exact number of trusted proxy hops that correctly set this header. Configure the proxy to replace untrusted forwarded headers and block direct access to the application. A wrong hop count or bypassable proxy allows spoofing and defeats IP limits. All WSGI workers must share the same persistent SQLite file and correct system time; separate database copies do not share limits or revocations.

Generate a random secret using the command above and store it in a secret manager or protected environment. The startup checks reject missing, short, and some obviously weak secrets, but cannot establish that a key is random. Never use a memorable phrase or reuse a test key. Changing the key invalidates cookies and changes hashed rate-limit keys. Review HTTPS, registration abuse controls, password recovery, secure secret storage, CORS/origins, backup and restore, persistent storage, and SQLite concurrency before deployment. In-flight operations that already passed session validation may complete while a concurrent logout occurs.

## Local website on Windows PowerShell

These commands create a **new separate** database named `local-financial.db`; they do not open or migrate the existing `financial.db`. Run the migration commands only for a new database. Preserve `local-financial.db` if you want to keep the accounts and transactions you create; do not run migrations against the existing personal database without its owner's separate approval.

```powershell
cd 'C:\Users\elama\Downloads\VS.Code\.vscode\financial-tracker'
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:FINANCIAL_DATABASE = Join-Path (Get-Location) 'local-financial.db'
$env:FINANCIAL_SECRET_KEY = .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
.\.venv\Scripts\python.exe migrate.py --database $env:FINANCIAL_DATABASE
.\.venv\Scripts\python.exe migrate_v2.py --database $env:FINANCIAL_DATABASE
.\.venv\Scripts\python.exe migrate_v3.py --database $env:FINANCIAL_DATABASE
.\.venv\Scripts\python.exe migrate_v4.py --database $env:FINANCIAL_DATABASE
.\.venv\Scripts\python.exe -c "from app import app; app.config['SESSION_COOKIE_SECURE']=False; app.run(host='127.0.0.1', port=5000, debug=False)"
```

Open `http://127.0.0.1:5000/register`, create an account, and sign in. On later starts, set the environment variables and run only the last command, not the migration commands. The generated key lasts for the current PowerShell session; changing it invalidates existing browser sessions. To keep sessions across restarts, store a randomly generated key securely outside Git and load it instead. The final command disables secure cookies **only for this localhost HTTP development process**; never use that override or Flask's development server in production.

The dashboard is at `/dashboard`, login at `/login`, and registration at `/register`; `GET /` retains its original JSON API response. The interface supports English, Russian, and Kazakh via the language selector. It displays KZT as whole tenge and preserves exact integer amounts and totals using `BigInt`; a modern browser with BigInt and HTML dialog support is required. The chart groups all transactions by date, showing each day's closing balance; future-dated transactions are included. Transaction text is inserted as text, not HTML.

The dashboard's period selector uses the current local calendar week (Monday–Sunday), month, year, or all time. Income, expenses, cash-flow lines, and category totals follow the selected period; the overall balance always includes all transactions. The search filters descriptions and categories locally without changing the statistics. There is no separate transaction-name field: the description serves that purpose. Operations with future dates are included when their date falls in the selected period.

## Savings goals and schema version 3

The dashboard supports multiple user-owned savings goals. A goal starts at zero; deposits and withdrawals reserve or release funds without creating transactions or changing total balance. Available balance is total balance minus all goal savings. When reserves are positive, changes to transactions (including legacy claims) that would reduce the total below reserves return `409` with code `reserved_funds_conflict`. A negative total remains permitted when reserves are zero. Deposits cannot exceed available funds or the remaining target; withdrawals cannot exceed saved funds; targets cannot be reduced below savings. Deleting a goal releases the reserve. Deadlines do not automatically delete or release goals.

Authenticated API: `GET /api/goals`, `POST /api/goals` (`title`, `target_amount`, optional `deadline`), `PUT /api/goals/<id>` (same fields), `DELETE /api/goals/<id>` (204), `POST /api/goals/<id>/deposit` and `/withdraw` (`amount`), and `GET /api/goals/summary` (`total_balance`, `reserved_savings`, `available_balance`). State-changing requests require `X-CSRF-Token`. Amounts are positive integral tenge, at most 9223372036854775807 per field. Conflicts return 409 with a `code`: `reserved_funds_conflict`, `insufficient_available`, `exceeds_goal_target`, `insufficient_goal_funds`, or `target_below_saved`. SQLite errors, including lock timeouts, return 503. Transaction creation, goal deposit and goal withdrawal require an `Idempotency-Key` header; see below.

For a new database, run `migrate.py`, `migrate_v2.py`, `migrate_v3.py`, then `migrate_v4.py`, each with the explicitly selected `--database` path. For an existing v2 database, stop all writers, create and verify a SQLite backup using the SQLite backup API, rehearse `migrate_v3.py --database COPY` on a temporary copy, and check data and `PRAGMA integrity_check`. Only after the database owner's separate approval run `migrate_v3.py --database PATH` on the intended real database. Migration uses a transaction, leaves existing users and transactions intact, and is repeatable. Restore the verified backup if recovery is necessary. Never run the migration against `financial.db` or `local-financial.db` without explicit approval.

Use a production WSGI server, HTTPS, a persistent SQLite volume, and a random persistent secret. SQLite serializes writes, so high contention can delay requests or return 503; retry only after confirming whether the prior operation completed. The browser currently uses one request per action and does not offer offline operation.


## Financial request idempotency and schema version 4

`POST /api/transactions`, `POST /api/goals/<id>/deposit` and `POST /api/goals/<id>/withdraw` require `Idempotency-Key` containing a lowercase UUID v4. Missing or invalid keys return 400 with `code: invalid_idempotency_key`. A key is scoped to the authenticated user; repeating the same valid operation returns the original successful JSON and status, with `Idempotency-Replayed: true`. Reusing it for different data, an endpoint or goal returns 409 with `code: idempotency_key_conflict`. Authentication and CSRF are still required on every request. Other routes are unchanged. Old clients must supply the new header.

The mutation and its successful response are committed in one SQLite transaction. Validation failures, financial conflicts, missing goals and database errors are not stored as successful operations. After a network error or 503, retry the same request with the same key. Use a new key for a genuinely new operation. The browser stores an unresolved request in sessionStorage by authenticated user ID; this may be lost on closing a tab or browser or clearing storage. Never assume recovery after closure. After success the dashboard reloads current data instead of applying a historical replay response.

Records are retained for 30 days and expired records are deleted in batches of up to 100 during financial writes. Once a record has been removed, an old key can execute again. Never automatically retry beyond 30 days; inspect the account and reconcile manually. Retention bounds time, not total number of records; monitor database growth.

For an existing v3 database, **obtain separate owner approval before touching the real database**. Stop all application processes and other writers, create a consistent SQLite backup using the SQLite backup API, verify the backup and rehearse on a separate copy. Run `python migrate_v4.py --database PATH_TO_COPY`, then verify `PRAGMA integrity_check`, `PRAGMA foreign_key_check`, schema version, and existing users, transactions and goals. After separate approval and a tested restore plan, run the same command against the explicitly selected real path. The migration is transactional and repeatable on version 4; application startup requires version 4. If rollback is necessary, stop all writers and restore the verified v3 backup; a restore also discards any changes made since that backup.
