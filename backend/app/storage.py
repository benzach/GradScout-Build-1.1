"""
Storage layer — where the dedup engine (Phase 0, pure Python, no DB
knowledge) meets real persistence.

This module does two dedup checks, in order, and it's worth understanding
why there are two rather than one:

1. EXACT check (cheap): has this exact URL from this exact site been
   scraped before? A unique constraint on job_sources(site, source_url)
   makes this a single indexed lookup. Every re-scrape of a posting we
   already know about gets caught HERE, for almost no cost — this matters
   because a scheduler polling every 15-30 minutes will re-fetch mostly
   the same jobs over and over; without this check, every single one of
   them would run through the expensive fuzzy engine every single cycle.

2. FUZZY check (only for genuinely new URLs): is this a new posting for
   a job we've already seen from a DIFFERENT source? This is Phase 0's
   dedup engine, unchanged — normalize -> block -> score -> decide.

On the fuzzy check's candidate pool: rather than re-implementing the
blocking company-match logic in SQL, we fetch a coarse pool from the
database (jobs posted within the last 30 days — a plain indexed range
query) and hand it to the ALREADY-TESTED Python blocking/scoring logic
from Phase 0 unchanged. This preserves exact fidelity with everything we
validated in Phase 0's test suite, at the cost of fetching a wider pool
than strictly necessary. At real scale (many thousands of jobs/day) the
known next optimization is adding a Postgres trigram index (pg_trgm
extension) so the company-fuzzy-match narrowing happens in SQL too — not
needed yet, and deliberately deferred rather than built speculatively.
"""
from datetime import datetime, timedelta, timezone
import os

from sqlalchemy.orm import Session

from app.models import Job, JobSource
from app.dedup.engine import dedup_against_existing
from app.dedup.normalize import normalize_title, normalize_company, normalize_location
from app.dedup.scoring import parse_salary_range
from app.locations import categorize_location, CANONICAL_LOCATIONS
from app.industries import categorize_industry, CANONICAL_INDUSTRIES
from app.ai_classification import classify_location_with_ai, classify_industry_with_ai

CANDIDATE_POOL_WINDOW_DAYS = 30


def _job_row_to_dict(job: Job) -> dict:
    """Converts a Job ORM row into the plain dict shape the (DB-agnostic) dedup engine expects."""
    return {
        "id": str(job.id),
        "title": job.title,
        "company": job.company,
        "location": job.location or "",
        "salary": job.salary_text or "",
        "description": job.description or "",
        "posted_date": job.posted_date.isoformat() if job.posted_date else "",
    }


