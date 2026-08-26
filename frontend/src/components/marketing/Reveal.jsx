import { useEffect, useRef, useState } from 'react'

/**
 * Fades/slides a section in the first time it scrolls into view.
 * Plain IntersectionObserver rather than pulling in an animation
 * library — matches this codebase's existing pattern (see backend's
 * app/email_digest.py) of not adding a dependency for something a
 * native browser API already covers fully.
 *
 * Respects prefers-reduced-motion by skipping the transform/opacity
 * transition entirely rather than just shortening it.
 */
export default function Reveal({ children, className = '', delayMs = 0, as: Tag = 'div' }) {
  const ref = useRef(null)
  const [visible, setVisible] = useState(false)
  const [reduceMotion, setReduceMotion] = useState(false)

  useEffect(() => {
    setReduceMotion(window.matchMedia('(prefers-reduced-motion: reduce)').matches)
  }, [])

  useEffect(() => {
    if (reduceMotion) {
      setVisible(true)
      return
    }
    const node = ref.current
    if (!node) return
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true)
          observer.disconnect()
        }
      },
      { threshold: 0.15, rootMargin: '0px 0px -40px 0px' },
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [reduceMotion])

  return (
    <Tag
      ref={ref}
      className={className}
      style={{
        transitionProperty: 'opacity, transform',
        transitionDuration: '700ms',
        transitionTimingFunction: 'cubic-bezier(0.16, 1, 0.3, 1)',
        transitionDelay: `${delayMs}ms`,
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(16px)',
      }}
    >
      {children}
    </Tag>
  )
}
