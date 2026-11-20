import hmac
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta

from flask import Flask, current_app, g, request, session
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge, UnsupportedMediaType
from werkzeug.security import check_password_hash, generate_password_hash

from database import (add_transaction, check_database, create_user, database_path,
                      delete_transaction, find_user, get_balance, get_transactions,
                      get_user, update_transaction)

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
                      PERMANENT_SESSION_LIFETIME=timedelta(hours=12))
    if config:
        app.config.update(config)
    if not isinstance(app.config['SECRET_KEY'], str) or len(app.config['SECRET_KEY']) < 32:
        raise RuntimeError('Set FINANCIAL_SECRET_KEY to a random secret of at least 32 characters')
    check_database(app.config['DATABASE'])

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
        return {'error': 'Database error'}, 500

    @app.before_request
    def protect_requests():
        g.user = None
        user_id = session.get('user_id')
        if type(user_id) is int and 0 < user_id <= MAX_AMOUNT:
            g.user = get_user(user_id, current_app.config['DATABASE'])
        if request.path.startswith('/api/transactions') or request.path == '/api/balance' or request.path == '/api/auth/me':
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
        user = find_user(username, current_app.config['DATABASE'])
        valid = check_password_hash(user['password_hash'] if user else DUMMY_HASH, password)
        if not user or not valid:
            return {'error': 'Invalid username or password'}, 401
        session.clear()
        session['user_id'] = user['id']
        session.permanent = True
        return {'message': 'Logged in'}

    @app.post('/api/auth/logout')
    def logout():
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

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=False)
