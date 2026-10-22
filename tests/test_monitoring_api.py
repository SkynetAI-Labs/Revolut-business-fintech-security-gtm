import sqlite3

import pytest
from fastapi.testclient import TestClient

import app.dependencies as dependencies
import app.models as models
import app.monitoring_routes as routes
from app.auth import create_access_token
from app.main import app, limiter


@pytest.fixture
def alert_client(tmp_path, monkeypatch):
    database = tmp_path / "alerts_api.db"

    def connect():
        connection = sqlite3.connect(database)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    for module in (models, dependencies, routes):
        monkeypatch.setattr(module, "get_connection", connect)
    models.create_tables()

    connection = connect()
    try:
        for customer_id in (1, 2, 3):
            connection.execute(
                "INSERT INTO customers (id, business_name, email) "
                "VALUES (?, ?, ?)",
                (customer_id, f"Business {customer_id}",
                 f"business{customer_id}@example.com"),
            )
            connection.execute(
                "INSERT INTO users "
                "(id, customer_id, email, password_hash, role) "
                "VALUES (?, ?, ?, ?, ?)",
                (customer_id, customer_id,
                 f"user{customer_id}@example.com", "test-only",
                 "admin" if customer_id == 3 else "user"),
            )
            connection.execute(
                "INSERT INTO accounts "
                "(id, customer_id, currency, balance_pence) "
                "VALUES (?, ?, 'GBP', 1000000)",
                (customer_id, customer_id),
            )

        for transaction_id, customer_id in [(1, 1), (2, 2), (3, 1)]:
            connection.execute(
                "INSERT INTO transactions "
                "(id, from_account_id, to_account_id, amount_pence) "
                "VALUES (?, ?, 3, 600000)",
                (transaction_id, customer_id),
            )
            connection.execute(
                "INSERT INTO monitoring_alerts "
                "(id, transaction_id, customer_id, rule_code, severity, "
                "evidence_json, transaction_at) "
                "VALUES (?, ?, ?, 'LARGE_TRANSFER', 'medium', "
                "?, '2026-10-22 12:00:00')",
                (transaction_id, transaction_id, customer_id, '{"rule_version": 1}'),
            )
        connection.commit()
    finally:
        connection.close()

    limiter._storage.reset()
    try:
        with TestClient(app) as client:
            yield client
    finally:
        limiter._storage.reset()


def headers(user_id):
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


@pytest.mark.parametrize("path", [
    "/monitoring/alerts", "/monitoring/admin/alerts",
])
def test_alert_routes_require_authentication(alert_client, path):
    response = alert_client.get(path)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_customer_sees_only_owned_alerts(alert_client):
    response = alert_client.get("/monitoring/alerts", headers=headers(1))
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [3, 1]
    for row in response.json():
        assert "customer_id" not in row
        assert "reviewed_by" not in row
        assert "reviewed_at" not in row
        assert "from_account_id" not in row
        assert "to_account_id" not in row
        assert row["evidence"] == {"rule_version": 1}


def test_customer_cannot_override_authenticated_scope(alert_client):
    response = alert_client.get(
        "/monitoring/alerts?customer_id=2", headers=headers(1)
    )
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [3, 1]


def test_other_customer_has_separate_scope(alert_client):
    response = alert_client.get("/monitoring/alerts", headers=headers(2))
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [2]


def test_standard_user_cannot_read_admin_alerts(alert_client):
    response = alert_client.get(
        "/monitoring/admin/alerts", headers=headers(1)
    )
    assert response.status_code == 403


def test_admin_can_read_all_alerts_and_review_metadata(alert_client):
    response = alert_client.get(
        "/monitoring/admin/alerts", headers=headers(3)
    )
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [3, 2, 1]
    assert {row["customer_id"] for row in response.json()} == {1, 2}
    assert all("reviewed_by" in row for row in response.json())


def test_admin_customer_filter(alert_client):
    response = alert_client.get(
        "/monitoring/admin/alerts?customer_id=2", headers=headers(3)
    )
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [2]


def test_pagination_preserves_customer_scope(alert_client):
    first = alert_client.get(
        "/monitoring/alerts?limit=1", headers=headers(1)
    )
    assert first.status_code == 200
    assert [row["id"] for row in first.json()] == [3]
    second = alert_client.get(
        "/monitoring/alerts?limit=1&before_id=3", headers=headers(1)
    )
    assert second.status_code == 200
    assert [row["id"] for row in second.json()] == [1]


@pytest.mark.parametrize("query", [
    "status=open", "severity=medium", "rule_code=LARGE_TRANSFER",
])
def test_matching_filters(alert_client, query):
    response = alert_client.get(
        f"/monitoring/alerts?{query}", headers=headers(1)
    )
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [3, 1]


