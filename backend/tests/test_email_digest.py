"""
Tests for app/email_digest.py. Uses a real database (fixtures build
real User/Job/UserJobMatch rows) but mocks the actual Resend HTTP call
— no real emails ever get sent by this suite.
"""
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.db import get_session
from app.email_digest import send_weekly_digests
from app.models import Job, JobSource, User, UserJobMatch


@pytest.fixture
def session():
    s = get_session()
    s.query(UserJobMatch).delete()
    s.query(JobSource).delete()
    s.query(Job).delete()
    s.query(User).delete()
    s.commit()
    yield s
    s.close()


def _make_match(session, user, **job_overrides):
    job_defaults = dict(
        title="Graduate Analyst", normalized_title="graduate analyst",
        company="Barclays", normalized_company="barclays",
        location="London", normalized_location="london", location_category="London",
    )
    job = Job(**{**job_defaults, **job_overrides})
    session.add(job)
    session.flush()
    match = UserJobMatch(user_id=user.id, job_id=job.id)
    session.add(match)
    session.flush()
    return match


_CONFIGURED_ENV = {
    "RESEND_API_KEY": "re_fake_key",
    "DIGEST_FROM_EMAIL": "digest@example.com",
    "FRONTEND_BASE_URL": "https://gradscout.example",
}


class _FakeResponse:
    def raise_for_status(self):
        pass


class TestUnconfigured:
    def test_unconfigured_is_a_total_noop(self, session):
        """No RESEND_API_KEY at all - must touch nothing, not even advance any cursors."""
        user = User(email="a@example.com")
        session.add(user)
        session.commit()
        _make_match(session, user)

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("RESEND_API_KEY", None)
            with patch("app.email_digest.requests.post") as mock_post:
                summary = send_weekly_digests(session)

        assert summary["configured"] is False
        mock_post.assert_not_called()
        session.refresh(user)
        assert user.last_digest_sent_at is None  # cursor NOT advanced


class TestConfigured:
    def test_sends_digest_for_user_with_new_matches(self, session):
        user = User(email="b@example.com")
        session.add(user)
        session.commit()
        _make_match(session, user)

        with patch.dict(os.environ, _CONFIGURED_ENV), \
             patch("app.email_digest.requests.post", return_value=_FakeResponse()) as mock_post:
            summary = send_weekly_digests(session)

        assert summary["configured"] is True
        assert summary["emails_sent"] == 1
        mock_post.assert_called_once()
        sent_json = mock_post.call_args.kwargs["json"]
        assert sent_json["to"] == ["b@example.com"]
        assert sent_json["from"] == "digest@example.com"
        assert "Graduate Analyst" in sent_json["html"]

    def test_advances_cursor_after_sending(self, session):
        user = User(email="c@example.com")
        session.add(user)
        session.commit()
        _make_match(session, user)

        with patch.dict(os.environ, _CONFIGURED_ENV), \
             patch("app.email_digest.requests.post", return_value=_FakeResponse()):
            send_weekly_digests(session)

        session.refresh(user)
        assert user.last_digest_sent_at is not None

    def test_user_with_no_new_matches_gets_no_email_but_cursor_still_advances(self, session):
        """So an empty week isn't silently re-included in next week's window too."""
        user = User(email="d@example.com")
        session.add(user)
        session.commit()

        with patch.dict(os.environ, _CONFIGURED_ENV), \
             patch("app.email_digest.requests.post") as mock_post:
            summary = send_weekly_digests(session)

        assert summary["skipped_no_matches"] == 1
        mock_post.assert_not_called()
        session.refresh(user)
        assert user.last_digest_sent_at is not None

    def test_user_with_digest_disabled_is_skipped_entirely(self, session):
        user = User(email="e@example.com", email_digest_enabled=False)
        session.add(user)
        session.commit()
        _make_match(session, user)

        with patch.dict(os.environ, _CONFIGURED_ENV), \
             patch("app.email_digest.requests.post") as mock_post:
            summary = send_weekly_digests(session)

        assert summary["users_considered"] == 0
        mock_post.assert_not_called()

    def test_dismissed_matches_are_excluded_from_the_digest(self, session):
        user = User(email="f@example.com")
        session.add(user)
        session.commit()
        match = _make_match(session, user)
        match.status = "dismissed"
        session.commit()

        with patch.dict(os.environ, _CONFIGURED_ENV), \
             patch("app.email_digest.requests.post") as mock_post:
            summary = send_weekly_digests(session)

        assert summary["skipped_no_matches"] == 1
        mock_post.assert_not_called()

    def test_only_matches_since_last_digest_are_included(self, session):
        user = User(email="g@example.com")
        session.add(user)
        session.commit()

        old_match = _make_match(session, user, title="Old Match")
        old_match.matched_at = datetime.now(timezone.utc) - timedelta(days=10)
        user.last_digest_sent_at = datetime.now(timezone.utc) - timedelta(days=3)
        session.commit()

        new_match = _make_match(session, user, title="New Match")
        session.commit()

        with patch.dict(os.environ, _CONFIGURED_ENV), \
             patch("app.email_digest.requests.post", return_value=_FakeResponse()) as mock_post:
            send_weekly_digests(session)

        sent_html = mock_post.call_args.kwargs["json"]["html"]
        assert "New Match" in sent_html
        assert "Old Match" not in sent_html

    def test_failed_send_does_not_raise_and_still_advances_cursor(self, session):
        """A transient failure to send shouldn't crash the whole cycle - same failure-isolation principle as app/notifications.py."""
        import requests as requests_module

        user = User(email="h@example.com")
        session.add(user)
        session.commit()
        _make_match(session, user)

        with patch.dict(os.environ, _CONFIGURED_ENV), \
             patch("app.email_digest.requests.post", side_effect=requests_module.exceptions.Timeout("simulated")):
            summary = send_weekly_digests(session)  # must not raise

        assert summary["emails_sent"] == 0
        session.refresh(user)
        assert user.last_digest_sent_at is not None
