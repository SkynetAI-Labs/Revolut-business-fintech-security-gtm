import jwt
import pytest
from datetime import datetime, timedelta, timezone

from app.auth import create_access_token
from app.config import JWT_SECRET_KEY, JWT_ALGORITHM


def test_valid_jwt():
    token = create_access_token(1)
    payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    assert payload["sub"] == "1"
    assert payload["exp"] - payload["iat"] == 1800


def test_expired_jwt_rejected():
    payload = {
        "sub": "1",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])


def test_tampered_jwt_rejected():
    token = create_access_token(1)
    parts = token.split(".")
    parts[2] = ("A" if parts[2][0] != "A" else "B") + parts[2][1:]
    tampered = ".".join(parts)
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(tampered, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
