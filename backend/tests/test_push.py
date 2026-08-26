"""
Tests for app/routers/push.py — subscription registration/removal and
the VAPID public key endpoint. Sending notifications is tested
separately in test_notifications.py; this file is purely about
whether a subscription gets correctly stored against the right user.
"""
import os

os.environ.setdefault("DISABLE_SCHEDULER", "true")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-do-not-use-in-production")

import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app
from app.models import PushSubscription, User
from app.security import create_access_token, hash_password

client = TestClient(app)


@pytest.fixture
def session():
    s = get_session()
    s.query(PushSubscription).delete()
    s.query(User).delete()
    s.commit()
    yield s
    s.close()


@pytest.fixture
def auth_headers(session):
    user = User(email="push-test@example.com", password_hash=hash_password("irrelevant-for-these-tests"))
    session.add(user)
    session.commit()
    token = create_access_token(user.id)
    return user, {"Authorization": f"Bearer {token}"}


class TestVapidPublicKey:
    def test_returns_configured_key(self, monkeypatch):
        monkeypatch.setenv("VAPID_PUBLIC_KEY", "fake-public-key")
        r = client.get("/push/vapid-public-key")
        assert r.status_code == 200
        assert r.json()["public_key"] == "fake-public-key"

    def test_no_auth_required(self):
        # Deliberately public — a VAPID public key isn't a secret, and
        # the frontend may need it before anyone's signed in.
        r = client.get("/push/vapid-public-key")
        assert r.status_code == 200


class TestSubscriptionCreate:
    def test_creates_new_subscription(self, session, auth_headers):
        user, headers = auth_headers
        r = client.post(
            "/push/subscriptions",
            json={"endpoint": "https://push.example.com/new", "keys": {"p256dh": "abc", "auth": "xyz"}},
            headers=headers,
        )
        assert r.status_code == 201
        stored = session.query(PushSubscription).filter_by(endpoint="https://push.example.com/new").first()
        assert stored is not None
        assert stored.user_id == user.id
        assert stored.p256dh == "abc"

    def test_resubscribing_same_endpoint_updates_not_duplicates(self, session, auth_headers):
        user, headers = auth_headers
        payload = {"endpoint": "https://push.example.com/resub", "keys": {"p256dh": "old", "auth": "old"}}
        client.post("/push/subscriptions", json=payload, headers=headers)

        payload["keys"] = {"p256dh": "new", "auth": "new"}
        r = client.post("/push/subscriptions", json=payload, headers=headers)
        assert r.status_code == 201

        matches = session.query(PushSubscription).filter_by(endpoint="https://push.example.com/resub").all()
        assert len(matches) == 1  # updated in place, not duplicated
        assert matches[0].p256dh == "new"

    def test_requires_auth(self):
        r = client.post(
            "/push/subscriptions",
            json={"endpoint": "https://push.example.com/noauth", "keys": {"p256dh": "a", "auth": "b"}},
        )
        assert r.status_code == 401

    def test_missing_keys_rejected(self, auth_headers):
        _, headers = auth_headers
        r = client.post("/push/subscriptions", json={"endpoint": "https://push.example.com/bad"}, headers=headers)
        assert r.status_code == 422


class TestSubscriptionDelete:
    def test_removes_own_subscription(self, session, auth_headers):
        user, headers = auth_headers
        session.add(PushSubscription(user_id=user.id, endpoint="https://push.example.com/todelete", p256dh="a", auth="b"))
        session.commit()

        r = client.request(
            "DELETE", "/push/subscriptions",
            json={"endpoint": "https://push.example.com/todelete"}, headers=headers,
        )
        assert r.status_code == 204
        assert session.query(PushSubscription).filter_by(endpoint="https://push.example.com/todelete").first() is None

    def test_cannot_remove_another_users_subscription(self, session, auth_headers):
        _, headers = auth_headers
        other_user = User(email="other-push@example.com")
        session.add(other_user)
        session.flush()
        session.add(PushSubscription(user_id=other_user.id, endpoint="https://push.example.com/notyours", p256dh="a", auth="b"))
        session.commit()

        client.request(
            "DELETE", "/push/subscriptions",
            json={"endpoint": "https://push.example.com/notyours"}, headers=headers,
        )
        # Still there — the delete is scoped to the caller's own user_id, so this quietly does nothing rather than erroring.
        assert session.query(PushSubscription).filter_by(endpoint="https://push.example.com/notyours").first() is not None
