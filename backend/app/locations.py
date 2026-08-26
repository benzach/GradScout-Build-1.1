"""
Canonical location taxonomy.

This is the single source of truth for "which finite set of locations
does GradScout recognize" — the frontend's location picker fetches this
list from GET /locations (see app/routers/locations.py) rather than
hardcoding its own copy, specifically to prevent the frontend and
backend drifting out of sync over time.

categorize_location() is called once, at job-storage time (see
app/storage.py), converting whatever free-text location a scraper
happened to produce into exactly one of these buckets. For a job that
still lands in "Other UK" after every rule below, app/storage.py calls
app/ai_classification.py as a second-pass fallback — see that module
for why a rule-based pass stays worth keeping even with an LLM
available (cost, latency, and determinism all favour resolving the
common cases here first).

Rebuilt against real production data (2,901 live jobs) after the first
version showed 69% falling into "Other UK" — that rate was too high to
be a tuning issue, so rather than guess at more keywords, the actual
raw location strings behind every "Other UK" job were pulled and
reviewed. Three real patterns emerged, each with a different fix:

1. UK POSTCODES, not city names. Several sources return raw postcodes
   ("EC3M6BL", "M13LD", "NN157JU") instead of a readable place name —
   the original version only ever looked for city names in the text,
   so a postcode-only string had literally nothing to match. Fixed by
   decoding the postcode's leading letter area code (e.g. "EC" -> EC
   is a London postcode area) via _POSTCODE_AREA_TO_LOCATION below.
2. Genuine missing UK towns — Stockport, Warrington, Doncaster,
   Blackpool, Chesterfield, Burnley, Woking, Basingstoke all appeared
   repeatedly in the real data and simply weren't in the original list.
3. Non-UK jobs. Kuala Lumpur, Madrid, Dublin, Kathmandu, Singapore,
   Hong Kong, Lahore, and even Dutch-language job titles show up in
   the real dataset despite sources being configured for UK results.
   These were previously silently mislabeled "Other UK", which is
   actively wrong, not just imprecise — a Madrid job is not in the UK.
   Given an honest "International" category instead. The proper fix
   for jobs like this appearing at all is tighter scraper-level
   location filtering — a separate, real follow-up, not something this
   taxonomy should paper over.

SECOND PASS (this update): "Other UK" was still catching a
disproportionate share of real jobs, so this expanded on the same
methodology rather than guessing further — two more genuine gaps, both
addressed below:

4. UK postcode area coverage was much thinner than it looked — only
   ~60 of the ~120 real postcode areas were mapped at all, and several
   of the missing ones are Greater London itself. CR (Croydon), BR
   (Bromley), DA (Dartford/Bexley), EN (Enfield), HA (Harrow), KT
   (Kingston), TW (Twickenham/Richmond), UB (Uxbridge/Hillingdon), IG
   (Ilford/Redbridge), and RM (Romford/Havering) are all outer London
   boroughs, folded into "London" rather than given their own entries
   — unlike a satellite town such as Stockport or Warrington, nobody
   markets or searches for a grad job as being specifically "in
   Croydon" the way they would "in Manchester" vs "in Stockport";
   Greater London operates as one job-market brand. WF (Wakefield) —
   flagged as a known, explicitly-accepted gap in the original version
   of this docstring and its own test suite — is fixed the other way,
   as a new standalone canonical town, following the Stockport/
   Warrington precedent instead, since Wakefield is a distinct city in
   its own right rather than a London-adjacent commuter borough.
5. ~25 more genuine mid-size UK towns, chosen the same way as the
   Stockport/Warrington batch — real, commonly-referenced UK towns
   with their own postcode area, not currently in the list. Unlike the
   original rewrite, this pass didn't have direct access to a fresh
   sample of live "Other UK" raw strings to confirm frequency against
   — so treat this as a principled expansion from known UK postcode
   geography, not a repeat of the original data-driven process. The
   same "pull the real raw strings and look" method that built this
   list in the first place is exactly how it should keep being tuned
   going forward — scripts/backfill_categories.py's per-category
   breakdown output is the tool for that.

Known limitations, still worth being upfront about:
  - Postcode area decoding is a best-effort lookup covering the areas
    that map cleanly to a canonical location — some valid UK postcode
    areas aren't mapped to any of our canonical cities and will still
    fall to "Other UK". That's a real, accepted gap, not a bug —
    better to leave a genuine unknown as "Other UK" (or let the AI
    fallback in app/ai_classification.py take a shot at it) than force
    it into a nearby but wrong city.
  - "York" vs "New York" and "London" vs "New London, Connecticut":
    word-boundary matching means these US cities would technically
    match — accepted as effectively irrelevant for a UK-only platform.
  - RH (postcode area) is canonicalized as "Crawley" since Crawley/
    Gatwick is the larger regional job market, even though the area's
    postal namesake town is technically Redhill — a deliberate,
    practical approximation, not an oversight.
"""
import re

