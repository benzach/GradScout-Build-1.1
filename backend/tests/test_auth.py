"""
Tests for self-hosted authentication: password hashing and access
tokens (app/security.py), the get_current_user dependency (app/auth.py),
and the signup/login endpoints (app/routers/auth.py).

Replaces the old Supabase-JWKS test suite entirely — there's no
external identity provider left to simulate, so these tests exercise
the real mechanism directly rather than mocking a network call.
"""
import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-do-not-use-in-production")

import time
from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.db import get_session
from app.main import app
from app.models import User
from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

client = TestClient(app)


@pytest.fixture
def session():
    s = get_session()
    s.query(User).delete()
    s.commit()
    yield s
    s.close()


class TestPasswordHashing:
    def test_correct_password_verifies(self):
        hashed = hash_password("correct-horse-battery-staple")
        assert verify_password("correct-horse-battery-staple", hashed)

    def test_wrong_password_rejected(self):
        hashed = hash_password("correct-horse-battery-staple")
        assert not verify_password("wrong-password", hashed)

    def test_empty_stored_hash_never_matches(self):
        """The migration default for pre-existing rows — must never verify as a match."""
        assert not verify_password("anything", "")

    def test_two_hashes_of_same_password_differ(self):
        """Confirms real per-hash salting, not a deterministic/broken shortcut."""
        assert hash_password("same-password") != hash_password("same-password")


class TestAccessTokens:
    def test_round_trip(self):
        user_id = uuid4()
        token = create_access_token(user_id)
        assert decode_access_token(token) == user_id

    def test_expired_token_rejected(self):
        from app.security import JWT_ALGORITHM, JWT_SECRET_KEY, ExpiredTokenError

        now = int(time.time())
        expired = jwt.encode(
            {"sub": str(uuid4()), "iat": now - 100, "exp": now - 50},
            JWT_SECRET_KEY, algorithm=JWT_ALGORITHM,
        )
        with pytest.raises(ExpiredTokenError):
            decode_access_token(expired)

    def test_token_signed_with_wrong_secret_rejected(self):
        from app.security import JWT_ALGORITHM, InvalidTokenError

        now = int(time.time())
        forged = jwt.encode(
            {"sub": str(uuid4()), "iat": now, "exp": now + 3600},
            "not-the-real-secret", algorithm=JWT_ALGORITHM,
        )
        with pytest.raises(InvalidTokenError):
            decode_access_token(forged)

    def test_token_missing_subject_claim_rejected(self):
        from app.security import JWT_ALGORITHM, JWT_SECRET_KEY, InvalidTokenError

        now = int(time.time())
        no_sub = jwt.encode({"iat": now, "exp": now + 3600}, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        with pytest.raises(InvalidTokenError):
            decode_access_token(no_sub)


class TestGetCurrentUser:
    def test_valid_token_for_existing_user_succeeds(self, session):
        user = User(email="real@example.com", password_hash=hash_password("whatever123"))
        session.add(user)
        session.commit()

        token = create_access_token(user.id)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        result = get_current_user(credentials=creds, session=session)

        assert result.id == user.id
        assert result.email == "real@example.com"

    def test_token_for_nonexistent_user_rejected(self, session):
        """
        Deliberately different from the old Supabase-backed behaviour,
        which auto-provisioned a row on first sight of a valid token
        (necessary there, since Supabase managed identity separately
        from this app's own `users` table). Now GradScout only ever
        issues a token for a user that already has a row (see
        routers/auth.py), so a well-signed token with no matching row
        means the account was deleted after the token was issued —
        correctly rejected, not silently re-created.
        """
        token = create_access_token(uuid4())
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=creds, session=session)
        assert exc_info.value.status_code == 401

    def test_malformed_token_rejected(self, session):
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not-a-real-jwt")
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=creds, session=session)
        assert exc_info.value.status_code == 401


class TestSignupEndpoint:
    def test_signup_creates_account_and_returns_working_token(self, session):
        r = client.post("/auth/signup", json={"email": "new@example.com", "password": "at-least-8-chars"})
        assert r.status_code == 201
        body = r.json()
        assert body["user"]["email"] == "new@example.com"
        assert body["token_type"] == "bearer"

        r2 = client.get("/criteria", headers={"Authorization": f"Bearer {body['access_token']}"})
        assert r2.status_code == 200

    def test_duplicate_email_rejected(self, session):
        client.post("/auth/signup", json={"email": "dupe@example.com", "password": "at-least-8-chars"})
        r = client.post("/auth/signup", json={"email": "dupe@example.com", "password": "different-pass"})
        assert r.status_code == 400

    def test_short_password_rejected(self, session):
        r = client.post("/auth/signup", json={"email": "short@example.com", "password": "short"})
        assert r.status_code == 422  # pydantic min_length=8, before this ever reaches the DB

    def test_password_never_stored_in_plaintext(self, session):
        client.post("/auth/signup", json={"email": "plain@example.com", "password": "at-least-8-chars"})
        user = session.query(User).filter_by(email="plain@example.com").first()
        assert user.password_hash != "at-least-8-chars"
        assert user.password_hash.startswith("$2")  # bcrypt's own format prefix

    def test_concurrent_signup_race_returns_400_not_500(self):
        """
        The pre-check and the insert aren't atomic. Reproduces the real
        race directly with two separate DB sessions, rather than trying
        to actually win a timing race through the HTTP client (which
        can't control transaction timing this precisely, and would be
        flaky by nature if it tried).
        """
        from fastapi import HTTPException
        from app.routers.auth import signup
        from app.schemas import SignupRequest

        session_a = get_session()
        session_b = get_session()
        try:
            body = SignupRequest(email="race-condition@example.com", password="at-least-8-chars")

            # Both "requests" pass the pre-check before either commits —
            # this is the exact window the code needs to survive.
            assert session_a.query(User).filter_by(email=body.email).first() is None
            assert session_b.query(User).filter_by(email=body.email).first() is None

            signup(body=body, session=session_b)  # wins the race, commits cleanly

            # session_a still thinks the coast is clear — this must not 500.
            with pytest.raises(HTTPException) as exc_info:
                signup(body=body, session=session_a)
            assert exc_info.value.status_code == 400
        finally:
            session_a.close()
            session_b.close()


