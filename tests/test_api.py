import importlib
import sqlite3
import sys

import pytest


@pytest.fixture
def raw_client(tmp_path, monkeypatch):
    from database import migrate_database, migrate_security_v2, migrate_goals_v3
    db = tmp_path / 'test.db'
    migrate_database(db)
    migrate_security_v2(db)
    migrate_goals_v3(db)
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
    from database import migrate_database, migrate_security_v2
    db = tmp_path / 'existing.db'
    with sqlite3.connect(db) as connection:
        connection.execute("CREATE TABLE transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT NOT NULL, amount INTEGER NOT NULL, category TEXT, description TEXT, date TEXT NOT NULL)")
        connection.execute("INSERT INTO transactions (type, amount, date) VALUES ('income', 42, '2026-11-19')")
    migrate_database(db)
    migrate_security_v2(db)
    migrate_security_v2(db)
    with sqlite3.connect(db) as connection:
        assert connection.execute('SELECT id, amount, user_id FROM transactions').fetchall() == [(1, 42, None)]
        assert connection.execute('PRAGMA user_version').fetchone()[0] == 2


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
    from database import migrate_database, migrate_security_v2, migrate_goals_v3
    db = tmp_path / 'legacy.db'
    with sqlite3.connect(db) as c:
        c.execute('CREATE TABLE transactions (id INTEGER PRIMARY KEY, type TEXT, amount INTEGER, category TEXT, description TEXT, date TEXT)')
        c.execute("INSERT INTO transactions VALUES (7, 'income', 99, NULL, NULL, '2026-11-20')")
    migrate_database(db)
    migrate_security_v2(db)
    migrate_goals_v3(db)
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
    from database import migrate_database, migrate_security_v2, migrate_goals_v3
    from claim_legacy import claim_unassigned
    db = tmp_path / 'legacy.db'
    migrate_database(db)
    migrate_security_v2(db)
    migrate_goals_v3(db)
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
        module.create_app(str(db), {'SECRET_KEY': 'test-only-secret-key-32-characters-long'})
    assert db.read_bytes() == before
    app = raw_client.application
    assert app.config['SESSION_COOKIE_HTTPONLY']
    assert app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'
    assert module.create_app(app.config['DATABASE'], {'SECRET_KEY': 'test-only-secret-key-32-characters-long'}).config['SESSION_COOKIE_SECURE']


def test_revoked_cookie_and_password_event(raw_client):
    from database import revoke_user_sessions
    c = AuthenticatedClient(raw_client)
    creds = {'username': 'alice', 'password': 'alice-password-123'}
    c.post('/api/auth/register', json=creds)
    c.post('/api/auth/login', json=creds)
    token = raw_client.get('/api/auth/csrf').get_json()['csrf_token']
    cookie_name = raw_client.application.config['SESSION_COOKIE_NAME']
    copied = raw_client.get_cookie(cookie_name).value
    stolen = raw_client.application.test_client()
    stolen.set_cookie(cookie_name, copied)
    other = AuthenticatedClient(raw_client.application.test_client())
    assert other.post('/api/auth/login', json=creds).status_code == 200
    assert stolen.get('/api/auth/me').status_code == 200
    assert c.post('/api/auth/logout').status_code == 200
    assert other.get('/api/auth/me').status_code == 200
    assert stolen.get('/api/auth/me').status_code == 401
    assert stolen.post('/api/transactions', json={'type': 'income', 'amount': 1, 'date': '2026-11-20'},
                       headers={'X-CSRF-Token': token}).status_code == 401
    c.post('/api/auth/login', json=creds)
    user_id = c.get('/api/auth/me').get_json()['id']
    revoke_user_sessions(raw_client.application.config['DATABASE'], user_id)
    assert c.get('/api/auth/me').status_code == 401
    assert other.get('/api/auth/me').status_code == 401


def test_login_rate_limit_is_atomic_and_temporary(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from database import migrate_database, migrate_security_v2, reserve_login_attempt
    db = tmp_path / 'rate.db'
    migrate_database(db)
    migrate_security_v2(db)
    def attempt(i):
        return reserve_login_attempt(db, 'ip' + str(i), 'target', 1000, 60, 30, 5)
    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(attempt, range(20)))
    assert results.count(0) == 5
    assert results.count(60) == 15
    assert reserve_login_attempt(db, 'fresh-ip', 'target', 1060, 60, 30, 5) == 0