def _fetch_candidate_pool(session: Session) -> list[dict]:
    """Coarse pre-filter: jobs posted recently, or with no parseable date at all."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=CANDIDATE_POOL_WINDOW_DAYS)
    rows = (
        session.query(Job)
        .filter((Job.posted_date == None) | (Job.posted_date >= cutoff))  # noqa: E711
        .all()
    )
    return [_job_row_to_dict(r) for r in rows]


def _classify_location(raw_location: str, remote_type: str, job_title: str) -> str:
    """
    Two-pass location classification: the fast, free, deterministic
    rules in app/locations.py first, then — only for the jobs that
    didn't resolve — a second attempt via app/ai_classification.py.
    See that module's docstring for why this stays a fallback rather
    than the primary path. A failed or unconfigured AI pass just keeps
    the rule-based "Other UK" result; it never makes things worse.
    """
    result = categorize_location(raw_location, remote_type)
    if result != "Other UK":
        return result
    ai_result = classify_location_with_ai(raw_location, job_title, CANONICAL_LOCATIONS)
    return ai_result or result


def _classify_industry(job_title: str, description: str) -> str:
    """Same two-pass pattern as _classify_location, for industry."""
    result = categorize_industry(job_title, description)
    if result != "Other":
        return result
    ai_result = classify_industry_with_ai(job_title, description, CANONICAL_INDUSTRIES)
    return ai_result or result


def _build_job_row(scraped_job: dict, possible_duplicate_of=None) -> Job:
    norm_title, remote_from_title = normalize_title(scraped_job.get("title", ""))
    norm_location, remote_from_location = normalize_location(scraped_job.get("location", ""))
    salary_min, salary_max = parse_salary_range(scraped_job.get("salary", ""))
    remote_type = remote_from_title or remote_from_location

    return Job(
        title=scraped_job.get("title", ""),
        normalized_title=norm_title,
        company=scraped_job.get("company", ""),
        normalized_company=normalize_company(scraped_job.get("company", "")),
        location=scraped_job.get("location", ""),
        normalized_location=norm_location,
        location_category=_classify_location(scraped_job.get("location", ""), remote_type, scraped_job.get("title", "")),
        remote_type=remote_type,
        salary_text=scraped_job.get("salary", ""),
        salary_min=salary_min,
        salary_max=salary_max,
        contract_type=scraped_job.get("contract_type", ""),
        industry_category=_classify_industry(scraped_job.get("title", ""), scraped_job.get("description", "")),
        description=scraped_job.get("description", ""),
        posted_date=_try_parse_date(scraped_job.get("posted_date", "")),
        possible_duplicate_of=possible_duplicate_of,
    )


def _try_parse_date(date_str: str):
    if not date_str:
        return None
    from app.dedup.scoring import _try_parse_date as parse_fn
    return parse_fn(date_str)


def process_scraped_job(session: Session, site_name: str, scraped_job: dict) -> dict:
    """
    The main entry point this module exposes. Takes one freshly-scraped
    job (plain dict — title, url, company, location, salary, description,
    posted_date, contract_type) plus which source it came from, and
    persists it correctly: as a new canonical job, merged into an
    existing one, or flagged for review.

    Returns a dict describing what happened, for logging/testing:
        {"action": "already_seen" | "insert_new" | "merge" | "flag_for_review",
         "job_id": "...", "match_score": <float, if applicable>}
    """
    source_url = scraped_job.get("url", "")

    # Layer 1: exact-URL check — cheap, catches most re-scrapes for free.
    existing_source = (
        session.query(JobSource)
        .filter_by(site=site_name, source_url=source_url)
        .first()
    )
    if existing_source:
        # Confirms this posting is still actually live, not just that we
        # once saw it — this is what a job's expiry sweep (see
        # sweep_expired_jobs below) relies on to tell "hasn't shown up in
        # a while" from "just haven't happened to re-scrape it yet".
        existing_source.scraped_at = datetime.now(timezone.utc)
        # A job that had gone quiet on every source and got marked
        # expired, then reappeared here (back on a source's results
        # again) - shouldn't stay flagged as expired once we have live
        # evidence otherwise.
        if existing_source.job.expired_at is not None:
            existing_source.job.expired_at = None
        session.commit()
        return {"action": "already_seen", "job_id": str(existing_source.job_id)}

    # Layer 2: fuzzy cross-source check — only reached for genuinely new URLs.
    candidates = _fetch_candidate_pool(session)
    outcome = dedup_against_existing(scraped_job, candidates)

    if outcome.action == "insert_new":
        job = _build_job_row(scraped_job)
        session.add(job)
        session.flush()  # assigns job.id without committing yet
        session.add(JobSource(
            job_id=job.id, site=site_name, source_url=source_url,
            raw_title=scraped_job.get("title", ""),
        ))
        session.commit()
        return {"action": "insert_new", "job_id": str(job.id)}

    elif outcome.action == "merge":
        job_id = outcome.best_match["id"]
        job = session.get(Job, job_id)
        job.last_updated_at = datetime.now(timezone.utc)
        session.add(JobSource(
            job_id=job.id, site=site_name, source_url=source_url,
            raw_title=scraped_job.get("title", ""),
        ))
        session.commit()
        return {
            "action": "merge", "job_id": str(job_id),
            "match_score": outcome.match_result.composite_score,
        }

    else:  # flag_for_review
        possible_dup_id = outcome.best_match["id"]
        job = _build_job_row(scraped_job, possible_duplicate_of=possible_dup_id)
        session.add(job)
        session.flush()
        session.add(JobSource(
            job_id=job.id, site=site_name, source_url=source_url,
            raw_title=scraped_job.get("title", ""),
        ))
        session.commit()
        return {
            "action": "flag_for_review", "job_id": str(job.id),
            "possible_duplicate_of": possible_dup_id,
            "match_score": outcome.match_result.composite_score,
        }


DEFAULT_JOB_EXPIRY_STALE_DAYS = 3


def sweep_expired_jobs(session: Session, stale_after_days: int | None = None) -> int:
    """
    Marks a job expired once NONE of its sources have been re-confirmed
    present within `stale_after_days` — see migrations/0011_job_expiry.sql
    and process_scraped_job() above for how "re-confirmed present" gets
    tracked in the first place. Called once at the end of every full
    scrape cycle (see app/pipeline.py); cheap enough to run that often
    rather than on a separate schedule, and more responsive that way too.

    This is a heuristic, not a certainty, and worth being clear-eyed
    about: a job dropping off a source's *returned* results (page 1 of
    N, typically) doesn't strictly prove the underlying posting is
    gone — just that it wasn't in this particular batch.
    `stale_after_days` exists specifically to absorb that noise: at the
    default 20-minute scrape interval (see app/scheduler.py), a
    genuinely-live posting gets dozens of chances to be re-confirmed
    well within 3 days, so the default stays conservative about calling
    something expired while still catching postings that are actually
    gone within a reasonable window. Override via the
    JOB_EXPIRY_STALE_DAYS env var if that trade-off needs adjusting for
    real observed behaviour.

    Returns the number of jobs newly marked expired, for logging.
    """
    if stale_after_days is None:
        stale_after_days = int(os.environ.get("JOB_EXPIRY_STALE_DAYS", str(DEFAULT_JOB_EXPIRY_STALE_DAYS)))
    cutoff = datetime.now(timezone.utc) - timedelta(days=stale_after_days)

    stale_jobs = (
        session.query(Job)
        .filter(Job.expired_at.is_(None))
        .filter(~Job.sources.any(JobSource.scraped_at >= cutoff))
        .all()
    )
    now = datetime.now(timezone.utc)
    for job in stale_jobs:
        job.expired_at = now
    session.commit()
    return len(stale_jobs)
