"""
Push subscription management — the frontend calls these after the user
grants notification permission and the service worker subscribes them
with the browser's own push service (see frontend's src/lib/push.js).

Sending actual notifications happens elsewhere entirely
(app/notifications.py, called only from the scheduler) — this router's
only job is storing and removing the addresses to send them to.
"""
import os

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user, get_db
from app.models import PushSubscription, User
from app.schemas import PushSubscriptionCreate, PushSubscriptionDelete

router = APIRouter(prefix="/push", tags=["push"])


@router.get("/vapid-public-key")
def get_vapid_public_key():
    # Public by design (no auth required) — a VAPID public key is
    # exactly that, public, the same way a TLS certificate's public key
    # is. The frontend needs this before a user has necessarily done
    # anything else yet.
    return {"public_key": os.environ.get("VAPID_PUBLIC_KEY", "")}


@router.post("/subscriptions", status_code=201)
def create_subscription(
    body: PushSubscriptionCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    existing = session.query(PushSubscription).filter_by(endpoint=body.endpoint).first()
    if existing:
        # The same browser subscribing again (e.g. after clearing site
        # data) — update in place and re-point it at whoever's
        # currently signed in on this device, rather than rejecting a
        # legitimate re-subscription as a duplicate.
        existing.user_id = user.id
        existing.p256dh = body.keys.p256dh
        existing.auth = body.keys.auth
    else:
        session.add(PushSubscription(
            user_id=user.id, endpoint=body.endpoint,
            p256dh=body.keys.p256dh, auth=body.keys.auth,
        ))
    session.commit()
    return {"status": "subscribed"}


@router.delete("/subscriptions", status_code=204)
def delete_subscription(
    body: PushSubscriptionDelete,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    session.query(PushSubscription).filter_by(endpoint=body.endpoint, user_id=user.id).delete()
    session.commit()