def test_login_rate_limit_and_untrusted_forwarded_for(raw_client):
    app = raw_client.application
    app.config.update(LOGIN_IP_LIMIT=2, LOGIN_USER_LIMIT=50)
    c = AuthenticatedClient(raw_client)
    for number in range(2):
        response = c.post('/api/auth/login', json={'username': 'user' + str(number), 'password': 'bad'},
                          headers={'X-Forwarded-For': '203.0.113.' + str(number + 1)})
        assert response.status_code == 401
    response = c.post('/api/auth/login', json={'username': 'user3', 'password': 'bad'},
                      headers={'X-Forwarded-For': '203.0.113.3'})
    assert response.status_code == 429
    assert 1 <= int(response.headers['Retry-After']) <= 60


def test_login_and_session_storage_fail_closed(raw_client, monkeypatch):
    module = sys.modules['app']
    c = AuthenticatedClient(raw_client)
    creds = {'username': 'alice', 'password': 'alice-password-123'}
    c.post('/api/auth/register', json=creds)
    def unavailable(*args, **kwargs):
        raise sqlite3.OperationalError('unavailable')
    with monkeypatch.context() as m:
        m.setattr(module, 'reserve_login_attempt', unavailable)
        assert c.post('/api/auth/login', json=creds).status_code == 503
    assert c.post('/api/auth/login', json=creds).status_code == 200
    csrf = raw_client.get('/api/auth/csrf').get_json()['csrf_token']
    with monkeypatch.context() as m:
        m.setattr(module, 'get_session_user', unavailable)
        assert raw_client.get('/api/transactions').status_code == 503
        assert raw_client.post('/api/transactions', json={}, headers={'X-CSRF-Token': csrf}).status_code == 503
        assert raw_client.post('/api/auth/logout', headers={'X-CSRF-Token': csrf}).status_code == 503


def test_security_configuration_and_migration_v2(tmp_path, raw_client):
    from database import migrate_database, migrate_security_v2
    module = sys.modules['app']
    app = raw_client.application
    for key in ('x' * 32, 'too-short', None):
        with pytest.raises(RuntimeError, match='SECRET_KEY'):
            module.create_app(app.config['DATABASE'], {'SECRET_KEY': key})
    with pytest.raises(RuntimeError, match='TRUSTED_PROXY_HOPS'):
        module.create_app(app.config['DATABASE'], {'SECRET_KEY': 'test-only-secret-key-32-characters-long',
                                                   'TRUSTED_PROXY_HOPS': -1})
    db = tmp_path / 'old.db'
    migrate_database(db)
    with sqlite3.connect(db) as con:
        con.execute("INSERT INTO transactions (type, amount, date) VALUES ('income', 99, '2026-11-20')")
    migrate_security_v2(db)
    migrate_security_v2(db)
    with sqlite3.connect(db) as con:
        assert con.execute('PRAGMA user_version').fetchone()[0] == 2
        assert con.execute('SELECT amount, user_id FROM transactions').fetchall() == [(99, None)]
        assert con.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'


def test_explicit_trusted_proxy_changes_limit_key(raw_client):
    module = sys.modules['app']
    app = module.create_app(raw_client.application.config['DATABASE'], {
        'SECRET_KEY': 'test-only-secret-key-32-characters-long', 'TESTING': True,
        'SESSION_COOKIE_SECURE': False, 'TRUSTED_PROXY_HOPS': 1,
        'LOGIN_IP_LIMIT': 1, 'LOGIN_USER_LIMIT': 50,
    })
    c = AuthenticatedClient(app.test_client())
    def login(ip, name):
        return c.post('/api/auth/login', json={'username': name, 'password': 'wrong'},
                      headers={'X-Forwarded-For': ip})
    assert login('203.0.113.1', 'user1').status_code == 401
    assert login('203.0.113.2', 'user2').status_code == 401
    assert login('203.0.113.1', 'user3').status_code == 429


def test_server_session_expiry(raw_client):
    client = AuthenticatedClient(raw_client)
    creds = {'username': 'alice', 'password': 'alice-password-123'}
    client.post('/api/auth/register', json=creds)
    client.post('/api/auth/login', json=creds)
    assert client.get('/api/auth/me').status_code == 200
    with sqlite3.connect(raw_client.application.config['DATABASE']) as con:
        con.execute('UPDATE auth_sessions SET expires_at = 0')
    assert client.get('/api/auth/me').status_code == 401