class TestLoginEndpoint:
    def test_correct_credentials_succeed(self, session):
        client.post("/auth/signup", json={"email": "login@example.com", "password": "correct-password"})
        r = client.post("/auth/login", json={"email": "login@example.com", "password": "correct-password"})
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_wrong_password_rejected(self, session):
        client.post("/auth/signup", json={"email": "login2@example.com", "password": "correct-password"})
        r = client.post("/auth/login", json={"email": "login2@example.com", "password": "wrong-password"})
        assert r.status_code == 401

    def test_nonexistent_email_rejected(self, session):
        r = client.post("/auth/login", json={"email": "nobody@example.com", "password": "whatever123"})
        assert r.status_code == 401


class TestAccountDeletion:
    def test_wrong_password_rejected(self, session):
        r = client.post("/auth/signup", json={"email": "delete1@example.com", "password": "correct-password"})
        token = r.json()["access_token"]

        r = client.request(
            "DELETE", "/auth/me", json={"password": "wrong-password"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 401
        # Still there — a rejected deletion must not have deleted anything.
        assert session.query(User).filter_by(email="delete1@example.com").count() == 1

    def test_correct_password_deletes_account(self, session):
        r = client.post("/auth/signup", json={"email": "delete2@example.com", "password": "correct-password"})
        token = r.json()["access_token"]

        r = client.request(
            "DELETE", "/auth/me", json={"password": "correct-password"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 204
        assert session.query(User).filter_by(email="delete2@example.com").count() == 0

    def test_deletion_cascades_to_everything(self, session):
        """
        The actual point of this feature: a privacy notice promising
        "delete everything" is only true if this cascade genuinely
        works, not just the login row. Proven directly against the
        real tables here rather than assumed from the migrations'
        ON DELETE CASCADE alone.
        """
        from app.models import Job, JobSource, PushSubscription, SearchCriteria, UserJobMatch

        # This file's own `session` fixture only cleans up Users (its
        # other tests never touch jobs) — but /feed matches against
        # every Job currently in the shared dev database, and a broad
        # "graduate" keyword can otherwise pick up leftover rows from
        # other test files run earlier in the same session.
        session.query(UserJobMatch).delete()
        session.query(JobSource).delete()
        session.query(Job).delete()
        session.commit()

        r = client.post("/auth/signup", json={"email": "delete3@example.com", "password": "correct-password"})
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        user_id = r.json()["user"]["id"]

        client.post("/criteria", json={"keywords": ["graduate"]}, headers=headers)

        job = Job(
            title="Graduate Analyst", normalized_title="graduate analyst",
            company="Barclays", normalized_company="barclays",
            location="London", normalized_location="london", location_category="London",
        )
        session.add(job)
        session.flush()
        session.add(JobSource(job_id=job.id, site="adzuna", source_url="https://example.com/1", raw_title="x"))
        session.commit()
        client.get("/feed", headers=headers)  # materializes a real UserJobMatch row

        client.post(
            "/push/subscriptions",
            json={"endpoint": "https://push.example.com/delete-test", "keys": {"p256dh": "a", "auth": "b"}},
            headers=headers,
        )

        assert session.query(SearchCriteria).filter_by(user_id=user_id).count() == 1
        assert session.query(UserJobMatch).filter_by(user_id=user_id).count() == 1
        assert session.query(PushSubscription).filter_by(user_id=user_id).count() == 1

        r = client.request("DELETE", "/auth/me", json={"password": "correct-password"}, headers=headers)
        assert r.status_code == 204

        assert session.query(SearchCriteria).filter_by(user_id=user_id).count() == 0
        assert session.query(UserJobMatch).filter_by(user_id=user_id).count() == 0
        assert session.query(PushSubscription).filter_by(user_id=user_id).count() == 0

    def test_requires_auth(self):
        r = client.request("DELETE", "/auth/me", json={"password": "whatever"})
        assert r.status_code == 401

    def test_deleted_token_no_longer_works(self, session):
        r = client.post("/auth/signup", json={"email": "delete4@example.com", "password": "correct-password"})
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        client.request("DELETE", "/auth/me", json={"password": "correct-password"}, headers=headers)

        r = client.get("/criteria", headers=headers)
        assert r.status_code == 401  # the same token can't be reused once the account it belongs to is gone
