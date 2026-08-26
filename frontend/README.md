# GradScout Frontend

React + Vite + Tailwind v4, built as an installable PWA (via
vite-plugin-pwa). GradScout issues and verifies its own auth tokens
(see `backend/app/auth.py`); this frontend just stores the resulting
token and sends it as a bearer header on every API call.

One React app serves two things at the same domain:

- **The public marketing site** — `/`, `/terms`, `/privacy`. Anyone can
  see these, signed in or not.
- **The product itself** — everything under `/app` (`/app/login`,
  `/app`, `/app/criteria`, `/app/feed`, `/app/jobs/:id`,
  `/app/settings`). `ProtectedRoute` sends anyone without a valid
  session straight to `/app/login`.

This split is why `App.jsx` has two distinct route groups rather than
one flat list — see the comments there before adding a new page, so it
lands in the right one.

## Setup

```bash
npm install
cp .env.example .env   # fill in your real API URL
npm run dev
```

You need one value in `.env`:
- `VITE_API_BASE_URL` — your deployed backend's public URL (Railway,
  or `http://localhost:8000` for local development against
  `uvicorn app.main:app --reload`)

## What's here

- **Marketing site** (`src/pages/marketing/`, `src/components/marketing/`)
  — `Landing.jsx` (hero, how it works, features, sources, FAQ),
  `NotFound.jsx`, and the shared `MarketingHeader` / `MarketingFooter` /
  `MarketingLayout` chrome. `Terms.jsx` and `Privacy.jsx` use this same
  chrome so they read as part of one site even when someone lands
  directly on `/privacy` from a search engine, rather than as orphaned
  standalone screens.
- **Auth** (`src/context/AuthContext.jsx`) — real sign-up and sign-in
  against the FastAPI backend's own `/auth` endpoints, session
  persisted and kept in sync automatically. `Login.jsx` reads
  `?mode=signup` from the URL so a marketing "Get started" button can
  deep-link straight to the sign-up tab instead of making someone find
  the toggle themselves.
- **API client** (`src/lib/api.js`) — wraps `fetch`, automatically
  attaches the current session's token as `Authorization: Bearer
  <token>` on every backend call.
- **The product screens** (`src/pages/`) — Home (hub), Criteria (saved
  search CRUD), JobFeed (swipe to favourite/dismiss, filter tabs),
  JobDetail, Settings (push notifications, email digest, account
  deletion). These keep their own mobile-first chrome (`BottomNav`,
  `BackButton`) — deliberately unrelated to the marketing site's header
  and footer, since they're a different kind of screen for a different
  moment (a focused tool, not a page to browse).

## PWA

`vite-plugin-pwa` generates the manifest and service worker
automatically on build. The installed app's `start_url` is `/app`, not
the marketing homepage — someone who's added GradScout to their home
screen wants the product, not the pitch for it; a signed-out tap still
lands on `/app/login` via `ProtectedRoute`.

API calls are configured as `NetworkOnly` in the caching strategy (see
`vite.config.js`), since a job alert app silently showing stale cached
data would defeat the entire point of the product.

Icons at `public/icon-192.png` / `icon-512.png` are the real GradScout
mark (also reused as the site's favicon and the marketing header/footer
logo via `src/components/marketing/Logo.jsx`) — replace all of these
together if the brand mark ever changes, since they're meant to stay
identical everywhere it appears.

## SEO

`index.html` carries the marketing site's meta description, Open Graph
and Twitter Card tags, and canonical URL — all pointed at
`https://www.gradscout.uk`. `public/robots.txt` allows crawling the
marketing/legal pages and disallows `/app` (there's nothing there for a
search engine to index — it's all behind a login). `public/sitemap.xml`
lists the same public pages; update its two `<lastmod>` dates if
`Terms.jsx` or `Privacy.jsx` meaningfully change.

The Open Graph preview image currently reused is `icon-512.png` (a
square icon, not a purpose-built social card) — swap `og:image` /
`twitter:image` in `index.html` for a real 1200×630 image whenever one
exists.

## Building for production

```bash
npm run build
```

Outputs to `dist/`.

## Deploying to www.gradscout.uk

This assumes the backend is already deployed (see `backend/README.md`
for the Railway steps) and you have its public URL to hand.

### 1. Deploy the frontend (Vercel)

Vercel is the easiest fit here — `vercel.json` is already set up with
the SPA rewrite every client-routed app like this one needs, so
navigating straight to `www.gradscout.uk/app/feed` (not just following
a link there) doesn't 404.

1. Push this repo to GitHub.
2. In Vercel: **New Project** → import the repo → set **Root
   Directory** to `frontend`.
3. Framework preset: Vite (should be auto-detected from `vite.config.js`).
4. Add one environment variable: `VITE_API_BASE_URL` = your backend's
   public URL (e.g. `https://gradscout-backend.up.railway.app`).
5. Deploy. Vercel gives you a `*.vercel.app` URL first — confirm the
   site loads and `/app/login` lets you sign up before moving to the
   custom domain.

(Netlify works too — `public/_redirects` covers the same SPA-fallback
need there. `vercel.json`'s `rewrites` only take effect on Vercel;
Netlify reads `_redirects` instead. Only one of the two matters
depending on which host you pick.)

### 2. Connect the domain

In the Vercel project: **Settings → Domains** → add both
`www.gradscout.uk` and `gradscout.uk` (add the apex too, and let Vercel
redirect it to `www` — that avoids the fairly common outcome of half
your visitors on `gradscout.uk` and half on `www.gradscout.uk`, split
across two unrelated-looking sites as far as a browser's address bar
and any cookies are concerned).

Vercel will show you the exact DNS records to add. In summary, at your
domain registrar / DNS provider:

| Type  | Name  | Value                    |
|-------|-------|--------------------------|
| CNAME | www   | `cname.vercel-dns.com`   |
| A     | @     | `76.76.21.21`            |

(Use whatever values Vercel's own Domains page actually shows you —
these are Vercel's current standard records at time of writing, but
check the dashboard rather than trusting a README that could go stale.)

DNS changes can take anywhere from a few minutes to a few hours to
propagate, depending on your registrar and the DNS record's TTL.

### 3. Tighten backend CORS

The backend's `app/main.py` currently allows every origin
(`allow_origins=["*"]`) — deliberately permissive for development,
flagged in its own comment as worth tightening "once Phase 6 gives you
[a frontend domain]." That's now `https://www.gradscout.uk`. This isn't
required for the site to *work* (a wildcard already permits it), but
it's worth doing before treating this as a real production launch
rather than a test deploy — restrict `allow_origins` to your actual
domain(s) so no other website can make authenticated requests against
your API using a visitor's browser.

### 4. Re-test end to end

Visit `https://www.gradscout.uk`, sign up through the real form, create
a saved search, and confirm the feed loads. If a saved search shows no
matches yet, the backend's scraping pipeline needs to have run at least
once — see `backend/README.md`'s section on the scheduler.
