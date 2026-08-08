-- Migration 0007: favouriting.
--
-- A favourite is independent of a match's workflow status
-- (new/seen/applied/dismissed) — you might favourite something you've
-- also marked "applied", so this is its own boolean rather than a
-- fifth status value that would force those two facts to collide.
--
-- Partial index: most rows will never be favourited, so indexing only
-- the true values keeps the index small and the "show me my
-- favourites" query cheap without paying for an index entry on every
-- non-favourited match too.

ALTER TABLE user_job_matches ADD COLUMN is_favourite BOOLEAN NOT NULL DEFAULT false;
CREATE INDEX idx_user_job_matches_is_favourite ON user_job_matches(user_id) WHERE is_favourite = true;