def test_security_migration_rolls_back_and_requires_existing_file(tmp_path):
    from database import migrate_database, migrate_security_v2
    db = tmp_path / 'rollback.db'
    migrate_database(db)
    with sqlite3.connect(db) as con:
        con.execute('CREATE TABLE login_attempts (unexpected TEXT)')
    with pytest.raises(sqlite3.OperationalError):
        migrate_security_v2(db)
    with sqlite3.connect(db) as con:
        assert con.execute('PRAGMA user_version').fetchone()[0] == 1
        assert con.execute("SELECT name FROM sqlite_master WHERE name='auth_sessions'").fetchone() is None
    missing = tmp_path / 'missing.db'
    with pytest.raises(sqlite3.OperationalError):
        migrate_security_v2(missing)
    assert not missing.exists()


def test_frontend_pages_and_static_assets(raw_client):
    for page in ('/dashboard', '/login', '/register'):
        response = raw_client.get(page)
        assert response.status_code == 200
        assert b'/static/style.css' in response.data
        assert b'/static/script.js' in response.data
    assert raw_client.get('/static/script.js').status_code == 200
    assert raw_client.get('/').get_json() == {'message': 'Financial Tracker API is running'}


def test_frontend_contract_exact_integer_and_safe_text(client):
    hostile = '<img src=x onerror=alert(1)>'
    amount = 9223372036854775807
    response = client.post('/api/transactions', json={'type': 'income', 'amount': amount,
                            'category': hostile, 'date': '2026-11-20'})
    assert response.status_code == 201
    data = client.get('/api/transactions').get_json()
    assert data[0]['category'] == hostile and data[0]['amount'] == amount
    assert client.get('/api/balance').get_json()['balance'] == amount


def test_redesign_dashboard_exposes_real_data_controls(raw_client):
    page = raw_client.get('/dashboard').get_data(as_text=True)
    for element_id in ('search-input', 'period-select', 'chart', 'donut', 'category-breakdown',
                       'transaction-list', 'transaction-dialog', 'logout'):
        assert f'id="{element_id}"' in page
    assert all(f'value="{period}"' in page for period in ('week', 'month', 'year', 'all'))
    assert '245 000' not in page and '12,5%' not in page
    assert 'Upgrade to Pro' not in page


def test_redesign_data_contract_preserves_negative_large_balance(client):
    maximum = 9223372036854775807
    hostile = '<img src=x onerror=alert(1)>'
    response = client.post('/api/transactions', json={'type': 'expense', 'amount': maximum,
                            'category': hostile, 'description': 'search me', 'date': '2026-01-10'})
    assert response.status_code == 201
    assert client.get('/api/balance').get_json()['balance'] == -maximum
    entry = client.get('/api/transactions').get_json()[0]
    assert entry['category'] == hostile and entry['description'] == 'search me'


def test_password_toggle_available_and_hidden_on_auth_pages(raw_client):
    for path in ('/login', '/register'):
        html = raw_client.get(path).get_data(as_text=True)
        assert 'id="password" name="password" type="password"' in html
        assert 'id="toggle-password"' in html and 'aria-controls="password"' in html
        assert 'aria-pressed="false"' in html


def test_dashboard_transaction_entry_controls(raw_client):
    html = raw_client.get('/dashboard').get_data(as_text=True)
    assert 'id="primary-income"' in html and 'id="primary-expense"' in html
    assert 'list="category-suggestions"' in html and '<datalist id="category-suggestions">' in html
    assert 'name="amount" inputmode="numeric"' in html


def test_goals_lifecycle_and_reserve_invariants(client):
    data = {'type': 'income', 'amount': 100, 'date': '2026-11-20'}
    client.post('/api/transactions', json=data)
    response = client.post('/api/goals', json={'title':'Laptop', 'target_amount':80, 'deadline':'2020-01-01'})
    assert response.status_code == 201
    goal = response.get_json(); goal_id = goal['id']; assert goal['saved_amount'] == 0
    url = f'/api/goals/{goal_id}'
    assert client.post(url + '/deposit', json={'amount':80}).status_code == 200
    assert client.get('/api/goals/summary').get_json() == {'total_balance':100,'reserved_savings':80,'available_balance':20}
    assert client.get('/api/balance').get_json()['balance'] == 100
    assert len(client.get('/api/transactions').get_json()) == 1
    assert client.post('/api/transactions',json={**data,'type':'expense','amount':21}).get_json()['code'] == 'reserved_funds_conflict'
    assert client.delete('/api/transactions/1').status_code == 409
    assert client.put('/api/transactions/1',json={**data,'amount':79}).status_code == 409
    assert client.put(url,json={'title':'Laptop','target_amount':79}).get_json()['code'] == 'target_below_saved'
    assert client.post(url+'/withdraw',json={'amount':81}).get_json()['code'] == 'insufficient_goal_funds'
    assert client.post(url+'/withdraw',json={'amount':80}).status_code == 200
    assert client.post('/api/transactions',json={**data,'type':'expense','amount':110}).status_code == 201
    assert client.get('/api/goals/summary').get_json()['available_balance'] == -10
    assert client.post(url+'/deposit',json={'amount':1}).get_json()['code'] == 'insufficient_available'
    assert client.delete(url).status_code == 204


