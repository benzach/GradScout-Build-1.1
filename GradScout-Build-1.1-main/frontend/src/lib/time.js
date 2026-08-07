/** "3 days ago" style formatting — no date library needed for something this small. */
export function timeAgo(isoString) {
  if (!isoString) return null
  const then = new Date(isoString)
  const diffDays = Math.floor((Date.now() - then.getTime()) / (1000 * 60 * 60 * 24))

  if (diffDays <= 0) return 'today'
  if (diffDays === 1) return '1 day ago'
  if (diffDays < 7) return `${diffDays} days ago`

  const diffWeeks = Math.floor(diffDays / 7)
  return diffWeeks === 1 ? '1 week ago' : `${diffWeeks} weeks ago`
}
