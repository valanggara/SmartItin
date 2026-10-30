// Mirrors common/schemas.py — kept in sync by hand since the backend's
// output_schema already guarantees the shape on the wire.

export interface SectionError {
  error: string
}

export type Loadable<T> = T | SectionError | null

export function isError<T>(value: Loadable<T>): value is SectionError {
  return value != null && typeof value === 'object' && 'error' in value
}

export interface FlightLeg {
  date: string
  departure_time: string
  arrival_time: string
  duration_hours: number
  flight_number: string
  airplane: string
  airline_logo: string
  stops: number
}

export interface FlightOption {
  airline: string
  flight_class: string
  price_total_idr: number
  outbound: FlightLeg
  return_leg: FlightLeg
  booking_link: string
  selected: boolean
}

export interface FlightResponse {
  flights: FlightOption[]
}

export interface Attraction {
  name: string
  description: string
  maps_link: string
  image_url: string
}

export interface TripExtension {
  name: string
  travel_time: string
  reason: string
  best_suited_for: string[]
  suggested_duration: string
}

export interface ResearchResponse {
  why_visit: string
  climate: string
  culture_notes: string[]
  safety_tips: string[]
  top_attractions: Attraction[]
  hidden_gems: Attraction[]
  trip_extensions: TripExtension[]
}

export interface StayOption {
  name: string
  location: string
  price_per_night_idr: number
  rating: number
  stars: number
  facilities: string[]
  maps_link: string
  image_url: string
  selected: boolean
}

export interface RestaurantOption {
  name: string
  cuisine: string
  price_range_min_idr: number
  price_range_max_idr: number
  location: string
  maps_link: string
  image_url: string
}

export interface StayFoodResponse {
  stays: StayOption[]
  restaurants: RestaurantOption[]
}

export interface DayPlan {
  day: number
  date: string
  morning: string
  afternoon: string
  evening: string
  estimated_cost_idr: number
  transportation_notes: string
}

export interface ItineraryResponse {
  itinerary: DayPlan[]
}

export interface ItineraryAlternative {
  option: string
  label: string
  description: string
}

export interface ItineraryModifyResponse {
  applied: boolean
  summary_of_changes: string
  modified_itinerary: DayPlan[]
  removed_activities: string[]
  added_activities: string[]
  reasoning: string
  alternatives: ItineraryAlternative[]
}

export interface BudgetAllocation {
  total_budget_idr: number
  target_flight_budget_idr: number
  target_hotel_budget_idr: number
  target_food_budget_idr: number
  target_activity_budget_idr: number
  over_budget: boolean
}

export interface CostSummary {
  budget_tier: string
  estimated_flight_cost_idr: number
  estimated_stay_cost_idr: number
  estimated_itinerary_cost_idr: number
  estimated_total_cost_idr: number
  budget_allocation: BudgetAllocation
}

export type BudgetTier = 'economy' | 'standard' | 'luxury'
export type FlightClass = 'economy' | 'premium_economy' | 'business' | 'first'
export type HotelStars = 2 | 3 | 4 | 5
export type TravelPace = 'relaxed' | 'packed'

export interface TripRequest {
  origin: string
  destination: string
  start_date: string
  end_date: string
  theme: string
  budget_tier: BudgetTier
  flight_class: FlightClass
  hotel_stars: HotelStars
  total_budget_idr: number
  travel_pace: TravelPace
}

export interface JobSections {
  flights: Loadable<FlightResponse>
  research: Loadable<ResearchResponse>
  accommodation: Loadable<StayFoodResponse>
  itinerary: Loadable<ItineraryResponse>
  cost_summary: Loadable<CostSummary>
}

export interface JobStatus {
  status: 'running' | 'done' | 'error'
  sections: JobSections
  error: string | null
  request: TripRequest
}
