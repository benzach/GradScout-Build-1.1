import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import TagInput from '../components/TagInput'
import MultiSelectDropdown from '../components/MultiSelectDropdown'
import BackButton from '../components/BackButton'

const CONTRACT_TYPE_OPTIONS = ['Full-time', 'Part-time', 'Permanent', 'Contract', 'Temporary', 'Internship']

// £2,000 increments starting at £18,000, up to £80,000 - covers the
// realistic range for graduate roles. Generated rather than hand-typed
// so the increment/start/end are each defined once and can't drift out
// of sync with each other.
const SALARY_MIN_START = 18000
const SALARY_MIN_END = 80000
const SALARY_MIN_STEP = 2000
const SALARY_OPTIONS = Array.from(
  { length: (SALARY_MIN_END - SALARY_MIN_START) / SALARY_MIN_STEP + 1 },
  (_, i) => SALARY_MIN_START + i * SALARY_MIN_STEP
)

const EMPTY_FORM = {
  label: '',
  keywords: [],
  excluded_keywords: [],
  locations: [],
  industries: [],
  salary_min: '',
  contract_types: [],
}

export default function Criteria() {
  const [existing, setExisting] = useState(null) // null = still loading
  const [locationOptions, setLocationOptions] = useState([]) // fetched from GET /locations - the backend's canonical list, never hardcoded here
  const [industryOptions, setIndustryOptions] = useState([]) // fetched from GET /industries - same principle
  const [form, setForm] = useState(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  // Only shown after a submit attempt with a blank name — not on every
  // keystroke, so the field doesn't start out looking like an error
  // before the user has even had a chance to type anything.
  const [labelTouched, setLabelTouched] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    api.get('/criteria').then(setExisting).catch((e) => setError(e.message))
    // Neither /locations nor /industries needs auth (see backend/app/routers/)
    // - fetched via plain fetch rather than the api client wrapper, since
    // there's no reason to require a session just to read a static list.
    const base = import.meta.env.VITE_API_BASE_URL
    fetch(`${base}/locations`).then((r) => r.json()).then(setLocationOptions).catch(() => setLocationOptions([]))
    fetch(`${base}/industries`).then((r) => r.json()).then(setIndustryOptions).catch(() => setIndustryOptions([]))
  }, [])

  function updateField(field, value) {
    setForm((f) => ({ ...f, [field]: value }))
  }

  function toggleContractType(type) {
    setForm((f) => ({
      ...f,
      contract_types: f.contract_types.includes(type)
        ? f.contract_types.filter((t) => t !== type)
        : [...f.contract_types, type],
    }))
  }

  const trimmedLabel = form.label.trim()
  const labelMissing = trimmedLabel.length === 0

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')

    if (labelMissing) {
      // Names are mandatory now - with several saved searches on the
      // Home/Criteria screens, "Untitled search" x3 is genuinely hard
      // to tell apart, which is the whole reason for this requirement.
      // Caught here (not just via the `required` attribute) so the
      // message is specific rather than the browser's generic one.
      setLabelTouched(true)
      return
    }

    setSubmitting(true)
    try {
      const created = await api.post('/criteria', {
        label: trimmedLabel,
        keywords: form.keywords,
        excluded_keywords: form.excluded_keywords,
        locations: form.locations,
        industries: form.industries,
        salary_min: form.salary_min ? parseInt(form.salary_min, 10) : null,
        contract_types: form.contract_types,
      })
      setExisting((prev) => [...(prev ?? []), created])
      setForm(EMPTY_FORM)
      setLabelTouched(false)
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDelete(id) {
    try {
      await api.delete(`/criteria/${id}`)
      setExisting((prev) => prev.filter((c) => c.id !== id))
    } catch (e) {
      setError(e.message)
    }
  }

  const isFirstCriteria = existing !== null && existing.length === 0

  return (
    <div className="min-h-screen bg-background px-4 py-8">
      <div className="max-w-sm mx-auto">
        <div className="mb-4">
          <BackButton onClick={() => navigate('/app')} />
        </div>

        <div className="mb-6">
          <h1 className="font-heading text-lg font-bold text-primary-900">
            {isFirstCriteria ? "What are you looking for?" : 'Your search criteria'}
          </h1>
          <p className="text-sm text-primary-600 mt-1">
            {isFirstCriteria
              ? "Set up your first search — you can add more, or come back and adjust this any time."
              : 'Add another search, or manage your existing ones below.'}
          </p>
        </div>

        {existing !== null && existing.length > 0 && (
          <div className="space-y-3 mb-6">
            {existing.map((c) => (
              <div key={c.id} className="bg-white rounded-xl p-4 shadow-sm border border-primary-100">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-heading text-sm font-bold text-primary-900">{c.label || 'Untitled search'}</p>
                    <p className="text-xs text-primary-500 mt-1">
                      {[
                        c.keywords.length > 0 && c.keywords.join(', '),
                        c.excluded_keywords?.length > 0 && `not ${c.excluded_keywords.join(', ')}`,
                        c.industries?.length > 0 && c.industries.join(', '),
                        c.locations.length > 0 && c.locations.join(', '),
                        c.salary_min && `£${c.salary_min.toLocaleString()}+`,
                      ].filter(Boolean).join(' · ') || 'No filters set'}
                    </p>
                  </div>
                  <button
                    onClick={() => handleDelete(c.id)}
                    className="text-xs text-primary-400 hover:text-red-500 shrink-0 ml-3"
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate className="bg-white rounded-2xl shadow-sm p-6 space-y-5">
          <div>
            <label className="block text-sm font-medium text-primary-700 mb-1.5">
              Name this search
            </label>
            <input
              type="text"
              required
              value={form.label}
              onChange={(e) => {
                updateField('label', e.target.value)
                if (labelTouched) setLabelTouched(false)
              }}
              onBlur={() => setLabelTouched(true)}
              placeholder="e.g. Software grad roles"
              aria-invalid={labelTouched && labelMissing}
              className={`w-full px-3.5 py-2.5 rounded-lg border text-primary-900 placeholder:text-primary-400 focus:outline-none focus:ring-2 focus:border-transparent ${
                labelTouched && labelMissing
                  ? 'border-red-300 focus:ring-red-400'
                  : 'border-primary-200 focus:ring-secondary-400'
              }`}
            />
            {labelTouched && labelMissing ? (
              <p className="text-xs text-red-600 mt-1.5">Give this search a name so you can tell it apart from your others.</p>
            ) : (
              <p className="text-xs text-primary-400 mt-1.5">Helps you tell this apart from your other saved searches.</p>
            )}
          </div>

          <TagInput
            label="Keywords"
            placeholder="e.g. software, data, analyst"
            values={form.keywords}
            onChange={(v) => updateField('keywords', v)}
          />

          <TagInput
            label="Exclude keywords"
            placeholder="e.g. senior, manager (optional)"
            values={form.excluded_keywords}
            onChange={(v) => updateField('excluded_keywords', v)}
          />

          <MultiSelectDropdown
            label="Industry"
            placeholder="Any industry"
            options={industryOptions}
            values={form.industries}
            onChange={(v) => updateField('industries', v)}
          />

          <MultiSelectDropdown
            label="Locations"
            placeholder="Any location"
            options={locationOptions}
            values={form.locations}
            onChange={(v) => updateField('locations', v)}
          />

          <div>
            <label htmlFor="salary_min" className="block text-sm font-medium text-primary-700 mb-1.5">
              Minimum salary <span className="text-primary-400 font-normal">(optional)</span>
            </label>
            <select
              id="salary_min"
              value={form.salary_min}
              onChange={(e) => updateField('salary_min', e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-lg border border-primary-200 text-primary-900 bg-white focus:outline-none focus:ring-2 focus:ring-secondary-400 focus:border-transparent"
            >
              <option value="">No minimum</option>
              {SALARY_OPTIONS.map((amount) => (
                <option key={amount} value={amount}>
                  £{amount.toLocaleString()}+
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-primary-700 mb-2">
              Contract type <span className="text-primary-400 font-normal">(optional — leave blank for any)</span>
            </label>
            <div className="flex flex-wrap gap-2">
              {CONTRACT_TYPE_OPTIONS.map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => toggleContractType(type)}
                  aria-pressed={form.contract_types.includes(type)}
                  className={`text-sm px-3 py-1.5 rounded-full border transition-colors ${
                    form.contract_types.includes(type)
                      ? 'bg-accent-300 border-accent-300 text-primary-900 font-medium'
                      : 'bg-white border-primary-200 text-primary-600'
                  }`}
                >
                  {type}
                </button>
              ))}
            </div>
          </div>

          {error && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2.5 rounded-lg bg-accent-300 text-primary-900 text-sm font-semibold hover:bg-accent-400 transition-colors disabled:opacity-50"
          >
            {submitting ? 'Saving…' : 'Save search'}
          </button>
        </form>
      </div>
    </div>
  )
}
