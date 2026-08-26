-- Migration 0012: negative keywords on a saved search.
--
-- `keywords` (existing) is an OR match — a job needs to match at least
-- one to be included. `excluded_keywords` is the inverse: a job
-- matching ANY of these is filtered out, regardless of everything else
-- about it. Lets someone searching "software grad roles" exclude
-- "senior" or "manager" to cut out the wrong-seniority listings that
-- keyword matching alone can't distinguish (a listing can quite
-- legitimately contain the word "graduate" AND "senior" at once -
-- e.g. "our senior team is hiring graduates" - so this is a genuinely
-- separate, deliberate opt-out, not something foldable into the
-- existing `keywords` field).
--
-- Same NOT NULL DEFAULT '{}' convention as every other array column on
-- this table (see migrations/0001_initial_schema.sql) - an empty
-- array, not NULL, means "no exclusions" and needs no special-casing
-- in app/matching.py's `if criteria.excluded_keywords:` check.

ALTER TABLE search_criteria ADD COLUMN excluded_keywords TEXT[] NOT NULL DEFAULT '{}';
