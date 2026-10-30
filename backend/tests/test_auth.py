import time

from cryptography.hazmat.primitives.asymmetric import ec


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_health_needs_no_login(client):
    assert client.get("/health").status_code == 200


def test_me_returns_logged_in_user(client, make_token):
    res = client.get("/me", headers=auth(make_token()))
    assert res.status_code == 200
    assert res.json() == {"id": "user-123", "email": "student@student.ubc.ca"}


def test_me_without_token_is_401(client):
    assert client.get("/me").status_code == 401


def test_me_with_garbage_token_is_401(client):
    assert client.get("/me", headers=auth("not-a-jwt")).status_code == 401


def test_me_with_expired_token_is_401(client, make_token):
    token = make_token(exp=int(time.time()) - 10)
    assert client.get("/me", headers=auth(token)).status_code == 401


def test_me_with_token_signed_by_someone_else_is_401(client, make_token):
    forged = make_token(key=ec.generate_private_key(ec.SECP256R1()))
    assert client.get("/me", headers=auth(forged)).status_code == 401


def test_me_with_wrong_audience_is_401(client, make_token):
    token = make_token(aud="something-else")
    assert client.get("/me", headers=auth(token)).status_code == 401


def test_me_with_wrong_issuer_is_401(client, make_token):
    token = make_token(iss="https://evil.example.com/auth/v1")
    assert client.get("/me", headers=auth(token)).status_code == 401


def test_me_without_subject_is_401(client, make_token):
    assert client.get("/me", headers=auth(make_token(sub=None))).status_code == 401
