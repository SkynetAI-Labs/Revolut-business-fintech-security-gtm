from fastapi.testclient import TestClient

from app.main import app, limiter


def test_health_rate_limit():
    limiter._storage.reset()
    client = TestClient(app)
    codes = [client.get("/health").status_code for _ in range(65)]
    assert codes.count(200) == 60
    assert codes.count(429) == 5
    limiter._storage.reset()
