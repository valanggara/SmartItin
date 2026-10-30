import { useEffect, useState } from 'react'
import { modifyItinerary } from '../api'
import type { DayPlan, ItineraryAlternative, ItineraryModifyResponse, ItineraryResponse, TripExtension } from '../types'
import { formatIDR, formatShortDate } from '../format'
import { CompassIcon } from './icons'

const SLOTS: { label: string; key: keyof Pick<DayPlan, 'morning' | 'afternoon' | 'evening'> }[] = [
  { label: 'Morning', key: 'morning' },
  { label: 'Afternoon', key: 'afternoon' },
  { label: 'Evening', key: 'evening' },
]

function DayCard({ day }: { day: DayPlan }) {
  return (
    <div className="flex overflow-hidden rounded-xl border border-sand-200 bg-sand-50">
      <div className="flex w-10 shrink-0 items-center justify-center bg-coral-500">
        <span className="[writing-mode:vertical-rl] rotate-180 whitespace-nowrap text-xs font-bold uppercase tracking-wide text-cream">
          Day {day.day}
        </span>
      </div>
      <div className="flex-1 p-4">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-sm font-medium text-teal-700">{formatShortDate(day.date)}</span>
          <span className="text-sm font-semibold text-coral-600">{formatIDR(day.estimated_cost_idr)}</span>
        </div>
        <div className="divide-y divide-dashed divide-sand-200">
          {SLOTS.map(({ label, key }) => (
            <div key={key} className="flex gap-4 py-2 text-sm">
              <span className="w-20 shrink-0 font-medium text-teal-600">{label}</span>
              <span className="text-teal-700/90">{day[key]}</span>
            </div>
          ))}
        </div>
        <p className="mt-2 text-xs italic text-teal-700/60">{day.transportation_notes}</p>
      </div>
    </div>
  )
}

