"""
Signup and login — GradScout's own account creation and authentication,
replacing Supabase Auth (see app/security.py and app/auth.py for why).

Deliberately minimal for a closed test-phase rollout: no email
verification step and no password-reset flow. Both are real gaps for a
public launch, but for ~20 testers you already know personally, that's
the right tradeoff — building a transactional email flow (which needs
its own third-party service, e.g. Resend or Postmark, meaning yet
another account to manage) isn't worth doing before a single real user
depends on it. Flagged explicitly here rather than silently skipped, so
it's a deliberate decision to revisit before a wider launch, not a gap
someone finds by accident later.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user, get_db
from app.models import User
from app.schemas import AccountDeleteRequest, LoginRequest, SignupRequest, TokenResponse, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse, status_code=201)
def signup(body: SignupRequest, session: Session = Depends(get_db)):
    existing = session.query(User).filter_by(email=body.email).first()
    if existing:
        # Deliberately vague — confirming "that email is already
        # registered" to an unauthenticated caller is a minor
        # account-enumeration leak. Not a serious risk for a 21-person
        # closed test, but free to avoid, so it's avoided.
        raise HTTPException(status_code=400, detail="Could not create an account with those details")

    user = User(email=body.email, password_hash=hash_password(body.password))
    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        # The check above and this insert aren't atomic — two signups
        # for the same email arriving close together can both pass the
        # `existing` check before either commits. Without this,
        # whichever one loses the race hits the database's own unique
        # constraint and surfaces as an unhandled 500, not a clean 400.
        session.rollback()
        raise HTTPException(status_code=400, detail="Could not create an account with those details")
    session.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, session: Session = Depends(get_db)):
    user = session.query(User).filter_by(email=body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        # Same response whether the email doesn't exist or the
        # password is wrong — distinguishing the two tells an attacker
        # which emails are registered accounts.
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.delete("/me", status_code=204)
def delete_account(
    body: AccountDeleteRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """
    Real, immediate, self-serve deletion — not a support-ticket
    promise. Deleting the users row cascades to search_criteria,
    user_job_matches, and push_subscriptions automatically (see each
    table's own ON DELETE CASCADE in their migrations), so this one
    delete genuinely removes everything tied to the account in a
    single transaction, not just the login itself.
    """
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect password")

    session.delete(user)
    session.commit()