def test_goal_delete_releases_and_target_limit(client):
    client.post('/api/transactions',json={'type':'income','amount':100,'date':'2026-11-20'})
    gid=client.post('/api/goals',json={'title':'A','target_amount':20}).get_json()['id']
    assert client.post(f'/api/goals/{gid}/deposit',json={'amount':21}).get_json()['code'] == 'exceeds_goal_target'
    client.post(f'/api/goals/{gid}/deposit',json={'amount':20})
    assert client.delete(f'/api/goals/{gid}').status_code == 204
    assert client.get('/api/goals/summary').get_json()['available_balance'] == 100


@pytest.mark.parametrize('goal', [None, [], {}, {'title':' ','target_amount':1}, {'title':'x','target_amount':True}, {'title':'x','target_amount':2**63}, {'title':'x','target_amount':1,'deadline':'2026-02-30'}, {'title':'x','target_amount':1,'saved_amount':1}, {'title':'x','target_amount':1,'user_id':2}])
def test_goal_invalid(client, goal):
    response = client.post('/api/goals', data='null', content_type='application/json') if goal is None else client.post('/api/goals', json=goal)
    assert response.status_code == 400


def test_goals_auth_csrf_and_ownership(raw_client):
    app=raw_client.application; alice=AuthenticatedClient(raw_client); bob=AuthenticatedClient(app.test_client())
    assert raw_client.get('/api/goals').status_code == 401
    for c,name in ((alice,'alice'),(bob,'bobby')):
        creds={'username':name,'password':'password-long-enough'}; c.post('/api/auth/register',json=creds); c.post('/api/auth/login',json=creds)
    gid=alice.post('/api/goals',json={'title':'Private','target_amount':1}).get_json()['id']
    assert raw_client.post('/api/goals',json={'title':'x','target_amount':1}).status_code == 403
    assert bob.get('/api/goals').get_json() == []
    assert bob.put(f'/api/goals/{gid}',json={'title':'x','target_amount':1}).status_code == 404
    assert bob.delete(f'/api/goals/{gid}').status_code == 404
    assert bob.post(f'/api/goals/{gid}/withdraw',json={'amount':1}).status_code == 404


def test_concurrent_goal_deposits_and_transaction_are_atomic(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from database import migrate_database,migrate_security_v2,migrate_goals_v3,create_user,add_transaction,create_goal,move_goal_funds,FinancialConflict,goal_summary
    db=tmp_path/'race.db'; migrate_database(db); migrate_security_v2(db); migrate_goals_v3(db)
    create_user('alice','hash',db); add_transaction(1,'income',100,None,None,'2026-01-01',db)
    first=create_goal(db,1,'A',100,None,'2026-01-01'); second=create_goal(db,1,'B',100,None,'2026-01-01')
    def deposit(gid):
        try: move_goal_funds(db,1,gid,70,True); return 'ok'
        except FinancialConflict: return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(deposit,[first['id'],second['id']]))
    assert sorted(results)==['conflict','ok']
    assert goal_summary(db,1)=={'total_balance':100,'reserved_savings':70,'available_balance':30}
    def competing(kind):
        try:
            if kind=='deposit': move_goal_funds(db,1,second['id'] if results[1]=='conflict' else first['id'],25,True)
            else: add_transaction(1,'expense',25,None,None,'2026-01-01',db)
            return 'ok'
        except FinancialConflict: return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool: outcomes=list(pool.map(competing,['deposit','expense']))
    assert sorted(outcomes)==['conflict','ok']
    state=goal_summary(db,1); assert state['available_balance']>=0