CANONICAL_LOCATIONS = [
    # England — major/mid-size cities and towns
    "London", "Manchester", "Birmingham", "Leeds", "Bristol", "Liverpool",
    "Sheffield", "Newcastle", "Nottingham", "Leicester", "Southampton",
    "Oxford", "Cambridge", "Reading", "Brighton", "York", "Bath",
    "Coventry", "Derby", "Hull", "Plymouth", "Norwich", "Exeter",
    "Milton Keynes", "Portsmouth", "Bournemouth", "Sunderland",
    "Wolverhampton", "Stoke-on-Trent", "Preston", "Bradford", "Ipswich",
    "Northampton", "Swindon", "Peterborough", "Luton", "Watford",
    "Guildford", "Chester", "Lincoln", "Gloucester", "Cheltenham",
    "Middlesbrough", "Stockport", "Warrington", "Doncaster", "Blackpool",
    "Chesterfield", "Burnley", "Woking", "Basingstoke",
    # England — added in the second expansion pass (see module docstring, point 5)
    "Wakefield", "Slough", "Stevenage", "St Albans", "Crawley",
    "Southend-on-Sea", "Chelmsford", "Colchester", "Medway", "Telford",
    "Shrewsbury", "Worcester", "Dudley", "Walsall", "Durham", "Harrogate",
    "Huddersfield", "Blackburn", "Wigan", "Oldham", "Bolton", "Lancaster",
    "Carlisle", "Darlington", "Taunton", "Salisbury",
    # Scotland
    "Edinburgh", "Glasgow", "Aberdeen", "Dundee",
    # Wales
    "Cardiff", "Swansea", "Newport",
    # Northern Ireland
    "Belfast",
    # Catch-alls
    "Remote", "International", "Other UK",
]

