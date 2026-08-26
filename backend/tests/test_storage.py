"""
Tests for the storage layer — the DB-backed version of everything Phase
0 already proved works in pure Python. Each test runs inside a
transaction that's rolled back afterward, so tests never leave residue
in the dev database for the next test (or for you, poking around
manually) to trip over.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.db import get_session
from app.models import Job, JobSource
from app.storage import process_scraped_job, sweep_expired_jobs

# storage.py's candidate pool only looks back CANDIDATE_POOL_WINDOW_DAYS
# (30) from whenever the test actually runs. Hardcoding an absolute
# date like "2026-07-01" works today and silently starts failing once
# real time carries "today" more than 30 days past it — exactly what
# happened here. Computing dates relative to `now` instead means these
# tests stay correct indefinitely, not just on the day they were written.
_NOW = datetime.now(timezone.utc)


def _days_ago(n: int) -> str:
    return (_NOW - timedelta(days=n)).strftime("%Y-%m-%d")


@pytest.fixture
def session():
    """
    Uses a real session against the dev database, with an explicit
    cleanup before each test — NOT the more common "wrap in a
    transaction and roll back" pattern, because process_scraped_job()
    calls session.commit() internally (correctly, for production use).
    A commit on a session ends the surrounding transaction regardless of
    what a test fixture wants, which silently breaks rollback-based
    isolation. Explicit truncation sidesteps that entirely and is easier
    to reason about.
    """
    s = get_session()
    s.query(JobSource).delete()
    s.query(Job).delete()
    s.commit()
    yield s
    s.close()


def test_new_job_creates_canonical_row_and_one_source(session):
    job = {
        "title": "Graduate Analyst", "url": "https://example.com/job/1",
        "company": "Barclays", "location": "London", "salary": "£35,000",
        "description": "Join our graduate scheme.", "posted_date": _days_ago(5),
        "contract_type": "Full-time",
    }
    result = process_scraped_job(session, "adzuna", job)
    assert result["action"] == "insert_new"
    assert session.query(Job).count() == 1
    assert session.query(JobSource).count() == 1


def test_same_job_different_source_merges_not_duplicates(session):
    """The core scenario: same job, different wording, different source, different URL."""
    adzuna_job = {
        "title": "Software Engineer - Remote", "url": "https://adzuna.example/1",
        "company": "Google LLC", "location": "London (Remote)",
        "salary": "£45,000 - £55,000",
        "description": "We are looking for a talented software engineer to join our growing team in London.",
        "posted_date": _days_ago(6), "contract_type": "Full-time",
    }
    reed_job = {
        "title": "Software Developer (Remote)", "url": "https://reed.example/2",
        "company": "Google", "location": "London (Remote)",
        "salary": "£46,000 - £54,000",
        "description": "We are looking for a talented software developer to join our growing team in London.",
        "posted_date": _days_ago(5), "contract_type": "Full-time",
    }
    r1 = process_scraped_job(session, "adzuna", adzuna_job)
    r2 = process_scraped_job(session, "reed", reed_job)

    assert r1["action"] == "insert_new"
    assert r2["action"] == "merge"
    assert r1["job_id"] == r2["job_id"]  # same canonical job
    assert session.query(Job).count() == 1
    assert session.query(JobSource).count() == 2


def test_rescraping_same_url_is_cheap_noop(session):
    job = {
        "title": "Graduate Analyst", "url": "https://example.com/job/1",
        "company": "Barclays", "location": "London", "salary": "£35,000",
        "description": "Join our graduate scheme.", "posted_date": _days_ago(5),
        "contract_type": "Full-time",
    }
    process_scraped_job(session, "adzuna", job)
    result = process_scraped_job(session, "adzuna", job)  # exact same posting again
    assert result["action"] == "already_seen"
    assert session.query(Job).count() == 1
    assert session.query(JobSource).count() == 1  # not duplicated


def test_different_companies_same_title_both_kept_distinct(session):
    """Every bank has a 'Graduate Analyst' - these must never merge."""
    barclays_job = {
        "title": "Graduate Analyst", "url": "https://example.com/barclays",
        "company": "Barclays", "location": "London", "salary": "£35,000",
        "description": "Join our graduate scheme working across investment banking.",
        "posted_date": _days_ago(5), "contract_type": "Full-time",
    }
    hsbc_job = {
        "title": "Graduate Analyst", "url": "https://example.com/hsbc",
        "company": "HSBC", "location": "London", "salary": "£34,000",
        "description": "Join our graduate scheme working across investment banking.",
        "posted_date": _days_ago(5), "contract_type": "Full-time",
    }
    process_scraped_job(session, "adzuna", barclays_job)
    result = process_scraped_job(session, "reed", hsbc_job)

    assert result["action"] == "insert_new"
    assert session.query(Job).count() == 2


def test_ambiguous_case_flagged_with_link_preserved(session):
    existing = {
        "title": "Graduate Marketing Executive", "url": "https://example.com/unilever1",
        "company": "Unilever", "location": "London", "salary": "£28,000",
        "description": "Join our fast-paced marketing team working on some of the biggest consumer brands in the world today.",
        "posted_date": _days_ago(20), "contract_type": "Full-time",
    }
    ambiguous = {
        "title": "Graduate Marketing Executive", "url": "https://example.com/unilever2",
        "company": "Unilever", "location": "London", "salary": "£30,000",
        "description": "An exciting opportunity has arisen for a graduate to join our brand management division working on household names.",
        "posted_date": _days_ago(9), "contract_type": "Full-time",
    }
    process_scraped_job(session, "adzuna", existing)
    result = process_scraped_job(session, "reed", ambiguous)

    assert result["action"] == "flag_for_review"
    assert session.query(Job).count() == 2  # kept as separate rows
    flagged_job = session.query(Job).filter_by(id=result["job_id"]).first()
    assert flagged_job.possible_duplicate_of is not None  # but linked


class TestJobExpiry:
    """app/storage.py's sweep_expired_jobs() and the scraped_at-bumping/un-expiry side of process_scraped_job()."""

    def test_rescraping_bumps_scraped_at(self, session):
        job = {
            "title": "Graduate Analyst", "url": "https://example.com/job/1",
            "company": "Barclays", "location": "London", "salary": "£35,000",
            "description": "Join our graduate scheme.", "posted_date": _days_ago(5),
            "contract_type": "Full-time",
        }
        process_scraped_job(session, "adzuna", job)
        source = session.query(JobSource).filter_by(source_url="https://example.com/job/1").first()
        old_scraped_at = source.scraped_at

        process_scraped_job(session, "adzuna", job)  # re-scrape, same posting
        session.refresh(source)
        assert source.scraped_at > old_scraped_at

    def test_sweep_marks_stale_job_expired(self, session):
        job = {
            "title": "Graduate Analyst", "url": "https://example.com/job/2",
            "company": "HSBC", "location": "London", "salary": "£35,000",
            "description": "Join our graduate scheme.", "posted_date": _days_ago(10),
            "contract_type": "Full-time",
        }
        process_scraped_job(session, "adzuna", job)
        source = session.query(JobSource).filter_by(source_url="https://example.com/job/2").first()
        source.scraped_at = datetime.now(timezone.utc) - timedelta(days=10)  # hasn't been re-seen in 10 days
        session.commit()

        newly_expired = sweep_expired_jobs(session, stale_after_days=3)
        assert newly_expired == 1
        job_row = session.query(Job).filter_by(id=source.job_id).first()
        assert job_row.is_expired is True

    def test_sweep_leaves_recently_seen_job_alone(self, session):
        job = {
            "title": "Graduate Analyst", "url": "https://example.com/job/3",
            "company": "Lloyds", "location": "London", "salary": "£35,000",
            "description": "Join our graduate scheme.", "posted_date": _days_ago(1),
            "contract_type": "Full-time",
        }
        process_scraped_job(session, "adzuna", job)  # scraped_at defaults to now

        newly_expired = sweep_expired_jobs(session, stale_after_days=3)
        assert newly_expired == 0
        job_row = session.query(Job).join(JobSource).filter(JobSource.source_url == "https://example.com/job/3").first()
        assert job_row.is_expired is False

    def test_job_with_one_stale_and_one_fresh_source_stays_active(self, session):
        """A job pulled from two sites shouldn't expire just because it dropped off ONE of them."""
        adzuna_job = {
            "title": "Graduate Software Engineer", "url": "https://adzuna.example/job/4",
            "company": "Google", "location": "London", "salary": "£45,000",
            "description": "Join our engineering graduate scheme working on real products.",
            "posted_date": _days_ago(10), "contract_type": "Full-time",
        }
        reed_job = {
            "title": "Graduate Software Engineer", "url": "https://reed.example/job/4",
            "company": "Google", "location": "London", "salary": "£45,000",
            "description": "Join our engineering graduate scheme working on real products.",
            "posted_date": _days_ago(10), "contract_type": "Full-time",
        }
        r1 = process_scraped_job(session, "adzuna", adzuna_job)
        process_scraped_job(session, "reed", reed_job)  # merges into the same job

        stale_source = session.query(JobSource).filter_by(source_url="https://adzuna.example/job/4").first()
        stale_source.scraped_at = datetime.now(timezone.utc) - timedelta(days=10)
        session.commit()
        # the reed source keeps its default (just-now) scraped_at - still fresh

        newly_expired = sweep_expired_jobs(session, stale_after_days=3)
        assert newly_expired == 0
        job_row = session.query(Job).filter_by(id=r1["job_id"]).first()
        assert job_row.is_expired is False

    def test_reappearing_job_is_unexpired(self, session):
        job = {
            "title": "Graduate Analyst", "url": "https://example.com/job/5",
            "company": "NatWest", "location": "London", "salary": "£35,000",
            "description": "Join our graduate scheme.", "posted_date": _days_ago(10),
            "contract_type": "Full-time",
        }
        process_scraped_job(session, "adzuna", job)
        source = session.query(JobSource).filter_by(source_url="https://example.com/job/5").first()
        source.scraped_at = datetime.now(timezone.utc) - timedelta(days=10)
        session.commit()
        sweep_expired_jobs(session, stale_after_days=3)

        job_row = session.query(Job).filter_by(id=source.job_id).first()
        assert job_row.is_expired is True  # confirms the setup actually expired it

        process_scraped_job(session, "adzuna", job)  # site lists it again
        session.refresh(job_row)
        assert job_row.is_expired is False

