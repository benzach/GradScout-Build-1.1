# GradScout

A graduate and entry-level job matching app for the UK. GradScout scans
several job board sources on a timer, deduplicates listings that are
really the same underlying role posted more than once, and matches
what's left against each user's own saved search criteria — surfaced
through an in-app feed, real-time push notifications, and an optional
weekly email digest.

The repo is split into two independently deployable pieces:

```
backend/    FastAPI + Postgres API — scraping, dedup, matching, auth, push, email digest
frontend/   React + Vite site — public marketing pages at / and the product itself at /app
```

Start with whichever half you're working on:

- **`backend/README.md`** — local setup, running the scrape pipeline
  manually, the API's auth model, and deploying to Railway.
- **`frontend/README.md`** — local setup, how the marketing site and
  the product share one React app, and deploying to Vercel/Netlify
  under a custom domain (written with `www.gradscout.uk` as the
  concrete example).

## How the pieces fit together

The frontend talks to the backend over plain HTTPS + a bearer token —
no shared database, no server-side rendering, no monorepo build step
tying the two together. That means they deploy independently:
backend on Railway (it needs a real Postgres instance and a
long-running process for the scheduler), frontend as a static build on
Vercel or Netlify. The only thing connecting them at runtime is the
frontend's `VITE_API_BASE_URL` environment variable, pointed at
wherever the backend actually lives.

## Where things stand

Auth, saved searches, the deduplicated job feed, favouriting/status
tracking, push notifications, the weekly email digest, and the PWA
install flow are all real and working end to end — see each
sub-project's own README for exact detail on what's built versus what's
explicitly still a known gap (email verification and password reset,
most notably — see `backend/README.md`'s Authentication section).
