"""
Tests for the full API surface: search criteria CRUD and the job feed
(the part that actually proves criteria filtering + the get-or-create
match pattern work correctly through real HTTP requests, not just
direct function calls).

Authenticates with real self-hosted tokens (app/security.py) — no
external identity provider to simulate, so tests just create a user
row directly and sign a token for it, exercising the exact same
get_current_user() path a real request takes.
"""
import os
os.environ["DISABLE_SCHEDULER"] = "true"  # must be set before importing app.main
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-do-not-use-in-production")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db import get_session
from app.models import Job, JobSource, SearchCriteria, User, UserJobMatch
from app.locations import categorize_location
from app.industries import categorize_industry
from app.security import create_access_token, hash_password

client = TestClient(app)


@pytest.fixture
def session():
    s = get_session()
    s.query(UserJobMatch).delete()
    s.query(JobSource).delete()
    s.query(Job).delete()
    s.query(SearchCriteria).delete()
    s.query(User).delete()
    s.commit()
    yield s
    s.close()


def _create_user_and_token(session, email="test@example.com"):
    user = User(email=email, password_hash=hash_password("irrelevant-for-these-tests"))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user, create_access_token(user.id)


@pytest.fixture
def auth_headers(session):
    """A real user row plus a real token for it — the shape of a genuinely logged-in request."""
    _, token = _create_user_and_token(session)
    return {"Authorization": f"Bearer {token}"}