@pytest.mark.parametrize("query", [
    "status=dismissed", "severity=high",
    "rule_code=HIGH_TRANSFER_FREQUENCY",
])
def test_nonmatching_filters_return_empty_list(alert_client, query):
    response = alert_client.get(
        f"/monitoring/alerts?{query}", headers=headers(1)
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize("query", [
    "limit=0", "limit=101", "before_id=0",
    "status=invalid", "severity=critical", "rule_code=invalid",
])
def test_invalid_filters_rejected(alert_client, query):
    response = alert_client.get(
        f"/monitoring/alerts?{query}", headers=headers(1)
    )
    assert response.status_code == 422


@pytest.mark.parametrize("path,count", [
    ("/monitoring/alerts", 30),
    ("/monitoring/admin/alerts", 10),
])
def test_alert_route_rate_limits(alert_client, path, count):
    user_id = 3 if "/admin/" in path else 1
    statuses = [
        alert_client.get(path, headers=headers(user_id)).status_code
        for _ in range(count + 1)
    ]
    assert statuses == [200] * count + [429]


def test_alert_response_security_headers(alert_client):
    response = alert_client.get("/monitoring/alerts", headers=headers(1))
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


@pytest.mark.parametrize("decision", ["reviewed", "dismissed"])
def test_review_records_administrator_and_preserves_evidence(
    alert_client, decision
):
    from datetime import datetime, timezone

    connection = routes.get_connection()
    try:
        before = dict(connection.execute(
            "SELECT * FROM monitoring_alerts WHERE id = 1"
        ).fetchone())
    finally:
        connection.close()

    started = datetime.now(timezone.utc)
    response = alert_client.patch(
        "/monitoring/admin/alerts/1/review",
        headers=headers(3),
        json={"status": decision},
    )
    finished = datetime.now(timezone.utc)

    assert response.status_code == 200
    result = response.json()
    assert result["id"] == 1
    assert result["status"] == decision
    assert result["reviewed_by"] == 3
    recorded = datetime.fromisoformat(result["reviewed_at"])
    assert recorded.utcoffset().total_seconds() == 0
    assert started <= recorded <= finished

    connection = routes.get_connection()
    try:
        after = dict(connection.execute(
            "SELECT * FROM monitoring_alerts WHERE id = 1"
        ).fetchone())
    finally:
        connection.close()

    changed_fields = {"status", "reviewed_by", "reviewed_at"}
    assert {
        key: value for key, value in after.items()
        if key not in changed_fields
    } == {
        key: value for key, value in before.items()
        if key not in changed_fields
    }
    assert after["status"] == decision
    assert after["reviewed_by"] == 3
    assert after["reviewed_at"] == result["reviewed_at"]


def test_review_requires_authentication(alert_client):
    response = alert_client.patch(
        "/monitoring/admin/alerts/1/review",
        json={"status": "reviewed"},
    )
    assert response.status_code == 401


@pytest.mark.parametrize("user_id", [1, 2])
def test_customer_cannot_review_alerts(alert_client, user_id):
    response = alert_client.patch(
        "/monitoring/admin/alerts/1/review",
        headers=headers(user_id),
        json={"status": "dismissed"},
    )
    assert response.status_code == 403
    connection = routes.get_connection()
    try:
        row = connection.execute(
            "SELECT status, reviewed_by, reviewed_at "
            "FROM monitoring_alerts WHERE id = 1"
        ).fetchone()
        assert tuple(row) == ("open", None, None)
    finally:
        connection.close()


@pytest.mark.parametrize("payload", [
    {"status": "open"},
    {"status": "invalid"},
    {},
    {"status": "reviewed", "reviewed_by": 1},
    {"status": "reviewed", "evidence": {}},
    {"status": "dismissed", "customer_id": 2},
])
def test_review_rejects_invalid_or_extra_fields(alert_client, payload):
    response = alert_client.patch(
        "/monitoring/admin/alerts/1/review",
        headers=headers(3),
        json=payload,
    )
    assert response.status_code == 422


@pytest.mark.parametrize("first,second", [
    ("reviewed", "dismissed"),
    ("dismissed", "reviewed"),
    ("reviewed", "reviewed"),
    ("dismissed", "dismissed"),
])
def test_final_review_cannot_be_overwritten(alert_client, first, second):
    initial = alert_client.patch(
        "/monitoring/admin/alerts/1/review",
        headers=headers(3),
        json={"status": first},
    )
    assert initial.status_code == 200

    response = alert_client.patch(
        "/monitoring/admin/alerts/1/review",
        headers=headers(3),
        json={"status": second},
    )
    assert response.status_code == 409

    connection = routes.get_connection()
    try:
        row = connection.execute(
            "SELECT status, reviewed_by, reviewed_at "
            "FROM monitoring_alerts WHERE id = 1"
        ).fetchone()
        assert row["status"] == first
        assert row["reviewed_by"] == initial.json()["reviewed_by"]
        assert row["reviewed_at"] == initial.json()["reviewed_at"]
    finally:
        connection.close()


def test_review_missing_alert_returns_404(alert_client):
    response = alert_client.patch(
        "/monitoring/admin/alerts/999/review",
        headers=headers(3),
        json={"status": "reviewed"},
    )
    assert response.status_code == 404


@pytest.mark.parametrize("alert_id", [0, -1])
def test_review_rejects_invalid_alert_id(alert_client, alert_id):
    response = alert_client.patch(
        f"/monitoring/admin/alerts/{alert_id}/review",
        headers=headers(3),
        json={"status": "reviewed"},
    )
    assert response.status_code == 422


def test_review_rate_limit(alert_client):
    statuses = [
        alert_client.patch(
            "/monitoring/admin/alerts/999/review",
            headers=headers(3),
            json={"status": "reviewed"},
        ).status_code
        for _ in range(11)
    ]
    assert statuses == [404] * 10 + [429]
