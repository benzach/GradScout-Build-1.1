import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      // Phase 7 needs a real push event handler and notificationclick
      // handler — generateSW mode (used through Stage 3) auto-writes a
      // service worker with no hook for either. injectManifest mode
      // uses OUR file (src/sw.js) instead, which vite-plugin-pwa
      // injects the precache manifest into at build time rather than
      // generating the whole file itself.
      strategies: 'injectManifest',
      srcDir: 'src',
      filename: 'sw.js',
      includeAssets: ['icon-192.png', 'icon-512.png'],
      // Explicit because the default glob (js/css/html only) would
      // otherwise leave the self-hosted font files (index.css's
      // @fontsource imports) uncached - meaning headings/body text
      // would silently fall back to a system font the first time the
      // app is opened offline. Must list every base type too (not just
      // the addition) once this option is set at all - see
      // vite-plugin-pwa's injectManifest docs.
      injectManifest: {
        globPatterns: ['**/*.{js,css,html,woff2}'],
      },
      manifest: {
        name: 'GradScout',
        short_name: 'GradScout',
        description: 'Graduate and entry-level jobs, found for you.',
        theme_color: '#3a405a',
        background_color: '#f3f5f9',
        display: 'standalone',
        // Installed from the browser via "Add to Home Screen" — that
        // icon should open the product, not gradscout.uk's marketing
        // homepage. ProtectedRoute still sends a signed-out tap
        // straight to /app/login, so this is safe either way.
        start_url: '/app',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
        ],
      },
      // No runtimeCaching config here (that was generateSW-only) — but
      // the cross-origin-API-calls-never-cached property this existed
      // for is preserved for free: src/sw.js's precacheAndRoute only
      // ever routes the same-origin build assets listed in its
      // manifest, so a cross-origin call to the Railway API was never
      // going to be intercepted by this service worker either way.
    }),
  ],
})