def test_v3_migration_preserves_and_rolls_back(tmp_path):
    from database import migrate_database,migrate_security_v2,migrate_goals_v3
    db=tmp_path/'old.db'; migrate_database(db); migrate_security_v2(db)
    with sqlite3.connect(db) as c:
        c.execute("INSERT INTO users (username,password_hash) VALUES ('alice','hash')")
        c.execute("INSERT INTO transactions (type,amount,date,user_id) VALUES ('income',42,'2026-01-01',1)")
    migrate_goals_v3(db); migrate_goals_v3(db)
    with sqlite3.connect(db) as c:
        assert c.execute('PRAGMA user_version').fetchone()[0]==3
        assert c.execute('SELECT amount,user_id FROM transactions').fetchall()==[(42,1)]
        assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    bad=tmp_path/'bad.db'; migrate_database(bad); migrate_security_v2(bad)
    with sqlite3.connect(bad) as c: c.execute('CREATE INDEX idx_goals_user_id ON transactions(user_id)')
    with pytest.raises(sqlite3.Error): migrate_goals_v3(bad)
    with sqlite3.connect(bad) as c:
        assert c.execute('PRAGMA user_version').fetchone()[0]==2
        assert c.execute("SELECT name FROM sqlite_master WHERE name='goals'").fetchone() is None


def test_goal_large_amount_and_total_over_sqlite_integer(client):
    maximum=2**63-1
    income={'type':'income','amount':maximum,'date':'2026-01-01'}
    assert client.post('/api/transactions',json=income).status_code==201
    assert client.post('/api/transactions',json=income).status_code==201
    goal=client.post('/api/goals',json={'title':'Large','target_amount':maximum}).get_json()
    assert client.post(f"/api/goals/{goal['id']}/deposit",json={'amount':maximum}).status_code==200
    assert client.get('/api/goals/summary').get_json()=={'total_balance':maximum*2,'reserved_savings':maximum,'available_balance':maximum}


def test_claim_legacy_cannot_break_reservation(tmp_path):
    from database import migrate_database,migrate_security_v2,migrate_goals_v3,add_transaction,create_goal,move_goal_funds,FinancialConflict
    from claim_legacy import claim_unassigned
    db=tmp_path/'claim.db'; migrate_database(db); migrate_security_v2(db); migrate_goals_v3(db)
    with sqlite3.connect(db) as c:
        c.execute("INSERT INTO users (username,password_hash) VALUES ('alice','hash')")
        c.execute("INSERT INTO transactions (type,amount,date) VALUES ('expense',30,'2026-01-01')")
    add_transaction(1,'income',100,None,None,'2026-01-01',db)
    gid=create_goal(db,1,'A',90,None,'2026-01-01')['id'];move_goal_funds(db,1,gid,90,True)
    with pytest.raises(FinancialConflict): claim_unassigned(db,1,1)
    with sqlite3.connect(db) as c:
        assert c.execute('SELECT user_id FROM transactions WHERE type = ?',('expense',)).fetchone()[0] is None


def test_locked_database_returns_503_without_writes(client, raw_client):
    db=raw_client.application.config['DATABASE']
    lock=sqlite3.connect(db);lock.execute('BEGIN IMMEDIATE')
    try:
        response=client.post('/api/goals',json={'title':'Locked','target_amount':1})
        assert response.status_code==503
    finally:
        lock.rollback();lock.close()
    assert client.get('/api/goals').get_json()==[]


def test_goal_ui_elements(raw_client):
    html=raw_client.get('/dashboard').get_data(as_text=True)
    for field in ('goal-add','goal-list','goal-form','transfer-form','reserved-value','available-value'):
        assert f'id="{field}"' in html


def test_goal_transfer_invalid_amounts_and_unknown_ids(client):
    gid=client.post('/api/goals',json={'title':'Target','target_amount':1}).get_json()['id']
    for value in (0,-1,True,1.5,2**63,'1'):
        response=client.post(f'/api/goals/{gid}/deposit',json={'amount':value})
        assert response.status_code==400 and response.get_json()['code']=='invalid_amount'
    assert client.delete(f'/api/goals/{2**63}').status_code==404
    assert client.post(f'/api/goals/{2**63}/deposit',json={'amount':1}).status_code==404


def test_goal_invalid_body_cannot_change_saved_amount(client):
    gid=client.post('/api/goals',json={'title':'Target','target_amount':10}).get_json()['id']
    response=client.put(f'/api/goals/{gid}',json={'title':'Target','target_amount':10,'saved_amount':8})
    assert response.status_code==400
    assert client.get('/api/goals').get_json()[0]['saved_amount']==0
