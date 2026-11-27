import os
import json
import hashlib
import time
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path

DEFAULT_DATABASE = Path(__file__).resolve().parent / 'financial.db'
SCHEMA_VERSION = 4


def database_path(path=None):
    return str(Path(path or os.environ.get('FINANCIAL_DATABASE', DEFAULT_DATABASE)).expanduser().resolve())


def connect(path, readonly=False, create=False):
    target = Path(database_path(path))
    if create:
        connection = sqlite3.connect(target)
    else:
        mode = 'ro' if readonly else 'rw'
        connection = sqlite3.connect(target.as_uri() + '?mode=' + mode, uri=True)
    connection.execute('PRAGMA foreign_keys = ON')
    return connection


def check_database(path):
    # Read-only check: a WSGI import must never migrate or create a database.
    with closing(connect(path, readonly=True)) as connection:
        version = connection.execute('PRAGMA user_version').fetchone()[0]
        if version != SCHEMA_VERSION:
            raise RuntimeError('Database schema requires an explicit migration')


def migrate_database(path):
    """Explicit migration only; caller is responsible for a verified backup."""
    with closing(connect(path, create=True)) as connection:
        try:
            connection.execute('BEGIN IMMEDIATE')
            version = connection.execute('PRAGMA user_version').fetchone()[0]
            if version == 1:
                connection.commit()
                return
            if version != 0:
                raise RuntimeError('Unsupported database schema version')
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'users' in tables:
                raise RuntimeError('Unexpected existing users table')
            connection.execute('''CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            )''')
            if 'transactions' in tables:
                columns = {row[1] for row in connection.execute('PRAGMA table_info(transactions)')}
                if columns != {'id', 'type', 'amount', 'category', 'description', 'date'}:
                    raise RuntimeError('Unexpected transactions schema')
                connection.execute('ALTER TABLE transactions ADD COLUMN user_id INTEGER REFERENCES users(id)')
            else:
                connection.execute('''CREATE TABLE transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
                    amount INTEGER NOT NULL CHECK (amount > 0),
                    category TEXT, description TEXT, date TEXT NOT NULL,
                    user_id INTEGER REFERENCES users(id)
                )''')
            connection.execute('CREATE INDEX idx_transactions_user_id ON transactions(user_id)')
            if connection.execute('PRAGMA foreign_key_check').fetchone():
                raise RuntimeError('Foreign key check failed')
            connection.execute('PRAGMA user_version = 1')
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def migrate_security_v2(path):
    """Explicitly upgrade schema v1; caller must back up first."""
    with closing(connect(path)) as connection:
        try:
            connection.execute('BEGIN IMMEDIATE')
            version = connection.execute('PRAGMA user_version').fetchone()[0]
            if version == 2:
                connection.commit()
                return
            if version != 1:
                raise RuntimeError('Security migration requires schema version 1')
            connection.execute('''CREATE TABLE auth_sessions (
                token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
                expires_at INTEGER NOT NULL
            )''')
            connection.execute('CREATE INDEX idx_auth_sessions_user ON auth_sessions(user_id)')
            connection.execute('CREATE INDEX idx_auth_sessions_expiry ON auth_sessions(expires_at)')
            connection.execute('''CREATE TABLE login_attempts (
                id INTEGER PRIMARY KEY, ip_hash TEXT NOT NULL,
                username_hash TEXT NOT NULL, attempted_at INTEGER NOT NULL
            )''')
            connection.execute('CREATE INDEX idx_attempt_ip_time ON login_attempts(ip_hash, attempted_at)')
            connection.execute('CREATE INDEX idx_attempt_user_time ON login_attempts(username_hash, attempted_at)')
            connection.execute('CREATE INDEX idx_attempt_time ON login_attempts(attempted_at)')
            if connection.execute('PRAGMA foreign_key_check').fetchone():
                raise RuntimeError('Foreign key check failed')
            connection.execute('PRAGMA user_version = 2')
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def reserve_login_attempt(path, ip_hash, username_hash, now, window, ip_limit, user_limit):
    """Atomically reserve an attempt for both keys; return retry seconds or zero."""
    with closing(connect(path)) as connection:
        try:
            connection.execute('BEGIN IMMEDIATE')
            cutoff = now - window
            connection.execute('DELETE FROM login_attempts WHERE attempted_at <= ?', (cutoff,))
            retry = 0
            for column, key, limit in (('ip_hash', ip_hash, ip_limit), ('username_hash', username_hash, user_limit)):
                count, oldest = connection.execute(
                    f'SELECT COUNT(*), MIN(attempted_at) FROM login_attempts WHERE {column} = ?', (key,)
                ).fetchone()
                if count >= limit:
                    retry = max(retry, oldest + window - now)
            if not retry:
                connection.execute('INSERT INTO login_attempts (ip_hash, username_hash, attempted_at) VALUES (?, ?, ?)',
                                   (ip_hash, username_hash, now))
            connection.commit()
            return retry
        except Exception:
            connection.rollback()
            raise


