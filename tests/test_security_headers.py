from fastapi.testclient import TestClient
from app.main import app


def test_security_headers():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
