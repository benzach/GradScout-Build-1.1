-- Migration 0011: job expiry tracking.
--
-- Nothing before this told you when a listing had actually disappeared
-- from its source — a job pulled from the site weeks ago could still
-- be sitting in someone's feed looking exactly as live as one posted
-- yesterday. `expired_at` (NULL = still active) is set by a periodic
-- sweep (see app/storage.py's sweep_expired_jobs(), called at the end
-- of every scrape cycle in app/pipeline.py) once NONE of a job's
-- sources have been re-confirmed present in a while.
--
-- "Re-confirmed present" relies on job_sources.scraped_at now actually
-- meaning that — previously it was only ever set once, at first
-- discovery, and never touched again. app/storage.py's
-- process_scraped_job() now bumps it (and un-expires the job, if it
-- had been marked expired and reappeared) every time an already-known
-- URL shows up again in a fresh scrape.
--
-- The new index supports that sweep's core query efficiently: "does
-- this job have any source confirmed within the last N days" is a
-- range scan on scraped_at, not a full table scan.

ALTER TABLE jobs ADD COLUMN expired_at TIMESTAMPTZ;
CREATE INDEX idx_job_sources_scraped_at ON job_sources(scraped_at);
