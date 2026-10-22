import sqlite3

import pytest
from fastapi.testclient import TestClient

import app.dependencies as dependencies
import app.main as main
from app.auth import create_access_token


@pytest.fixture
def tenant_client(tmp_path, monkeypatch):
    db_path = tmp_path / "tenant_isolation.db"

    def connect():
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    connection = connect()
    connection.executescript("""
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            business_name TEXT NOT NULL,
            email TEXT NOT NULL
        );

        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            role TEXT NOT NULL
        );

        CREATE TABLE accounts (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            currency TEXT NOT NULL,
            balance_pence INTEGER NOT NULL
        );

        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY,
            from_account_id INTEGER NOT NULL,
            to_account_id INTEGER NOT NULL,
            amount_pence INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );
    """)
    connection.executemany("INSERT INTO customers VALUES (?, ?, ?)", [(1, "Business A", "a@example.com"), (2, "Business B", "b@example.com"), (3, "Business C", "c@example.com")])
    connection.executemany("INSERT INTO users VALUES (?, ?, ?)", [(1, 1, "user"), (2, 2, "user"), (3, 3, "user")])
    connection.executemany("INSERT INTO accounts VALUES (?, ?, ?, ?)", [(101, 1, "GBP", 100000), (202, 2, "GBP", 200000), (303, 3, "GBP", 300000)])
    connection.executemany("INSERT INTO transactions VALUES (?, ?, ?, ?, ?)", [(1, 101, 202, 1000, "2026-10-22"), (2, 202, 303, 2000, "2026-10-22")])
    connection.commit()
    connection.close()

    monkeypatch.setattr(dependencies, "get_connection", connect)
    monkeypatch.setattr(main, "get_connection", connect)
    return TestClient(main.app)


def test_customer_isolation(tenant_client):
    token = create_access_token(1)
    response = tenant_client.get(
        "/customers",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert {row["id"] for row in response.json()} == {1}


def test_account_isolation(tenant_client):
    token = create_access_token(1)
    response = tenant_client.get(
        "/accounts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert {row["id"] for row in response.json()} == {101}


def test_transaction_isolation(tenant_client):
    token = create_access_token(1)
    response = tenant_client.get(
        "/transactions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert {row["id"] for row in response.json()} == {1}
