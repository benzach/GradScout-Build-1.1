import { ArrowLeft } from 'lucide-react'

/**
 * The back control used at the top-left of every non-tab screen
 * (Criteria, JobFeed, JobDetail, Privacy). Previously this was a small
 * inline text link ("← Back") with no real padding — easy to miss and
 * hard to hit accurately on a phone. This is a real <button> sized to
 * meet the ~44x44px minimum recommended touch target (WCAG 2.5.5 /
 * Apple & Material HIG), not just a bigger font.
 *
 * `onClick` defaults to browser back (`navigate(-1)`) if not given,
 * but most call sites pass an explicit destination instead — going to
 * a named route (e.g. `/`) is more predictable than history-based back
 * when a user could have arrived at the current screen several
 * different ways (deep link, push notification, etc).
 */
export default function BackButton({ onClick, label = 'Back', className = '' }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      className={`inline-flex items-center gap-1.5 -ml-2.5 min-h-[44px] min-w-[44px] px-3 py-2.5 rounded-full text-primary-700 hover:bg-primary-100 active:bg-primary-200 transition-colors ${className}`}
    >
      <ArrowLeft size={24} strokeWidth={2.25} />
      <span className="text-[15px] font-medium">{label}</span>
    </button>
  )
}
