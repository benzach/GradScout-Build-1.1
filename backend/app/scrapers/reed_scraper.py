"""
Reed.co.uk API scraper. Verified against a real Reed API response.
Requires REED_API_KEY environment variable. Uses Reed's built-in
graduate=true parameter — genuinely graduate-targeted, not keyword-based.

Full-description fetching: Reed's search endpoint only ever returns a
truncated jobDescription snippet — confirmed against Reed's own
Jobseeker API docs (reed.co.uk/developers/jobseeker), not an assumption.
The full, untruncated description is only available from Reed's
separate per-job details endpoint (GET /api/1.0/jobs/{jobId}), one
request per job. This mirrors the same "opt-in, bounded" pattern
app/scrapers/rss_scraper.py already uses for its own detail-page
fetch (fetch_details / detail_fetch_limit config keys) — deliberately
the same names and shape, rather than inventing a parallel convention.

Why opt-in and bounded, specifically for Reed: the free Reed API tier
allows 1,000 requests/day, and GradScout's scheduler runs every
SCRAPE_INTERVAL_MINUTES (20 by default — see app/scheduler.py), i.e.
up to ~72 times/day. At the default detail_fetch_limit=10, worst case
is 72 x (1 search + 10 detail) = 792 requests/day — under budget with
headroom. Raising detail_fetch_limit needs to be weighed against that
same math: at 20-minute intervals, anything past ~13 would risk
exceeding the daily quota on its own, before counting the search
requests. If SCRAPE_INTERVAL_MINUTES is set lower (more frequent
scrapes), this limit should come down too.
"""
import os
import time

import requests

from app.scrapers.base import BaseScraper

REED_SEARCH_URL = "https://www.reed.co.uk/api/1.0/search"
REED_JOB_DETAIL_URL = "https://www.reed.co.uk/api/1.0/jobs/{job_id}"
TIMEOUT = 15
DETAIL_FETCH_DELAY_SECONDS = 0.5  # be polite — don't hammer Reed's API


class ReedScraper(BaseScraper):
    def scrape(self) -> list[dict]:
        api_key = os.environ.get("REED_API_KEY")
        if not api_key:
            raise RuntimeError(
                "REED_API_KEY must be set as an environment variable "
                "(register free at https://www.reed.co.uk/developers/jobseeker)"
            )

        params = {
            "keywords": self.config.get("keywords", ""),
            "locationName": self.config.get("locationName", ""),
            "graduate": "true" if self.config.get("graduate_only", True) else "false",
            "resultsToTake": self.config.get("results_to_take", 100),
        }
        params = {k: v for k, v in params.items() if v not in ("", None)}

        resp = requests.get(REED_SEARCH_URL, params=params, auth=(api_key, ""), timeout=TIMEOUT)
        resp.raise_for_status()
        results = resp.json().get("results", [])
        jobs = [self._parse_job(item) for item in results]

        fetch_full_description = self.config.get("fetch_full_description", False)
        detail_fetch_limit = self.config.get("detail_fetch_limit", 10)

        if fetch_full_description:
            for i, (item, job) in enumerate(zip(results, jobs)):
                if i >= detail_fetch_limit:
                    break
                job_id = item.get("jobId")
                if not job_id:
                    continue
                try:
                    full_description = self._fetch_full_description(job_id, api_key)
                    if full_description:
                        job["description"] = full_description
                except Exception as e:
                    # One job's detail call failing shouldn't lose the
                    # whole listing — it just keeps the shorter snippet
                    # already parsed from the search result.
                    print(f"  (Reed detail fetch failed for job {job_id}: {e})")
                finally:
                    time.sleep(DETAIL_FETCH_DELAY_SECONDS)

        return jobs

    def _fetch_full_description(self, job_id, api_key: str) -> str:
        resp = requests.get(
            REED_JOB_DETAIL_URL.format(job_id=job_id), auth=(api_key, ""), timeout=TIMEOUT
        )
        resp.raise_for_status()
        return (resp.json().get("jobDescription") or "").strip()

    def _parse_job(self, item: dict) -> dict:
        salary_min, salary_max = item.get("minimumSalary"), item.get("maximumSalary")
        # NOTE: `.get(key, default)` only falls back to `default` when the
        # KEY IS MISSING — if Reed's API returns "currency": null
        # explicitly (seen in practice for jobs with no salary at all),
        # .get() returns None, not "GBP", and `None + " "` crashes. The
        # `or` pattern below handles both "missing" and "present but
        # null" the same way, everywhere it matters in this function.
        currency = item.get("currency") or "GBP"
        symbol = "£" if currency == "GBP" else currency + " "

        salary = ""
        if salary_min and salary_max:
            salary = f"{symbol}{salary_min:,.0f} - {symbol}{salary_max:,.0f}"
        elif salary_min:
            salary = f"{symbol}{salary_min:,.0f}+"

        contract_type_parts = []
        if item.get("contractType"):
            contract_type_parts.append(str(item["contractType"]).title())
        if item.get("fullTime"):
            contract_type_parts.append("Full-time")
        if item.get("partTime"):
            contract_type_parts.append("Part-time")

        return {
            "title": (item.get("jobTitle") or "").strip(),
            "url": (item.get("jobUrl") or "").strip(),
            "company": item.get("employerName") or "",
            "location": item.get("locationName") or "",
            "salary": salary,
            "contract_type": ", ".join(contract_type_parts),
            "description": item.get("jobDescription") or "",
            "posted_date": item.get("date") or "",
        }
