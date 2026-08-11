-- Migration 0004: add location_category to jobs.
--
-- This is the taxonomy-level location filter that app/locations.py's
-- categorize_location() has always populated (see app/storage.py) and
-- that app/matching.py's location filtering has always assumed exists
-- — "EXACT membership, not substring matching" against a finite set of
-- canonical locations, per that module's own docstring.
--
-- This file was missing from the delivered project: migrations jumped
-- 0003 -> 0005 with no 0004 ever present, even though 0005's own
-- comments describe industry_category as "mirroring how
-- location_category works" — meaning this migration should already
-- have existed by the time 0005 was written. Recreated here, in its
-- correct chronological position rather than appended at the end,
-- since nothing in 0005 (or the code depending on either column)
-- assumes this migration hasn't already run.

ALTER TABLE jobs ADD COLUMN location_category TEXT;
CREATE INDEX idx_jobs_location_category ON jobs(location_category);
