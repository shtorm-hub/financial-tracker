import os
import sqlite3
from contextlib import closing
from pathlib import Path

DEFAULT_DATABASE = Path(__file__).resolve().parent / 'financial.db'
SCHEMA_VERSION = 1


def database_path(path=None):
    return str(Path(path or os.environ.get('FINANCIAL_DATABASE', DEFAULT_DATABASE)).expanduser().resolve())


def connect(path, readonly=False):
    target = Path(database_path(path))
    connection = sqlite3.connect(target.as_uri() + '?mode=ro', uri=True) if readonly else sqlite3.connect(target)
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
    with closing(connect(path)) as connection:
        try:
            connection.execute('BEGIN IMMEDIATE')
            version = connection.execute('PRAGMA user_version').fetchone()[0]
            if version == SCHEMA_VERSION:
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
            connection.execute(f'PRAGMA user_version = {SCHEMA_VERSION}')
            connection.commit()
        except Exception:
            connection.rollback()
            raise


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
