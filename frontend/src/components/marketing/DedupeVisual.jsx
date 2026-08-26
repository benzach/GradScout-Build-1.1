import { GitMerge, Star } from 'lucide-react'

/**
 * The hero's signature visual: the same graduate role, worded slightly
 * differently by three of the real sources GradScout actually scans
 * (Adzuna, Reed, Jooble — see backend/migrations/0002_seed_sources.sql),
 * collapsing into the one clean, deduplicated card a GradScout user
 * actually sees. Styled to match the real in-app job card
 * (src/pages/JobFeed.jsx's JobCard) so this isn't an invented mockup —
 * it's what the product's own UI looks like.
 */
export default function DedupeVisual() {
  return (
    <div className="w-full max-w-sm mx-auto select-none" aria-hidden="true">
      {/* The noisy, duplicated sightings */}
      <div className="relative h-[132px] mb-2">
        <NoiseChip
          source="Jooble"
          title="Software Engineer - Graduate 2026"
          meta="Manchester · £28k"
          style={{ transform: 'translate(6%, 26px) rotate(-3deg)', zIndex: 5, opacity: 0.75 }}
        />
        <NoiseChip
          source="Adzuna"
          title="Graduate Software Engineer"
          meta="Manchester · £28,000"
          style={{ transform: 'translate(-8%, 8px) rotate(-6deg)', zIndex: 10, opacity: 0.9 }}
        />
        <NoiseChip
          source="Reed"
          title="Software Engineer (Graduate Scheme)"
          meta="Manchester, UK · £28k–£32k"
          style={{ transform: 'translate(3%, 0px) rotate(4deg)', zIndex: 20, opacity: 1 }}
        />
      </div>

      {/* The merge indicator */}
      <div className="flex items-center justify-center gap-2 my-3">
        <span className="h-px w-10 bg-primary-200" />
        <span className="flex items-center justify-center w-8 h-8 rounded-full bg-white border border-primary-200 shadow-sm text-secondary-700">
          <GitMerge size={15} />
        </span>
        <span className="h-px w-10 bg-primary-200" />
      </div>

      {/* The one clean result */}
      <div className="bg-white rounded-2xl shadow-md p-4 border border-primary-100">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <p className="font-heading text-sm font-bold text-primary-900 truncate">
              Graduate Software Engineer
            </p>
            <p className="text-xs text-primary-500 mt-0.5">Northbridge Analytics</p>
          </div>
          <Star size={18} className="text-accent-300 shrink-0" fill="currentColor" />
        </div>
        <p className="text-xs text-primary-400 mt-2">Manchester · £28,000–£32,000 · Graduate scheme · 2 days ago</p>
        <span className="inline-block mt-2 text-[11px] text-primary-600 bg-primary-50 px-2 py-0.5 rounded-md">
          Technology
        </span>
        <p className="text-[11px] text-primary-400 mt-2">Also found on 2 other sites</p>
      </div>
    </div>
  )
}

function NoiseChip({ source, title, meta, style }) {
  return (
    <div
      className="absolute inset-x-6 top-0 bg-white rounded-xl shadow-sm border border-primary-100 px-3 py-2.5"
      style={style}
    >
      <p className="text-[10px] uppercase tracking-wide font-semibold text-primary-400">via {source}</p>
      <p className="text-xs font-semibold text-primary-700 truncate mt-0.5">{title}</p>
      <p className="text-[10px] text-primary-400 mt-0.5">{meta}</p>
    </div>
  )
}
