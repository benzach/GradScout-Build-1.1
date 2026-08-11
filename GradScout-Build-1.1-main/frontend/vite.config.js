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
      includeAssets: ['icon-192.png', 'icon-512.png'],
      manifest: {
        name: 'GradScout',
        short_name: 'GradScout',
        description: 'Graduate and entry-level jobs, found for you.',
        theme_color: '#0a2a1c',
        background_color: '#f8fafc',
        display: 'standalone',
        start_url: '/',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
        ],
      },
      workbox: {
        runtimeCaching: [
          {
            // Anything not same-origin as the deployed frontend is the
            // FastAPI backend (VITE_API_BASE_URL, a different Railway
            // domain) — never served from cache. A job-alert app
            // silently showing stale matches would defeat the entire
            // point of the product.
            urlPattern: ({ url }) => url.origin !== self.location.origin,
            handler: 'NetworkOnly',
          },
        ],
      },
    }),
  ],
})
