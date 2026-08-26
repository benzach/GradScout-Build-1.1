/**
 * Optional, privacy-friendly usage analytics via Plausible
 * (plausible.io — works with either their cloud service or a
 * self-hosted instance). No cookies, no cross-site tracking, no
 * personal data — a genuinely different category from the ad-tracking
 * kind of analytics the Privacy Notice already promises GradScout
 * doesn't do.
 *
 * Entirely optional and off by default: this is the one integration in
 * the app I (Claude) can't actually finish for you — it needs a real
 * Plausible account (cloud or self-hosted) that only you can create,
 * so this file can only wire up the hook, not turn it on. Leave
 * VITE_PLAUSIBLE_DOMAIN unset and this does nothing at all — no
 * script tag, no request, no console noise.
 *
 * Injected via JS at runtime rather than a static <script> tag in
 * index.html specifically so "unconfigured" truly means zero network
 * requests — a hardcoded tag pointing at a domain that may not exist
 * yet would otherwise fire on every single page load regardless.
 */
export function initAnalytics() {
  const domain = import.meta.env.VITE_PLAUSIBLE_DOMAIN
  if (!domain) return

  // Defaults to Plausible's cloud service; override for a self-hosted
  // instance (e.g. VITE_PLAUSIBLE_SCRIPT_SRC=https://analytics.yourdomain.com/js/script.js).
  const scriptSrc = import.meta.env.VITE_PLAUSIBLE_SCRIPT_SRC || 'https://plausible.io/js/script.js'

  const script = document.createElement('script')
  script.defer = true
  script.dataset.domain = domain
  script.src = scriptSrc
  document.head.appendChild(script)
}