# Substrings (lowercase) that, if found anywhere in the raw location
# text, map to that canonical category. Checked in the order below;
# first match wins. Compound names include both hyphenated and
# spaced variants since sources are inconsistent about which they use.
_LOCATION_PATTERNS = [
    ("London", ["london"]),
    ("Manchester", ["manchester"]),
    ("Birmingham", ["birmingham"]),
    ("Leeds", ["leeds"]),
    ("Bristol", ["bristol"]),
    ("Liverpool", ["liverpool"]),
    ("Sheffield", ["sheffield"]),
    ("Newcastle", ["newcastle", "tyne and wear", "tyneside"]),
    ("Nottingham", ["nottingham"]),
    ("Leicester", ["leicester"]),
    ("Southampton", ["southampton"]),
    ("Oxford", ["oxford"]),
    ("Cambridge", ["cambridge"]),
    ("Reading", ["reading"]),
    ("Brighton", ["brighton"]),
    ("York", ["york"]),
    ("Bath", ["bath"]),
    ("Coventry", ["coventry"]),
    ("Derby", ["derby"]),
    ("Hull", ["hull", "kingston upon hull"]),
    ("Plymouth", ["plymouth"]),
    ("Norwich", ["norwich"]),
    ("Exeter", ["exeter"]),
    ("Milton Keynes", ["milton keynes"]),
    ("Portsmouth", ["portsmouth"]),
    ("Bournemouth", ["bournemouth"]),
    ("Sunderland", ["sunderland"]),
    ("Wolverhampton", ["wolverhampton"]),
    ("Stoke-on-Trent", ["stoke-on-trent", "stoke on trent"]),
    ("Preston", ["preston"]),
    ("Bradford", ["bradford"]),
    ("Ipswich", ["ipswich"]),
    ("Northampton", ["northampton"]),
    ("Swindon", ["swindon"]),
    ("Peterborough", ["peterborough"]),
    ("Luton", ["luton"]),
    ("Watford", ["watford"]),
    ("Guildford", ["guildford"]),
    ("Chester", ["chester"]),
    ("Lincoln", ["lincoln"]),
    ("Gloucester", ["gloucester"]),
    ("Cheltenham", ["cheltenham"]),
    ("Middlesbrough", ["middlesbrough"]),
    ("Stockport", ["stockport"]),
    ("Warrington", ["warrington"]),
    ("Doncaster", ["doncaster"]),
    ("Blackpool", ["blackpool"]),
    ("Chesterfield", ["chesterfield"]),
    ("Burnley", ["burnley"]),
    ("Woking", ["woking"]),
    ("Basingstoke", ["basingstoke"]),
    ("Wakefield", ["wakefield"]),
    ("Slough", ["slough"]),
    ("Stevenage", ["stevenage"]),
    ("St Albans", ["st albans", "st. albans"]),
    ("Crawley", ["crawley"]),
    ("Southend-on-Sea", ["southend-on-sea", "southend on sea", "southend"]),
    ("Chelmsford", ["chelmsford"]),
    ("Colchester", ["colchester"]),
    ("Medway", ["medway", "rochester", "chatham", "gillingham"]),
    ("Telford", ["telford"]),
    ("Shrewsbury", ["shrewsbury"]),
    ("Worcester", ["worcester"]),
    ("Dudley", ["dudley"]),
    ("Walsall", ["walsall"]),
    ("Durham", ["durham"]),
    ("Harrogate", ["harrogate"]),
    ("Huddersfield", ["huddersfield"]),
    ("Blackburn", ["blackburn"]),
    ("Wigan", ["wigan"]),
    ("Oldham", ["oldham"]),
    ("Bolton", ["bolton"]),
    ("Lancaster", ["lancaster"]),
    ("Carlisle", ["carlisle"]),
    ("Darlington", ["darlington"]),
    ("Taunton", ["taunton"]),
    ("Salisbury", ["salisbury"]),
    ("Edinburgh", ["edinburgh"]),
    ("Glasgow", ["glasgow"]),
    ("Aberdeen", ["aberdeen"]),
    ("Dundee", ["dundee"]),
    ("Cardiff", ["cardiff"]),
    ("Swansea", ["swansea"]),
    ("Newport", ["newport"]),
    ("Belfast", ["belfast"]),
]

# Non-UK cities that showed up in real production data despite sources
# being configured for UK results — see module docstring. Deliberately
# limited to cities actually observed, not broader country names: an
# earlier version also included generic country names like "ireland"
# as a speculative extension, which caused a real regression — "Belfast,
# Northern Ireland" (genuinely UK territory) was being miscategorized as
# International, since "Ireland" appears as a standalone word inside
# "Northern Ireland" too. Evidence-based city names avoid this risk
# entirely; broader country-name matching isn't worth the collision risk
# without a specific observed case requiring it.
_INTERNATIONAL_PATTERNS = [
    "kuala lumpur", "madrid", "dublin", "kathmandu", "singapore",
    "hong kong", "lahore",
]

_REMOTE_KEYWORDS = [
    "remote", "work from home", "wfh", "anywhere", "home based",
    "home-based", "internet",  # "internet" seen in real data as a
                                 # placeholder location for fully-remote roles
]

