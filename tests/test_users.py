import sqlite3

import pytest

import app.users as users
from app.security import hash_password


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    db_path = tmp_path / "users_test.db"

    def connect():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    conn = connect()
    conn.execute("CREATE TABLE customers (id INTEGER PRIMARY KEY)")
    conn.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
    """)
    conn.execute("INSERT INTO customers (id) VALUES (1)")
    conn.execute(
        "INSERT INTO users (customer_id, email, password_hash) VALUES (?, ?, ?)",
        (1, "lab2-test@example.com", hash_password("DemoSecurePassword123!")),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(users, "get_connection", connect)


def test_valid_login(test_db):
    assert users.authenticate_user(
        "lab2-test@example.com", "DemoSecurePassword123!"
    ) == 1


def test_incorrect_password_rejected(test_db):
    assert users.authenticate_user(
        "lab2-test@example.com", "WrongPassword123!"
    ) is None


def test_unknown_user_rejected(test_db):
    assert users.authenticate_user(
        "unknown@example.com", "DemoSecurePassword123!"
    ) is None


def test_registration_hashes_password(test_db):
    user_id = users.register_user(
        1, "new-user@example.com", "SecureDemoPassword123!"
    )
    conn = users.get_connection()
    record = conn.execute(
        "SELECT password_hash, role FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    conn.close()

    assert record["password_hash"].startswith("$argon2id$")
    assert record["role"] == "user"


def test_duplicate_registration_rejected(test_db):
    with pytest.raises(ValueError):
        users.register_user(
            1, "lab2-test@example.com", "SecureDemoPassword123!"
        )


def test_weak_password_rejected(test_db):
    with pytest.raises(ValueError):
        users.register_user(1, "weak@example.com", "short")


def test_invalid_customer_rejected(test_db):
    with pytest.raises(ValueError):
        users.register_user(
            999, "invalid@example.com", "SecureDemoPassword123!"
        )
