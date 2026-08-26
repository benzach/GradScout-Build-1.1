"""
Tests for scraper parsing logic — no network, no database. Each fixture
mirrors real page/feed structure that was verified against the actual
live sites during the prototype phase (see conversation history / old
project's config/sites.yaml notes for provenance of each pattern).
"""
from bs4 import BeautifulSoup
import pytest

from app.scrapers.static_scraper import StaticScraper
from app.scrapers.rss_scraper import RSSScraper
from app.scrapers.reed_scraper import ReedScraper


def test_reed_handles_explicit_null_currency_not_just_missing():
    """
    Regression test for a real production crash: Reed's API returns
    "currency": null explicitly for some jobs (not just omits the key).
    dict.get(key, default) only falls back to default when the key is
    MISSING, not when it's present-but-null — this silently returned
    None instead of "GBP" and crashed on `None + " "`.
    """
    scraper = ReedScraper({"name": "reed"})
    item = {
        "jobTitle": "Graduate Trainee", "jobUrl": "https://reed.co.uk/jobs/1",
        "employerName": "Some Co", "locationName": "Leeds",
        "minimumSalary": None, "maximumSalary": None, "currency": None,
    }
    job = scraper._parse_job(item)  # must not raise
    assert job["title"] == "Graduate Trainee"
    assert job["salary"] == ""


class _FakeResponse:
    """Minimal stand-in for requests.Response, matching the .json()/.raise_for_status() surface these scrapers actually use."""
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_scraper_headers_do_not_impersonate_a_browser():
    """
    Regression test for a real fix: these headers used to spoof a Chrome
    User-Agent to get past bot detection on sites without an API. The
    User-Agent must now honestly identify the bot, not claim to be a
    browser.
    """
    from app.scrapers.http_headers import build_scraper_headers

    headers = build_scraper_headers()
    assert "GradScoutBot" in headers["User-Agent"]
    assert "Chrome" not in headers["User-Agent"]
    assert "Mozilla" not in headers["User-Agent"]


def test_scraper_headers_include_contact_when_configured():
    from unittest.mock import patch

    from app.scrapers.http_headers import build_scraper_headers

    with patch.dict("os.environ", {
        "SCRAPER_CONTACT_URL": "https://example.com/about",
        "SCRAPER_CONTACT_EMAIL": "hello@example.com",
    }):
        headers = build_scraper_headers()

    assert "https://example.com/about" in headers["User-Agent"]
    assert "hello@example.com" in headers["User-Agent"]


def test_scraper_headers_still_honest_without_contact_configured():
    """Unconfigured contact info shouldn't make the header lie by omission with a fake one - just a bare, still-honest identifier."""
    from unittest.mock import patch

    from app.scrapers.http_headers import build_scraper_headers

    with patch.dict("os.environ", {}, clear=True):
        headers = build_scraper_headers()

    assert headers["User-Agent"] == "GradScoutBot/1.0"


def test_reed_full_description_disabled_by_default():
    """fetch_full_description defaults to False - must not make any extra requests unless explicitly opted in."""
    from unittest.mock import patch

    scraper = ReedScraper({"name": "reed"})
    search_response = _FakeResponse({"results": [
        {"jobId": 1, "jobTitle": "Grad Role", "jobUrl": "https://reed.co.uk/jobs/1",
         "employerName": "Co", "locationName": "London", "jobDescription": "Short snippet..."},
    ]})

    with patch("app.scrapers.reed_scraper.requests.get", return_value=search_response) as mock_get, \
         patch.dict("os.environ", {"REED_API_KEY": "fake-key"}):
        jobs = scraper.scrape()

    assert mock_get.call_count == 1  # only the search call - no detail fetch
    assert jobs[0]["description"] == "Short snippet..."


