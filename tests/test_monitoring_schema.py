import sqlite3

import pytest

import app.models as models


@pytest.fixture
def monitoring_db(tmp_path, monkeypatch):
    database = tmp_path / "monitoring.db"

    def connect():
        connection = sqlite3.connect(database)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    monkeypatch.setattr(models, "get_connection", connect)
    models.create_tables()

    with connect() as connection:
        connection.execute(
            "INSERT INTO customers (id, business_name, email) "
            "VALUES (1, 'Test Business', 'test@example.com')"
        )
        connection.executemany(
            "INSERT INTO accounts "
            "(id, customer_id, currency, balance_pence) VALUES (?, 1, 'GBP', ?)",
            [(1, 1000000), (2, 500000)],
        )
        connection.execute(
            "INSERT INTO transactions "
            "(id, from_account_id, to_account_id, amount_pence) "
            "VALUES (1, 1, 2, 100)"
        )

    connection = connect()
    try:
        yield connection
    finally:
        connection.close()


def insert_alert(connection, rule="LARGE_TRANSFER"):
    connection.execute(
        "INSERT INTO monitoring_alerts "
        "(transaction_id, customer_id, rule_code, severity, "
        "evidence_json, transaction_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (1, 1, rule, "medium", "{}", "2026-10-22 12:00:00"),
    )


def test_schema_reinitialization_preserves_banking_data(monitoring_db):
    models.create_tables()
    models.create_tables()

    balances = monitoring_db.execute(
        "SELECT balance_pence FROM accounts ORDER BY id"
    ).fetchall()
    assert [row["balance_pence"] for row in balances] == [1000000, 500000]
    assert monitoring_db.execute(
        "SELECT COUNT(*) FROM transactions"
    ).fetchone()[0] == 1


def test_duplicate_transaction_rule_is_rejected(monitoring_db):
    insert_alert(monitoring_db)
    with pytest.raises(sqlite3.IntegrityError):
        insert_alert(monitoring_db)


def test_distinct_rules_can_flag_same_transaction(monitoring_db):
    insert_alert(monitoring_db)
    insert_alert(monitoring_db, "HIGH_TRANSFER_FREQUENCY")
    assert monitoring_db.execute(
        "SELECT COUNT(*) FROM monitoring_alerts"
    ).fetchone()[0] == 2


def test_new_alert_has_open_status_and_no_reviewer(monitoring_db):
    insert_alert(monitoring_db)
    alert = monitoring_db.execute(
        "SELECT status, reviewed_by, reviewed_at FROM monitoring_alerts"
    ).fetchone()
    assert alert["status"] == "open"
    assert alert["reviewed_by"] is None
    assert alert["reviewed_at"] is None


def test_completed_review_requires_reviewer_and_timestamp(monitoring_db):
    insert_alert(monitoring_db)
    with pytest.raises(sqlite3.IntegrityError):
        monitoring_db.execute(
            "UPDATE monitoring_alerts SET status = 'reviewed'"
        )


def test_alert_requires_existing_transaction(monitoring_db):
    with pytest.raises(sqlite3.IntegrityError):
        monitoring_db.execute(
            "INSERT INTO monitoring_alerts "
            "(transaction_id, customer_id, rule_code, severity, "
            "evidence_json, transaction_at) "
            "VALUES (999, 1, 'LARGE_TRANSFER', 'medium', '{}', "
            "'2026-10-22 12:00:00')"
        )
