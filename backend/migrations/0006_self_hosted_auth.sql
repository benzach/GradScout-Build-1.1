-- Migration 0006: self-hosted authentication.
--
-- GradScout no longer depends on Supabase for identity. Previously
-- Supabase Auth issued and verified JWTs, and this app's `users` table
-- just mirrored whichever UUID Supabase assigned (see app/auth.py's
-- history for the old JWKS-verification approach). Running both
-- Supabase (database + auth) and Railway (API hosting) meant two
-- platforms, two bills, and two sets of free-tier limits to hit — this
-- migration is the schema half of collapsing that down to Railway
-- alone, with the app hashing and verifying passwords itself.
--
-- Existing rows (there shouldn't be any real ones yet, since the
-- frontend has never actually been functional against this backend)
-- get an empty string, which bcrypt.checkpw can never match against
-- any real password — safe by construction, not just by convention.

ALTER TABLE users ADD COLUMN password_hash TEXT NOT NULL DEFAULT '';
