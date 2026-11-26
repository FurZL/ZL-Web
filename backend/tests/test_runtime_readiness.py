"""Readiness reports both dependency states without leaking exceptions."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import health
from app.core.redis import get_redis


def test_readiness_reports_database_and_redis(monkeypatch):
    class Redis:
        healthy = True
        async def ping(self):
            if not self.healthy:
                raise RuntimeError("redis secret")

    class Connection:
        healthy = True
        async def __aenter__(self):
            if not self.healthy:
                raise RuntimeError("database secret")
            return self
        async def __aexit__(self, *_):
            return None
        async def execute(self, _query):
            return None

    class Engine:
        def connect(self):
            return connection

    redis, connection = Redis(), Connection()
    monkeypatch.setattr(health, "engine", Engine())
    app = FastAPI()
    app.include_router(health.router)
    app.dependency_overrides[get_redis] = lambda: redis
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok"}
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": True, "redis": True}
    redis.healthy = False
    response = client.get("/ready")
    assert response.status_code == 503 and response.json()["database"] and not response.json()["redis"]
    connection.healthy = False
    response = client.get("/ready")
    assert response.status_code == 503 and not response.json()["database"]
    assert "secret" not in response.text
