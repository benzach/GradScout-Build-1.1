"""
Weekly email digest — a fallback (really, a complement) to push
notifications (see app/notifications.py) for people who haven't
installed the PWA, or hit iOS Safari's real push-adoption friction (see
components/InstallBanner.jsx). A weekly summary email reaches an
account regardless of any of that.

Independent of push, not conditional on its absence — someone with
both enabled just gets both, which is reasonable (a real-time nudge and
a weekly roundup serve different moments), and checking "does this user
have a currently-working push subscription" would add real complexity
for a distinction that doesn't obviously need to exist yet.

Uses Resend's HTTP API (api.resend.com) via plain requests, not their
Python SDK — matches this codebase's established pattern of avoiding a
dependency for something one HTTP call fully covers (see
app/ai_classification.py for the same reasoning, with Anthropic's own
API). Entirely optional: RESEND_API_KEY / DIGEST_FROM_EMAIL unset means
send_weekly_digests() is a deliberate, total no-op — not "try and fail
per user" — see the guard at the top of that function for why that
distinction matters here specifically.
"""
import os
from datetime import datetime, timedelta, timezone

import requests

from app.models import User, UserJobMatch

RESEND_API_URL = "https://api.resend.com/emails"
DEFAULT_DIGEST_LOOKBACK_DAYS = 7
_TIMEOUT_SECONDS = 15


def _send_email(to: str, subject: str, html: str, api_key: str, from_address: str) -> bool:
    """Low-level send via Resend. Returns True on success, False on any failure — never raises."""
    try:
        response = requests.post(
            RESEND_API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"from": from_address, "to": [to], "subject": subject, "html": html},
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"  -> digest email failed for {to}: {e}")
        return False


def _build_digest_html(matches: list[UserJobMatch], frontend_base: str) -> str:
    rows = []
    for match in matches:
        job = match.job
        location = job.location_category or job.location or ""
        meta = " · ".join(p for p in (location, job.salary_text or "") if p)
        link = f"{frontend_base}/jobs/{match.id}" if frontend_base else "#"
        rows.append(
            f'<tr><td style="padding:12px 0;border-bottom:1px solid #e3e6ef;">'
            f'<a href="{link}" style="color:#3A405A;font-weight:600;text-decoration:none;font-size:15px;">{job.title}</a><br/>'
            f'<span style="color:#4B526E;font-size:13px;">{job.company}</span><br/>'
            f'<span style="color:#7B84A0;font-size:12px;">{meta}</span>'
            f'</td></tr>'
        )

    settings_link = f"{frontend_base}/settings" if frontend_base else "#"
    plural = "es" if len(matches) != 1 else ""

    return (
        '<div style="font-family:sans-serif;max-width:480px;margin:0 auto;">'
        '<h2 style="color:#3A405A;">Your GradScout digest</h2>'
        f'<p style="color:#4B526E;font-size:14px;">{len(matches)} new job{"s" if len(matches) != 1 else ""} '
        'matching your saved searches this week.</p>'
        f'<table style="width:100%;border-collapse:collapse;">{"".join(rows)}</table>'
        f'<p style="color:#7B84A0;font-size:12px;margin-top:24px;">'
        f'Don\'t want these? Turn off email digests any time from '
        f'<a href="{settings_link}" style="color:#4B526E;">Settings</a>.</p>'
        '</div>'
    )


def send_weekly_digests(session, lookback_days: int | None = None) -> dict:
    """
    Sends one digest email per eligible user, covering matches created
    since their last digest (or, for a user who's never had one, the
    last `lookback_days`). Matches the user has already dismissed are
    left out — no point resurfacing something they've already said
    "not interested" to.

    Deliberately checks configuration ONCE, up front, rather than
    per-user: if Resend isn't configured at all, this is a total no-op
    that touches nothing — critically, it does NOT advance anyone's
    last_digest_sent_at. Advancing that cursor while no email was
    actually sent would silently shrink the window of the FIRST real
    digest once Resend eventually does get configured (it would only
    cover the gap since this no-op ran, not the user's actual full
    backlog) — the same failure mode a naive "try to send, catch the
    error, move on" per-user loop would produce by accident.

    Returns a summary dict for logging/testing.
    """
    api_key = os.environ.get("RESEND_API_KEY")
    from_address = os.environ.get("DIGEST_FROM_EMAIL")
    summary = {"configured": bool(api_key and from_address), "users_considered": 0, "emails_sent": 0, "skipped_no_matches": 0}

    if not summary["configured"]:
        return summary

    frontend_base = os.environ.get("FRONTEND_BASE_URL", "").rstrip("/")
    if lookback_days is None:
        lookback_days = int(os.environ.get("DIGEST_LOOKBACK_DAYS", str(DEFAULT_DIGEST_LOOKBACK_DAYS)))

    now = datetime.now(timezone.utc)
    users = session.query(User).filter_by(email_digest_enabled=True).all()

    for user in users:
        summary["users_considered"] += 1
        since = user.last_digest_sent_at or (now - timedelta(days=lookback_days))

        matches = (
            session.query(UserJobMatch)
            .filter_by(user_id=user.id)
            .filter(UserJobMatch.matched_at >= since)
            .filter(UserJobMatch.status != "dismissed")
            .order_by(UserJobMatch.matched_at.desc())
            .all()
        )

        if matches:
            html = _build_digest_html(matches, frontend_base)
            subject = f"{len(matches)} new graduate job match{'es' if len(matches) != 1 else ''}"
            if _send_email(user.email, subject, html, api_key, from_address):
                summary["emails_sent"] += 1
        else:
            summary["skipped_no_matches"] += 1

        # Cursor advances either way (matches or not) - this IS
        # configured and this user WAS actually considered, so next
        # week's window should start from now, not silently re-include
        # this same empty week again next time.
        user.last_digest_sent_at = now

    session.commit()
    return summary
