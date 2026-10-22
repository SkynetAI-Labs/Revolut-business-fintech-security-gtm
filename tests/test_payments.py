import sqlite3

import pytest

from app import payments


@pytest.fixture
def test_database(tmp_path, monkeypatch):
    database = tmp_path / "test_banking.db"

    def connect():
        connection = sqlite3.connect(database)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    connection = connect()
    connection.executescript("""
        CREATE TABLE accounts (
            id INTEGER PRIMARY KEY,
            currency TEXT NOT NULL,
            balance_pence INTEGER NOT NULL CHECK (balance_pence >= 0)
        );

        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY,
            from_account_id INTEGER NOT NULL,
            to_account_id INTEGER NOT NULL,
            amount_pence INTEGER NOT NULL CHECK (amount_pence > 0)
        );

        INSERT INTO accounts VALUES (1, 'GBP', 1000000);
        INSERT INTO accounts VALUES (2, 'GBP', 500000);
    """)
    connection.commit()
    connection.close()

    monkeypatch.setattr(payments, "get_connection", connect)
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
        count = connection.execute(
            "SELECT COUNT(*) FROM transactions"
        ).fetchone()[0]

        assert balances == [1000000, 500000]
        assert count == 0
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

    finally:
        connection.close()
