import hmac
import hashlib
import ipaddress
import os
import re
import secrets
import sqlite3
import time
from datetime import datetime, timedelta, timezone

from flask import Flask, current_app, g, request, session, render_template
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge, UnsupportedMediaType
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix

from database import (add_transaction, check_database, create_user, database_path,
                      delete_transaction, find_user, get_balance, get_transactions,
                      get_session_user, update_transaction, create_session,
                      reserve_login_attempt, revoke_session, FinancialConflict,
                      list_goals, goal_summary, create_goal, change_goal, remove_goal,
                      move_goal_funds)

MAX_AMOUNT = 2**63 - 1
MAX_CATEGORY_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 1000
USERNAME_PATTERN = re.compile(r'^[a-z0-9_]{3,32}$')
DUMMY_HASH = generate_password_hash('not-a-real-account-password', method='scrypt')


def validate_transaction(data):
    if not isinstance(data, dict):
        return None, 'JSON object required'
    if 'user_id' in data:
        return None, 'user_id is not accepted'
    transaction_type = data.get('type')
    if transaction_type not in ('expense', 'income'):
        return None, 'Invalid transaction type'
    amount = data.get('amount')
    if type(amount) is not int or not 0 < amount <= MAX_AMOUNT:
        return None, 'Invalid amount'
    category = data.get('category')
    if category is not None and (not isinstance(category, str) or len(category) > MAX_CATEGORY_LENGTH):
        return None, 'Invalid category'
    description = data.get('description')
    if description is not None and (not isinstance(description, str) or len(description) > MAX_DESCRIPTION_LENGTH):
        return None, 'Invalid description'
    date = data.get('date')
    if not isinstance(date, str):
        return None, 'Invalid date'
    try:
        date = datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')
    except ValueError:
        return None, 'Invalid date'
    return (transaction_type, amount, category, description, date), None


def credentials(data, registration=False):
    if not isinstance(data, dict):
        return None
    username, password = data.get('username'), data.get('password')
    if not isinstance(username, str) or not isinstance(password, str):
        return None
    username = username.strip().lower()
    if not USERNAME_PATTERN.fullmatch(username) or len(password) > 256 or (registration and len(password) < 12):
        return None
    return username, password


