import json
import sqlite3

import pytest

import app.models as models
from app.monitoring import (
    analyse_historical_transactions,
    assess_transaction,
)


@pytest.fixture
def history_db(tmp_path, monkeypatch):
    path = tmp_path / "history.db"

    def connect():
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    monkeypatch.setattr(models, "get_connection", connect)
    models.create_tables()
    connection = connect()
    connection.execute(
        "INSERT INTO customers (id, business_name, email) "
        "VALUES (1, 'History Test', 'history@example.com')"
    )
    connection.executemany(
        "INSERT INTO accounts "
        "(id, customer_id, currency, balance_pence) "
        "VALUES (?, 1, 'GBP', ?)",
        [(1, 2000000), (2, 0)],
    )
    connection.executemany(
        "INSERT INTO transactions "
        "(id, from_account_id, to_account_id, amount_pence, created_at) "
        "VALUES (?, 1, 2, ?, ?)",
        [
            (1, 600000, "2026-10-22 12:00:00"),
            (2, 600000, "2026-10-22 12:00:00"),
            (3, 600000, "2026-10-22 14:00:00"),
        ],
    )
    connection.commit()
    try:
        yield connection
    finally:
        connection.close()


def test_batches_resume_and_respect_fixed_upper_id(history_db):
    history_db.execute("BEGIN")
    first = analyse_historical_transactions(history_db, limit=1)
    assert first["processed_count"] == 1
    assert first["next_after_id"] == 1
    assert first["up_to_id"] == 3
    assert first["has_more"] is True

    history_db.execute(
        "INSERT INTO transactions "
        "(id, from_account_id, to_account_id, amount_pence, created_at) "
        "VALUES (4, 1, 2, 100, '2026-10-22 15:00:00')"
    )
    second = analyse_historical_transactions(
        history_db,
        after_id=first["next_after_id"],
        up_to_id=first["up_to_id"],
    )
    assert second["processed_count"] == 2
    assert second["next_after_id"] == 3
    assert second["has_more"] is False
    assert history_db.execute(
        "SELECT COUNT(*) FROM monitoring_alerts WHERE transaction_id = 4"
    ).fetchone()[0] == 0


def test_replay_preserves_existing_alert_evidence_and_status(history_db):
    history_db.execute("BEGIN")
    first = analyse_historical_transactions(history_db)
    assert first["alerts_created"] == 4

    history_db.execute(
        "INSERT INTO users "
        "(id, customer_id, email, password_hash, role) "
        "VALUES (1, 1, 'admin@example.com', 'test-only', 'admin')"
    )
    history_db.execute(
        "UPDATE monitoring_alerts SET status = 'dismissed', "
        "reviewed_by = 1, reviewed_at = '2026-10-22 16:00:00' WHERE id = 1"
    )
    before = [
        tuple(row) for row in history_db.execute(
            "SELECT * FROM monitoring_alerts ORDER BY id"
        )
    ]
    second = analyse_historical_transactions(history_db)
    assert second["alerts_created"] == 0
    after = [
        tuple(row) for row in history_db.execute(
            "SELECT * FROM monitoring_alerts ORDER BY id"
        )
    ]
    assert after == before


def test_original_times_and_equal_timestamp_id_order(history_db):
    first = assess_transaction(history_db, 1)
    second = assess_transaction(history_db, 2)
    third = assess_transaction(history_db, 3)

    assert {match.rule_code for match in first.matches} == {
        "LARGE_TRANSFER"
    }
    cumulative = next(
        match for match in second.matches
        if match.rule_code == "HIGH_OUTGOING_VALUE"
    )
    assert cumulative.evidence["total_pence"] == 1200000
    assert {match.rule_code for match in third.matches} == {
        "LARGE_TRANSFER"
    }

    history_db.execute("BEGIN")
    analyse_historical_transactions(history_db)
    row = history_db.execute(
        "SELECT transaction_at, evidence_json FROM monitoring_alerts "
        "WHERE transaction_id = 2 AND rule_code = 'HIGH_OUTGOING_VALUE'"
    ).fetchone()
    assert row["transaction_at"] == "2026-10-22T12:00:00+00:00"
    assert json.loads(row["evidence_json"])["upper_transaction_id"] == 2


def test_historical_analysis_can_be_rolled_back(history_db):
    before = [
        tuple(row) for row in history_db.execute(
            "SELECT * FROM transactions ORDER BY id"
        )
    ]
    history_db.execute("BEGIN")
    analyse_historical_transactions(history_db)
    assert history_db.in_transaction
    history_db.rollback()

    assert history_db.execute(
        "SELECT COUNT(*) FROM monitoring_alerts"
    ).fetchone()[0] == 0
    assert [
        tuple(row) for row in history_db.execute(
            "SELECT * FROM transactions ORDER BY id"
        )
    ] == before
    assert [
        row[0] for row in history_db.execute(
            "SELECT balance_pence FROM accounts ORDER BY id"
        )
    ] == [2000000, 0]


def test_explicit_transaction_is_required(history_db):
    with pytest.raises(ValueError, match="explicit transaction"):
        analyse_historical_transactions(history_db)


@pytest.mark.parametrize("arguments", [
    {"after_id": -1},
    {"after_id": True},
    {"limit": 0},
    {"limit": 1001},
    {"limit": True},
    {"up_to_id": -1},
    {"up_to_id": True},
])
def test_invalid_batch_arguments_are_rejected(history_db, arguments):
    history_db.execute("BEGIN")
    with pytest.raises(ValueError):
        analyse_historical_transactions(history_db, **arguments)
