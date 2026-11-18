from database import create_database, add_transaction, get_transactions
from flask import Flask, request
from datetime import datetime

app = Flask(__name__)

@app.route("/")
def home():
    return {"message": "Financial Tracker API is running"}


@app.route("/api/transactions", methods=["GET"])
def transactions():
    db_transactions = get_transactions()
    return db_transactions


@app.route("/api/transactions", methods=["POST"])
def create_transactions():
    data = request.get_json()

    if not isinstance(data, dict):
        return {"error": "JSON object required"}, 400

    transaction_type = data.get("type")
    if transaction_type not in ("expense", "income"):
        return {"error": "Invalid transaction type"}, 400

    amount = data.get("amount")
    if type(amount) is not int or amount <= 0:
        return {"error": "Invalid amount"}, 400
    
    category = data.get("category")
    if not isinstance(category, (str, type(None))):
        return {"error": "Invalid category"}, 400

    description = data.get("description")
    if not isinstance(description, (str, type(None))):
        return {"error": "Invalid description"}, 400
    
    date = data.get("date")
    if not isinstance(date, str):
        return {"error": "Invalid date"}, 400

    try:
        formatted_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return {"error": "Invalid date"}, 400

    date = formatted_date.strftime("%Y-%m-%d")

    add_transaction(
        transaction_type, amount, category, description, date
        )

    return {"message": "Transaction created"}, 201


if __name__ == "__main__":
    create_database()
    app.run(debug=True)
