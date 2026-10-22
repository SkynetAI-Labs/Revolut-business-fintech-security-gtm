import sqlite3

import pytest

import app.models as models
from app.monitoring import assess_transaction


@pytest.fixture
def detection_db(tmp_path, monkeypatch):
    database = tmp_path / "detection.db"

    def connect():
        connection = sqlite3.connect(database)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    monkeypatch.setattr(models, "get_connection", connect)
    models.create_tables()
    connection = connect()
    connection.execute(
        "INSERT INTO customers (id, business_name, email) "
        "VALUES (1, 'Detection Test', 'detection@example.com')"
    )
    connection.executemany(
        "INSERT INTO accounts "
        "(id, customer_id, currency, balance_pence) "
        "VALUES (?, 1, 'GBP', 10000000)",
        [(1,), (2,), (3,)],
    )
    connection.commit()
    try:
        yield connection
    finally:
        connection.close()


def add_transaction(connection, transaction_id, amount, occurred, recipient=2):
    connection.execute(
        "INSERT INTO transactions "
        "(id, from_account_id, to_account_id, amount_pence, created_at) "
        "VALUES (?, 1, ?, ?, ?)",
        (transaction_id, recipient, amount, occurred),
    )


@pytest.mark.parametrize("rule,value,expected", [
    ("LARGE_TRANSFER", 499999, False),
    ("LARGE_TRANSFER", 500000, False),
    ("LARGE_TRANSFER", 500001, True),
    ("HIGH_TRANSFER_FREQUENCY", 4, False),
    ("HIGH_TRANSFER_FREQUENCY", 5, False),
    ("HIGH_TRANSFER_FREQUENCY", 6, True),
    ("HIGH_OUTGOING_VALUE", 999999, False),
    ("HIGH_OUTGOING_VALUE", 1000000, False),
    ("HIGH_OUTGOING_VALUE", 1000001, True),
    ("RAPID_REPEATED_TRANSFERS", 2, False),
    ("RAPID_REPEATED_TRANSFERS", 3, False),
    ("RAPID_REPEATED_TRANSFERS", 4, True),
])
def test_database_assessment_thresholds(detection_db, rule, value, expected):
    timestamp = "2026-10-22 12:00:00"

    if rule == "LARGE_TRANSFER":
        amounts = [value]
    elif rule == "HIGH_OUTGOING_VALUE":
        amounts = [value // 2, value - value // 2]
    else:
        amounts = [100] * value

    for transaction_id, amount in enumerate(amounts, start=1):
        add_transaction(detection_db, transaction_id, amount, timestamp)

    assessment = assess_transaction(detection_db, len(amounts))
    codes = {match.rule_code for match in assessment.matches}
    assert (rule in codes) is expected
    assert assessment.customer_id == 1


@pytest.mark.parametrize("rule,window,count,old_amount,trigger_amount", [
    ("HIGH_TRANSFER_FREQUENCY", 600, 5, 100, 100),
    ("HIGH_OUTGOING_VALUE", 3600, 1, 600000, 500000),
    ("RAPID_REPEATED_TRANSFERS", 300, 3, 100, 100),
])
@pytest.mark.parametrize("offset,expected", [
    (-1, True), (0, True), (1, False),
])
def test_detection_window_boundaries(
    detection_db, rule, window, count, old_amount, trigger_amount,
    offset, expected
):
    from datetime import datetime, timedelta, timezone

    trigger_time = datetime(2026, 10, 22, 12, tzinfo=timezone.utc)
    historical_time = trigger_time - timedelta(seconds=window + offset)

    for transaction_id in range(1, count + 1):
        add_transaction(
            detection_db, transaction_id, old_amount,
            historical_time.isoformat(),
        )
    add_transaction(
        detection_db, count + 1, trigger_amount, trigger_time.isoformat()
    )

    assessment = assess_transaction(detection_db, count + 1)
    codes = {match.rule_code for match in assessment.matches}
    assert (rule in codes) is expected


def test_future_transactions_do_not_affect_earlier_assessment(detection_db):
    for transaction_id in range(1, 7):
        add_transaction(
            detection_db, transaction_id, 600000,
            "2026-10-22 12:00:01",
        )
    add_transaction(detection_db, 7, 100, "2026-10-22 12:00:00")

    assert assess_transaction(detection_db, 7).matches == ()


def test_other_senders_do_not_contribute_to_windows(detection_db):
    for transaction_id in range(1, 7):
        detection_db.execute(
            "INSERT INTO transactions "
            "(id, from_account_id, to_account_id, amount_pence, created_at) "
            "VALUES (?, 3, 2, 600000, '2026-10-22 12:00:00')",
            (transaction_id,),
        )
    add_transaction(detection_db, 7, 100, "2026-10-22 12:00:00")

    assert assess_transaction(detection_db, 7).matches == ()


def test_repeated_rule_counts_only_matching_recipient(detection_db):
    for transaction_id in range(1, 4):
        add_transaction(
            detection_db, transaction_id, 100,
            "2026-10-22 12:00:00", recipient=3,
        )
    add_transaction(detection_db, 4, 100, "2026-10-22 12:00:00", recipient=2)

    codes = {
        match.rule_code
        for match in assess_transaction(detection_db, 4).matches
    }
    assert "RAPID_REPEATED_TRANSFERS" not in codes


def test_equivalent_utc_offsets_share_window_boundary(detection_db):
    add_transaction(
        detection_db, 1, 600000, "2026-10-22T12:00:00+01:00"
    )
    add_transaction(
        detection_db, 2, 500000, "2026-10-22T12:00:00+00:00"
    )

    match = next(
        match for match in assess_transaction(detection_db, 2).matches
        if match.rule_code == "HIGH_OUTGOING_VALUE"
    )
    assert match.evidence["total_pence"] == 1100000
    assert match.evidence["window_start"] == "2026-10-22T11:00:00+00:00"
