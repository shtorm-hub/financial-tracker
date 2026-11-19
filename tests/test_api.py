import importlib
import sqlite3
import sys

import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Set the path before importing app: its WSGI instance initializes on import.
    db = tmp_path / 'test.db'
    monkeypatch.setenv('FINANCIAL_DATABASE', str(db))
    sys.modules.pop('app', None)
    module = importlib.import_module('app')
    assert module.app.config['DATABASE'] == str(db.resolve())
    module.app.config['TESTING'] = True
    return module.app.test_client()


def test_existing_endpoints(client):
    assert client.get('/').get_json() == {'message': 'Financial Tracker API is running'}
    assert client.get('/api/transactions').get_json() == []
    assert client.get('/api/balance').get_json() == {'income': 0, 'expense': 0, 'balance': 0}
    for kind, amount in [('income', 120), ('expense', 20)]:
        response = client.post('/api/transactions', json={
            'type': kind, 'amount': amount, 'category': 'food',
            'description': None, 'date': '2026-11-19'})
        assert response.status_code == 201
        assert response.get_json() == {'message': 'Transaction created'}
    transactions = client.get('/api/transactions').get_json()
    assert len(transactions) == 2
    assert transactions[0] == {'id': 1, 'type': 'income', 'amount': 120,
                               'category': 'food', 'description': None, 'date': '2026-11-19'}
    assert client.get('/api/balance').get_json() == {'income': 120, 'expense': 20, 'balance': 100}


@pytest.mark.parametrize('change', [
    {'type': 'other'}, {'type': None}, {'amount': True}, {'amount': 0},
    {'amount': 1.5}, {'amount': 2**63}, {'category': 1}, {'category': 'x' * 101},
    {'description': []}, {'description': 'x' * 1001}, {'date': '2026-02-30'}, {'date': None},
])
def test_invalid_fields(client, change):
    data = {'type': 'income', 'amount': 1, 'date': '2026-11-19'}
    data.update(change)
    response = client.post('/api/transactions', json=data)
    assert response.status_code == 400
    assert 'error' in response.get_json()
    assert client.get('/api/transactions').get_json() == []


def test_json_errors_and_body_limit(client):
    assert client.post('/api/transactions', json=[]).status_code == 400
    malformed = client.post('/api/transactions', data='{', content_type='application/json')
    assert malformed.status_code == 400 and malformed.is_json
    wrong_type = client.post('/api/transactions', data='{}', content_type='text/plain')
    assert wrong_type.status_code == 415 and wrong_type.is_json
    oversized = client.post('/api/transactions', data=' ' * 17000, content_type='application/json')
    assert oversized.status_code == 413 and oversized.is_json


def test_initialization_preserves_existing_data(tmp_path, monkeypatch):
    db = tmp_path / 'existing.db'
    with sqlite3.connect(db) as connection:
        connection.execute("CREATE TABLE transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT NOT NULL, amount INTEGER NOT NULL, category TEXT, description TEXT, date TEXT NOT NULL)")
        connection.execute("INSERT INTO transactions (type, amount, date) VALUES ('income', 42, '2026-11-19')")
    monkeypatch.setenv('FINANCIAL_DATABASE', str(db))
    sys.modules.pop('app', None)
    module = importlib.import_module('app')
    assert module.app.test_client().get('/api/balance').get_json()['balance'] == 42
    assert module.create_app(str(db)).test_client().get('/api/transactions').get_json()[0]['amount'] == 42
