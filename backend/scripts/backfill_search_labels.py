"""
One-off backfill: gives every existing SearchCriteria row with a blank
or NULL label a real, human-readable name.

Needed because search naming only became mandatory going forward (see
SearchCriteriaCreate.label in app/schemas.py) — any searches created
before that change may still have label=NULL sitting in the database.
The frontend already falls back to displaying "Untitled search" for
those, so nothing is broken without this, but with several unnamed
searches "Untitled search" x3 is exactly the confusion the mandatory
name requirement exists to avoid — this makes existing rows benefit
from it too, retroactively.

Generates a name from the criteria's own keywords/locations/industries
(the same fields a user would have typed a label to summarise anyway),
falling back to "Untitled search N" only if a row has no fields at all
to build a name from.

Usage:
    DATABASE_URL=<your real production connection string> python -m scripts.backfill_search_labels

Safe to re-run — only touches rows where label is still NULL or blank,
so anything already named (by a user, or by a previous run of this
script) is left untouched.
"""
from app.db import get_session, DATABASE_URL
from app.models import SearchCriteria


def _masked_target(url: str) -> str:
    """Shows enough of the connection target to confirm it's the right database, without printing the password."""
    if "@" not in url:
        return url
    _, host_part = url.rsplit("@", 1)
    return f"...@{host_part}"


def _generate_label(criteria: SearchCriteria, fallback_index: int) -> str:
    parts = [
        ", ".join(criteria.keywords[:3]) if criteria.keywords else None,
        ", ".join(criteria.locations[:2]) if criteria.locations else None,
        ", ".join(criteria.industries[:2]) if criteria.industries else None,
    ]
    summary = " · ".join(p for p in parts if p)
    if not summary:
        return f"Untitled search {fallback_index}"
    # Title-cased and capped so a keyword-heavy criteria set doesn't
    # produce an unreasonably long label - this only needs to be
    # recognisable at a glance, not a complete description.
    label = summary[:60].strip()
    return label[0].upper() + label[1:] if label else f"Untitled search {fallback_index}"


def backfill():
    print(f"Connecting to: {_masked_target(DATABASE_URL)}")
    if "localhost" in DATABASE_URL or "gradscout_dev" in DATABASE_URL:
        print(
            "\n*** WARNING: this looks like the LOCAL default database, not a "
            "real production DATABASE_URL. If you meant to backfill production, set "
            "DATABASE_URL explicitly before running this script. Continuing "
            "against the local database in 3 seconds... (Ctrl+C to cancel) ***\n"
        )
        import time
        time.sleep(3)

    session = get_session()
    unnamed = session.query(SearchCriteria).filter(
        (SearchCriteria.label.is_(None)) | (SearchCriteria.label == "")
    ).all()
    print(f"Found {len(unnamed)} unnamed search(es) to label...")

    if len(unnamed) == 0:
        print("\nNothing to do — every saved search already has a name.")
        session.close()
        return

    for i, criteria in enumerate(unnamed, start=1):
        criteria.label = _generate_label(criteria, i)

    session.commit()
    session.close()
    print("Done.")


if __name__ == "__main__":
    backfill()
