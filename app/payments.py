from app.database import get_connection


def transfer_funds(from_account_id: int, to_account_id: int, amount_pence: int):
    if amount_pence <= 0:
        raise ValueError("Transfer amount must be positive.")

    if from_account_id == to_account_id:
        raise ValueError("Cannot transfer to the same account.")

    connection = get_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        sender = connection.execute(
            "SELECT id, currency, balance_pence FROM accounts WHERE id = ?",
            (from_account_id,)
        ).fetchone()

        receiver = connection.execute(
            "SELECT id, currency FROM accounts WHERE id = ?",
            (to_account_id,)
        ).fetchone()

        if sender is None or receiver is None:
            raise ValueError("Account not found.")

        if sender["currency"] != receiver["currency"]:
            raise ValueError("Cross-currency transfers are not supported.")

        if sender["balance_pence"] < amount_pence:
            raise ValueError("Insufficient funds.")

        connection.execute(
            "UPDATE accounts SET balance_pence = balance_pence - ? WHERE id = ?",
            (amount_pence, from_account_id)
        )

        connection.execute(
            "UPDATE accounts SET balance_pence = balance_pence + ? WHERE id = ?",
            (amount_pence, to_account_id)
        )

        cursor = connection.execute(
            """INSERT INTO transactions
               (from_account_id, to_account_id, amount_pence)
               VALUES (?, ?, ?)""",
            (from_account_id, to_account_id, amount_pence)
        )

        connection.commit()

        return {
            "transaction_id": cursor.lastrowid,
            "from_account_id": from_account_id,
            "to_account_id": to_account_id,
            "amount_pence": amount_pence,
            "status": "completed"
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
