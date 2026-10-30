import type { FlightLeg, FlightResponse } from '../types'
import { formatDuration, formatIDR, formatShortDate } from '../format'

function LegTimeline({ label, leg }: { label: string; leg: FlightLeg }) {
  const stopsLabel = leg.stops === 0 ? 'Non-stop' : `${leg.stops} stop${leg.stops > 1 ? 's' : ''}`

  return (
    <div>
      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-teal-600">
        {label} · {formatShortDate(leg.date)}
      </p>
      <div className="flex items-center gap-3">
        {(leg.flight_number || leg.airplane) && (
          <div className="mr-2 text-center">
            {leg.flight_number && (
              <p className="rounded bg-sand-100 px-1 font-mono text-[10px] text-teal-600">{leg.flight_number}</p>
            )}
            {leg.airplane && <p className="text-[9px] text-teal-700/50">{leg.airplane}</p>}
          </div>
        )}

        <div className="text-center">
          <p className="font-semibold text-teal-700">{leg.departure_time}</p>
          <p className="text-[10px] uppercase tracking-wide text-teal-700/50">Departure</p>
        </div>

        <div className="flex-1">
          <div className="relative my-1.5 h-px bg-sand-200">
            <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded border border-sand-200 bg-cream px-1.5 text-[9px] text-teal-700/60">
              {leg.stops}
            </span>
          </div>
          <p className="text-center text-[10px] tracking-wide text-teal-700/50">
            {formatDuration(leg.duration_hours)} · {stopsLabel}
          </p>
        </div>

        <div className="text-center">
          <p className="font-semibold text-teal-700">{leg.arrival_time}</p>
          <p className="text-[10px] uppercase tracking-wide text-teal-700/50">Arrival</p>
        </div>
      </div>
    </div>
  )
}

export function FlightsContent({ data }: { data: FlightResponse }) {
  if (data.flights.length === 0) {
    return <p className="text-sm text-teal-600/70">No flight options were found for this route and dates.</p>
  }

  return (
    <div className="space-y-4">
      {data.flights.map((flight, i) => (
        <a
          key={i}
          href={flight.booking_link}
          target="_blank"
          rel="noreferrer"
          className="relative flex flex-col gap-4 rounded-2xl border border-sand-200 bg-sand-50 p-5 transition hover:border-teal-500 hover:shadow-md sm:flex-row sm:items-center"
        >
          {flight.selected && (
            <span className="absolute -top-3 left-4 rounded-full bg-teal-600 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-cream">
              Recommended
            </span>
          )}

          <div className="flex shrink-0 items-center gap-3 sm:w-40">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg border border-sand-200 bg-cream text-2xl">
              {flight.outbound.airline_logo ? (
                <img src={flight.outbound.airline_logo} alt="" className="h-6 w-6" />
              ) : (
                '✈️'
              )}
            </div>
            <div>
              <p className="font-semibold text-teal-700">{flight.airline}</p>
              <p className="text-xs italic text-teal-700/60">{flight.flight_class}</p>
            </div>
          </div>

          <div className="flex-1 space-y-3 border-sand-200 sm:border-l sm:border-r sm:px-5">
            <LegTimeline label="Outbound" leg={flight.outbound} />
            <LegTimeline label="Return" leg={flight.return_leg} />
          </div>

          <div className="flex shrink-0 items-center justify-between gap-4 sm:w-36 sm:flex-col sm:items-end sm:gap-2">
            <div className="sm:text-right">
              <p className="font-display text-xl text-coral-600">{formatIDR(flight.price_total_idr)}</p>
              <p className="text-xs text-teal-700/60">total, round trip</p>
            </div>
            <span className="rounded-lg bg-teal-500 px-4 py-2 text-sm font-medium text-cream transition group-hover:bg-teal-600">
              View deal →
            </span>
          </div>
        </a>
      ))}
    </div>
  )
}
