from app.database import get_connection
from app.schemas import AccountResponse, CustomerResponse, TransactionResponse
from fastapi import FastAPI

app = FastAPI(
    title="Revolut Business Fintech API",
    description="Independent simulated fintech API developed by SkynetAI-Labs.",
    version="0.1.0",
)


@app.get("/")
def home():
    return {
        "project": "Revolut Business Fintech Security & GTM",
        "developer": "SkynetAI-Labs",
        "status": "running",
        "type": "Independent portfolio simulation",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/customers", response_model=list[CustomerResponse])
def list_customers():
    connection = get_connection()
    try:
        rows = connection.execute(
            "SELECT id, business_name, email FROM customers ORDER BY id"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


@app.get("/accounts", response_model=list[AccountResponse])
def list_accounts():
    connection = get_connection()
    try:
        rows = connection.execute(
            "SELECT id, customer_id, currency, balance_pence "
            "FROM accounts ORDER BY id"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


@app.get("/transactions", response_model=list[TransactionResponse])
def list_transactions():
    connection = get_connection()
    try:
        rows = connection.execute(
            "SELECT id, from_account_id, to_account_id, "
            "amount_pence, created_at "
            "FROM transactions ORDER BY id DESC"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()
