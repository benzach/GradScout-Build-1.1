"""
Direct unit tests for app/matching.py's job_matches_criteria(). This
module previously had no dedicated tests of its own — only indirect
coverage via test_api.py's /feed tests and test_scheduler.py — which
made it easy for a new filter dimension (excluded_keywords, added
alongside these tests) to go in without anything pinning down its
exact behaviour in isolation.

Job and SearchCriteria are plain SQLAlchemy model instances here, never
added to a session or persisted — job_matches_criteria() only touches
plain column attributes for everything exercised below, so no database
is needed. (The one exception is criteria.sources_enabled, which reads
job.sources, a relationship - deliberately not touched by any test
here, to keep this file DB-free; that one dimension already gets real
coverage via test_api.py/test_scheduler.py instead.)
"""
from app.matching import job_matches_criteria
from app.models import Job, SearchCriteria


def _job(**overrides) -> Job:
    defaults = dict(
        title="Graduate Software Engineer",
        description="Join our engineering team building real products.",
        location_category="London",
        industry_category="Technology",
        contract_type="Full-time",
        salary_min=35000,
        salary_max=40000,
    )
    return Job(**{**defaults, **overrides})


def _criteria(**overrides) -> SearchCriteria:
    defaults = dict(
        keywords=[], excluded_keywords=[], locations=[], industries=[],
        contract_types=[], salary_min=None, sources_enabled=None,
    )
    return SearchCriteria(**{**defaults, **overrides})


class TestExistingDimensions:
    """A baseline for the dimensions excluded_keywords sits alongside — not exhaustive, just enough to pin down the existing contract before adding to it."""

    def test_no_criteria_set_matches_everything(self):
        assert job_matches_criteria(_job(), _criteria()) is True

    def test_keyword_match_is_case_insensitive_and_ORed(self):
        job = _job(title="Graduate Analyst", description="")
        assert job_matches_criteria(job, _criteria(keywords=["ANALYST"])) is True
        assert job_matches_criteria(job, _criteria(keywords=["marketing", "analyst"])) is True
        assert job_matches_criteria(job, _criteria(keywords=["marketing"])) is False

    def test_location_is_exact_membership_not_substring(self):
        job = _job(location_category="London")
        assert job_matches_criteria(job, _criteria(locations=["London"])) is True
        assert job_matches_criteria(job, _criteria(locations=["New London"])) is False

    def test_missing_salary_is_not_excluded(self):
        job = _job(salary_min=None, salary_max=None)
        assert job_matches_criteria(job, _criteria(salary_min=30000)) is True


class TestExcludedKeywords:
    def test_no_exclusions_set_does_not_filter_anything(self):
        job = _job(title="Senior Graduate Manager")
        assert job_matches_criteria(job, _criteria()) is True

    def test_excluded_keyword_in_title_filters_the_job_out(self):
        job = _job(title="Graduate Software Engineer")
        criteria = _criteria(excluded_keywords=["graduate"])
        assert job_matches_criteria(job, criteria) is False

    def test_excluded_keyword_in_description_also_filters_it_out(self):
        job = _job(title="Software Engineer", description="Reports to the senior manager.")
        criteria = _criteria(excluded_keywords=["senior"])
        assert job_matches_criteria(job, criteria) is False

    def test_excluded_keyword_check_is_case_insensitive(self):
        job = _job(title="SENIOR Graduate Analyst")
        criteria = _criteria(excluded_keywords=["senior"])
        assert job_matches_criteria(job, criteria) is False

    def test_job_without_any_excluded_keyword_still_matches(self):
        job = _job(title="Graduate Software Engineer", description="Entry-level role.")
        criteria = _criteria(excluded_keywords=["senior", "manager", "lead"])
        assert job_matches_criteria(job, criteria) is True

    def test_excluded_keywords_are_ORed_any_one_is_enough_to_exclude(self):
        job = _job(title="Graduate Team Lead")
        criteria = _criteria(excluded_keywords=["senior", "lead", "manager"])
        assert job_matches_criteria(job, criteria) is False

    def test_include_and_exclude_can_combine(self):
        """The realistic case this feature exists for: include 'graduate', but not if it's also senior/managerial."""
        wanted = _job(title="Graduate Software Engineer")
        unwanted = _job(title="Graduate Programme - Senior Engineering Manager")
        criteria = _criteria(keywords=["graduate"], excluded_keywords=["senior", "manager"])

        assert job_matches_criteria(wanted, criteria) is True
        assert job_matches_criteria(unwanted, criteria) is False

    def test_exclusion_is_checked_after_other_filters_short_circuit(self):
        """A job failing on location shouldn't need the exclusion check to fail correctly - same end result, just confirms the ordering documented in the module docstring doesn't change the outcome."""
        job = _job(location_category="Manchester", title="Graduate Analyst")
        criteria = _criteria(locations=["London"], excluded_keywords=["graduate"])
        assert job_matches_criteria(job, criteria) is False
