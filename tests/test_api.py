import importlib
import sqlite3
import sys

import pytest


@pytest.fixture
def raw_client(tmp_path, monkeypatch):
    from database import migrate_database
    db = tmp_path / 'test.db'
    migrate_database(db)
    monkeypatch.setenv('FINANCIAL_DATABASE', str(db))
    monkeypatch.setenv('FINANCIAL_SECRET_KEY', 'test-only-secret-key-32-characters-long')
    sys.modules.pop('app', None)
    module = importlib.import_module('app')
    assert module.app.config['DATABASE'] == str(db.resolve())
    module.app.config.update(TESTING=True, SESSION_COOKIE_SECURE=False)
    return module.app.test_client()


class AuthenticatedClient:
    def __init__(self, client):
        self.client = client

    def get(self, *args, **kwargs):
        return self.client.get(*args, **kwargs)

    def request(self, method, url, **kwargs):
        token = self.client.get('/api/auth/csrf').get_json()['csrf_token']
        kwargs.setdefault('headers', {})['X-CSRF-Token'] = token
        return getattr(self.client, method)(url, **kwargs)

    def post(self, url, **kwargs):
        return self.request('post', url, **kwargs)

    def put(self, url, **kwargs):
        return self.request('put', url, **kwargs)

    def delete(self, url, **kwargs):
        return self.request('delete', url, **kwargs)


@pytest.fixture
def client(raw_client):
    client = AuthenticatedClient(raw_client)
    data = {'username': 'alice', 'password': 'a secure test password'}
    assert client.post('/api/auth/register', json=data).status_code == 201
    assert client.post('/api/auth/login', json=data).status_code == 200
    return client


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


def test_migration_preserves_existing_data(tmp_path):
    from database import migrate_database
    db = tmp_path / 'existing.db'
    with sqlite3.connect(db) as connection:
        connection.execute("CREATE TABLE transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT NOT NULL, amount INTEGER NOT NULL, category TEXT, description TEXT, date TEXT NOT NULL)")
        connection.execute("INSERT INTO transactions (type, amount, date) VALUES ('income', 42, '2026-11-19')")
    migrate_database(db)
    migrate_database(db)
    with sqlite3.connect(db) as connection:
        assert connection.execute('SELECT id, amount, user_id FROM transactions').fetchall() == [(1, 42, None)]
        assert connection.execute('PRAGMA user_version').fetchone()[0] == 1


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


def test_isolation_and_authentication(raw_client):
    app = raw_client.application
    alice = AuthenticatedClient(raw_client)
    bob = AuthenticatedClient(app.test_client())
    a = {'username': 'alice', 'password': 'alice-password-123'}
    b = {'username': 'bob', 'password': 'bob-password-12345'}
    for client, credentials in ((alice, a), (bob, b)):
        assert client.post('/api/auth/register', json=credentials).status_code == 201
        assert client.post('/api/auth/login', json=credentials).status_code == 200
    original = {'type': 'income', 'amount': 50, 'date': '2026-11-20'}
    assert alice.post('/api/transactions', json=original).status_code == 201
    assert bob.get('/api/transactions').get_json() == []
    assert bob.get('/api/balance').get_json() == {'income': 0, 'expense': 0, 'balance': 0}
    assert bob.put('/api/transactions/1', json=original).status_code == 404
    assert bob.delete('/api/transactions/1').status_code == 404
    assert bob.post('/api/transactions', json={**original, 'user_id': 1}).status_code == 400
    assert alice.get('/api/balance').get_json()['income'] == 50
    assert len(alice.get('/api/transactions').get_json()) == 1
    assert alice.get('/api/auth/me').get_json()['username'] == 'alice'
    assert alice.post('/api/auth/logout').status_code == 200
    assert alice.get('/api/transactions').status_code == 401
    assert alice.get('/api/auth/me').status_code == 401
    assert alice.post('/api/transactions', json=original).status_code == 401
    assert alice.put('/api/transactions/1', json=original).status_code == 401
    assert alice.delete('/api/transactions/1').status_code == 401
    attacker = app.test_client()
    attacker.set_cookie(app.config['SESSION_COOKIE_NAME'], 'forged-user-id-1')
    assert attacker.get('/api/transactions').status_code == 401


def test_csrf_all_state_changes(raw_client):
    app = raw_client.application
    data = {'username': 'alice', 'password': 'alice-password-123'}
    for endpoint in ('register', 'login', 'logout'):
        assert raw_client.post('/api/auth/' + endpoint, json=data).status_code == 403
    c = AuthenticatedClient(raw_client)
    assert c.post('/api/auth/register', json=data).status_code == 201
    assert c.post('/api/auth/login', json=data).status_code == 200
    transaction = {'type': 'income', 'amount': 1, 'date': '2026-11-20'}
    assert raw_client.post('/api/transactions', json=transaction).status_code == 403
    assert raw_client.put('/api/transactions/1', json=transaction).status_code == 403
    assert raw_client.delete('/api/transactions/1').status_code == 403
    assert raw_client.post('/api/auth/logout').status_code == 403
    token = raw_client.get('/api/auth/csrf').get_json()['csrf_token']
    assert raw_client.post('/api/transactions', json=transaction, headers={'X-CSRF-Token': 'wrong'}).status_code == 403
    assert raw_client.post('/api/transactions', json=transaction, headers={'X-CSRF-Token': token}).status_code == 201
    other = app.test_client()
    other_token = other.get('/api/auth/csrf').get_json()['csrf_token']
    assert raw_client.delete('/api/transactions/1', headers={'X-CSRF-Token': other_token}).status_code == 403
    assert c.post('/api/auth/logout').status_code == 200
    assert raw_client.post('/api/auth/login', json=data, headers={'X-CSRF-Token': token}).status_code == 403