def test_reed_full_description_fetch_replaces_snippet_when_enabled():
    from unittest.mock import patch

    scraper = ReedScraper({"name": "reed", "fetch_full_description": True, "detail_fetch_limit": 5})
    search_response = _FakeResponse({"results": [
        {"jobId": 42, "jobTitle": "Grad Role", "jobUrl": "https://reed.co.uk/jobs/42",
         "employerName": "Co", "locationName": "London", "jobDescription": "Short snippet..."},
    ]})
    detail_response = _FakeResponse({"jobDescription": "The full, untruncated job description text goes here."})

    def fake_get(url, **kwargs):
        return detail_response if "jobs/42" in url else search_response

    with patch("app.scrapers.reed_scraper.requests.get", side_effect=fake_get), \
         patch("app.scrapers.reed_scraper.time.sleep"), \
         patch.dict("os.environ", {"REED_API_KEY": "fake-key"}):
        jobs = scraper.scrape()

    assert jobs[0]["description"] == "The full, untruncated job description text goes here."


def test_reed_full_description_fetch_respects_detail_fetch_limit():
    """Only the first `detail_fetch_limit` jobs get the extra request - this is what keeps the feature within Reed's daily quota."""
    from unittest.mock import patch

    scraper = ReedScraper({"name": "reed", "fetch_full_description": True, "detail_fetch_limit": 1})
    search_response = _FakeResponse({"results": [
        {"jobId": 1, "jobTitle": "Role A", "jobUrl": "u1", "employerName": "Co", "locationName": "London", "jobDescription": "snippet A"},
        {"jobId": 2, "jobTitle": "Role B", "jobUrl": "u2", "employerName": "Co", "locationName": "London", "jobDescription": "snippet B"},
    ]})
    detail_calls = []

    def fake_get(url, **kwargs):
        if "jobs/" in url:
            detail_calls.append(url)
            return _FakeResponse({"jobDescription": "full text"})
        return search_response

    with patch("app.scrapers.reed_scraper.requests.get", side_effect=fake_get), \
         patch("app.scrapers.reed_scraper.time.sleep"), \
         patch.dict("os.environ", {"REED_API_KEY": "fake-key"}):
        jobs = scraper.scrape()

    assert len(detail_calls) == 1  # limit=1, even though there were 2 results
    assert jobs[0]["description"] == "full text"
    assert jobs[1]["description"] == "snippet B"  # second job keeps its original snippet


def test_reed_detail_fetch_failure_falls_back_to_snippet():
    """One job's detail call failing must not lose the listing or crash the whole scrape."""
    from unittest.mock import patch
    import requests as requests_module

    scraper = ReedScraper({"name": "reed", "fetch_full_description": True, "detail_fetch_limit": 5})
    search_response = _FakeResponse({"results": [
        {"jobId": 1, "jobTitle": "Role A", "jobUrl": "u1", "employerName": "Co", "locationName": "London", "jobDescription": "original snippet"},
    ]})

    def fake_get(url, **kwargs):
        if "jobs/" in url:
            raise requests_module.exceptions.Timeout("simulated timeout")
        return search_response

    with patch("app.scrapers.reed_scraper.requests.get", side_effect=fake_get), \
         patch("app.scrapers.reed_scraper.time.sleep"), \
         patch.dict("os.environ", {"REED_API_KEY": "fake-key"}):
        jobs = scraper.scrape()  # must not raise

    assert jobs[0]["description"] == "original snippet"


