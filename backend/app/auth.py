"""
Authentication dependency — verifies GradScout's own access tokens
(app/security.py), issued by POST /auth/signup and POST /auth/login
(app/routers/auth.py).

Deliberately keeps get_current_user()'s signature and return type
(still just `-> User`) unchanged from every previous version of this
file — every router in this codebase depends on
`Depends(get_current_user)`, and none of them need to change when the
mechanism underneath it does. That was the entire point of building
this as its own isolated file from Phase 3 onward, and it holds again
here: this is the only file that changed to drop Supabase entirely.

Earlier versions of this file verified Supabase-issued JWTs against
Supabase's JWKS endpoint. That's gone now — GradScout issues and
verifies its own tokens, so there's no external identity provider, no
JWKS fetch, and no second platform account this app needs just to
authenticate someone.
"""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import User
from app.security import ExpiredTokenError, InvalidTokenError, decode_access_token

security = HTTPBearer()


def get_db():
    session = get_session()
    try:
        yield session
    finally:
        session.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_db),
) -> User:
    try:
        user_id = decode_access_token(credentials.credentials)
    except ExpiredTokenError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    user = session.get(User, user_id)
    if not user:
        # A well-formed, correctly-signed token for a user_id that no
        # longer has a row — the account was deleted after this token
        # was issued. Not the "brand-new user" case Supabase's
        # auto-provisioning used to handle: every token GradScout
        # issues is only ever handed out for a user that already
        # exists (see routers/auth.py), so a missing row here always
        # means "gone", never "not created yet".
        raise HTTPException(status_code=401, detail="No account found for this token")

    return user
