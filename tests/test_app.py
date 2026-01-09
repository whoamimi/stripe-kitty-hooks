# tests/test_app.py

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_health():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "message": "Stripe Payment Service is running."
    }

    health_response = client.get("/health")
    assert response.status_code == health_response.status_code
    assert response.json() == health_response.json()