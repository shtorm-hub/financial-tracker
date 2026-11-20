import sqlite3
from datetime import datetime

from flask import Flask, current_app, request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge, UnsupportedMediaType

from database import (add_transaction, create_database, database_path, delete_transaction,
                      get_balance, get_transactions, update_transaction)

MAX_AMOUNT = 2**63 - 1
MAX_CATEGORY_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 1000


def validate_transaction(data):
    if not isinstance(data, dict):
        return None, 'JSON object required'
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


def create_app(database=None):
    app = Flask(__name__)
    app.config['DATABASE'] = database_path(database)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024
    create_database(app.config['DATABASE'])

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

    @app.route('/')
    def home():
        return {'message': 'Financial Tracker API is running'}

    @app.route('/api/transactions', methods=['GET'])
    def transactions():
        return get_transactions(current_app.config['DATABASE'])

    @app.route('/api/transactions', methods=['POST'])
    def create_transactions():
        values, error = validate_transaction(request.get_json())
        if error:
            return {'error': error}, 400
        add_transaction(*values, path=current_app.config['DATABASE'])
        return {'message': 'Transaction created'}, 201

    @app.route('/api/transactions/<int:transaction_id>', methods=['PUT'])
    def replace_transaction(transaction_id):
        values, error = validate_transaction(request.get_json())
        if error:
            return {'error': error}, 400
        if transaction_id > MAX_AMOUNT or not update_transaction(
                transaction_id, *values, path=current_app.config['DATABASE']):
            return {'error': 'Transaction not found'}, 404
        return {'message': 'Transaction updated'}, 200

    @app.route('/api/transactions/<int:transaction_id>', methods=['DELETE'])
    def remove_transaction(transaction_id):
        if transaction_id > MAX_AMOUNT or not delete_transaction(
                transaction_id, path=current_app.config['DATABASE']):
            return {'error': 'Transaction not found'}, 404
        return '', 204

    @app.route('/api/balance', methods=['GET'])
    def balance():
        return get_balance(current_app.config['DATABASE'])

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=False)
