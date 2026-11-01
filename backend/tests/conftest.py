import time

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db, make_engine
from app.main import app
from app.settings import settings

JWT_SECRET = "test-secret-at-least-32-bytes-long!!"
SUPABASE_URL = "https://test.supabase.co"


def make_token(sub: str, email: str, **overrides) -> str:
    """A token shaped like the ones Supabase issues, signed with the legacy shared secret."""
    secret = overrides.pop("secret", JWT_SECRET)
    claims = {
        "sub": sub,
        "email": email,
        "aud": "authenticated",
        "iss": f"{SUPABASE_URL}/auth/v1",
        "exp": int(time.time()) + 3600,
        "role": "authenticated",
    } | overrides
    return jwt.encode(claims, secret, algorithm="HS256")


@pytest.fixture
def db_session(monkeypatch):
    monkeypatch.setattr(settings, "supabase_jwt_secret", JWT_SECRET)
    monkeypatch.setattr(settings, "supabase_url", SUPABASE_URL)

    engine = make_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestSession
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def anon(db_session):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def login(db_session):
    """login("axel") returns a client signed in as axel@example.com."""
    clients = []

    def _login(name: str) -> TestClient:
        token = make_token(f"sub-{name}", f"{name}@example.com")
        client = TestClient(app, headers={"Authorization": f"Bearer {token}"})
        clients.append(client)
        assert client.get("/me").status_code == 200  # creates the user row
        return client

    yield _login
    for c in clients:
        c.close()


@pytest.fixture
def axel(login):
    return login("axel")


@pytest.fixture
def ebba(login):
    return login("ebba")


@pytest.fixture
def couple(axel, ebba):
    """Axel's Amex shared into a household with Ebba. Returns (household_id, account_id)."""
    hh = axel.post("/households", json={"name": "Axel & Ebba"}).json()
    assert axel.post(f"/households/{hh['id']}/members", json={"email": "ebba@example.com"}).status_code == 201
    account = axel.post("/accounts", json={"name": "Amex", "household_id": hh["id"]}).json()
    return hh["id"], account["id"]
