import sqlite3

import pytest

from app import models, payments


@pytest.fixture
def test_database(tmp_path, monkeypatch):
    database = tmp_path / "test_banking.db"

    def connect():
        connection = sqlite3.connect(database)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    monkeypatch.setattr(models, "get_connection", connect)
    monkeypatch.setattr(payments, "get_connection", connect)
    models.create_tables()

    connection = connect()
    try:
        connection.execute(
            "INSERT INTO customers (id, business_name, email) "
            "VALUES (1, 'Payment Test Business', 'payments@example.com')"
        )
        connection.executemany(
            "INSERT INTO accounts "
            "(id, customer_id, currency, balance_pence) "
            "VALUES (?, 1, 'GBP', ?)",
            [(1, 1000000), (2, 500000)],
        )
        connection.commit()
    finally:
        connection.close()

    return connect


@pytest.mark.parametrize(
    "sender,receiver,amount",
    [
        (1, 2, 999999999),
        (1, 2, -100),
        (1, 2, 0),
        (1, 1, 100),
        (999, 2, 100),
    ],
)
def test_invalid_transfer_preserves_balances(
    test_database, sender, receiver, amount
):
    with pytest.raises(ValueError):
        payments.transfer_funds(sender, receiver, amount)

    connection = test_database()
    try:
        balances = [
            row["balance_pence"]
            for row in connection.execute(
                "SELECT balance_pence FROM accounts ORDER BY id"
            )
        ]
        assert balances == [1000000, 500000]
        assert connection.execute(
            "SELECT COUNT(*) FROM transactions"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM monitoring_alerts"
        ).fetchone()[0] == 0
    finally:
        connection.close()


def test_successful_transfer_preserves_total(test_database):
    result = payments.transfer_funds(1, 2, 25000)

    assert result["status"] == "completed"
    assert result["amount_pence"] == 25000

    connection = test_database()
    try:
        balances = [
            row["balance_pence"]
            for row in connection.execute(
                "SELECT balance_pence FROM accounts ORDER BY id"
            )
        ]
        transactions = connection.execute(
            "SELECT * FROM transactions"
        ).fetchall()

        assert balances == [975000, 525000]
        assert sum(balances) == 1500000
        assert len(transactions) == 1
        assert transactions[0]["amount_pence"] == 25000
        assert connection.execute(
            "SELECT COUNT(*) FROM monitoring_alerts"
        ).fetchone()[0] == 0
    finally:
        connection.close()


def test_large_transfer_completes_and_stores_alert(test_database):
    result = payments.transfer_funds(1, 2, 600000)

    connection = test_database()
    try:
        alert = connection.execute(
            "SELECT * FROM monitoring_alerts"
        ).fetchone()
        assert result["status"] == "completed"
        assert alert["transaction_id"] == result["transaction_id"]
        assert alert["customer_id"] == 1
        assert alert["rule_code"] == "LARGE_TRANSFER"
        assert alert["status"] == "open"
        balances = [
            row["balance_pence"]
            for row in connection.execute(
                "SELECT balance_pence FROM accounts ORDER BY id"
            )
        ]
        assert balances == [400000, 1100000]
    finally:
        connection.close()


def test_monitoring_failure_rolls_back_payment_and_alerts(
    test_database, monkeypatch
):
    original_monitor = payments.monitor_transaction

    def fail_after_alert_insert(connection, transaction_id):
        original_monitor(connection, transaction_id)
        assert connection.execute(
            "SELECT COUNT(*) FROM monitoring_alerts"
        ).fetchone()[0] == 1
        raise RuntimeError("Simulated monitoring failure")

    monkeypatch.setattr(
        payments, "monitor_transaction", fail_after_alert_insert
    )

    with pytest.raises(RuntimeError, match="Simulated monitoring failure"):
        payments.transfer_funds(1, 2, 600000)

    connection = test_database()
    try:
        balances = [
            row["balance_pence"]
            for row in connection.execute(
                "SELECT balance_pence FROM accounts ORDER BY id"
            )
        ]
        assert balances == [1000000, 500000]
        assert connection.execute(
            "SELECT COUNT(*) FROM transactions"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM monitoring_alerts"
        ).fetchone()[0] == 0
    finally:
        connection.close()


@pytest.mark.parametrize(
    "sender,receiver,amount",
    [
        (1, 2, 999999999),
        (1, 2, -100),
        (1, 2, 0),
        (1, 1, 100),
        (999, 2, 100),
        (1, 999, 100),
    ],
)
def test_rejected_transfers_never_call_monitoring(
    test_database, monkeypatch, sender, receiver, amount
):
    calls = []

    def record_monitoring_call(connection, transaction_id):
        calls.append(transaction_id)

    monkeypatch.setattr(
        payments, "monitor_transaction", record_monitoring_call
    )

    with pytest.raises(ValueError):
        payments.transfer_funds(sender, receiver, amount)

    assert calls == []
