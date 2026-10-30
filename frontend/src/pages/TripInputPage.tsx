import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { startTrip } from '../api'
import { BrandLogo } from '../components/BrandLogo'
import { BudgetTierCard } from '../components/BudgetTierCard'
import { DatePicker } from '../components/DatePicker'
import {
  CalendarIcon,
  CompassIcon,
  FlagIcon,
  GemIcon,
  MapPinIcon,
  PlaneIcon,
  StarOutlineIcon,
  UsersIcon,
  WalletIcon,
} from '../components/icons'
import { SelectField } from '../components/SelectField'
import { formatIDR } from '../format'
import { usePageTitle } from '../hooks/usePageTitle'
import { FLIGHT_CLASS_OPTIONS, HOTEL_STAR_OPTIONS, THEME_OPTIONS, TIER_DEFAULTS, TRAVEL_PACE_OPTIONS } from '../tiers'
import type { BudgetTier, FlightClass, HotelStars, TravelPace, TripRequest } from '../types'

export function TripInputPage() {
  usePageTitle('SmartItin - Home')
  const navigate = useNavigate()

  const [origin, setOrigin] = useState('')
  const [destination, setDestination] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [theme, setTheme] = useState(THEME_OPTIONS[0])
  const [travelPace, setTravelPace] = useState<TravelPace>('packed')
  const [totalBudget, setTotalBudget] = useState('')
  const [budgetTier, setBudgetTier] = useState<BudgetTier>('standard')
  const [flightClass, setFlightClass] = useState<FlightClass>(TIER_DEFAULTS.standard.flightClass)
  const [hotelStars, setHotelStars] = useState<HotelStars>(TIER_DEFAULTS.standard.hotelStars)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const totalBudgetIdr = Number(totalBudget)

  function handleTierSelect(tier: BudgetTier) {
    setBudgetTier(tier)
    setFlightClass(TIER_DEFAULTS[tier].flightClass)
    setHotelStars(TIER_DEFAULTS[tier].hotelStars)
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!origin || !destination || !startDate || !endDate) {
      setError('Please fill in origin, destination, and both dates.')
      return
    }
    if (endDate < startDate) {
      setError('End date must be after the start date.')
      return
    }
    if (!totalBudget || totalBudgetIdr <= 0) {
      setError('Please enter your total trip budget.')
      return
    }

    const payload: TripRequest = {
      origin,
      destination,
      start_date: startDate,
      end_date: endDate,
      theme,
      budget_tier: budgetTier,
      flight_class: flightClass,
      hotel_stars: hotelStars,
      total_budget_idr: totalBudgetIdr,
      travel_pace: travelPace,
    }

    setSubmitting(true)
    setError(null)
    try {
      const jobId = await startTrip(payload)
      sessionStorage.setItem('lastTripRequest', JSON.stringify(payload))
      navigate(`/results?job=${jobId}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      setSubmitting(false)
    }
  }

  return (
    <main className="mx-auto min-h-screen max-w-3xl px-4 py-12 sm:py-16">
      <header className="mb-10 text-center">
        <BrandLogo />
      </header>

      <form onSubmit={handleSubmit} className="space-y-8">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-teal-700">Origin</span>
            <div className="relative">
              <MapPinIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-teal-700/50" />
              <input
                value={origin}
                onChange={(e) => setOrigin(e.target.value)}
                placeholder="e.g. Jakarta"
                className="w-full rounded-lg border border-sand-200 bg-cream py-2 pl-9 pr-3 text-teal-700 outline-none placeholder:text-teal-700/40 focus:border-teal-500"
              />
            </div>
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-teal-700">Destination</span>
            <div className="relative">
              <FlagIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-teal-700/50" />
              <input
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                placeholder="e.g. Bali"
                className="w-full rounded-lg border border-sand-200 bg-cream py-2 pl-9 pr-3 text-teal-700 outline-none placeholder:text-teal-700/40 focus:border-teal-500"
              />
            </div>
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-teal-700">Departure date</span>
            <DatePicker
              value={startDate}
              onChange={setStartDate}
              placeholder="Select date"
              icon={<CalendarIcon className="h-4 w-4" />}
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-teal-700">Return date</span>
            <DatePicker
              value={endDate}
              onChange={setEndDate}
              placeholder="Select date"
              min={startDate || undefined}
              icon={<CalendarIcon className="h-4 w-4" />}
            />
          </label>
        </div>

        <label className="block">
          <span className="mb-1 block text-sm font-medium text-teal-700">Travel theme</span>
          <SelectField
            value={theme}
            onChange={(e) => setTheme(e.target.value)}
            icon={<UsersIcon className="h-4 w-4" />}
          >
            {THEME_OPTIONS.map((t) => (
              <option key={t} value={t}>
                {t.replace(/\b\w/g, (c) => c.toUpperCase())}
              </option>
            ))}
          </SelectField>
        </label>

        <label className="block">
          <span className="mb-1 block text-sm font-medium text-teal-700">Travel pace</span>
          <SelectField
            value={travelPace}
            onChange={(e) => setTravelPace(e.target.value as TravelPace)}
            icon={<CompassIcon className="h-4 w-4" />}
          >
            {TRAVEL_PACE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </SelectField>
        </label>

        <label className="block">
          <span className="mb-1 block text-sm font-medium text-teal-700">Total budget (IDR)</span>
          <div className="relative">
            <WalletIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-teal-700/50" />
            <input
              type="number"
              min={0}
              step={100000}
              value={totalBudget}
              onChange={(e) => setTotalBudget(e.target.value)}
              placeholder="e.g. 5000000"
              className="w-full rounded-lg border border-sand-200 bg-cream py-2 pl-9 pr-3 text-teal-700 outline-none placeholder:text-teal-700/40 focus:border-teal-500"
            />
          </div>
          {totalBudgetIdr > 0 && (
            <p className="mt-1 text-xs text-teal-700/60">≈ {formatIDR(totalBudgetIdr)}</p>
          )}
        </label>

        <div>
          <span className="mb-2 flex items-center gap-1.5 text-sm font-medium text-teal-700">
            <GemIcon className="h-4 w-4 text-teal-700/60" />
            Travel style
          </span>
          <div className="flex flex-col gap-3 sm:flex-row">
            {(Object.keys(TIER_DEFAULTS) as BudgetTier[]).map((tier) => (
              <BudgetTierCard
                key={tier}
                tier={tier}
                defaults={TIER_DEFAULTS[tier]}
                selected={budgetTier === tier}
                onSelect={() => handleTierSelect(tier)}
              />
            ))}
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-teal-700">Flight class</span>
            <SelectField
              value={flightClass}
              onChange={(e) => setFlightClass(e.target.value as FlightClass)}
              icon={<PlaneIcon className="h-4 w-4" />}
            >
              {FLIGHT_CLASS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </SelectField>
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-teal-700">Hotel stars</span>
            <SelectField
              value={hotelStars}
              onChange={(e) => setHotelStars(Number(e.target.value) as HotelStars)}
              icon={<StarOutlineIcon className="h-4 w-4" />}
            >
              {HOTEL_STAR_OPTIONS.map((stars) => (
                <option key={stars} value={stars}>
                  {'★'.repeat(stars)}
                </option>
              ))}
            </SelectField>
          </label>
        </div>

        {error && <p className="text-sm text-coral-600">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-xl bg-teal-500 px-6 py-3 font-display text-lg text-cream transition hover:bg-teal-600 disabled:opacity-60"
        >
          {submitting ? 'Starting your plan…' : 'Plan my trip'}
        </button>
      </form>
    </main>
  )
}