class TestAuth:
    def test_missing_token_rejected(self, session):
        r = client.get("/criteria")
        assert r.status_code == 401  # HTTPBearer's actual default for a missing Authorization header

    def test_malformed_token_rejected(self, session):
        r = client.get("/criteria", headers={"Authorization": "Bearer not-a-real-jwt"})
        assert r.status_code == 401

    def test_token_for_deleted_or_nonexistent_user_rejected(self, session):
        from uuid import uuid4
        token = create_access_token(uuid4())  # well-signed, but no matching user row
        r = client.get("/criteria", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401

    def test_valid_token_for_real_user_succeeds(self, session):
        _, token = _create_user_and_token(session, email="realuser@example.com")
        r = client.get("/criteria", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200


class TestCriteria:
    def test_create_and_list(self, auth_headers):
        r = client.post("/criteria", json={
            "label": "Software grad roles", "keywords": ["software", "engineer"],
            "locations": ["London"], "salary_min": 25000,
        }, headers=auth_headers)
        assert r.status_code == 201
        assert r.json()["label"] == "Software grad roles"

        r = client.get("/criteria", headers=auth_headers)
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_cannot_access_another_users_criteria(self, session, auth_headers):
        r = client.post("/criteria", json={"keywords": ["x"]}, headers=auth_headers)
        criteria_id = r.json()["id"]

        _, other_token = _create_user_and_token(session, email="other@example.com")
        other_headers = {"Authorization": f"Bearer {other_token}"}

        r = client.get(f"/criteria/{criteria_id}", headers=other_headers)
        assert r.status_code == 404  # not 403 - see _get_owned_criteria's docstring

    def test_update_is_partial(self, auth_headers):
        r = client.post("/criteria", json={"keywords": ["a"], "locations": ["London"]}, headers=auth_headers)
        criteria_id = r.json()["id"]

        r = client.patch(f"/criteria/{criteria_id}", json={"keywords": ["b"]}, headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["keywords"] == ["b"]
        assert r.json()["locations"] == ["London"]  # untouched by the partial update

    def test_delete(self, auth_headers):
        r = client.post("/criteria", json={"keywords": ["a"]}, headers=auth_headers)
        criteria_id = r.json()["id"]

        r = client.delete(f"/criteria/{criteria_id}", headers=auth_headers)
        assert r.status_code == 204

        r = client.get(f"/criteria/{criteria_id}", headers=auth_headers)
        assert r.status_code == 404


def _seed_job(session, title, company, location, description="", salary_min=None):
    job = Job(
        title=title, normalized_title=title.lower(),
        company=company, normalized_company=company.lower(),
        location=location, normalized_location=location.lower(),
        location_category=categorize_location(location),  # matches what storage.py does for real jobs
        industry_category=categorize_industry(title, description),  # matches what storage.py does for real jobs
        description=description, salary_min=salary_min,
    )
    session.add(job)
    session.flush()
    session.add(JobSource(job_id=job.id, site="adzuna", source_url=f"https://example.com/{job.id}", raw_title=title))
    session.commit()
    return job


class TestFeed:

    def test_no_active_criteria_gives_empty_feed(self, auth_headers):
        r = client.get("/feed", headers=auth_headers)
        assert r.status_code == 200
        assert r.json() == {"items": [], "total": 0, "limit": 20, "offset": 0}

    def test_feed_only_returns_matching_jobs(self, session, auth_headers):
        _seed_job(session, "Graduate Software Engineer", "Google", "London",
                        description="Join our engineering team")
        _seed_job(session, "Graduate Chef", "Ritz Hotel", "London",
                        description="Join our kitchen team")

        client.post("/criteria", json={"keywords": ["software"], "locations": ["London"]}, headers=auth_headers)

        r = client.get("/feed", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["items"][0]["job"]["title"] == "Graduate Software Engineer"
        assert body["items"][0]["job"]["sources"][0]["site"] == "adzuna"
        assert body["items"][0]["status"] == "new"

    def test_feed_materializes_matches_idempotently(self, session, auth_headers):
        """Calling /feed twice shouldn't create duplicate match rows for the same job."""
        _seed_job(session, "Graduate Analyst", "Barclays", "London")
        client.post("/criteria", json={"keywords": ["analyst"]}, headers=auth_headers)

        client.get("/feed", headers=auth_headers)
        client.get("/feed", headers=auth_headers)

        user_row = session.query(User).first()
        assert session.query(UserJobMatch).filter_by(user_id=user_row.id).count() == 1

    def test_match_status_update(self, session, auth_headers):
        _seed_job(session, "Graduate Analyst", "Barclays", "London")
        client.post("/criteria", json={"keywords": ["analyst"]}, headers=auth_headers)

        feed = client.get("/feed", headers=auth_headers).json()
        match_id = feed["items"][0]["id"]

        r = client.patch(f"/matches/{match_id}", json={"status": "applied"}, headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "applied"

    def test_cannot_update_another_users_match(self, session, auth_headers):
        _seed_job(session, "Graduate Analyst", "Barclays", "London")
        client.post("/criteria", json={"keywords": ["analyst"]}, headers=auth_headers)
        feed = client.get("/feed", headers=auth_headers).json()
        match_id = feed["items"][0]["id"]

        _, other_token = _create_user_and_token(session, email="other2@example.com")
        other_headers = {"Authorization": f"Bearer {other_token}"}

        r = client.patch(f"/matches/{match_id}", json={"status": "applied"}, headers=other_headers)
        assert r.status_code == 404

    def test_salary_min_excludes_lower_but_keeps_unparsed(self, session, auth_headers):
        _seed_job(session, "Grad Role A", "Co A", "London", salary_min=20000)
        _seed_job(session, "Grad Role B", "Co B", "London", salary_min=35000)
        _seed_job(session, "Grad Role C", "Co C", "London", salary_min=None)  # unparsed

        client.post("/criteria", json={"salary_min": 30000}, headers=auth_headers)
        r = client.get("/feed", headers=auth_headers)
        titles = {item["job"]["title"] for item in r.json()["items"]}
        assert titles == {"Grad Role B", "Grad Role C"}  # A excluded, C kept despite missing data


class TestFavourites:
    """Uses the same module-level _seed_job() helper as TestFeed — favouriting is a property of a match, so these tests need the same "seed a job, save criteria, fetch the feed for a real match id" setup, without re-running TestFeed's own tests via inheritance."""

    def test_new_matches_are_not_favourited_by_default(self, session, auth_headers):
        _seed_job(session, "Graduate Analyst", "Barclays", "London")
        client.post("/criteria", json={"keywords": ["analyst"]}, headers=auth_headers)
        feed = client.get("/feed", headers=auth_headers).json()
        assert feed["items"][0]["is_favourite"] is False

    def test_favouriting_a_match(self, session, auth_headers):
        _seed_job(session, "Graduate Analyst", "Barclays", "London")
        client.post("/criteria", json={"keywords": ["analyst"]}, headers=auth_headers)
        match_id = client.get("/feed", headers=auth_headers).json()["items"][0]["id"]

        r = client.patch(f"/matches/{match_id}", json={"is_favourite": True}, headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["is_favourite"] is True

    def test_favouriting_does_not_change_status(self, session, auth_headers):
        """The whole point of a separate field: favouriting something already marked 'applied' shouldn't reset it back to 'new'."""
        _seed_job(session, "Graduate Analyst", "Barclays", "London")
        client.post("/criteria", json={"keywords": ["analyst"]}, headers=auth_headers)
        match_id = client.get("/feed", headers=auth_headers).json()["items"][0]["id"]

        client.patch(f"/matches/{match_id}", json={"status": "applied"}, headers=auth_headers)
        r = client.patch(f"/matches/{match_id}", json={"is_favourite": True}, headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "applied"  # untouched by the favourite-only patch
        assert r.json()["is_favourite"] is True

    def test_status_update_does_not_unfavourite(self, session, auth_headers):
        _seed_job(session, "Graduate Analyst", "Barclays", "London")
        client.post("/criteria", json={"keywords": ["analyst"]}, headers=auth_headers)
        match_id = client.get("/feed", headers=auth_headers).json()["items"][0]["id"]

        client.patch(f"/matches/{match_id}", json={"is_favourite": True}, headers=auth_headers)
        r = client.patch(f"/matches/{match_id}", json={"status": "dismissed"}, headers=auth_headers)
        assert r.json()["is_favourite"] is True  # a dismissed job can still be a favourite

    def test_unfavouriting(self, session, auth_headers):
        _seed_job(session, "Graduate Analyst", "Barclays", "London")
        client.post("/criteria", json={"keywords": ["analyst"]}, headers=auth_headers)
        match_id = client.get("/feed", headers=auth_headers).json()["items"][0]["id"]

        client.patch(f"/matches/{match_id}", json={"is_favourite": True}, headers=auth_headers)
        r = client.patch(f"/matches/{match_id}", json={"is_favourite": False}, headers=auth_headers)
        assert r.json()["is_favourite"] is False

    def test_empty_patch_rejected(self, session, auth_headers):
        _seed_job(session, "Graduate Analyst", "Barclays", "London")
        client.post("/criteria", json={"keywords": ["analyst"]}, headers=auth_headers)
        match_id = client.get("/feed", headers=auth_headers).json()["items"][0]["id"]

        r = client.patch(f"/matches/{match_id}", json={}, headers=auth_headers)
        assert r.status_code == 422  # neither field provided — almost certainly a frontend bug, not a legitimate no-op

    def test_favourites_only_filter(self, session, auth_headers):
        _seed_job(session, "Graduate Analyst", "Barclays", "London")
        _seed_job(session, "Graduate Engineer", "Google", "London", description="Join our engineering team")
        client.post("/criteria", json={"keywords": ["graduate"], "locations": ["London"]}, headers=auth_headers)

        feed = client.get("/feed", headers=auth_headers).json()
        assert feed["total"] == 2
        analyst_match = next(m for m in feed["items"] if m["job"]["title"] == "Graduate Analyst")
        client.patch(f"/matches/{analyst_match['id']}", json={"is_favourite": True}, headers=auth_headers)

        r = client.get("/feed?favourites_only=true", headers=auth_headers)
        body = r.json()
        assert body["total"] == 1
        assert body["items"][0]["job"]["title"] == "Graduate Analyst"

    def test_favourites_only_includes_dismissed_favourites(self, session, auth_headers):
        """Favourites_only is independent of status — a dismissed-but-favourited job should still show up here."""
        _seed_job(session, "Graduate Analyst", "Barclays", "London")
        client.post("/criteria", json={"keywords": ["analyst"]}, headers=auth_headers)
        match_id = client.get("/feed", headers=auth_headers).json()["items"][0]["id"]

        client.patch(f"/matches/{match_id}", json={"is_favourite": True, "status": "dismissed"}, headers=auth_headers)

        r = client.get("/feed?favourites_only=true", headers=auth_headers)
        assert r.json()["total"] == 1