function ModifyResultPanel({
  result,
  pending,
  onChooseAlternative,
  onKeepCurrent,
}: {
  result: ItineraryModifyResponse
  pending: boolean
  onChooseAlternative: (alt: ItineraryAlternative) => void
  onKeepCurrent: () => void
}) {
  if (!result.applied) {
    return (
      <div className="rounded-xl border border-coral-400/40 bg-coral-400/10 p-4 text-sm">
        <p className="font-medium text-teal-700">Couldn't fit this into the current trip as-is.</p>
        <p className="mt-1 text-teal-700/80">{result.reasoning}</p>
        <div className="mt-3 space-y-2">
          {result.alternatives.map((alt) => (
            <div key={alt.option} className="rounded-lg bg-cream p-2.5">
              <p className="font-medium text-teal-700">Option {alt.option}:</p>
              <p className="mt-0.5 text-teal-700/70">
                <span className="font-medium text-teal-700/90">{alt.label}.</span> {alt.description}
              </p>
              {alt.option === 'C' ? (
                <button
                  type="button"
                  onClick={onKeepCurrent}
                  disabled={pending}
                  className="mt-2 rounded-lg border border-teal-500 px-3 py-1 text-xs font-medium text-teal-600 transition hover:bg-teal-500 hover:text-cream disabled:opacity-50"
                >
                  Keep current itinerary
                </button>
              ) : alt.option === 'A' ? (
                <button
                  type="button"
                  onClick={() => onChooseAlternative(alt)}
                  disabled={pending}
                  className="mt-2 rounded-lg bg-teal-500 px-3 py-1 text-xs font-medium text-cream transition hover:bg-teal-600 disabled:opacity-50"
                >
                  {pending ? 'Applying…' : 'Choose this option'}
                </button>
              ) : (
                <p className="mt-2 text-xs italic text-teal-700/50">
                  Extending the trip requires a new flight search — not available to apply automatically yet.
                </p>
              )}
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-teal-500/30 bg-teal-500/5 p-4 text-sm">
      <p className="font-medium text-teal-700">{result.summary_of_changes}</p>
      {result.added_activities.length > 0 && (
        <p className="mt-1 text-teal-700/80">
          <span className="font-medium">Added: </span>
          {result.added_activities.join(', ')}
        </p>
      )}
      {result.removed_activities.length > 0 && (
        <p className="mt-1 text-teal-700/80">
          <span className="font-medium">Removed: </span>
          {result.removed_activities.join(', ')}
        </p>
      )}
      <p className="mt-1 text-teal-700/60 italic">{result.reasoning}</p>
    </div>
  )
}

interface ItineraryContentProps {
  data: ItineraryResponse
  extensions: TripExtension[]
  jobId: string | null
  // ResultsPage doesn't otherwise know about edits made here (add_extension/
  // apply_alternative update this component's own local state) — reported
  // upward so anything built outside this component (e.g. the PDF export)
  // reflects the current itinerary, not the original one from the job's
  // first poll. Fires once on mount with the original data too, so "no
  // edits made" still keeps the parent correctly in sync.
  onItineraryChange?: (itinerary: DayPlan[]) => void
}

export function ItineraryContent({ data, extensions, jobId, onItineraryChange }: ItineraryContentProps) {
  const [itinerary, setItinerary] = useState(data.itinerary)

  useEffect(() => {
    onItineraryChange?.(itinerary)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [itinerary])

  const [pending, setPending] = useState<string | null>(null)
  const [results, setResults] = useState<Record<string, ItineraryModifyResponse>>({})
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [applied, setApplied] = useState<Set<string>>(new Set())

  async function handleAdd(extension: TripExtension) {
    if (!jobId) return
    setPending(extension.name)
    setErrors((prev) => ({ ...prev, [extension.name]: '' }))
    try {
      const result = await modifyItinerary(jobId, 'add_extension', { extension })
      setResults((prev) => ({ ...prev, [extension.name]: result }))
      if (result.applied) {
        setItinerary(result.modified_itinerary)
        setApplied((prev) => new Set(prev).add(extension.name))
      }
    } catch (err) {
      setErrors((prev) => ({
        ...prev,
        [extension.name]: err instanceof Error ? err.message : String(err),
      }))
    } finally {
      setPending(null)
    }
  }

  async function handleChooseAlternative(extension: TripExtension, alt: ItineraryAlternative) {
    if (!jobId) return
    setPending(extension.name)
    setErrors((prev) => ({ ...prev, [extension.name]: '' }))
    try {
      const result = await modifyItinerary(jobId, 'apply_alternative', { extension, chosen_alternative: alt })
      setResults((prev) => ({ ...prev, [extension.name]: result }))
      if (result.applied) {
        setItinerary(result.modified_itinerary)
        setApplied((prev) => new Set(prev).add(extension.name))
      }
    } catch (err) {
      setErrors((prev) => ({
        ...prev,
        [extension.name]: err instanceof Error ? err.message : String(err),
      }))
    } finally {
      setPending(null)
    }
  }

  function handleKeepCurrent(extensionName: string) {
    setResults((prev) => {
      const next = { ...prev }
      delete next[extensionName]
      return next
    })
  }

  return (
    <div className="space-y-5">
      {itinerary.map((day) => (
        <DayCard key={day.day} day={day} />
      ))}

      {extensions.length > 0 && (
        <div className="border-t border-sand-200 pt-5">
          <h3 className="mb-3 flex items-center gap-1.5 text-sm font-semibold uppercase tracking-wide text-teal-600">
            <CompassIcon className="h-4 w-4" />
            Optional trip extensions
          </h3>
          <div className="space-y-3">
            {extensions.map((ext) => (
              <div key={ext.name} className="rounded-xl border border-sand-200 bg-sand-50 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-teal-700">{ext.name}</p>
                    <p className="text-xs text-teal-700/60">
                      {ext.travel_time} away · {ext.suggested_duration}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleAdd(ext)}
                    disabled={pending === ext.name || applied.has(ext.name) || !jobId}
                    className="shrink-0 whitespace-nowrap rounded-lg bg-teal-500 px-3 py-1.5 text-xs font-medium text-cream transition hover:bg-teal-600 disabled:opacity-50"
                  >
                    {applied.has(ext.name) ? 'Added ✓' : pending === ext.name ? 'Adding…' : 'Add to Itinerary'}
                  </button>
                </div>
                <p className="mt-2 text-sm text-teal-700/80">{ext.reason}</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {ext.best_suited_for.map((tag) => (
                    <span key={tag} className="rounded-full bg-teal-500/10 px-2 py-0.5 text-xs text-teal-600">
                      {tag}
                    </span>
                  ))}
                </div>
                {errors[ext.name] && <p className="mt-2 text-xs text-coral-600">{errors[ext.name]}</p>}
                {results[ext.name] && (
                  <div className="mt-3">
                    <ModifyResultPanel
                      result={results[ext.name]}
                      pending={pending === ext.name}
                      onChooseAlternative={(alt) => handleChooseAlternative(ext, alt)}
                      onKeepCurrent={() => handleKeepCurrent(ext.name)}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
