import os
import sqlite3
from contextlib import closing
from pathlib import Path

DEFAULT_DATABASE = Path(__file__).resolve().parent / 'financial.db'
SCHEMA_VERSION = 2


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


def add_transaction(user_id, transaction_type, amount, category, description, date, path):
    with closing(connect(path)) as connection, connection:
        connection.execute('''INSERT INTO transactions (user_id, type, amount, category, description, date)
                              VALUES (?, ?, ?, ?, ?, ?)''',
                           (user_id, transaction_type, amount, category, description, date))


def update_transaction(user_id, transaction_id, transaction_type, amount, category, description, date, path):
    with closing(connect(path)) as connection, connection:
        cursor = connection.execute('''UPDATE transactions SET type = ?, amount = ?, category = ?,
            description = ?, date = ? WHERE id = ? AND user_id = ?''',
            (transaction_type, amount, category, description, date, transaction_id, user_id))
        return cursor.rowcount > 0


def delete_transaction(user_id, transaction_id, path):
    with closing(connect(path)) as connection, connection:
        return connection.execute('DELETE FROM transactions WHERE id = ? AND user_id = ?',
                                  (transaction_id, user_id)).rowcount > 0


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
