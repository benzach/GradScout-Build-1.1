"""
The scheduler — this is what turns "an API that answers when asked"
into "a system that watches constantly," which was the original point
of moving off the prototype's once-a-day GitHub Actions cron.

Runs INSIDE the same process as the FastAPI app (via APScheduler's
BackgroundScheduler, a thread, not a separate service) — so deploying
this is just deploying the API as normal; there's no second Railway
service to configure. It wakes up on an interval and does exactly two
things, using logic that already exists and is already tested:

  1. app.pipeline.run_pipeline() — scrape every enabled source, dedup,
     store (Phase 2, unchanged).
  2. app.matching.compute_and_materialize_matches() — for every user
     with at least one active criteria set, check their criteria against
     recent jobs and materialize any new matches (Phase 3, unchanged,
     now called by a timer instead of only by someone loading the feed).

Nothing about the underlying data model changes for this phase — the
scheduler is a new CALLER of code that already exists, not new business
logic. That's deliberate: it's the payoff of building compute_and_materialize_matches
as a shared, reusable function back in Phase 3/the jobs.py refactor.
"""
import os
import traceback
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.db import get_session
from app.email_digest import send_weekly_digests
from app.matching import compute_and_materialize_matches
from app.models import SearchCriteria, User
from app.notifications import send_notifications_for_new_matches
from app.pipeline import run_pipeline

SCRAPE_INTERVAL_MINUTES = int(os.environ.get("SCRAPE_INTERVAL_MINUTES", "20"))
# Cron-style day-of-week/hour, UTC. Default: Monday 08:00 UTC — a
# reasonable "start of week" moment; deliberately not tied to the
# scrape interval above, since a digest is a once-a-week thing, not a
# tighter-loop concern. See .env.example for how to change this.
DIGEST_DAY_OF_WEEK = os.environ.get("DIGEST_DAY_OF_WEEK", "mon")
DIGEST_HOUR_UTC = int(os.environ.get("DIGEST_HOUR_UTC", "8"))

_scheduler: BackgroundScheduler | None = None


def run_scheduled_cycle() -> dict:
    """
    One full cycle: scrape -> dedup -> store -> materialize matches for
    every user. Returns a summary dict — used directly by tests, and
    printed (Railway captures stdout as logs) so failures are visible,
    not silent, per the roadmap's explicit requirement for this phase.
    """
    started_at = datetime.now(timezone.utc)
    session = get_session()
    summary = {"started_at": started_at.isoformat(), "pipeline": None, "users_processed": 0, "match_errors": []}

    try:
        summary["pipeline"] = run_pipeline(session)
        print(f"[scheduler] pipeline: {summary['pipeline']}")

        # Every user with at least one active criteria set gets checked.
        # A single query for "which user_ids have an active criteria row"
        # rather than looping all users, since most of the work (the
        # actual matching) is per-criteria-set anyway.
        user_ids_with_active_criteria = {
            row[0] for row in session.query(SearchCriteria.user_id).filter_by(active=True).distinct()
        }

        # Collected across every user in this cycle, then notified
        # about in one batch at the end — see app/notifications.py's
        # module docstring for why sending only happens here, never
        # from GET /feed's call to the same matching function.
        all_new_matches = []

        for user_id in user_ids_with_active_criteria:
            user = session.get(User, user_id)
            if not user:
                continue
            criteria_list = session.query(SearchCriteria).filter_by(user_id=user_id, active=True).all()
            try:
                new_matches = []
                compute_and_materialize_matches(session, user, criteria_list, new_matches_out=new_matches)
                summary["users_processed"] += 1
                all_new_matches.extend(new_matches)
            except Exception as e:
                # One user's matching logic failing (e.g. a data
                # oddity in their criteria) shouldn't stop everyone
                # else's matches from being computed — same
                # failure-isolation principle as run_pipeline's
                # per-source handling in Phase 2.
                print(f"[scheduler] match computation failed for user {user_id}: {e}")
                summary["match_errors"].append({"user_id": str(user_id), "error": str(e)})

        if all_new_matches:
            summary["notifications"] = send_notifications_for_new_matches(session, all_new_matches)
            print(f"[scheduler] notifications: {summary['notifications']}")

    except Exception as e:
        print(f"[scheduler] cycle failed entirely: {e}")
        traceback.print_exc()
        summary["fatal_error"] = str(e)
    finally:
        session.close()

    summary["finished_at"] = datetime.now(timezone.utc).isoformat()
    print(f"[scheduler] cycle complete: {summary}")
    return summary


def run_weekly_digest_job() -> dict:
    """Separate from run_scheduled_cycle - a digest is a once-a-week concern, not something to bolt onto the scrape/match loop."""
    session = get_session()
    try:
        summary = send_weekly_digests(session)
        print(f"[scheduler] weekly digest: {summary}")
        return summary
    except Exception as e:
        print(f"[scheduler] weekly digest failed: {e}")
        traceback.print_exc()
        return {"fatal_error": str(e)}
    finally:
        session.close()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler  # already running — don't start a second one

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        run_scheduled_cycle,
        trigger=IntervalTrigger(minutes=SCRAPE_INTERVAL_MINUTES),
        id="scrape_and_match_cycle",
        next_run_time=datetime.now(timezone.utc),  # run once immediately on startup, then on the interval
        max_instances=1,  # never let two cycles overlap if one runs long
    )
    _scheduler.add_job(
        run_weekly_digest_job,
        trigger=CronTrigger(day_of_week=DIGEST_DAY_OF_WEEK, hour=DIGEST_HOUR_UTC, timezone="UTC"),
        id="weekly_email_digest",
        max_instances=1,
        # No next_run_time override here, unlike the scrape cycle above
        # — a digest running immediately on every deploy/restart would
        # mean a mid-week Railway redeploy could send an extra,
        # unexpected email. Waits for its actual scheduled time instead.
    )
    _scheduler.start()
    print(f"[scheduler] started — scrape/match every {SCRAPE_INTERVAL_MINUTES} minute(s), "
          f"digest {DIGEST_DAY_OF_WEEK} {DIGEST_HOUR_UTC}:00 UTC")
    return _scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        print("[scheduler] stopped")
