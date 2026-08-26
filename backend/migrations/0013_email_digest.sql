-- Migration 0013: weekly email digest.
--
-- A fallback (really, a complement) to push notifications (see
-- app/notifications.py) for people who haven't installed the PWA, or
-- are on iOS Safari where PWA push has real adoption friction (see
-- components/InstallBanner.jsx) - a weekly email reaches an account
-- regardless of any of that.
--
-- email_digest_enabled defaults to TRUE: this is a summary of the
-- user's OWN saved-search matches, which is squarely within what the
-- Privacy Notice already discloses ("to match and notify you about
-- relevant jobs") - not a marketing opt-in. Toggleable off from
-- Settings any time (see app/routers/auth.py's new PATCH /auth/me).
--
-- last_digest_sent_at is the cursor app/email_digest.py's
-- send_weekly_digests() uses to scope "matches since your last
-- digest" - NULL means "never sent one", not "disabled" (that's what
-- email_digest_enabled is for); the two are independent on purpose.

ALTER TABLE users ADD COLUMN email_digest_enabled BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE users ADD COLUMN last_digest_sent_at TIMESTAMPTZ;
