import { precacheAndRoute } from 'workbox-precaching'

// Precaches the app shell — this is what "generateSW" mode (the
// default, used through Stage 3) did automatically. Switching to a
// custom service worker via injectManifest means doing this one line
// explicitly, in exchange for being able to add the two listeners
// below, which generateSW mode has no hook for at all. self.__WB_MANIFEST
// is injected by vite-plugin-pwa at build time — not something defined
// here.
precacheAndRoute(self.__WB_MANIFEST)

self.addEventListener('push', (event) => {
  let data = {}
  try {
    data = event.data ? event.data.json() : {}
  } catch {
    data = { title: 'GradScout', body: event.data ? event.data.text() : 'You have a new match.' }
  }

  const title = data.title || 'GradScout'
  const options = {
    body: data.body || '',
    icon: '/icon-192.png',
    badge: '/icon-192.png',
    // Carried through to notificationclick below — this is how a tap
    // knows which specific job to open, rather than just launching
    // the app in general.
    data: { matchId: data.match_id || null },
  }

  event.waitUntil(self.registration.showNotification(title, options))
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const matchId = event.notification.data?.matchId
  const targetUrl = matchId ? `/app/jobs/${matchId}` : '/app/feed'

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientsList) => {
      // Reuse an already-open tab if one exists, rather than piling up
      // a new one every time a notification is tapped.
      for (const client of clientsList) {
        if ('focus' in client) {
          client.navigate(targetUrl)
          return client.focus()
        }
      }
      return self.clients.openWindow(targetUrl)
    }),
  )
})
