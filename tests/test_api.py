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


def test_update_and_delete_transactions(client):
    for amount in (120, 30):
        assert client.post('/api/transactions', json={
            'type': 'income', 'amount': amount, 'date': '2026-11-19'
        }).status_code == 201

    updated = {'type': 'expense', 'amount': 20, 'category': 'food',
               'description': 'lunch', 'date': '2026-11-20'}
    response = client.put('/api/transactions/1', json=updated)
    assert response.status_code == 200
    assert response.get_json() == {'message': 'Transaction updated'}
    transactions = client.get('/api/transactions').get_json()
    assert next(t for t in transactions if t['id'] == 1) == {'id': 1, **updated}
    assert next(t for t in transactions if t['id'] == 2)['amount'] == 30
    assert client.get('/api/balance').get_json() == {'income': 30, 'expense': 20, 'balance': 10}
    assert client.put('/api/transactions/1', json=updated).status_code == 200

    response = client.delete('/api/transactions/1')
    assert response.status_code == 204 and response.data == b''
    assert [t['id'] for t in client.get('/api/transactions').get_json()] == [2]
    assert client.get('/api/balance').get_json() == {'income': 30, 'expense': 0, 'balance': 30}
    assert client.delete('/api/transactions/1').status_code == 404


@pytest.mark.parametrize('change', [
    {'type': 'other'}, {'type': None}, {'amount': True}, {'amount': 0},
    {'amount': 1.5}, {'amount': 2**63}, {'category': 1}, {'category': 'x' * 101},
    {'description': []}, {'description': 'x' * 1001}, {'date': '2026-02-30'}, {'date': None},
])
def test_update_rejects_invalid_fields_without_changing_record(client, change):
    original = {'type': 'income', 'amount': 1, 'date': '2026-11-19'}
    client.post('/api/transactions', json=original)
    before = client.get('/api/transactions').get_json()
    response = client.put('/api/transactions/1', json={**original, **change})
    assert response.status_code == 400 and 'error' in response.get_json()
    assert client.get('/api/transactions').get_json() == before


def test_update_json_errors_and_missing_ids(client):
    valid = {'type': 'income', 'amount': 1, 'date': '2026-11-19'}
    assert client.put('/api/transactions/1', json=[]).status_code == 400
    assert client.put('/api/transactions/1', data='{', content_type='application/json').status_code == 400
    assert client.put('/api/transactions/1', data='{}', content_type='text/plain').status_code == 415
    assert client.put('/api/transactions/1', data=' ' * 17000, content_type='application/json').status_code == 413
    for transaction_id in (1, 2**63):
        url = f'/api/transactions/{transaction_id}'
        assert client.put(url, json=valid).status_code == 404
        assert client.delete(url).status_code == 404
    assert client.get('/api/transactions').get_json() == []
