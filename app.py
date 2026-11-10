from database import create_database, add_transaction, get_transactions
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return {"message": "Financial Tracker API is running"}

if __name__ == "__main__":
    create_database()
    app.run(debug=True)
