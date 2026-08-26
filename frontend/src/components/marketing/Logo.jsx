import { Link } from 'react-router-dom'

/**
 * Reuses the real app icon (public/icon-*.png — the same mark used for
 * the browser favicon, PWA home-screen icon, and push notifications)
 * rather than redrawing it, so the site nav/footer and the installed
 * app always show the exact same mark. Rounded here via CSS since the
 * source PNGs are delivered full-bleed square (maskable-icon
 * convention — the OS applies its own mask shape on Android, so the
 * file itself carries no baked-in corner radius to match).
 */
export function Mark({ size = 32, className = '' }) {
  return (
    <img
      src="/icon-192.png"
      alt=""
      width={size}
      height={size}
      className={`rounded-[28%] shrink-0 ${className}`}
      style={{ width: size, height: size }}
    />
  )
}

export default function Logo({ className = '', wordmarkClassName = '', size = 32, to = '/' }) {
  return (
    <Link to={to} className={`inline-flex items-center gap-2.5 ${className}`}>
      <Mark size={size} />
      <span className={`font-heading font-extrabold tracking-tight text-primary-900 ${wordmarkClassName}`}>
        GradScout
      </span>
    </Link>
  )
}
