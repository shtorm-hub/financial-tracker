# Financial Tracker

Flask API for tracking income and expenses with SQLite. Python 3.14 is the project target.

## Setup and run

```sh
python -m venv .venv
# Activate the virtual environment, then:
pip install -r requirements.txt
python app.py
```

The development server runs with debug disabled. For a WSGI server, use `app:app` (or the `app:create_app` factory). The database schema is initialized once when an app instance is created, not per request. This is not a deployment guide.

By default the database is `financial.db` beside `database.py`, independent of the process working directory. Set the `FINANCIAL_DATABASE` environment variable to use another path; absolute paths are recommended. Its parent directory must already exist and be writable. Existing databases are preserved; initialization only creates a missing table and does not migrate existing schemas. Back up your database before changing configuration or upgrading.

## API

All successful response shapes below match the original API. Dates are stored in `YYYY-MM-DD` format. Amounts are positive integers; the application does not define a currency or conversion to minor units.

- `GET /` returns `200` and `{"message":"Financial Tracker API is running"}`.
- `GET /api/transactions` returns `200` and an array of objects with `id`, `type`, `amount`, `category`, `description`, and `date`. Order is unspecified.
- `POST /api/transactions` accepts an `application/json` object with required `type` (`income` or `expense`), `amount` (integer from 1 to 9223372036854775807), and `date` (valid date parsed as `YYYY-MM-DD`); optional `category` and `description` are strings or null, with maximum lengths of 100 and 1000 characters respectively. The request body is limited to 16 KiB. Success returns `201` and `{"message":"Transaction created"}`.
- `PUT /api/transactions/<id>` replaces a transaction using the same fields and validation as POST; omitted optional fields become null. Success returns `200` and `{"message":"Transaction updated"}`. Invalid data returns `400`; valid data for a missing ID returns `404` and `{"error":"Transaction not found"}`. Validation happens before the existence check.
- `DELETE /api/transactions/<id>` deletes a transaction and returns `204` with an empty body. A missing ID returns `404` and `{"error":"Transaction not found"}`.
- `GET /api/balance` returns `200` and an object such as `{"income":120,"expense":20,"balance":100}`.

Invalid fields, non-object JSON and malformed JSON return `400` with an `error` string. An unsupported JSON content type returns `415`; an oversized body returns `413`. Database errors return `500` without exposing database details. Error responses have the shape `{"error":"..."}`.

## Tests

```sh
python -m pytest
```

Tests set `FINANCIAL_DATABASE` to a pytest temporary path before importing the app and never use the project database.

The API currently has no authentication or user isolation; do not expose personal financial data through it.
