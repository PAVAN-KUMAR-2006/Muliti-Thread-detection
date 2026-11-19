"""Test setup. Everything runs against a throwaway SQLite database in a temp folder. The environment is overridden
BEFORE the app is imported, and the suite refuses to run if the database is not SQLite, so it can never touch the
development PostgreSQL database."""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="sentinel-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["JWT_SECRET"] = "test-only-secret-" + "x" * 40
os.environ["MODEL_DIR"] = f"{_tmp}/models"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"

import uuid  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402

assert settings.database_url.startswith("sqlite"), "Refusing to run tests against a non-SQLite database"

from app import models  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.ml import service  # noqa: E402
from app.routes_auth import limiter  # noqa: E402

limiter.enabled = False  # many users are registered in quick succession; rate limiting is not what is under test
PASSWORD = "Str0ng!Passw0rd"


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    service._cache.clear()
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture
def make_user(client):
    def make(email: str):
        r = client.post("/api/auth/register", json={"name": "Test User", "email": email, "password": PASSWORD})
        assert r.status_code == 201, r.text
        d = r.json()
        return {"Authorization": f"Bearer {d['access_token']}"}, d["user"]["id"]
    return make


@pytest.fixture
def add_scan(db):
    def add(user_id, label="Phishing", score=90.0, level="CRITICAL", scan_type="website", summary="http://example.test/x"):
        s = models.Scan(user_id=uuid.UUID(user_id), scan_type=scan_type, input_summary=summary, label=label, risk_score=score,
                        risk_level=level, confidence=0.9, status="completed", explanation="e", recommendation="r")
        db.add(s); db.commit()
        return str(s.id)
    return add
