from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.main import app

client = TestClient(app)


def test_home():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_customers_unauthenticated():
    response = client.get("/customers")
    assert response.status_code == 401


def test_accounts_unauthenticated():
    response = client.get("/accounts")
    assert response.status_code == 401


def test_transactions_unauthenticated():
    response = client.get("/transactions")
    assert response.status_code == 401


def test_authenticated_banking_endpoints():
    token = create_access_token(1)
    headers = {"Authorization": f"Bearer {token}"}

    for endpoint in ("/customers", "/accounts", "/transactions"):
        response = client.get(endpoint, headers=headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


def test_nonexistent_user_rejected():
    token = create_access_token(999999)
    headers = {"Authorization": f"Bearer {token}"}

    for endpoint in ("/customers", "/accounts", "/transactions"):
        response = client.get(endpoint, headers=headers)
        assert response.status_code == 401


import sqlite3
from datetime import datetime, timedelta, timezone

import jwt
import pytest

import app.dependencies as dependencies
import app.main as main
import app.models as models
from app.config import JWT_SECRET_KEY, JWT_ALGORITHM


@pytest.fixture(autouse=True)
def isolated_api_db(tmp_path, monkeypatch):
    db_path = tmp_path / "api_test.db"

    def connect():
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    monkeypatch.setattr(models, "get_connection", connect)
    monkeypatch.setattr(main, "get_connection", connect)
    monkeypatch.setattr(dependencies, "get_connection", connect)
    models.create_tables()

    connection = connect()
    try:
        connection.execute(
            "INSERT INTO customers (id, business_name, email) VALUES (?, ?, ?)",
            (1, "Test Business", "business@example.com"),
        )
        connection.execute(
            "INSERT INTO users "
            "(id, customer_id, email, password_hash, role) "
            "VALUES (?, ?, ?, ?, ?)",
            (1, 1, "user@example.com", "unused-in-token-tests", "user"),
        )
        connection.commit()
    finally:
        connection.close()

    main.limiter._storage.reset()
    yield
    main.limiter._storage.reset()


@pytest.mark.parametrize("case", ["missing_expiry", "expired", "tampered"])
def test_invalid_tokens_rejected_by_api(case):
    payload = {"sub": "1"}
    if case != "missing_expiry":
        payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=5)
    if case == "expired":
        payload["exp"] = datetime.now(timezone.utc) - timedelta(minutes=5)

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    if case == "tampered":
        parts = token.split(".")
        parts[2] = ("A" if parts[2][0] != "A" else "B") + parts[2][1:]
        token = ".".join(parts)

    for endpoint in ("/customers", "/accounts", "/transactions"):
        response = client.get(
            endpoint,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
