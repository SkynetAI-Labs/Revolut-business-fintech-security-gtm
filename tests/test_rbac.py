import sqlite3

import pytest
from fastapi.testclient import TestClient

import app.dependencies as dependencies
from app.auth import create_access_token
from app.main import app


@pytest.fixture
def rbac_db(tmp_path, monkeypatch):
    db_path = tmp_path / "rbac_test.db"

    def connect():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    conn = connect()
    conn.execute(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, role TEXT NOT NULL)"
    )
    conn.executemany(
        "INSERT INTO users (id, role) VALUES (?, ?)",
        [(1, "user"), (2, "admin")],
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(dependencies, "get_connection", connect)
    return TestClient(app)


def test_admin_endpoint_requires_authentication(rbac_db):
    response = rbac_db.get("/admin/security-status")
    assert response.status_code == 401


def test_standard_user_cannot_access_admin_endpoint(rbac_db):
    token = create_access_token(1)
    response = rbac_db.get(
        "/admin/security-status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_administrator_can_access_admin_endpoint(rbac_db):
    token = create_access_token(2)
    response = rbac_db.get(
        "/admin/security-status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["access"] == "administrator"
    assert response.json()["authenticated_user_id"] == 2


def test_nonexistent_user_cannot_access_admin_endpoint(rbac_db):
    token = create_access_token(999)
    response = rbac_db.get(
        "/admin/security-status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
