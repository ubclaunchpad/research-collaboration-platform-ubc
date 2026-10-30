"""Checks the login token and works out which user sent the request."""

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

load_dotenv()

# tokens are signed with Supabase's private key, we check them with the public one
ALGORITHMS = ["ES256", "RS256"]
AUDIENCE = "authenticated"

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str | None


def _auth_url() -> str:
    return f"{os.environ['SUPABASE_URL'].rstrip('/')}/auth/v1"


@lru_cache
def get_jwks_client() -> PyJWKClient:
    return PyJWKClient(f"{_auth_url()}/.well-known/jwks.json")


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    jwks_client: Annotated[PyJWKClient, Depends(get_jwks_client)],
) -> CurrentUser:
    if credentials is None:
        raise _unauthorized("Not authenticated")

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(credentials.credentials)
        claims = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=ALGORITHMS,
            audience=AUDIENCE,
            issuer=_auth_url(),
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWKClientConnectionError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Auth service unreachable"
        ) from exc
    except jwt.PyJWTError as exc:
        raise _unauthorized("Invalid or expired token") from exc

    return CurrentUser(id=claims["sub"], email=claims.get("email"))
