import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import JWT_SECRET_KEY, JWT_ALGORITHM
from app.database import get_connection

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> int:
    error = HTTPException(
        status_code=401,
        detail="Invalid or missing authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise error

    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
        user_id = int(payload["sub"])
        if user_id <= 0:
            raise ValueError("Invalid user ID")
        connection = get_connection()
        try:
            user = connection.execute(
                "SELECT id FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        finally:
            connection.close()

        if user is None:
            raise error

        return user_id
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        raise error


def require_admin(user_id: int = Depends(get_current_user_id)) -> int:
    connection = get_connection()
    try:
        user = connection.execute(
            "SELECT role FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        connection.close()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Administrator access required",
        )

    return user_id


def get_current_customer_id(
    user_id: int = Depends(get_current_user_id),
) -> int:
    connection = get_connection()
    try:
        user = connection.execute(
            "SELECT customer_id FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        connection.close()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user["customer_id"]
