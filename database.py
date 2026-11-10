import sqlite3


def create_database():

    connection = sqlite3.connect("financial.db")
    cursor = connection.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL CHECK (type IN ("income", "expense")),
            amount INTEGER NOT NULL CHECK (amount > 0),
            category TEXT,
            description TEXT,
            date TEXT NOT NULL
        )
    ''')

    connection.commit()
    connection.close()


def add_transaction(type, amount, category, description, date):
    
    connection = sqlite3.connect("financial.db")
    cursor = connection.cursor()

    cursor.execute('''
        INSERT INTO transactions (type, amount, category, description, date)
        VALUES (?, ?, ?, ?, ?)
    ''', (type, amount, category, description, date))

    connection.commit()
    connection.close()


def get_transactions():

    connection = sqlite3.connect("financial.db")
    cursor = connection.cursor()

    cursor.execute('''
        SELECT * FROM transactions
    ''')

    result = cursor.fetchall()

    connection.close()
    return result
