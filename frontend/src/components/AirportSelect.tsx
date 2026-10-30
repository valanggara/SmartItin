import { useEffect, useId, useMemo, useRef, useState, type ReactNode } from 'react'

export interface Airport {
  iata: string
  name: string
  city: string
  country: string
  keywords: string
  large: boolean
}

// ~3k airports (see scripts/build_airports.py) — fetched once on first use
// and shared by every AirportSelect, rather than bundled into the JS.
let airportsPromise: Promise<Airport[]> | null = null
function loadAirports(): Promise<Airport[]> {
  airportsPromise ??= fetch('/airports.json').then((res) => {
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return res.json() as Promise<Airport[]>
  })
  return airportsPromise
}

const MAX_RESULTS = 50

function airportLabel(airport: Airport) {
  return `${airport.country.toUpperCase()} - ${airport.city.toUpperCase()}`
}

// Ranks exact IATA hits first, then city/country prefix matches, then any
// substring hit (airport name or alias keywords) — so "tokyo" surfaces
// Haneda/Narita before an airport that merely mentions Tokyo somewhere.
function search(airports: Airport[], query: string): Airport[] {
  const q = query.trim().toLowerCase()
  if (!q) return airports.filter((a) => a.large).slice(0, MAX_RESULTS)

  const scored: { airport: Airport; score: number }[] = []
  for (const airport of airports) {
    const city = airport.city.toLowerCase()
    const country = airport.country.toLowerCase()
    let score = -1
    if (airport.iata.toLowerCase() === q) score = 0
    else if (city.startsWith(q)) score = 1
    else if (country.startsWith(q)) score = 2
    else if (`${country} - ${city}`.includes(q) || `${city}, ${country}`.includes(q)) score = 3
    else if (airport.name.toLowerCase().includes(q) || airport.keywords.toLowerCase().includes(q)) score = 4
    if (score >= 0) scored.push({ airport, score: score * 2 + (airport.large ? 0 : 1) })
  }
  scored.sort((a, b) => a.score - b.score)
  return scored.slice(0, MAX_RESULTS).map((s) => s.airport)
}

interface AirportSelectProps {
  value: Airport | null
  onChange: (airport: Airport | null) => void
  ariaLabel: string
  placeholder?: string
  icon?: ReactNode
}

export function AirportSelect({ value, onChange, ariaLabel, placeholder, icon }: AirportSelectProps) {
  const listId = useId()
  const [airports, setAirports] = useState<Airport[]>([])
  const [loadError, setLoadError] = useState(false)
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const rootRef = useRef<HTMLDivElement>(null)
  const listRef = useRef<HTMLUListElement>(null)

  useEffect(() => {
    loadAirports()
      .then(setAirports)
      .catch(() => setLoadError(true))
  }, [])

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const results = useMemo(() => search(airports, query), [airports, query])

  useEffect(() => {
    listRef.current?.children[active]?.scrollIntoView({ block: 'nearest' })
  }, [active])

  function select(airport: Airport) {
    onChange(airport)
    setQuery('')
    setOpen(false)
  }

  function openList() {
    if (open) return
    setQuery('')
    setActive(0)
    setOpen(true)
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setOpen(true)
      setActive((i) => Math.min(i + 1, results.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((i) => Math.max(i - 1, 0))
    } else if (e.key === 'Enter' && open) {
      e.preventDefault()
      if (results[active]) select(results[active])
    } else if (e.key === 'Escape' || e.key === 'Tab') {
      setOpen(false)
    }
  }

  const displayValue = open ? query : value ? `${airportLabel(value)} (${value.iata})` : ''

  return (
    <div ref={rootRef} className="relative">
      {icon && (
        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-teal-700/50">{icon}</span>
      )}
      <input
        role="combobox"
        aria-label={ariaLabel}
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        value={displayValue}
        onChange={(e) => {
          setQuery(e.target.value)
          setActive(0)
          setOpen(true)
        }}
        onFocus={openList}
        onClick={openList}
        onKeyDown={handleKeyDown}
        placeholder={loadError ? 'Could not load airports' : placeholder}
        className={`w-full truncate rounded-lg border border-sand-200 bg-cream py-2 pr-8 text-teal-700 outline-none placeholder:text-teal-700/40 focus:border-teal-500 ${
          icon ? 'pl-9' : 'pl-3'
        }`}
      />
      <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-teal-700/50">
        ▾
      </span>
      {open && (
        <ul
          id={listId}
          ref={listRef}
          role="listbox"
          className="absolute z-20 mt-1 max-h-72 w-full overflow-y-auto rounded-lg border border-sand-200 bg-cream py-1 shadow-lg"
        >
          {results.length === 0 && (
            <li className="px-3 py-2 text-sm text-teal-700/60">
              {airports.length === 0 && !loadError ? 'Loading airports…' : 'No airports found'}
            </li>
          )}
          {results.map((airport, i) => (
            <li
              key={airport.iata}
              role="option"
              aria-selected={i === active}
              onMouseDown={(e) => {
                e.preventDefault()
                select(airport)
              }}
              onMouseEnter={() => setActive(i)}
              className={`cursor-pointer px-3 py-2 ${i === active ? 'bg-teal-500/10' : ''}`}
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className="truncate text-sm font-medium text-teal-700">{airportLabel(airport)}</span>
                <span className="shrink-0 font-mono text-xs text-teal-700/70">{airport.iata}</span>
              </div>
              <p className="truncate text-xs text-teal-700/60">{airport.name}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
