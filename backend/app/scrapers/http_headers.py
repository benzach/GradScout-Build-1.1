"""
Shared HTTP headers for the scrapers that hit sites without an official
API (currently app/scrapers/static_scraper.py, and the RSS scraper's
detail-page fetch in app/scrapers/rss_scraper.py). Reed, Adzuna, and
Jooble are official, key-authenticated APIs and have nothing to do with
this module.

Sends an honest, identifying User-Agent rather than impersonating a
browser. This used to spoof a real Chrome User-Agent string (plus a
full browser-like header set) specifically to get past basic
bot-detection — which meant, in practice, disguising automated access
to sites that don't offer an API as if it were a person clicking
around in a browser.

That's worth being straightforward about instead: identifying a bot
honestly is the actual norm for well-behaved crawlers (see e.g.
ons.gov.uk/help/fairusepolicy, which explicitly asks bots to "set an
appropriate user agent header that clearly identifies you and provides
a contact") — it lets a site's operators recognise, rate-limit, or
allowlist a legitimate bot instead of just seeing anomalous automated
traffic with no way to tell what it is or reach whoever's running it.
It also means this codebase isn't quietly doing the opposite of the
"identify yourself" story elsewhere in the app.

SCRAPER_CONTACT_URL / SCRAPER_CONTACT_EMAIL are separate env vars, not
hardcoded — set these to a real URL/address once GradScout has a public
presence to point to (see .env.example). Left unset, the User-Agent is
still an honest, non-impersonating identifier — it just can't point
anywhere useful yet, which is the truth of where the project is right
now, not a reason to fake a browser in the meantime.
"""
import os


def build_scraper_headers() -> dict:
    contact_url = os.environ.get("SCRAPER_CONTACT_URL", "").strip()
    contact_email = os.environ.get("SCRAPER_CONTACT_EMAIL", "").strip()
    contact_parts = [p for p in (contact_url, contact_email) if p]
    contact = f" ({'; '.join(contact_parts)})" if contact_parts else ""

    return {
        "User-Agent": f"GradScoutBot/1.0{contact}",
        # Genuinely informative, not part of any disguise: an honest
        # bot fetching HTML still has a real preferred content type and
        # language, same as it would if these were left unset.
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
    }
