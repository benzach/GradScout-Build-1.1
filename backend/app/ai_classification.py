"""
AI-assisted fallback for location/industry classification.

app/locations.py and app/industries.py do the real work: fast,
free, deterministic, and — critically — fully explainable, which
matters when someone asks "why is this job categorized as X". They
stay the first pass for every single job. This module is only ever
called as a SECOND pass, and only for the minority of jobs that
already failed the rule-based pass (landed in "Other UK" / "Other") —
see app/storage.py for exactly where it's wired in.

Why not replace the rule-based pass entirely? Three reasons this stays
a fallback rather than the primary path:
  - Cost and latency. An LLM call per job, for every job, doesn't scale
    the way a keyword/regex lookup does, and isn't worth paying for on
    the ~90%+ of jobs a simple postcode or city-name match already
    resolves correctly.
  - Determinism. The same "Manchester" string should always categorize
    the same way; a rule-based lookup guarantees that, an LLM call
    technically doesn't.
  - It's genuinely well-suited to the part it IS used for: the
    remaining jobs are exactly the free-text, ambiguous, or unusually-
    phrased cases (a village not in any fixed list, a location
    described in a sentence rather than a name) that benefit from
    actual language understanding rather than substring matching.

Both functions below constrain the model to literally choosing from
the existing canonical list (CANONICAL_LOCATIONS / CANONICAL_INDUSTRIES)
rather than generating free text, and the response is validated against
that same list before being trusted — if the model returns anything
else (a hallucinated category, a refusal, malformed output), that's
treated as "couldn't classify" and the job keeps its rule-based result
rather than accepting an unvalidated answer for a field with a fixed,
finite set of legitimate values.

Fully optional: every function here returns None if ANTHROPIC_API_KEY
isn't set, exactly like the scrapers' own API key checks (see e.g.
app/scrapers/adzuna_scraper.py) - the app works fine, just without this
extra pass, if no key is configured.
"""
import os

import requests

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

# Haiku, deliberately: this is a small, high-volume, tightly-constrained
# classification call (pick one item from a fixed list), not a task
# that benefits from a larger model - Haiku is materially cheaper and
# faster, which matters when this may run against every "Other
# UK"/"Other" job in a scrape cycle. Bump this to a Sonnet model string
# if real-world accuracy on the ambiguous cases ends up mattering more
# than per-call cost.
MODEL = "claude-haiku-4-5-20251001"

_TIMEOUT_SECONDS = 15


def _call_classifier(system: str, user: str) -> str | None:
    """
    Shared request/response handling for both classifier functions
    below. Returns the model's raw trimmed text response, or None on
    any failure (missing key, network error, non-200, unexpected
    response shape) - callers are responsible for validating that text
    against their own canonical list before trusting it.

    Broad except by design, matching this codebase's existing
    failure-isolation principle (see app/pipeline.py's module
    docstring): a bad response from an optional enrichment call must
    never be the thing that crashes an otherwise-successful job import.
    """
    # Read at call time, not module import time - matches how every
    # scraper in this codebase reads its own API key (see e.g.
    # app/scrapers/reed_scraper.py's REED_API_KEY) inside scrape(),
    # not as a module-level constant. Same reasoning applies here: a
    # module-level constant is captured once, the first time this
    # module is imported, and never re-read after that.
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        response = requests.post(
            ANTHROPIC_API_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": MODEL,
                "max_tokens": 20,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        content = response.json()["content"]
        text = "".join(block["text"] for block in content if block.get("type") == "text")
        return text.strip()
    except Exception as e:
        print(f"  -> AI classification call failed (falling back to rule-based result): {e}")
        return None


def classify_location_with_ai(raw_location: str, job_title: str, canonical_locations: list[str]) -> str | None:
    """
    Second-pass location classification for a job app/locations.py
    already tried and landed on "Other UK" for. Returns a canonical
    location, or None if the model couldn't confidently pick one (in
    which case the caller should just keep "Other UK").
    """
    if not raw_location.strip():
        return None

    options = ", ".join(canonical_locations)
    system = (
        "You classify UK graduate job locations. You will be given a raw "
        "location string and a job title. Reply with EXACTLY ONE location "
        f"name from this fixed list, and nothing else — no punctuation, no "
        f"explanation: {options}. "
        "If the raw location genuinely doesn't correspond to any of these "
        "(for example it's outside the UK, or gives no usable location "
        "information at all), reply with exactly: UNKNOWN."
    )
    user = f"Location: {raw_location}\nJob title: {job_title}"

    result = _call_classifier(system, user)
    if result in canonical_locations:
        return result
    return None


def classify_industry_with_ai(job_title: str, description: str, canonical_industries: list[str]) -> str | None:
    """Same pattern as classify_location_with_ai, for industry categorization."""
    if not job_title.strip():
        return None

    options = ", ".join(canonical_industries)
    system = (
        "You classify UK graduate job listings by industry. You will be "
        "given a job title and (if available) a description. Reply with "
        f"EXACTLY ONE industry name from this fixed list, and nothing else "
        f"— no punctuation, no explanation: {options}. "
        "If nothing on the list is a reasonable fit, reply with exactly: UNKNOWN."
    )
    # Descriptions from some sources are just a short snippet - that's
    # fine here, a title plus a sentence or two of context is normally
    # enough signal for industry, unlike location which often needs the
    # raw string itself to be the primary signal.
    user = f"Job title: {job_title}\nDescription: {(description or '')[:600]}"

    result = _call_classifier(system, user)
    if result in canonical_industries:
        return result
    return None
