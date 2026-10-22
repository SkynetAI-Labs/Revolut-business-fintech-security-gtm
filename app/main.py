from app.monitoring_routes import router as monitoring_router
from app.database import get_connection
from app.security_headers import SecurityHeadersMiddleware
from app.schemas import AccountResponse, CustomerResponse, TransactionResponse
from fastapi import FastAPI, Depends, Request
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from app.dependencies import get_current_user_id, get_current_customer_id, require_admin

from app.rate_limiting import limiter

app = FastAPI(
    title="Revolut Business Fintech API",
    description="Independent simulated fintech API developed by SkynetAI-Labs.",
    version="0.1.0",
)


@app.get("/")
@limiter.limit("60/minute")
def home(request: Request):
    return {
        "project": "Revolut Business Fintech Security & GTM",
        "developer": "SkynetAI-Labs",
        "status": "running",
        "type": "Independent portfolio simulation",
    }


@app.get("/health")
@limiter.limit("60/minute")
def health(request: Request):
    return {"status": "healthy"}


@app.get("/customers", response_model=list[CustomerResponse])
@limiter.limit("30/minute")
def list_customers(
    request: Request,
    customer_id: int = Depends(get_current_customer_id),
):
    connection = get_connection()
    try:
        rows = connection.execute(
            "SELECT id, business_name, email "
            "FROM customers WHERE id = ?",
            (customer_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


@app.get("/accounts", response_model=list[AccountResponse])
@limiter.limit("30/minute")
def list_accounts(
    request: Request,
    customer_id: int = Depends(get_current_customer_id),
):
    connection = get_connection()
    try:
        rows = connection.execute(
            "SELECT id, customer_id, currency, balance_pence "
            "FROM accounts WHERE customer_id = ? ORDER BY id",
            (customer_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


@app.get("/transactions", response_model=list[TransactionResponse])
@limiter.limit("20/minute")
def list_transactions(
    request: Request,
    customer_id: int = Depends(get_current_customer_id),
):
    connection = get_connection()
    try:
        rows = connection.execute(
            "SELECT t.id, t.from_account_id, t.to_account_id, "
            "t.amount_pence, t.created_at "
            "FROM transactions AS t "
            "WHERE EXISTS ("
            "SELECT 1 FROM accounts AS a "
            "WHERE a.id = t.from_account_id AND a.customer_id = ?"
            ") OR EXISTS ("
            "SELECT 1 FROM accounts AS a "
            "WHERE a.id = t.to_account_id AND a.customer_id = ?"
            ") ORDER BY t.id DESC",
            (customer_id, customer_id),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


@app.get("/admin/security-status")
@limiter.limit("10/minute")
def admin_security_status(
    request: Request,
    user_id: int = Depends(require_admin),
):
    return {
        "status": "secure",
        "access": "administrator",
        "authenticated_user_id": user_id,
        "environment": "portfolio-simulation",
    }

app.include_router(monitoring_router)

app.add_middleware(SecurityHeadersMiddleware)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