def create_session(path, token_hash, user_id, expires_at, now):
    with closing(connect(path)) as connection, connection:
        connection.execute('DELETE FROM auth_sessions WHERE expires_at <= ?', (now,))
        connection.execute('INSERT INTO auth_sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)',
                           (token_hash, user_id, expires_at))


def get_session_user(path, token_hash, now):
    with closing(connect(path)) as connection:
        connection.row_factory = sqlite3.Row
        return connection.execute('''SELECT users.id, users.username FROM auth_sessions
            JOIN users ON users.id = auth_sessions.user_id
            WHERE token_hash = ? AND expires_at > ?''', (token_hash, now)).fetchone()


def revoke_session(path, token_hash):
    with closing(connect(path)) as connection, connection:
        connection.execute('DELETE FROM auth_sessions WHERE token_hash = ?', (token_hash,))


def revoke_user_sessions(path, user_id):
    """Use in the same security workflow as a password reset or compromise."""
    with closing(connect(path)) as connection, connection:
        connection.execute('DELETE FROM auth_sessions WHERE user_id = ?', (user_id,))


def create_user(username, password_hash, path):
    with closing(connect(path)) as connection, connection:
        connection.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, password_hash))


def find_user(username, path):
    with closing(connect(path)) as connection:
        connection.row_factory = sqlite3.Row
        return connection.execute('SELECT id, username, password_hash FROM users WHERE username = ?', (username,)).fetchone()


def get_user(user_id, path):
    with closing(connect(path)) as connection:
        connection.row_factory = sqlite3.Row
        return connection.execute('SELECT id, username FROM users WHERE id = ?', (user_id,)).fetchone()


class FinancialConflict(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@contextmanager
def write_transaction(path):
    with closing(connect(path)) as connection:
        try:
            connection.execute('BEGIN IMMEDIATE')
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def snapshot(connection, user_id):
    total = sum(amount if kind == 'income' else -amount for kind, amount in
                connection.execute('SELECT type, amount FROM transactions WHERE user_id = ?', (user_id,)))
    reserved = sum(row[0] for row in connection.execute('SELECT saved_amount FROM goals WHERE user_id = ?', (user_id,)))
    return {'total_balance': total, 'reserved_savings': reserved, 'available_balance': total - reserved}


def assert_reserves(connection, user_id):
    state = snapshot(connection, user_id)
    if state['reserved_savings'] > 0 and state['available_balance'] < 0:
        raise FinancialConflict('reserved_funds_conflict')


def add_transaction(user_id, transaction_type, amount, category, description, date, path):
    with write_transaction(path) as connection:
        connection.execute('INSERT INTO transactions (user_id, type, amount, category, description, date) VALUES (?, ?, ?, ?, ?, ?)',
                           (user_id, transaction_type, amount, category, description, date))
        assert_reserves(connection, user_id)


def update_transaction(user_id, transaction_id, transaction_type, amount, category, description, date, path):
    with write_transaction(path) as connection:
        cursor = connection.execute('UPDATE transactions SET type = ?, amount = ?, category = ?, description = ?, date = ? WHERE id = ? AND user_id = ?',
                                    (transaction_type, amount, category, description, date, transaction_id, user_id))
        assert_reserves(connection, user_id)
        return cursor.rowcount > 0


def delete_transaction(user_id, transaction_id, path):
    with write_transaction(path) as connection:
        cursor = connection.execute('DELETE FROM transactions WHERE id = ? AND user_id = ?', (transaction_id, user_id))
        assert_reserves(connection, user_id)
        return cursor.rowcount > 0


def get_transactions(user_id, path):
    with closing(connect(path)) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute('''SELECT id, type, amount, category, description, date
            FROM transactions WHERE user_id = ?''', (user_id,))]


