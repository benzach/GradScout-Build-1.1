"""
Sends real push notifications via the Web Push protocol (pywebpush),
using VAPID credentials — see scripts/generate_vapid_keys.py for how
those get created, and app/routers/push.py for how a subscription gets
here in the first place.

Deliberately isolated from app/matching.py and app/scheduler.py: those
modules decide WHAT counts as a new match; this module only knows HOW
to tell someone about one, once that decision's already been made.
Keeping "decide" and "notify" as separate steps is what keeps a live
GET /feed request — which also calls compute_and_materialize_matches,
every time anyone opens the app — from ever accidentally sending a
push. Only app/scheduler.py's background cycle calls
send_notifications_for_new_matches; the feed endpoint never does.
"""
import json
import os
from datetime import datetime, timezone

from pywebpush import WebPushException, webpush

from app.models import PushSubscription, UserJobMatch

VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_SUBJECT_EMAIL = os.environ.get("VAPID_SUBJECT_EMAIL", "")


def send_notifications_for_new_matches(session, new_matches: list[UserJobMatch]) -> dict:
    """
    Attempts delivery for every given match, to every push subscription
    its user has. Never raises — a failure to notify one user about one
    match should never stop the scheduler cycle for everyone else,
    matching the same failure-isolation principle used throughout this
    codebase (see app/scheduler.py's per-user try/except).

    notified_at gets set once delivery has been ATTEMPTED, not only on
    confirmed success — this is a deliberate simplification. It means
    a genuinely transient failure (the push service being briefly down)
    won't be retried on the next cycle, since by then this match is no
    longer "new". Acceptable for a closed test at this scale; a proper
    retry queue would be real added complexity for a failure mode that,
    in practice, should be rare.
    """
    summary = {"attempted": 0, "sent": 0, "expired_removed": 0, "errors": []}

    if not VAPID_PRIVATE_KEY or not VAPID_SUBJECT_EMAIL:
        # Not configured yet — deliberately silent rather than logging
        # an error on every single cycle, since a fresh deploy without
        # VAPID keys set up is a completely normal, expected state
        # while the rest of the app is still being tested.
        return summary

    # Grouped by user so a user with multiple new matches in the same
    # cycle only needs one subscription lookup, not one per match.
    matches_by_user: dict = {}
    for match in new_matches:
        matches_by_user.setdefault(match.user_id, []).append(match)

    for user_id, user_matches in matches_by_user.items():
        subscriptions = session.query(PushSubscription).filter_by(user_id=user_id).all()

        for match in user_matches:
            summary["attempted"] += 1
            job = match.job
            location_bit = job.location_category or job.location or ""
            payload = json.dumps({
                "title": f"New match: {job.title}",
                "body": f"{job.company} — {location_bit}" if location_bit else job.company,
                "match_id": str(match.id),
            })

            if not subscriptions:
                # Nobody to send to yet (permission never granted, or
                # granted on a device not currently subscribed) — still
                # marked processed so this exact match isn't
                # reconsidered every cycle forever. See this function's
                # own docstring on what notified_at actually means.
                match.notified_at = datetime.now(timezone.utc)
                continue

            delivered_to_at_least_one = False
            for sub in list(subscriptions):  # list() — session.delete() below mutates the underlying query result otherwise
                try:
                    webpush(
                        subscription_info={
                            "endpoint": sub.endpoint,
                            "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                        },
                        data=payload,
                        vapid_private_key=VAPID_PRIVATE_KEY,
                        vapid_claims={"sub": f"mailto:{VAPID_SUBJECT_EMAIL}"},
                    )
                    delivered_to_at_least_one = True
                except WebPushException as e:
                    status_code = e.response.status_code if e.response is not None else None
                    if status_code in (404, 410):
                        # The push service itself is saying this
                        # subscription will never work again —
                        # uninstalled, permission revoked, or expired.
                        # Removing it now is what keeps this from
                        # silently failing on every future cycle too.
                        session.delete(sub)
                        summary["expired_removed"] += 1
                    else:
                        summary["errors"].append(f"user={user_id} endpoint={sub.endpoint[:50]}...: {e}")

            if delivered_to_at_least_one:
                summary["sent"] += 1
            match.notified_at = datetime.now(timezone.utc)

    session.commit()
    return summary