def test_registration_login_and_password_hash(raw_client):
    c = AuthenticatedClient(raw_client)
    creds = {'username': 'Alice', 'password': 'alice-password-123'}
    assert c.post('/api/auth/register', json=creds).status_code == 201
    assert c.post('/api/auth/register', json={**creds, 'username': 'alice'}).status_code == 409
    assert c.post('/api/auth/register', json={'username': 'bob', 'password': 'short'}).status_code == 400
    assert c.post('/api/auth/login', json={**creds, 'password': 'incorrect'}).status_code == 401
    assert c.post('/api/auth/login', json={'username': 'unknown', 'password': 'incorrect'}).status_code == 401
    with sqlite3.connect(raw_client.application.config['DATABASE']) as db:
        password_hash = db.execute('SELECT password_hash FROM users').fetchone()[0]
        assert password_hash.startswith('scrypt:') and creds['password'] not in password_hash
    assert c.post('/api/auth/login', json=creds).status_code == 200
    assert c.get('/api/auth/me').get_json()['username'] == 'alice'


def test_legacy_rows_hidden_and_migration_rollback(tmp_path, monkeypatch):
    from database import migrate_database
    db = tmp_path / 'legacy.db'
    with sqlite3.connect(db) as c:
        c.execute('CREATE TABLE transactions (id INTEGER PRIMARY KEY, type TEXT, amount INTEGER, category TEXT, description TEXT, date TEXT)')
        c.execute("INSERT INTO transactions VALUES (7, 'income', 99, NULL, NULL, '2026-11-20')")
    migrate_database(db)
    monkeypatch.setenv('FINANCIAL_DATABASE', str(db))
    monkeypatch.setenv('FINANCIAL_SECRET_KEY', 'test-only-secret-key-32-characters-long')
    sys.modules.pop('app', None)
    module = importlib.import_module('app')
    module.app.config.update(TESTING=True, SESSION_COOKIE_SECURE=False)
    client = AuthenticatedClient(module.app.test_client())
    creds = {'username': 'alice', 'password': 'alice-password-123'}
    client.post('/api/auth/register', json=creds)
    client.post('/api/auth/login', json=creds)
    assert client.get('/api/transactions').get_json() == []
    assert client.get('/api/balance').get_json()['income'] == 0
    assert client.delete('/api/transactions/7').status_code == 404
    with sqlite3.connect(db) as c:
        assert c.execute('SELECT id, amount, user_id FROM transactions').fetchall() == [(7, 99, None)]
    bad = tmp_path / 'bad.db'
    with sqlite3.connect(bad) as c:
        c.execute('CREATE TABLE transactions (unexpected TEXT)')
    with pytest.raises(RuntimeError):
        migrate_database(bad)
    with sqlite3.connect(bad) as c:
        assert c.execute('PRAGMA user_version').fetchone()[0] == 0
        assert c.execute("SELECT name FROM sqlite_master WHERE name='users'").fetchone() is None


def test_legacy_assignment_requires_matching_user_and_count(tmp_path):
    from database import migrate_database
    from claim_legacy import claim_unassigned
    db = tmp_path / 'legacy.db'
    migrate_database(db)
    with sqlite3.connect(db) as c:
        c.execute("INSERT INTO users (username, password_hash) VALUES ('alice', 'hash')")
        c.execute("INSERT INTO transactions (type, amount, date) VALUES ('income', 42, '2026-11-19')")
    with pytest.raises(ValueError):
        claim_unassigned(db, 999, 1)
    with pytest.raises(ValueError):
        claim_unassigned(db, 1, 2)
    with sqlite3.connect(db) as c:
        assert c.execute('SELECT user_id FROM transactions').fetchone()[0] is None
    assert claim_unassigned(db, 1, 1) == 1
    with sqlite3.connect(db) as c:
        assert c.execute('SELECT user_id FROM transactions').fetchone()[0] == 1


def test_startup_requires_secret_and_migrated_database(tmp_path, monkeypatch, raw_client):
    module = sys.modules['app']
    db = tmp_path / 'unmigrated.db'
    with sqlite3.connect(db) as c:
        c.execute('CREATE TABLE marker (id INTEGER)')
    before = db.read_bytes()
    with pytest.raises(RuntimeError, match='SECRET_KEY'):
        module.create_app(str(db), {'SECRET_KEY': None})
    with pytest.raises(RuntimeError, match='migration'):
        module.create_app(str(db), {'SECRET_KEY': 'x' * 32})
    assert db.read_bytes() == before
    app = raw_client.application
    assert app.config['SESSION_COOKIE_HTTPONLY']
    assert app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'
    assert module.create_app(app.config['DATABASE'], {'SECRET_KEY': 'x' * 32}).config['SESSION_COOKIE_SECURE']
