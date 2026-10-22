"""Configure authentication for tests without relying on the local .env."""

import os
import secrets

os.environ["JWT_SECRET_KEY"] = secrets.token_hex(32)
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_EXPIRE_MINUTES"] = "30"