def create_app(database=None, config=None):
    app = Flask(__name__)
    app.config.update(DATABASE=database_path(database), SECRET_KEY=os.environ.get('FINANCIAL_SECRET_KEY'),
                      MAX_CONTENT_LENGTH=16 * 1024, SESSION_COOKIE_HTTPONLY=True,
                      SESSION_COOKIE_SECURE=True, SESSION_COOKIE_SAMESITE='Lax',
                      PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
                      TRUSTED_PROXY_HOPS=int(os.environ.get('FINANCIAL_TRUSTED_PROXY_HOPS', '0')),
                      LOGIN_WINDOW=60, LOGIN_IP_LIMIT=30, LOGIN_USER_LIMIT=5)
    if config:
        app.config.update(config)
    key = app.config['SECRET_KEY']
    if not isinstance(key, str) or len(key) < 32 or len(set(key)) < 8:
        raise RuntimeError('Set FINANCIAL_SECRET_KEY to a random secret of at least 32 characters')
    hops = app.config['TRUSTED_PROXY_HOPS']
    if type(hops) is not int or not 0 <= hops <= 10:
        raise RuntimeError('TRUSTED_PROXY_HOPS must be an integer between 0 and 10')
    for setting in ('LOGIN_WINDOW', 'LOGIN_IP_LIMIT', 'LOGIN_USER_LIMIT'):
        if type(app.config[setting]) is not int or app.config[setting] < 1:
            raise RuntimeError(f'{setting} must be a positive integer')
    if hops:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops)
    check_database(app.config['DATABASE'])

    def keyed_hash(value):
        return hmac.new(app.config['SECRET_KEY'].encode('utf-8'), value.encode('utf-8'), hashlib.sha256).hexdigest()

    def token_hash(value):
        return hashlib.sha256(value.encode('utf-8')).hexdigest()

    @app.errorhandler(BadRequest)
    def bad_request(error):
        return {'error': 'Invalid JSON'}, 400

    @app.errorhandler(UnsupportedMediaType)
    def unsupported_media_type(error):
        return {'error': 'Content-Type must be application/json'}, 415

    @app.errorhandler(RequestEntityTooLarge)
    def request_too_large(error):
        return {'error': 'Request body too large'}, 413

    @app.errorhandler(sqlite3.Error)
    def database_error(error):
        current_app.logger.exception('Database operation failed')
        return {'error': 'Database error'}, 503

    @app.errorhandler(FinancialConflict)
    def financial_conflict(error):
        return {'error': error.code, 'code': error.code}, 409

    @app.before_request
    def protect_requests():
        g.user = None
        sid = session.get('session_id')
        if isinstance(sid, str) and len(sid) <= 128:
            g.user = get_session_user(current_app.config['DATABASE'], token_hash(sid), int(time.time()))
        if request.path.startswith(('/api/transactions', '/api/goals')) or request.path == '/api/balance' or request.path == '/api/auth/me':
            if g.user is None:
                return {'error': 'Authentication required'}, 401
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            token = session.get('csrf_token')
            supplied = request.headers.get('X-CSRF-Token', '')
            if not isinstance(token, str) or not hmac.compare_digest(token.encode('utf-8'), supplied.encode('utf-8')):
                return {'error': 'Invalid CSRF token'}, 403

    @app.after_request
    def prevent_sensitive_caching(response):
        if request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/')
    def home():
        return {'message': 'Financial Tracker API is running'}

    @app.get('/dashboard')
    def dashboard_page():
        return render_template('index.html')

    @app.get('/login')
    def login_page():
        return render_template('auth.html', mode='login')

    @app.get('/register')
    def register_page():
        return render_template('auth.html', mode='register')

    @app.get('/api/auth/csrf')
    def csrf():
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_urlsafe(32)
        return {'csrf_token': session['csrf_token']}

    @app.post('/api/auth/register')
    def register():
        values = credentials(request.get_json(), registration=True)
        if values is None:
            return {'error': 'Invalid username or password'}, 400
        username, password = values
        try:
            create_user(username, generate_password_hash(password, method='scrypt'), current_app.config['DATABASE'])
        except sqlite3.IntegrityError:
            return {'error': 'Username already exists'}, 409
        return {'message': 'User registered'}, 201

    @app.post('/api/auth/login')
    def login():
        values = credentials(request.get_json())
        if values is None:
            return {'error': 'Invalid username or password'}, 400
        username, password = values
        try:
            client_ip = str(ipaddress.ip_address(request.remote_addr or ''))
        except ValueError:
            return {'error': 'Client address unavailable'}, 503
        retry = reserve_login_attempt(current_app.config['DATABASE'], keyed_hash('ip:' + client_ip),
                                      keyed_hash('user:' + username), int(time.time()),
                                      app.config['LOGIN_WINDOW'], app.config['LOGIN_IP_LIMIT'],
                                      app.config['LOGIN_USER_LIMIT'])
        if retry:
            return {'error': 'Too many login attempts'}, 429, {'Retry-After': str(retry)}
        user = find_user(username, current_app.config['DATABASE'])
        valid = check_password_hash(user['password_hash'] if user else DUMMY_HASH, password)
        if not user or not valid:
            return {'error': 'Invalid username or password'}, 401
        old_sid = session.get('session_id')
        if isinstance(old_sid, str) and len(old_sid) <= 128:
            revoke_session(current_app.config['DATABASE'], token_hash(old_sid))
        sid = secrets.token_urlsafe(32)
        now = int(time.time())
        create_session(current_app.config['DATABASE'], token_hash(sid), user['id'],
                       now + int(app.permanent_session_lifetime.total_seconds()), now)
        session.clear()
        session['session_id'] = sid
        session.permanent = True
        return {'message': 'Logged in'}

    @app.post('/api/auth/logout')
    def logout():
        sid = session.get('session_id')
        if isinstance(sid, str) and len(sid) <= 128:
            revoke_session(current_app.config['DATABASE'], token_hash(sid))
        session.clear()
        return {'message': 'Logged out'}

    @app.get('/api/auth/me')
    def me():
        return {'id': g.user['id'], 'username': g.user['username']}

    @app.get('/api/transactions')
    def transactions():
        return get_transactions(g.user['id'], current_app.config['DATABASE'])

    @app.post('/api/transactions')
    def create_transactions():
        values, error = validate_transaction(request.get_json())
        if error:
            return {'error': error}, 400
        add_transaction(g.user['id'], *values, path=current_app.config['DATABASE'])
        return {'message': 'Transaction created'}, 201

    @app.put('/api/transactions/<int:transaction_id>')
    def replace_transaction(transaction_id):
        values, error = validate_transaction(request.get_json())
        if error:
            return {'error': error}, 400
        if transaction_id > MAX_AMOUNT or not update_transaction(g.user['id'], transaction_id, *values,
                                                                  path=current_app.config['DATABASE']):
            return {'error': 'Transaction not found'}, 404
        return {'message': 'Transaction updated'}, 200

    @app.delete('/api/transactions/<int:transaction_id>')
    def remove_transaction(transaction_id):
        if transaction_id > MAX_AMOUNT or not delete_transaction(g.user['id'], transaction_id,
                                                                  path=current_app.config['DATABASE']):
            return {'error': 'Transaction not found'}, 404
        return '', 204

    @app.get('/api/balance')
    def balance():
        return get_balance(g.user['id'], current_app.config['DATABASE'])

    def goal_fields(data):
        if not isinstance(data, dict) or set(data) - {'title', 'target_amount', 'deadline'}:
            return None
        title, target, deadline = data.get('title'), data.get('target_amount'), data.get('deadline')
        if not isinstance(title, str) or not title.strip() or len(title.strip()) > 100:
            return None
        if type(target) is not int or not 0 < target <= MAX_AMOUNT:
            return None
        if deadline is not None:
            if not isinstance(deadline, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', deadline):
                return None
            try:
                datetime.strptime(deadline, '%Y-%m-%d')
            except ValueError:
                return None
        return title.strip(), target, deadline

    @app.get('/api/goals')
    def goals():
        return list_goals(current_app.config['DATABASE'], g.user['id'])

    @app.get('/api/goals/summary')
    def goals_summary():
        return goal_summary(current_app.config['DATABASE'], g.user['id'])

    @app.post('/api/goals')
    def goals_create():
        values = goal_fields(request.get_json())
        if values is None:
            return {'error': 'Invalid goal data', 'code': 'invalid_goal'}, 400
        return create_goal(current_app.config['DATABASE'], g.user['id'], *values,
                           datetime.now(timezone.utc).isoformat()), 201

    @app.put('/api/goals/<int:goal_id>')
    def goals_update(goal_id):
        values = goal_fields(request.get_json())
        if values is None:
            return {'error': 'Invalid goal data', 'code': 'invalid_goal'}, 400
        goal = None if goal_id > MAX_AMOUNT else change_goal(current_app.config['DATABASE'], g.user['id'], goal_id, *values)
        return goal if goal else ({'error': 'Goal not found', 'code': 'goal_not_found'}, 404)

    @app.delete('/api/goals/<int:goal_id>')
    def goals_delete(goal_id):
        if goal_id > MAX_AMOUNT or not remove_goal(current_app.config['DATABASE'], g.user['id'], goal_id):
            return {'error': 'Goal not found', 'code': 'goal_not_found'}, 404
        return '', 204

    @app.post('/api/goals/<int:goal_id>/<operation>')
    def goals_transfer(goal_id, operation):
        if operation not in ('deposit', 'withdraw'):
            return {'error': 'Not found', 'code': 'not_found'}, 404
        data = request.get_json()
        if not isinstance(data, dict) or set(data) != {'amount'} or type(data['amount']) is not int or not 0 < data['amount'] <= MAX_AMOUNT:
            return {'error': 'Invalid amount', 'code': 'invalid_amount'}, 400
        result = None if goal_id > MAX_AMOUNT else move_goal_funds(current_app.config['DATABASE'], g.user['id'], goal_id, data['amount'], operation == 'deposit')
        return result if result else ({'error': 'Goal not found', 'code': 'goal_not_found'}, 404)

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=False)