def test_charityjob_parses_title_location_salary_contract():
    html = """
    <div class="job-listing">
      <h2><a href="/jobs/mark-evison-foundation-/schools-project-officer/1073612?tsId=0">Schools' Project Officer</a></h2>
      <p>Mark Evison Foundation, London (On-site)</p>
      <p>£30,000 - £35,000 per year</p>
      <p>Full-time Permanent</p>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    scraper = StaticScraper({"name": "charityjob", "url": "https://www.charityjob.co.uk/project-officer-jobs-in-london"})
    jobs = scraper.parse_charityjob(soup)

    assert len(jobs) == 1
    job = jobs[0]
    assert job["title"] == "Schools' Project Officer"
    assert "Mark Evison Foundation" in job["location"]
    assert "£30,000" in job["salary"]
    assert "Full-time" in job["contract_type"]
    assert "Permanent" in job["contract_type"]


def test_acca_parses_title_company_location_salary():
    html = """
    <div>
    <h3><a href="/job/13953917/assistant-manager/?LinkSource=PremiumListing">Assistant Manager</a></h3>
    <ul>
      <li>Karachi (PK)</li>
      <li>100,000-160,000</li>
      <li>Gadoon Textile Mills Limited</li>
    </ul>
    <p>Handles finance operations including reporting, budgeting, costing, taxation, and treasury.</p>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    scraper = StaticScraper({"name": "acca", "url": "https://jobs.accaglobal.com/jobs/entry-level/"})
    jobs = scraper.parse_acca(soup)

    assert len(jobs) == 1
    job = jobs[0]
    assert job["title"] == "Assistant Manager"
    assert job["company"] == "Gadoon Textile Mills Limited"
    assert job["location"] == "Karachi (PK)"
    assert job["salary"] == "100,000-160,000"


def test_thirdsector_parses_title_location_salary_contract():
    html = """
    <div>
    <h2><a href="/jobdetail/27692/scotland-practitioner">Scotland Practitioner</a></h2>
    <ul><li>Leith, Edinburgh</li><li>£40,149 per annum</li><li>Full Time</li></ul>
    <p>Great graduate-level opportunity in Scotland.</p>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    scraper = StaticScraper({"name": "thirdsector", "url": "https://jp.thirdsector.co.uk/jobs"})
    jobs = scraper.parse_thirdsector(soup)

    assert len(jobs) == 1
    job = jobs[0]
    assert job["title"] == "Scotland Practitioner"
    assert job["location"] == "Leith, Edinburgh"
    assert "Full-time" in job["contract_type"]  # "Full Time" (space) correctly normalized


def test_w4mpjobs_rss_parses_location_from_category_company_from_author(tmp_path):
    feed_xml = """<?xml version="1.0" encoding="utf-8"?><rss version="2.0"><channel>
    <item>
      <title>Senior Parliamentary Assistant</title>
      <description>&lt;p&gt;Great opportunity in Westminster.&lt;/p&gt;</description>
      <link>http://www.w4mpjobs.org/JobDetails.aspx?jobid=99713</link>
      <pubDate>10 Jul 2026 21:42:12</pubDate>
      <author>Alex Ballinger MP (Halesowen)</author>
      <category>London</category>
    </item>
    </channel></rss>"""
    feed_file = tmp_path / "feed.xml"
    feed_file.write_text(feed_xml)

    scraper = RSSScraper({"name": "w4mpjobs", "url": str(feed_file)})
    jobs = scraper.scrape()

    assert len(jobs) == 1
    job = jobs[0]
    assert job["title"] == "Senior Parliamentary Assistant"
    assert job["location"] == "London"  # from <category>, not description text
    assert job["company"] == "Alex Ballinger MP"  # trailing "(Halesowen)" stripped


def test_rss_real_url_timeout_raises_cleanly_not_hangs():
    """
    Regression test for a real production issue: feedparser.parse(url)
    has no timeout of its own, so a slow/unresponsive real HTTP source
    could hang the scheduler indefinitely instead of failing visibly.
    For any http(s):// URL, this must go through requests (which DOES
    have a timeout) and raise promptly and catchably.
    """
    from unittest.mock import patch
    import requests as requests_module

    scraper = RSSScraper({"name": "w4mpjobs", "url": "https://example.com/feed.rss"})
    with patch("app.scrapers.rss_scraper.requests.get", side_effect=requests_module.exceptions.Timeout("simulated timeout")):
        with pytest.raises(requests_module.exceptions.Timeout):
            scraper.scrape()
