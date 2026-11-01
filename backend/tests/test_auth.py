import time

import jwt
import pytest

from tests.conftest import make_token


def get_me(client, token):
    return client.get("/me", headers={"Authorization": f"Bearer {token}"})


def test_no_token_is_401(anon):
    r = anon.get("/me")
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "token",
    [
        "not-a-jwt",
        make_token("u1", "a@example.com", secret="some-other-secret-at-least-32-bytes"),
        make_token("u1", "a@example.com", exp=int(time.time()) - 10),
        make_token("u1", "a@example.com", aud="anon"),
        make_token("u1", "a@example.com", iss="https://evil.supabase.co/auth/v1"),
        jwt.encode({"sub": "u1", "aud": "authenticated"}, None, algorithm="none"),
    ],
    ids=["garbage", "wrong-secret", "expired", "wrong-audience", "wrong-issuer", "alg-none"],
)
def test_invalid_tokens_are_401(anon, token):
    assert get_me(anon, token).status_code == 401


def test_token_without_sub_is_401(anon):
    token = jwt.encode(
        {"aud": "authenticated", "iss": "https://test.supabase.co/auth/v1", "exp": int(time.time()) + 60},
        "test-secret-at-least-32-bytes-long!!",
        algorithm="HS256",
    )
    assert get_me(anon, token).status_code == 401


def test_first_sign_in_creates_user(anon):
    r = get_me(anon, make_token("u1", "axel@example.com"))
    assert r.status_code == 200
    assert r.json() == {"id": 1, "email": "axel@example.com", "display_name": "axel", "households": []}
    # Same subject, same user.
    assert get_me(anon, make_token("u1", "axel@example.com")).json()["id"] == 1


def test_email_change_follows_the_token(anon):
    get_me(anon, make_token("u1", "old@example.com"))
    assert get_me(anon, make_token("u1", "new@example.com")).json()["email"] == "new@example.com"


def test_rename_me(axel):
    r = axel.patch("/me", json={"display_name": "  Axel  "})
    assert r.status_code == 200
    assert r.json()["display_name"] == "Axel"
