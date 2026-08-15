import { useEffect, useState } from 'react'
import { Share, X } from 'lucide-react'

const DISMISS_KEY = 'gradscout_install_banner_dismissed'

function isStandalone() {
  // Two different APIs because there are two different platforms to
  // detect "already installed" on — the standard media query most
  // browsers support, and Safari's own older, iOS-only property.
  return window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true
}

function isIOS() {
  return /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream
}

/**
 * Deliberately two very different code paths, not one generic
 * "install" button, because the platforms genuinely don't offer the
 * same capability:
 *
 * - Android/Chrome fires a real `beforeinstallprompt` event this
 *   component can capture and trigger programmatically on a tap.
 * - iOS Safari has no equivalent API at all, by Apple's own design —
 *   the only path is a user manually using Share → Add to Home
 *   Screen, so the most this banner can do there is tell them that,
 *   clearly, since there's nothing to wire up otherwise.
 *
 * This matters a lot here specifically because push notifications
 * (Stage 4) don't work on iOS at all until this step is done.
 */
export default function InstallBanner() {
  const [deferredPrompt, setDeferredPrompt] = useState(null)
  const [visible, setVisible] = useState(false)
  const [platform, setPlatform] = useState(null)

  useEffect(() => {
    if (isStandalone() || localStorage.getItem(DISMISS_KEY)) return

    if (isIOS()) {
      // No event to wait for — iOS never fires beforeinstallprompt, so
      // this is the one case where the banner just shows immediately.
      setPlatform('ios')
      setVisible(true)
      return
    }

    function handleBeforeInstallPrompt(e) {
      e.preventDefault() // stops the browser's own mini-infobar so ours shows instead, at a moment we control
      setDeferredPrompt(e)
      setPlatform('android')
      setVisible(true)
    }

    function handleAppInstalled() {
      // Covers installing via the browser's own menu instead of this
      // banner's button — either path should stop nagging afterward.
      setVisible(false)
      localStorage.setItem(DISMISS_KEY, 'true')
    }

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt)
    window.addEventListener('appinstalled', handleAppInstalled)
    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt)
      window.removeEventListener('appinstalled', handleAppInstalled)
    }
  }, [])

  function dismiss() {
    setVisible(false)
    localStorage.setItem(DISMISS_KEY, 'true')
  }

  async function handleInstallClick() {
    if (!deferredPrompt) return
    deferredPrompt.prompt()
    const { outcome } = await deferredPrompt.userChoice
    setDeferredPrompt(null)
    setVisible(false)
    if (outcome !== 'accepted') {
      // They explicitly said no — respect that rather than asking again next visit.
      localStorage.setItem(DISMISS_KEY, 'true')
    }
  }

  if (!visible) return null

  return (
    <div className="fixed bottom-0 inset-x-0 z-50 bg-brand-950 text-white px-4 py-3 flex items-center gap-3 shadow-lg">
      {platform === 'ios' ? (
        <p className="text-sm flex-1 flex items-center gap-1.5 flex-wrap">
          <Share size={15} className="inline shrink-0" />
          Install GradScout: tap Share, then <span className="font-semibold">Add to Home Screen</span> — needed for notifications to work.
        </p>
      ) : (
        <p className="text-sm flex-1">Install GradScout for the full experience, including notifications.</p>
      )}

      <div className="flex items-center gap-2 shrink-0">
        {platform === 'android' && (
          <button
            onClick={handleInstallClick}
            className="text-sm font-medium bg-white text-brand-950 px-3 py-1.5 rounded-lg hover:bg-slate-100 transition-colors"
          >
            Install
          </button>
        )}
        <button onClick={dismiss} aria-label="Dismiss" className="text-white/70 hover:text-white p-1">
          <X size={18} />
        </button>
      </div>
    </div>
  )
}
