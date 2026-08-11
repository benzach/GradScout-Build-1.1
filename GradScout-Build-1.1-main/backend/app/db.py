"""
Database connection. Reads DATABASE_URL from environment; falls back to
the local dev database for testing.

In production, DATABASE_URL should point at Railway's own Postgres
plugin — but Railway does NOT wire this in automatically. It needs an
explicit reference variable on the backend service itself
(DATABASE_URL = ${{Postgres.DATABASE_URL}}, or whatever your Postgres
service is actually named) — see backend/README.md's Deploying
section. Skipping that step is exactly how a stale or manually-pasted
connection string ends up here instead, which is hard to notice from
the Railway dashboard alone; the startup log line below exists
specifically so a wrong value is obvious immediately rather than only
surfacing as a confusing 500 on the first real request.

One more gotcha worth knowing: several hosts (Railway and Heroku both
included) have, at various points, handed out connection strings
starting with `postgres://`, but SQLAlchemy 1.4+ requires
`postgresql://` — the two-character difference is a real, common
source of a deploy silently failing with a confusing error. Handled
here once, so it's never a surprise later.
"""
import os
from urllib.parse import urlparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://gradscout:localdev@localhost/gradscout_dev"
)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Host only, never the password — printed once at startup so "which
# database is this process actually about to talk to?" has an
# unambiguous answer in the deploy logs, rather than needing to trust
# what the Railway dashboard's Variables tab appears to show.
print(f"[db] Connecting to Postgres host: {urlparse(DATABASE_URL).hostname}")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def get_session():
    return SessionLocal()
