import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app.auth import get_jwks_client
from app.main import app

SUPABASE_URL = "https://example.supabase.co"
ISSUER = f"{SUPABASE_URL}/auth/v1"


class FakeJWKSClient:
    """Fake version of the Supabase key client, always returns our test key."""

    def __init__(self, public_key):
        self._public_key = public_key

    def get_signing_key_from_jwt(self, token):
        return SimpleNamespace(key=self._public_key)


@pytest.fixture(autouse=True)
def supabase_url(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", SUPABASE_URL)


@pytest.fixture(scope="session")
def private_key():
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture
def client(private_key):
    app.dependency_overrides[get_jwks_client] = lambda: FakeJWKSClient(
        private_key.public_key()
    )
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def make_token(private_key):
    def make(key=None, **overrides):
        claims = {
            "sub": "user-123",
            "email": "student@student.ubc.ca",
            "aud": "authenticated",
            "iss": ISSUER,
            "exp": int(time.time()) + 3600,
        }
        claims.update(overrides)
        claims = {k: v for k, v in claims.items() if v is not None}
        return jwt.encode(claims, key or private_key, algorithm="ES256")

    return make
