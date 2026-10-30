// Mirrors common/tiers.py TIER_DEFAULTS — used to pre-fill (not lock) the
// Flight Class / Hotel Stars dropdowns when a budget tier card is selected.

import type { BudgetTier, FlightClass, HotelStars, TravelPace } from './types'

export interface TierDefaults {
  label: string
  tagline: string
  bullets: string[]
  flightClass: FlightClass
  hotelStars: HotelStars
  diningStyle: string
  activityStyle: string
}

export const TIER_DEFAULTS: Record<BudgetTier, TierDefaults> = {
  economy: {
    label: 'Economy',
    tagline: 'Budget friendly',
    bullets: ['Economy flights', '2–3★ guesthouses', 'Street food', 'Free/low-cost attractions'],
    flightClass: 'economy',
    hotelStars: 3,
    diningStyle: 'street food and casual local eateries',
    activityStyle: 'free or low-cost attractions',
  },
  standard: {
    label: 'Standard',
    tagline: 'Comfortable mid-range',
    bullets: ['Premium economy flights', '3–4★ hotels', 'Mid-range dining', 'Guided tours'],
    flightClass: 'premium_economy',
    hotelStars: 4,
    diningStyle: 'mid-range restaurants',
    activityStyle: 'paid attractions and guided tours',
  },
  luxury: {
    label: 'Luxury',
    tagline: 'Splurge worthy',
    bullets: ['Business class flights', '4–5★ resorts', 'Fine dining', 'Premium private experiences'],
    flightClass: 'business',
    hotelStars: 5,
    diningStyle: 'fine dining',
    activityStyle: 'premium and private experiences',
  },
}

export const FLIGHT_CLASS_OPTIONS: { value: FlightClass; label: string }[] = [
  { value: 'economy', label: 'Economy' },
  { value: 'premium_economy', label: 'Premium Economy' },
  { value: 'business', label: 'Business' },
  { value: 'first', label: 'First' },
]

export const HOTEL_STAR_OPTIONS: HotelStars[] = [2, 3, 4, 5]

export const TRAVEL_PACE_OPTIONS: { value: TravelPace; label: string }[] = [
  { value: 'relaxed', label: 'Relaxed' },
  { value: 'packed', label: 'Packed' },
]

export const THEME_OPTIONS = [
  'family holiday',
  'solo traveler',
  'couple getaway',
  'leisure',
  'culinary',
  'nature',
  'sports',
  'business',
  'conference',
  'concert',
]
