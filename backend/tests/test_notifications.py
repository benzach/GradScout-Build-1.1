"""
Tests for app/notifications.py — the actual push-sending logic.
webpush() itself is always mocked here: these tests are about OUR
orchestration (grouping by user, handling expired subscriptions,
marking notified_at, never crashing the caller), not about proving the
Web Push protocol implementation works, which is pywebpush's job to
test, not ours.
"""
import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-do-not-use-in-production")

from unittest.mock import MagicMock, patch

import pytest

from app.db import get_session
from app.models import Job, PushSubscription, SearchCriteria, User, UserJobMatch
from app.notifications import send_notifications_for_new_matches
from pywebpush import WebPushException


@pytest.fixture
def session():
    s = get_session()
    s.query(UserJobMatch).delete()
    s.query(PushSubscription).delete()
    s.query(Job).delete()
    s.query(SearchCriteria).delete()
    s.query(User).delete()
    s.commit()
    yield s
    s.close()


def _make_match(session, email="notif-test@example.com"):
    user = User(email=email)
    session.add(user)
    session.flush()

    job = Job(
        title="Graduate Analyst", normalized_title="graduate analyst",
        company="Barclays", normalized_company="barclays",
        location="London", normalized_location="london", location_category="London",
    )
    session.add(job)
    session.flush()

    match = UserJobMatch(user_id=user.id, job_id=job.id, status="new")
    session.add(match)
    session.commit()
    return user, match


@pytest.fixture(autouse=True)
def vapid_configured(monkeypatch):
    """Every test in this file gets real-looking VAPID config by default — test_no_vapid_keys_configured_returns_silently explicitly unsets it instead."""
    monkeypatch.setattr("app.notifications.VAPID_PRIVATE_KEY", "fake-private-key-for-tests")
    monkeypatch.setattr("app.notifications.VAPID_SUBJECT_EMAIL", "test@example.com")


class TestNotificationSending:
    def test_no_vapid_keys_configured_returns_silently(self, session, monkeypatch):
        monkeypatch.setattr("app.notifications.VAPID_PRIVATE_KEY", "")
        _, match = _make_match(session)

        summary = send_notifications_for_new_matches(session, [match])

        assert summary == {"attempted": 0, "sent": 0, "expired_removed": 0, "errors": []}
        assert match.notified_at is None  # never touched — not even attempted

    def test_no_subscriptions_still_marks_notified(self, session):
        """Nobody to send to (permission never granted) — must not be retried forever, so notified_at still gets set."""
        _, match = _make_match(session)

        with patch("app.notifications.webpush") as mock_webpush:
            summary = send_notifications_for_new_matches(session, [match])
            mock_webpush.assert_not_called()

        assert summary["attempted"] == 1
        assert summary["sent"] == 0
        assert match.notified_at is not None

    def test_successful_send_marks_notified_and_counts_sent(self, session):
        user, match = _make_match(session)
        session.add(PushSubscription(user_id=user.id, endpoint="https://push.example.com/abc", p256dh="key", auth="auth"))
        session.commit()

        with patch("app.notifications.webpush") as mock_webpush:
            summary = send_notifications_for_new_matches(session, [match])
            assert mock_webpush.call_count == 1
            call_kwargs = mock_webpush.call_args.kwargs
            assert call_kwargs["subscription_info"]["endpoint"] == "https://push.example.com/abc"
            assert call_kwargs["vapid_claims"] == {"sub": "mailto:test@example.com"}

        assert summary["sent"] == 1
        assert match.notified_at is not None

    def test_expired_subscription_is_removed(self, session):
        user, match = _make_match(session)
        session.add(PushSubscription(user_id=user.id, endpoint="https://push.example.com/dead", p256dh="key", auth="auth"))
        session.commit()

        fake_response = MagicMock(status_code=410)
        with patch("app.notifications.webpush", side_effect=WebPushException("Gone", response=fake_response)):
            summary = send_notifications_for_new_matches(session, [match])

        assert summary["expired_removed"] == 1
        assert summary["sent"] == 0
        remaining = session.query(PushSubscription).filter_by(endpoint="https://push.example.com/dead").first()
        assert remaining is None  # actually deleted, not just marked somehow

    def test_non_expiry_error_recorded_but_does_not_crash(self, session):
        user, match = _make_match(session)
        session.add(PushSubscription(user_id=user.id, endpoint="https://push.example.com/flaky", p256dh="key", auth="auth"))
        session.commit()

        fake_response = MagicMock(status_code=500)
        with patch("app.notifications.webpush", side_effect=WebPushException("Server error", response=fake_response)):
            summary = send_notifications_for_new_matches(session, [match])  # must not raise

        assert len(summary["errors"]) == 1
        assert summary["sent"] == 0
        # A 500 isn't a "this will never work" signal like 410 is — the subscription should survive to be retried next time.
        still_there = session.query(PushSubscription).filter_by(endpoint="https://push.example.com/flaky").first()
        assert still_there is not None

    def test_one_of_several_subscriptions_succeeding_counts_as_sent(self, session):
        """A user with two devices, one dead: still counts as delivered overall, since they were reached on at least one."""
        user, match = _make_match(session)
        session.add(PushSubscription(user_id=user.id, endpoint="https://push.example.com/dead2", p256dh="k", auth="a"))
        session.add(PushSubscription(user_id=user.id, endpoint="https://push.example.com/alive", p256dh="k", auth="a"))
        session.commit()

        fake_response = MagicMock(status_code=410)

        def side_effect(*args, **kwargs):
            if kwargs["subscription_info"]["endpoint"].endswith("dead2"):
                raise WebPushException("Gone", response=fake_response)
            return None  # the "alive" one succeeds

        with patch("app.notifications.webpush", side_effect=side_effect):
            summary = send_notifications_for_new_matches(session, [match])

        assert summary["sent"] == 1
        assert summary["expired_removed"] == 1

    def test_multiple_matches_for_same_user_all_processed(self, session):
        user, match1 = _make_match(session, email="multi@example.com")
        job2 = Job(
            title="Graduate Engineer", normalized_title="graduate engineer",
            company="Google", normalized_company="google",
            location="London", normalized_location="london", location_category="London",
        )
        session.add(job2)
        session.flush()
        match2 = UserJobMatch(user_id=user.id, job_id=job2.id, status="new")
        session.add(match2)
        session.add(PushSubscription(user_id=user.id, endpoint="https://push.example.com/multi", p256dh="k", auth="a"))
        session.commit()

        with patch("app.notifications.webpush") as mock_webpush:
            summary = send_notifications_for_new_matches(session, [match1, match2])
            assert mock_webpush.call_count == 2  # one send per match, same subscription reused for both

        assert summary["attempted"] == 2
        assert summary["sent"] == 2
