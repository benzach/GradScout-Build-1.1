"""
Database connection. Reads DATABASE_URL from environment; falls back to
the local dev database for testing.

In production, DATABASE_URL points at Railway's own Postgres plugin —
attaching one to this project gives Railway's web service this
variable automatically, so nothing needs setting by hand. One gotcha
worth knowing: several hosts (Railway and Heroku both included) have,
at various points, handed out connection strings starting with
`postgres://`, but SQLAlchemy 1.4+ requires `postgresql://` — the
two-character difference is a real, common source of a deploy silently
failing with a confusing error. Handled here once, so it's never a
surprise later.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://gradscout:localdev@localhost/gradscout_dev"
)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def get_session():
    return SessionLocal()
