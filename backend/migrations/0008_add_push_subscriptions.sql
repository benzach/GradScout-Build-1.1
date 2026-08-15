-- Migration 0008: push notification subscriptions.
--
-- One row per browser/device a user has granted notification
-- permission on — a user could reasonably have more than one (phone +
-- laptop), so this is its own table rather than a column on `users`.
-- `endpoint` is globally unique by construction (it's a URL the push
-- service itself generates per-subscription), which is what makes it
-- safe to upsert on: re-subscribing the same browser naturally
-- replaces its own row rather than creating a duplicate.

CREATE TABLE push_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    endpoint TEXT NOT NULL UNIQUE,
    p256dh TEXT NOT NULL,
    auth TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_push_subscriptions_user_id ON push_subscriptions(user_id);
