import { api } from './api'

/**
 * Converts a base64url string (what the backend's VAPID public key
 * comes as) into the raw Uint8Array the Push API's applicationServerKey
 * actually requires. The browser API and our backend don't speak the
 * same encoding natively — this is the standard conversion every
 * Web Push integration needs, not something specific to this app.
 */
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = window.atob(base64)
  return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)))
}

export function isPushSupported() {
  return 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window
}

/** 'unsupported' | 'default' | 'granted' | 'denied' */
export function getNotificationPermissionState() {
  if (!isPushSupported()) return 'unsupported'
  return Notification.permission
}

export async function enablePushNotifications() {
  if (!isPushSupported()) {
    // The most common real cause on a phone: iOS requires the app to
    // already be added to the home screen before these APIs exist at
    // all — visiting the site in a normal Safari tab isn't enough,
    // and there's no way to detect or explain that more specifically
    // than this from inside the page itself.
    throw new Error('Push notifications are not supported in this browser or context.')
  }

  const permission = await Notification.requestPermission()
  if (permission !== 'granted') {
    throw new Error('Notification permission was not granted.')
  }

  const registration = await navigator.serviceWorker.ready
  const { public_key: vapidPublicKey } = await api.get('/push/vapid-public-key')
  if (!vapidPublicKey) {
    throw new Error('Push notifications are not configured on the server yet.')
  }

  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
  })

  await api.post('/push/subscriptions', subscription.toJSON())
  return subscription
}

export async function disablePushNotifications() {
  if (!isPushSupported()) return
  const registration = await navigator.serviceWorker.ready
  const subscription = await registration.pushManager.getSubscription()
  if (!subscription) return

  // Best-effort — if the backend call fails, still unsubscribe locally
  // rather than leaving the user stuck unable to turn notifications
  // off just because a network request hiccuped.
  await api.delete('/push/subscriptions', { endpoint: subscription.endpoint }).catch(() => {})
  await subscription.unsubscribe()
}
