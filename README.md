# Financial Tracker

Flask and SQLite personal finance API. Phase 3 adds username-based accounts and cookie sessions. This API is not ready for public deployment: login rate limiting is not implemented and is a **production blocker**.

## Setup

Use Python 3.14 and install dependencies with `pip install -r requirements.txt`. Set `FINANCIAL_DATABASE` to an absolute database path (default: `financial.db` next to `database.py`) and `FINANCIAL_SECRET_KEY` to a persistent, unpredictable random secret of at least 32 characters. Keep the secret outside Git; changing it invalidates sessions. For example, generate one privately with `python -c "import secrets; print(secrets.token_urlsafe(48))"` and store it in a secure environment variable. Never use the example test secret in production.

The app checks the schema read-only at startup and refuses an unmigrated database. It does not create or migrate a database on WSGI import or on requests. To initialize a **new, explicitly selected** database, run `python migrate.py --database PATH`. For an existing database, follow the migration procedure below first. Then `python app.py` runs with debug disabled; WSGI entry point is `app:app`.

Session cookies default to `Secure`, `HttpOnly`, and `SameSite=Lax`, with a 12-hour lifetime. Use HTTPS in production. For a local HTTP-only development environment, use a local app factory configuration with `SESSION_COOKIE_SECURE=False`; never use that override in production. Flask's signed cookie is not encrypted; it stores a user ID and CSRF token, not financial data or passwords. Logout clears the browser cookie but does not revoke a previously copied cookie; add server-side revocation before relying on forced logout.

## API and frontend integration

All API responses are JSON except successful DELETE (`204`, empty body). The root `GET /` remains public. The transaction and balance routes require a session; an unauthenticated request returns `401 {"error":"Authentication required"}`. Financial data is always scoped to the authenticated user. A `user_id` field in transaction JSON is rejected.

Cookie and CSRF flow for Medet's frontend:

1. Send `GET /api/auth/csrf` with cookies; retain the returned `csrf_token` in memory.
2. Send `X-CSRF-Token: <token>` and the session cookie on every POST, PUT, PATCH, or DELETE, including registration, login, and logout. A missing, wrong, or stale token returns `403`.
3. Login and logout clear the old session. Fetch a fresh token after each before the next changing request. Never place tokens in URLs.
4. For a separate frontend origin, configure exact allowed origins and credentialed CORS only after choosing deployment origins; this project does not currently enable CORS. Cookie `SameSite` and HTTPS settings must be reviewed for that topology. Frontend should use `credentials: 'include'` when appropriate.

Authentication endpoints:

- `POST /api/auth/register`: JSON `{"username":"alice","password":"..."}`; `201 {"message":"User registered"}`. Usernames normalize to lowercase, must contain 3–32 ASCII letters, digits, or underscores. Passwords must contain 12–256 characters. Duplicate username returns `409`; invalid input returns `400`. Registration does not log the user in.
- `POST /api/auth/login`: same fields; `200 {"message":"Logged in"}`; incorrect credentials return `401`. Malformed input returns `400`.
- `POST /api/auth/logout`: `200 {"message":"Logged out"}` and clears the session.
- `GET /api/auth/me`: `200` with `id` and `username`, or `401`.
- `GET /api/auth/csrf`: `200 {"csrf_token":"..."}` and sets or uses the session cookie.

Transaction endpoints:

- `GET /api/transactions`: `200`, array of `id`, `type`, `amount`, `category`, `description`, `date`. Order is unspecified.
- `POST /api/transactions`: JSON object with `type` (`income` or `expense`), `amount` (positive integer up to 9223372036854775807), and valid `date` (`YYYY-MM-DD`). Optional `category` and `description` are null or strings of at most 100 and 1000 characters. Success: `201 {"message":"Transaction created"}`.
- `PUT /api/transactions/<id>`: same validation as POST, replaces all fields; omitted optional fields become null. Success: `200 {"message":"Transaction updated"}`.
- `DELETE /api/transactions/<id>`: success `204` with no body.
- `GET /api/balance`: `200`, for example `{"income":120,"expense":20,"balance":100}`.

PUT and DELETE return `404 {"error":"Transaction not found"}` for both missing and other users' IDs. PUT validates input before checking existence. Body size is limited to 16 KiB; invalid JSON or fields return `400`, unsupported content type `415`, too large body `413`, and database errors `500`. Error responses contain an `error` string. Amounts are integers; currency and minor units are not defined.

## Existing database migration

Do not migrate the real `financial.db` without explicit owner approval. Stop all writers, create and verify a SQLite backup, and rehearse on a temporary copy. Then explicitly run `python migrate.py --database PATH` only after approval. The migration is transactional and versioned; existing rows retain their IDs and values and get `user_id = NULL`. They remain invisible to every account and are never automatically assigned. Startup refuses a schema that has not been migrated.

The optional local administrative command `python claim_legacy.py --database PATH --user-id ID --expected-count COUNT --confirm` assigns **all** unassigned rows to that existing user. Before using it, independently inspect the database in read-only mode, verify the target user and the count, back up, and obtain the owner's explicit authorization. The command aborts if the count has changed. There is no web endpoint for claiming rows.

## Tests

`python -m pytest` runs against isolated temporary databases. Tests initialize or migrate only temporary paths and set the test database before importing the WSGI app. They check cross-user access, session and CSRF behavior, migration and rollback, and existing transaction validation.

Before public deployment, implement and test login rate limiting suitable for the deployment topology. Also review password recovery, secure secret storage, session revocation, HTTPS, CORS/origins, backup and restore, and persistent database storage. Registration is currently open to anyone who can reach the server.
