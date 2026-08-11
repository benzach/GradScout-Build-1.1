"""
Self-hosted password hashing and access tokens.

Replaces Supabase Auth entirely. GradScout used to rely on it for both
password handling and JWT issuance/verification (the old app/auth.py
verified tokens against Supabase's JWKS endpoint) — which meant running
on two platforms (Supabase for auth + database, Railway for the API)
even though Railway can host a Postgres database itself just as easily.
Consolidating onto Railway alone means GradScout now has to do the two
things Supabase Auth was doing for free: hash passwords safely, and
issue/verify its own tokens. Both halves are intentionally small and
boring — this is exactly the kind of code where "boring and correct"
beats "clever".
"""
import os
import time
from uuid import UUID

import bcrypt
import jwt

# Must be set as a real secret in every deployed environment (a Railway
# environment variable — generate one with e.g. `openssl rand -hex 32`).
# No hardcoded fallback: a default value baked into source code would
# mean anyone who's ever seen this repo could forge a valid token for
# any user. Tests set their own value before importing this module.
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "")
JWT_ALGORITHM = "HS256"

# Long-lived on purpose: this is a mobile PWA for a closed test group,
# not a banking app. Forcing re-login every few hours would just train
# testers to stop using it. Revoking a token before this expiry would
# need a server-side blocklist — real complexity this prototype doesn't
# need yet (see the roadmap's notes on what's deliberately deferred).
ACCESS_TOKEN_LIFETIME_SECONDS = 60 * 60 * 24 * 30  # 30 days

# bcrypt silently truncates anything past 72 bytes rather than hashing
# the rest of it — a real footgun if not enforced up front, since it
# would mean "correctpassword123...(80 chars of anything)" and
# "correctpassword123" hash identically. Enforced in schemas.py's
# SignupRequest (max_length=72) so this never sees a longer string, but
# checked again here too, since this module shouldn't silently trust
# its caller to have done that.
MAX_PASSWORD_BYTES = 72


class InvalidTokenError(Exception):
    """Token is malformed, has a bad signature, or is missing required claims."""


class ExpiredTokenError(InvalidTokenError):
    """Token is well-formed but past its expiry."""


def hash_password(password: str) -> str:
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Never raises on a malformed hash (e.g. the '' default for pre-migration rows) — just returns False."""
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: UUID) -> str:
    if not JWT_SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY is not configured on the server")
    now = int(time.time())
    payload = {"sub": str(user_id), "iat": now, "exp": now + ACCESS_TOKEN_LIFETIME_SECONDS}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> UUID:
    if not JWT_SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY is not configured on the server")
    try:
        claims = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise ExpiredTokenError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise InvalidTokenError(str(e))

    try:
        return UUID(claims["sub"])
    except (KeyError, ValueError):
        raise InvalidTokenError("Token missing a valid subject claim")
