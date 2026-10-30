import type { CostSummary } from '../types'
import { formatIDR } from '../format'

export function CostSummaryContent({ data }: { data: CostSummary }) {
  const rows: { label: string; value: number }[] = [
    { label: 'Flights', value: data.estimated_flight_cost_idr },
    { label: 'Stay', value: data.estimated_stay_cost_idr },
    { label: 'Itinerary (activities & meals)', value: data.estimated_itinerary_cost_idr },
  ]
  const max = Math.max(...rows.map((r) => r.value), 1)

  return (
    <div className="space-y-4">
      {data.budget_allocation.over_budget && (
        <p className="rounded-lg bg-coral-500/10 px-3 py-2 text-xs font-medium text-coral-600">
          This trip's estimated total is above your budget — consider a lower budget tier or fewer nights.
        </p>
      )}
      <div className="space-y-3">
        {rows.map((row) => (
          <div key={row.label}>
            <div className="mb-1 flex justify-between text-sm">
              <span className="text-teal-700/80">{row.label}</span>
              <span className="font-medium text-teal-700">{formatIDR(row.value)}</span>
            </div>
            <div className="h-2 w-full rounded-full bg-sand-200">
              <div
                className="h-2 rounded-full bg-teal-500"
                style={{ width: `${Math.max((row.value / max) * 100, 2)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
      <div className="flex items-baseline justify-between border-t border-sand-200 pt-3">
        <span className="font-display text-lg text-teal-700">Estimated total</span>
        <span className="font-display text-2xl text-coral-600">{formatIDR(data.estimated_total_cost_idr)}</span>
      </div>
    </div>
  )
}
