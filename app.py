import sqlite3
from datetime import datetime

from flask import Flask, current_app, request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge, UnsupportedMediaType

from database import add_transaction, create_database, database_path, get_balance, get_transactions

MAX_AMOUNT = 2**63 - 1
MAX_CATEGORY_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 1000


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
        data = request.get_json()
        if not isinstance(data, dict):
            return {'error': 'JSON object required'}, 400

        transaction_type = data.get('type')
        if transaction_type not in ('expense', 'income'):
            return {'error': 'Invalid transaction type'}, 400

        amount = data.get('amount')
        if type(amount) is not int or not 0 < amount <= MAX_AMOUNT:
            return {'error': 'Invalid amount'}, 400

        category = data.get('category')
        if category is not None and (not isinstance(category, str) or len(category) > MAX_CATEGORY_LENGTH):
            return {'error': 'Invalid category'}, 400

        description = data.get('description')
        if description is not None and (not isinstance(description, str) or len(description) > MAX_DESCRIPTION_LENGTH):
            return {'error': 'Invalid description'}, 400

        date = data.get('date')
        if not isinstance(date, str):
            return {'error': 'Invalid date'}, 400
        try:
            date = datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')
        except ValueError:
            return {'error': 'Invalid date'}, 400

        add_transaction(transaction_type, amount, category, description, date,
                        current_app.config['DATABASE'])
        return {'message': 'Transaction created'}, 201

    @app.route('/api/balance', methods=['GET'])
    def balance():
        return get_balance(current_app.config['DATABASE'])

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=False)