# UK postcode "area" codes (the 1-2 leading letters of a postcode, e.g.
# "EC" in "EC3M 6BL") mapped to the nearest canonical location. Only
# includes areas with a clean, sensible mapping to one of our named
# cities — see the "known limitations" note in the module docstring for
# what's deliberately left unmapped.
_POSTCODE_AREA_TO_LOCATION = {
    "E": "London", "EC": "London", "N": "London", "NW": "London",
    "SE": "London", "SW": "London", "W": "London", "WC": "London",
    # Outer London boroughs — see module docstring, point 4, for why
    # these fold into "London" rather than becoming their own entries.
    "CR": "London", "BR": "London", "DA": "London", "EN": "London",
    "HA": "London", "KT": "London", "TW": "London", "UB": "London",
    "IG": "London", "RM": "London",
    "M": "Manchester", "B": "Birmingham", "LS": "Leeds", "BS": "Bristol",
    "L": "Liverpool", "S": "Sheffield", "NE": "Newcastle", "NG": "Nottingham",
    "LE": "Leicester", "SO": "Southampton", "OX": "Oxford", "CB": "Cambridge",
    "RG": "Reading", "BN": "Brighton", "YO": "York", "BA": "Bath",
    "CV": "Coventry", "DE": "Derby", "HU": "Hull", "PL": "Plymouth",
    "NR": "Norwich", "EX": "Exeter", "MK": "Milton Keynes", "PO": "Portsmouth",
    "BH": "Bournemouth", "SR": "Sunderland", "WV": "Wolverhampton",
    "ST": "Stoke-on-Trent", "PR": "Preston", "BD": "Bradford", "IP": "Ipswich",
    "NN": "Northampton", "SN": "Swindon", "PE": "Peterborough", "LU": "Luton",
    "WD": "Watford", "GU": "Guildford", "CH": "Chester", "LN": "Lincoln",
    "GL": "Gloucester", "TS": "Middlesbrough", "SK": "Stockport",
    "WA": "Warrington", "DN": "Doncaster", "FY": "Blackpool",
    "WF": "Wakefield", "SL": "Slough", "SG": "Stevenage", "AL": "St Albans",
    "RH": "Crawley", "SS": "Southend-on-Sea", "CM": "Chelmsford",
    "CO": "Colchester", "ME": "Medway", "TF": "Telford", "SY": "Shrewsbury",
    "WR": "Worcester", "DY": "Dudley", "WS": "Walsall", "DH": "Durham",
    "HG": "Harrogate", "HD": "Huddersfield", "BB": "Blackburn", "WN": "Wigan",
    "OL": "Oldham", "BL": "Bolton", "LA": "Lancaster", "CA": "Carlisle",
    "DL": "Darlington", "TA": "Taunton", "SP": "Salisbury",
    "EH": "Edinburgh", "G": "Glasgow", "AB": "Aberdeen", "DD": "Dundee",
    "CF": "Cardiff", "SA": "Swansea", "NP": "Newport", "BT": "Belfast",
}

# Matches the leading letter(s) of a UK postcode outward code, e.g.
# "EC3M6BL" -> "EC", "M13LD" -> "M", "RG11AF" -> "RG".
_POSTCODE_AREA_PATTERN = re.compile(r"^([A-Z]{1,2})\d")


def _try_match_postcode(raw_location: str) -> str | None:
    """Returns a canonical location if the raw text looks like a bare UK postcode with a known area code, else None."""
    candidate = raw_location.strip().upper().replace(" ", "")
    match = _POSTCODE_AREA_PATTERN.match(candidate)
    if not match:
        return None
    area = match.group(1)
    return _POSTCODE_AREA_TO_LOCATION.get(area)


def categorize_location(raw_location: str, remote_type: str = "") -> str:
    """
    Maps a raw, free-text location string (plus the already-extracted
    remote_type signal from normalize.py, if available) onto exactly
    one of CANONICAL_LOCATIONS.

    Check order: Remote -> International -> named UK city -> UK
    postcode -> Other UK. Remote is checked first and takes priority
    over any city mentioned in the text — a listing that says "London
    (Remote)" is categorized as Remote, since that's the more useful
    bucket for someone specifically filtering for remote work.
    """
    text = (raw_location or "").lower()

    if remote_type == "remote" or any(kw in text for kw in _REMOTE_KEYWORDS):
        return "Remote"

    if any(kw in text for kw in _INTERNATIONAL_PATTERNS):
        return "International"

    for category, patterns in _LOCATION_PATTERNS:
        for pattern in patterns:
            if re.search(rf"\b{re.escape(pattern)}\b", text):
                return category

    postcode_match = _try_match_postcode(raw_location or "")
    if postcode_match:
        return postcode_match

    return "Other UK"