def get_balance(user_id, path):
    transactions = get_transactions(user_id, path)
    income = sum(t['amount'] for t in transactions if t['type'] == 'income')
    expense = sum(t['amount'] for t in transactions if t['type'] == 'expense')
    return {'income': income, 'expense': expense, 'balance': income - expense}


def migrate_goals_v3(path):
    with write_transaction(path) as connection:
        version = connection.execute('PRAGMA user_version').fetchone()[0]
        if version == 3:
            return
        if version != 2:
            raise RuntimeError('Goals migration requires schema version 2')
        connection.execute("""CREATE TABLE goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            title TEXT NOT NULL CHECK (length(trim(title)) > 0 AND length(title) <= 100),
            target_amount INTEGER NOT NULL CHECK (target_amount > 0),
            saved_amount INTEGER NOT NULL DEFAULT 0 CHECK (saved_amount >= 0 AND saved_amount <= target_amount),
            deadline TEXT, created_at TEXT NOT NULL
        )""")
        connection.execute('CREATE INDEX idx_goals_user_id ON goals(user_id)')
        if connection.execute('PRAGMA foreign_key_check').fetchone():
            raise RuntimeError('Foreign key check failed')
        connection.execute('PRAGMA user_version = 3')


def goal_row(connection, user_id, goal_id):
    connection.row_factory = sqlite3.Row
    row = connection.execute('SELECT id, title, target_amount, saved_amount, deadline, created_at FROM goals WHERE id = ? AND user_id = ?', (goal_id, user_id)).fetchone()
    return dict(row) if row else None


def list_goals(path, user_id):
    with closing(connect(path)) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute('SELECT id, title, target_amount, saved_amount, deadline, created_at FROM goals WHERE user_id = ? ORDER BY id', (user_id,))]


def goal_summary(path, user_id):
    with closing(connect(path)) as connection:
        connection.execute('BEGIN')
        return snapshot(connection, user_id)


def create_goal(path, user_id, title, target, deadline, created_at):
    with write_transaction(path) as connection:
        cur = connection.execute('INSERT INTO goals (user_id, title, target_amount, deadline, created_at) VALUES (?, ?, ?, ?, ?)', (user_id, title, target, deadline, created_at))
        return goal_row(connection, user_id, cur.lastrowid)


def change_goal(path, user_id, goal_id, title, target, deadline):
    with write_transaction(path) as connection:
        goal = goal_row(connection, user_id, goal_id)
        if goal is None:
            return None
        if target < goal['saved_amount']:
            raise FinancialConflict('target_below_saved')
        connection.execute('UPDATE goals SET title = ?, target_amount = ?, deadline = ? WHERE id = ? AND user_id = ?', (title, target, deadline, goal_id, user_id))
        return goal_row(connection, user_id, goal_id)


def remove_goal(path, user_id, goal_id):
    with write_transaction(path) as connection:
        return connection.execute('DELETE FROM goals WHERE id = ? AND user_id = ?', (goal_id, user_id)).rowcount > 0


