import { useState } from 'react'

/**
 * Free-text chip input for fields with no finite option list (keywords)
 * — the free-text counterpart to MultiSelectDropdown, which handles
 * fields that DO have one (locations, industries). Type, press Enter
 * or comma to commit a chip; backspace on an empty input removes the
 * last one.
 */
export default function TagInput({ label, placeholder, values, onChange }) {
  const [input, setInput] = useState('')

  function commitTag(raw) {
    const tag = raw.trim()
    if (tag && !values.includes(tag)) {
      onChange([...values, tag])
    }
    setInput('')
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      commitTag(input)
    } else if (e.key === 'Backspace' && input === '' && values.length > 0) {
      onChange(values.slice(0, -1))
    }
  }

  function removeTag(tag) {
    onChange(values.filter((v) => v !== tag))
  }

  return (
    <div>
      <label className="block text-sm font-medium text-primary-700 mb-1.5">{label}</label>
      <div className="w-full flex flex-wrap items-center gap-1.5 px-3 py-2 rounded-lg border border-primary-200 bg-white focus-within:ring-2 focus-within:ring-secondary-400">
        {values.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 bg-secondary-100 text-primary-800 text-xs px-2 py-0.5 rounded-md"
          >
            {tag}
            <button
              type="button"
              onClick={() => removeTag(tag)}
              className="text-primary-400 hover:text-primary-700"
              aria-label={`Remove ${tag}`}
            >
              ×
            </button>
          </span>
        ))}
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={() => commitTag(input)}
          placeholder={values.length === 0 ? placeholder : ''}
          className="flex-1 min-w-[80px] text-sm text-primary-900 placeholder:text-primary-400 outline-none py-0.5"
        />
      </div>
      <p className="text-xs text-primary-400 mt-1">Press Enter or comma to add</p>
    </div>
  )
}
