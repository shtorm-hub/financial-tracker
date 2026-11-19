import os
import sqlite3
from contextlib import closing
from pathlib import Path

DEFAULT_DATABASE = Path(__file__).resolve().parent / "financial.db"


def database_path(path=None):
    return str(Path(path or os.environ.get("FINANCIAL_DATABASE", DEFAULT_DATABASE)).expanduser().resolve())


def create_database(path=None):
    with closing(sqlite3.connect(database_path(path))) as connection:
        with connection:
            connection.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
                    amount INTEGER NOT NULL CHECK (amount > 0),
                    category TEXT,
                    description TEXT,
                    date TEXT NOT NULL
                )
            ''')


def add_transaction(type, amount, category, description, date, path=None):
    with closing(sqlite3.connect(database_path(path))) as connection:
        with connection:
            connection.execute('''
                INSERT INTO transactions (type, amount, category, description, date)
                VALUES (?, ?, ?, ?, ?)
            ''', (type, amount, category, description, date))


def get_transactions(path=None):
    with closing(sqlite3.connect(database_path(path))) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute('SELECT * FROM transactions')]


def get_balance(path=None):
    transactions = get_transactions(path)
    income = sum(t['amount'] for t in transactions if t['type'] == 'income')
    expense = sum(t['amount'] for t in transactions if t['type'] == 'expense')
    return {'income': income, 'expense': expense, 'balance': income - expense}
