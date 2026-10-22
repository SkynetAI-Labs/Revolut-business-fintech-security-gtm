import sqlite3

from app.database import get_connection
from app.security import hash_password


def register_user(customer_id: int, email: str, password: str) -> int:
    email = email.strip().lower()

    if not email or "@" not in email:
        raise ValueError("Invalid email address")

    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters")

    connection = get_connection()

    try:
        customer = connection.execute(
            "SELECT id FROM customers WHERE id = ?",
            (customer_id,),
        ).fetchone()

        if customer is None:
            raise ValueError("Customer does not exist")

        password_hash = hash_password(password)

        cursor = connection.execute(
            """
            INSERT INTO users (customer_id, email, password_hash, role)
            VALUES (?, ?, ?, 'user')
            """,
            (customer_id, email, password_hash),
        )

        connection.commit()
        return cursor.lastrowid

    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise ValueError("Registration could not be completed") from exc

    finally:
        connection.close()


def authenticate_user(email: str, password: str):
    email = email.strip().lower()
    connection = get_connection()

    try:
        user = connection.execute(
            "SELECT id, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()

        if user is None:
            return None

        from app.security import verify_password

        if not verify_password(password, user["password_hash"]):
            return None

        return user["id"]

    finally:
        connection.close()