def move_goal_funds(path, user_id, goal_id, amount, deposit):
    with write_transaction(path) as connection:
        goal = goal_row(connection, user_id, goal_id)
        if goal is None:
            return None
        state = snapshot(connection, user_id)
        if deposit:
            if amount > state['available_balance']:
                raise FinancialConflict('insufficient_available')
            if amount > goal['target_amount'] - goal['saved_amount']:
                raise FinancialConflict('exceeds_goal_target')
            new_saved = goal['saved_amount'] + amount
        else:
            if amount > goal['saved_amount']:
                raise FinancialConflict('insufficient_goal_funds')
            new_saved = goal['saved_amount'] - amount
        connection.execute('UPDATE goals SET saved_amount = ? WHERE id = ? AND user_id = ?', (new_saved, goal_id, user_id))
        return {'goal': goal_row(connection, user_id, goal_id), 'summary': snapshot(connection, user_id)}


def migrate_idempotency_v4(path):
    with write_transaction(path) as connection:
        version = connection.execute('PRAGMA user_version').fetchone()[0]
        if version == 4:
            return
        if version != 3:
            raise RuntimeError('Idempotency migration requires schema version 3')
        connection.execute("""CREATE TABLE idempotency_records (
            user_id INTEGER NOT NULL REFERENCES users(id),
            idempotency_key TEXT NOT NULL CHECK(length(idempotency_key) = 36),
            operation TEXT NOT NULL, resource_id INTEGER,
            request_fingerprint TEXT NOT NULL CHECK(length(request_fingerprint) = 64),
            response_status INTEGER NOT NULL,
            response_body TEXT NOT NULL CHECK(length(response_body) <= 16384),
            created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
            UNIQUE(user_id, idempotency_key)
        )""")
        connection.execute('CREATE INDEX idx_idempotency_expiry ON idempotency_records(expires_at)')
        if connection.execute('PRAGMA foreign_key_check').fetchone():
            raise RuntimeError('Foreign key check failed')
        connection.execute('PRAGMA user_version = 4')


def idempotent_financial_operation(path, user_id, key, operation, resource_id, values):
    canonical = json.dumps([1, operation, resource_id, values], ensure_ascii=True, separators=(',', ':'))
    fingerprint = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    now = int(time.time())
    with write_transaction(path) as connection:
        connection.execute('DELETE FROM idempotency_records WHERE rowid IN (SELECT rowid FROM idempotency_records WHERE expires_at <= ? ORDER BY expires_at LIMIT 100)', (now,))
        row = connection.execute('SELECT request_fingerprint, response_status, response_body FROM idempotency_records WHERE user_id = ? AND idempotency_key = ?', (user_id, key)).fetchone()
        if row:
            if row[0] != fingerprint:
                raise FinancialConflict('idempotency_key_conflict')
            return row[1], json.loads(row[2]), True
        if operation == 'transaction':
            connection.execute('INSERT INTO transactions (user_id, type, amount, category, description, date) VALUES (?, ?, ?, ?, ?, ?)', (user_id, *values))
            assert_reserves(connection, user_id)
            status, result = 201, {'message': 'Transaction created'}
        else:
            goal = goal_row(connection, user_id, resource_id) if resource_id <= 2**63 - 1 else None
            if goal is None:
                return 404, {'error': 'Goal not found', 'code': 'goal_not_found'}, False
            amount = values[0]
            state = snapshot(connection, user_id)
            if operation == 'deposit':
                if amount > state['available_balance']:
                    raise FinancialConflict('insufficient_available')
                if amount > goal['target_amount'] - goal['saved_amount']:
                    raise FinancialConflict('exceeds_goal_target')
                new_saved = goal['saved_amount'] + amount
            else:
                if amount > goal['saved_amount']:
                    raise FinancialConflict('insufficient_goal_funds')
                new_saved = goal['saved_amount'] - amount
            connection.execute('UPDATE goals SET saved_amount = ? WHERE id = ? AND user_id = ?', (new_saved, resource_id, user_id))
            status, result = 200, {'goal': goal_row(connection, user_id, resource_id), 'summary': snapshot(connection, user_id)}
        body = json.dumps(result, ensure_ascii=True, separators=(',', ':'))
        connection.execute('INSERT INTO idempotency_records (user_id, idempotency_key, operation, resource_id, request_fingerprint, response_status, response_body, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                           (user_id, key, operation, resource_id, fingerprint, status, body, now, now + 30 * 86400))
        return status, result, False
