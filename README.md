# Financial Tracker

Flask and SQLite personal finance API with username accounts, revocable cookie sessions, CSRF protection, and SQLite-backed login limits.

## Setup

Use Python 3.14 and install dependencies with `pip install -r requirements.txt`. Set `FINANCIAL_DATABASE` to an absolute database path (default: `financial.db` next to `database.py`) and `FINANCIAL_SECRET_KEY` to a persistent, unpredictable random secret of at least 32 characters. Keep the secret outside Git; changing it invalidates sessions. For example, generate one privately with `python -c "import secrets; print(secrets.token_urlsafe(48))"` and store it in a secure environment variable. Never use the example test secret in production.

The app checks the schema read-only at startup and refuses an unmigrated database. It does not create or migrate a database on WSGI import or on requests. For a **new, explicitly selected** database, run `python migrate.py --database PATH` and then `python migrate_v2.py --database PATH`. For an existing database, follow the migration procedure below first. Then `python app.py` runs with debug disabled; WSGI entry point is `app:app`.

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
