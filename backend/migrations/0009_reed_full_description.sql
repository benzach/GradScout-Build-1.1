-- Migration 0009: turn on Reed's full-description fetch (see the
-- "Full-description fetching" note in app/scrapers/reed_scraper.py for
-- the full reasoning and the request-budget math behind the numbers
-- below).
--
-- Only Reed gets this: Adzuna's search API only ever returns a snippet
-- with no full-text option at all (confirmed against Adzuna's own API
-- docs), and Jooble's free tier is a 500-requests-LIFETIME quota (not
-- even daily), which rules out any extra per-job request entirely.
-- Reed is the one source among the three where a genuine fix exists.
--
-- detail_fetch_limit=10 is deliberately conservative, not the maximum
-- that fits Reed's 1,000/day quota - see the scraper's module
-- docstring for the exact math. Safe to raise later once you've
-- watched a few days of real usage against your actual scrape
-- frequency (see SCRAPE_INTERVAL_MINUTES).
--
-- The || operator merges into the existing config rather than
-- replacing it outright, so 'graduate_only' and 'results_to_take'
-- (set in migrations/0002_seed_sources.sql) are left untouched.

UPDATE sources
SET config = config || '{"fetch_full_description": true, "detail_fetch_limit": 10}'::jsonb
WHERE name = 'reed';
