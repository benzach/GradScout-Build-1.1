-- Migration 0010: pause CharityJob, ACCA, and ThirdSector.
--
-- None of the three offer a public API — app/scrapers/static_scraper.py
-- gets their listings by parsing the rendered HTML of their public
-- pages, and (until this same change) was doing so while impersonating
-- a real Chrome browser specifically to get past basic bot detection.
-- That's very likely outside what these sites' own Terms of Service
-- permit, and it's a genuine problem to have running while approaching
-- OTHER job boards for official, above-board API partnerships.
--
-- Paused, not deleted: `enabled = false` is read by
-- app/scrapers/registry.py's load_enabled_sources(), so the scheduler
-- simply skips these three rows on every cycle — no code changes
-- needed, and nothing about the parsing logic itself was wrong. Existing
-- Job/JobSource rows from these three sources are left untouched; only
-- new scraping is paused.
--
-- Re-enabling: once there's either explicit permission from the site,
-- or a considered decision to accept the risk, this is a one-line
-- UPDATE sources SET enabled = true WHERE name IN (...) — no migration
-- needed for that part, though see also app/scrapers/http_headers.py
-- for the now-honest (not browser-spoofing) User-Agent these will use
-- once turned back on.

UPDATE sources
SET enabled = false
WHERE name IN ('charityjob', 'acca', 'thirdsector');
