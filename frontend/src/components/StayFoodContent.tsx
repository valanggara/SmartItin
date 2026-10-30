import type { StayFoodResponse } from '../types'
import { formatIDR } from '../format'
import { FallbackImage, MapsLink } from './FallbackImage'

export function StayFoodContent({ data }: { data: StayFoodResponse }) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-teal-600">Where to stay</h3>
        <div className="grid gap-4 sm:grid-cols-2">
          {data.stays.map((stay, i) => (
            <div key={i} className="relative overflow-hidden rounded-xl border border-sand-200 bg-sand-50">
              {stay.selected && (
                <span className="absolute left-3 top-3 z-10 rounded-full bg-teal-600 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-cream">
                  Recommended
                </span>
              )}
              <FallbackImage src={stay.image_url} alt={stay.name} className="h-32 w-full object-cover" />
              <div className="p-4">
                <div className="flex items-start justify-between gap-2">
                  <p className="font-semibold text-teal-700">{stay.name}</p>
                  <span className="whitespace-nowrap text-xs text-coral-500">{'★'.repeat(stay.stars)}</span>
                </div>
                <p className="text-sm text-teal-700/70">{stay.location}</p>
                <p className="mt-2 font-display text-lg text-coral-600">
                  {formatIDR(stay.price_per_night_idr)}
                  <span className="text-sm font-normal text-teal-700/60"> / night</span>
                </p>
                <p className="text-xs text-teal-700/70">Rating {stay.rating.toFixed(1)}</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {stay.facilities.map((f, j) => (
                    <span key={j} className="rounded-full bg-teal-500/10 px-2 py-0.5 text-xs text-teal-600">
                      {f}
                    </span>
                  ))}
                </div>
                <MapsLink href={stay.maps_link} className="mt-2 inline-block" />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-teal-600">Where to eat</h3>
        <div className="grid gap-3 sm:grid-cols-2">
          {data.restaurants.map((r, i) => (
            <div key={i} className="flex gap-3 rounded-lg bg-sand-50 p-3">
              <FallbackImage src={r.image_url} alt={r.name} className="h-16 w-16 shrink-0 rounded-md object-cover" />
              <div className="min-w-0">
                <div className="flex items-baseline justify-between gap-2">
                  <p className="font-medium text-teal-700">{r.name}</p>
                  <span className="shrink-0 text-xs text-teal-700/60">
                    {formatIDR(r.price_range_min_idr)} - {formatIDR(r.price_range_max_idr)}
                  </span>
                </div>
                <p className="text-sm text-teal-700/70">
                  {r.cuisine} · {r.location}
                </p>
                <MapsLink href={r.maps_link} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
