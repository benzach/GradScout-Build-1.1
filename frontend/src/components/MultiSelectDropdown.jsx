import { useEffect, useRef, useState } from 'react'

/**
 * A closed-by-default dropdown for choosing from a large, finite list
 * (locations, industries) without crowding the screen the way a wall
 * of always-visible toggle chips would once the list gets long (52
 * locations, 22 industries). Includes a search box inside the open
 * panel so finding one option among many doesn't mean scrolling
 * through all of them.
 */
export default function MultiSelectDropdown({ label, placeholder, options, values, onChange }) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const containerRef = useRef(null)

  useEffect(() => {
    function handleClickOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  function toggleOption(option) {
    onChange(values.includes(option) ? values.filter((v) => v !== option) : [...values, option])
  }

  const filteredOptions = options.filter((o) => o.toLowerCase().includes(search.toLowerCase()))

  const summary =
    values.length === 0 ? placeholder : values.length <= 2 ? values.join(', ') : `${values.length} selected`

  return (
    <div ref={containerRef} className="relative">
      <label className="block text-sm font-medium text-primary-700 mb-1.5">{label}</label>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg border border-primary-200 bg-white text-sm text-left focus:outline-none focus:ring-2 focus:ring-secondary-400"
      >
        <span className={values.length === 0 ? 'text-primary-400' : 'text-primary-900'}>{summary}</span>
        <svg
          className={`w-4 h-4 text-primary-400 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute z-10 mt-1.5 w-full bg-white rounded-lg border border-primary-200 shadow-lg max-h-72 flex flex-col">
          <div className="p-2 border-b border-primary-100">
            <input
              type="text"
              autoFocus
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search…"
              className="w-full px-2.5 py-1.5 text-sm rounded-md border border-primary-200 focus:outline-none focus:ring-1 focus:ring-secondary-400"
            />
          </div>
          <div className="overflow-y-auto py-1">
            {filteredOptions.length === 0 ? (
              <p className="text-xs text-primary-400 px-3 py-2">No matches</p>
            ) : (
              filteredOptions.map((option) => (
                <label
                  key={option}
                  className="flex items-center gap-2.5 px-3 py-2 text-sm text-primary-700 hover:bg-secondary-50 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={values.includes(option)}
                    onChange={() => toggleOption(option)}
                    className="rounded border-primary-300 text-secondary-600 focus:ring-secondary-400"
                  />
                  {option}
                </label>
              ))
            )}
          </div>
        </div>
      )}

      {values.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {values.map((v) => (
            <span key={v} className="inline-flex items-center gap-1 bg-secondary-100 text-primary-800 text-xs px-2 py-0.5 rounded-md">
              {v}
              <button type="button" onClick={() => toggleOption(v)} className="text-primary-400 hover:text-primary-700" aria-label={`Remove ${v}`}>
                ×
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
