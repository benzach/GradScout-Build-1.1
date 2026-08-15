"""
Generates a VAPID key pair for Web Push — run this ONCE, then paste the
two values into Railway's environment variables (VAPID_PRIVATE_KEY and
VAPID_PUBLIC_KEY) and never regenerate them afterward. Regenerating
would invalidate every push subscription anyone has already granted,
silently breaking notifications for every existing tester until they
re-enable them.

Usage:
    python -m scripts.generate_vapid_keys

Both keys come out as base64url strings — the exact format
app/notifications.py and the frontend's subscribe() call both expect
directly, with no PEM files or extra conversion needed anywhere.
"""
from py_vapid import Vapid
from py_vapid.utils import b64urlencode
from cryptography.hazmat.primitives import serialization


def main():
    v = Vapid()
    v.generate_keys()

    private_raw = v.private_key.private_numbers().private_value.to_bytes(32, "big")
    public_raw = v.public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )

    print("Add these two as Railway environment variables on the backend service:\n")
    print(f"VAPID_PRIVATE_KEY={b64urlencode(private_raw)}")
    print(f"VAPID_PUBLIC_KEY={b64urlencode(public_raw)}")
    print("\nVAPID_SUBJECT_EMAIL also needs setting — any real email address")
    print("you control. Push services use it to contact you if your server")
    print("is ever misbehaving, before blocking it outright.")


if __name__ == "__main__":
    main()
