import { Document, Link, Page, StyleSheet, Text, View } from '@react-pdf/renderer'
import { formatDuration, formatIDR, formatShortDate } from '../format'
import type {
  CostSummary,
  DayPlan,
  FlightResponse,
  ResearchResponse,
  StayFoodResponse,
  TripRequest,
} from '../types'

const COLORS = {
  teal: '#0f5c5c',
  tealSoft: '#4a8a8a',
  coral: '#d9583f',
  sand: '#e8ddc9',
  sandLight: '#f6f1e6',
  cream: '#fdfaf3',
  text: '#2b3a3a',
}

const styles = StyleSheet.create({
  page: {
    paddingTop: 36,
    paddingBottom: 44,
    paddingHorizontal: 40,
    fontSize: 10,
    color: COLORS.text,
    fontFamily: 'Helvetica',
  },
  coverTitle: {
    fontSize: 26,
    color: COLORS.teal,
    marginBottom: 6,
  },
  coverMeta: {
    fontSize: 11,
    color: COLORS.tealSoft,
    marginBottom: 2,
  },
  sectionTitle: {
    fontSize: 15,
    color: COLORS.teal,
    marginBottom: 10,
    marginTop: 18,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.sand,
    paddingBottom: 6,
  },
  subTitle: {
    fontSize: 11,
    color: COLORS.tealSoft,
    marginBottom: 4,
    marginTop: 10,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  card: {
    backgroundColor: COLORS.sandLight,
    borderRadius: 6,
    padding: 10,
    marginBottom: 8,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  badge: {
    fontSize: 8,
    color: COLORS.cream,
    backgroundColor: COLORS.teal,
    borderRadius: 3,
    paddingVertical: 2,
    paddingHorizontal: 6,
    marginBottom: 4,
    alignSelf: 'flex-start',
    textTransform: 'uppercase',
  },
  bold: { fontFamily: 'Helvetica-Bold' },
  muted: { color: COLORS.tealSoft, fontSize: 9 },
  price: { color: COLORS.coral, fontSize: 12, fontFamily: 'Helvetica-Bold' },
  link: { color: COLORS.tealSoft, fontSize: 8, marginTop: 2 },
  bullet: { flexDirection: 'row', marginBottom: 2 },
  bulletDot: { width: 8, fontSize: 9 },
  bulletText: { flex: 1, fontSize: 9, lineHeight: 1.4 },
  // Standalone body copy — NOT `bulletText`, whose `flex: 1` only resolves
  // to a real height inside `styles.bullet`'s row. Reused outside that
  // context, react-pdf's Yoga layout collapses it to zero height and the
  // next block renders directly on top of it.
  paragraph: { fontSize: 9, lineHeight: 1.4 },
  footer: {
    position: 'absolute',
    bottom: 20,
    left: 40,
    right: 40,
    fontSize: 8,
    color: COLORS.tealSoft,
    textAlign: 'center',
  },
  twoCol: { flexDirection: 'row', gap: 16 },
  col: { flex: 1 },
})

function MapsLinkText({ href }: { href: string }) {
  if (!href) return null
  return (
    <Link src={href} style={styles.link}>
      View on map
    </Link>
  )
}

function BookingLinkText({ href }: { href: string }) {
  if (!href) return null
  return (
    <Link src={href} style={styles.link}>
      View flight
    </Link>
  )
}

function BulletList({ items }: { items: string[] }) {
  return (
    <View>
      {items.map((item, i) => (
        <View key={i} style={styles.bullet}>
          <Text style={styles.bulletDot}>•</Text>
          <Text style={styles.bulletText}>{item}</Text>
        </View>
      ))}
    </View>
  )
}

function FlightsSection({ data }: { data: FlightResponse }) {
  return (
    <View>
      <Text style={styles.sectionTitle}>Flights</Text>
      {data.flights.map((flight, i) => (
        <View key={i} style={styles.card} wrap={false}>
          {flight.selected && <Text style={styles.badge}>Recommended</Text>}
          <View style={styles.row}>
            <Text style={styles.bold}>
              {flight.airline} · {flight.flight_class}
            </Text>
            <Text style={styles.price}>{formatIDR(flight.price_total_idr)}</Text>
          </View>
          <Text style={[styles.muted, { marginTop: 4 }]}>
            Outbound {formatShortDate(flight.outbound.date)}: {flight.outbound.departure_time} -{' '}
            {flight.outbound.arrival_time} ({formatDuration(flight.outbound.duration_hours)},{' '}
            {flight.outbound.stops === 0 ? 'non-stop' : `${flight.outbound.stops} stop(s)`}) ·{' '}
            {flight.outbound.flight_number}
          </Text>
          <Text style={styles.muted}>
            Return {formatShortDate(flight.return_leg.date)}: {flight.return_leg.departure_time} -{' '}
            {flight.return_leg.arrival_time} ({formatDuration(flight.return_leg.duration_hours)},{' '}
            {flight.return_leg.stops === 0 ? 'non-stop' : `${flight.return_leg.stops} stop(s)`}) ·{' '}
            {flight.return_leg.flight_number}
          </Text>
          <BookingLinkText href={flight.booking_link} />
        </View>
      ))}
    </View>
  )
}

function ResearchSection({ data }: { data: ResearchResponse }) {
  return (
    <View>
      <View>
        <Text style={styles.sectionTitle}>Destination Guide</Text>
        <Text style={styles.subTitle}>Why visit?</Text>
        <Text style={styles.paragraph}>{data.why_visit}</Text>
        <Text style={styles.subTitle}>Weather</Text>
        <Text style={styles.paragraph}>{data.climate}</Text>
        <View style={styles.twoCol}>
          <View style={styles.col}>
            <Text style={styles.subTitle}>Culture notes</Text>
            <BulletList items={data.culture_notes} />
          </View>
          <View style={styles.col}>
            <Text style={styles.subTitle}>Safety tips</Text>
            <BulletList items={data.safety_tips} />
          </View>
        </View>
      </View>

      <View>
        <Text style={styles.subTitle}>Top attractions</Text>
        {data.top_attractions.map((a, i) => (
          <View key={i} style={styles.card} wrap={false}>
            <Text style={styles.bold}>{a.name}</Text>
            <Text style={styles.paragraph}>{a.description}</Text>
            <MapsLinkText href={a.maps_link} />
          </View>
        ))}
        <Text style={styles.subTitle}>Hidden gems</Text>
        {data.hidden_gems.map((a, i) => (
          <View key={i} style={styles.card} wrap={false}>
            <Text style={styles.bold}>{a.name}</Text>
            <Text style={styles.paragraph}>{a.description}</Text>
            <MapsLinkText href={a.maps_link} />
          </View>
        ))}
      </View>
    </View>
  )
}

function StayFoodSection({ data }: { data: StayFoodResponse }) {
  return (
    <View>
      <Text style={styles.sectionTitle}>Stay & Food</Text>
      <Text style={styles.subTitle}>Where to stay</Text>
      {data.stays.map((stay, i) => (
        <View key={i} style={styles.card} wrap={false}>
          {stay.selected && <Text style={styles.badge}>Recommended</Text>}
          <View style={styles.row}>
            <Text style={styles.bold}>
              {stay.name} ({'*'.repeat(stay.stars)})
            </Text>
            <Text style={styles.price}>{formatIDR(stay.price_per_night_idr)} / night</Text>
          </View>
          <Text style={styles.muted}>
            {stay.location} · Rating {stay.rating.toFixed(1)}
          </Text>
          {stay.facilities.length > 0 && (
            <Text style={[styles.muted, { marginTop: 2 }]}>{stay.facilities.join(' · ')}</Text>
          )}
          <MapsLinkText href={stay.maps_link} />
        </View>
      ))}
      <Text style={styles.subTitle}>Where to eat</Text>
      {data.restaurants.map((r, i) => (
        <View key={i} style={styles.card} wrap={false}>
          <View style={styles.row}>
            <Text style={styles.bold}>{r.name}</Text>
            <Text style={styles.muted}>
              {formatIDR(r.price_range_min_idr)} - {formatIDR(r.price_range_max_idr)}
            </Text>
          </View>
          <Text style={styles.muted}>
            {r.cuisine} · {r.location}
          </Text>
          <MapsLinkText href={r.maps_link} />
        </View>
      ))}
    </View>
  )
}

function ItinerarySection({ itinerary }: { itinerary: DayPlan[] }) {
  return (
    <View>
      <Text style={styles.sectionTitle}>Day-by-Day Itinerary</Text>
      {itinerary.map((day) => (
        <View key={day.day} style={styles.card} wrap={false}>
          <View style={styles.row}>
            <Text style={styles.bold}>
              Day {day.day} · {formatShortDate(day.date)}
            </Text>
            <Text style={styles.price}>{formatIDR(day.estimated_cost_idr)}</Text>
          </View>
          <Text style={[styles.paragraph, { marginTop: 4 }]}>
            <Text style={styles.bold}>Morning: </Text>
            {day.morning}
          </Text>
          <Text style={styles.paragraph}>
            <Text style={styles.bold}>Afternoon: </Text>
            {day.afternoon}
          </Text>
          <Text style={styles.paragraph}>
            <Text style={styles.bold}>Evening: </Text>
            {day.evening}
          </Text>
          {day.transportation_notes && (
            <Text style={[styles.muted, { marginTop: 3, fontStyle: 'italic' }]}>
              {day.transportation_notes}
            </Text>
          )}
        </View>
      ))}
    </View>
  )
}

function CostSummarySection({ data }: { data: CostSummary }) {
  const rows = [
    { label: 'Flights', value: data.estimated_flight_cost_idr },
    { label: 'Stay', value: data.estimated_stay_cost_idr },
    { label: 'Itinerary (activities & meals)', value: data.estimated_itinerary_cost_idr },
  ]
  return (
    <View wrap={false}>
      <Text style={styles.sectionTitle}>Cost Summary</Text>
      {data.budget_allocation.over_budget && (
        <Text style={[styles.card, { color: COLORS.coral, fontSize: 9 }]}>
          This trip's estimated total is above the requested budget.
        </Text>
      )}
      {rows.map((row) => (
        <View key={row.label} style={[styles.row, { marginBottom: 6 }]}>
          <Text style={styles.muted}>{row.label}</Text>
          <Text style={styles.bold}>{formatIDR(row.value)}</Text>
        </View>
      ))}
      <View
        style={[
          styles.row,
          { borderTopWidth: 1, borderTopColor: COLORS.sand, paddingTop: 8, marginTop: 4 },
        ]}
      >
        <Text style={[styles.bold, { fontSize: 13, color: COLORS.teal }]}>Estimated total</Text>
        <Text style={[styles.price, { fontSize: 15 }]}>{formatIDR(data.estimated_total_cost_idr)}</Text>
      </View>
    </View>
  )
}

interface TripPlanPdfProps {
  request: TripRequest
  flights: FlightResponse | null
  research: ResearchResponse | null
  accommodation: StayFoodResponse | null
  itinerary: DayPlan[] | null
  costSummary: CostSummary | null
}

export function TripPlanPdf({ request, flights, research, accommodation, itinerary, costSummary }: TripPlanPdfProps) {
  return (
    <Document title={`SmartItin - ${request.origin} to ${request.destination}`}>
      <Page size="A4" style={styles.page}>
        <Text style={styles.coverTitle}>
          {request.origin} to {request.destination}
        </Text>
        <Text style={styles.coverMeta}>
          {formatShortDate(request.start_date)} – {formatShortDate(request.end_date)}
        </Text>
        <Text style={styles.coverMeta}>
          {request.theme.replace(/\b\w/g, (c) => c.toUpperCase())} · {request.budget_tier} tier ·{' '}
          {request.travel_pace} pace{request.halal_food ? ' · halal food' : ''}
        </Text>

        {flights && <FlightsSection data={flights} />}
        {research && <ResearchSection data={research} />}
        {accommodation && <StayFoodSection data={accommodation} />}
        {itinerary && itinerary.length > 0 && <ItinerarySection itinerary={itinerary} />}
        {costSummary && <CostSummarySection data={costSummary} />}

        <Text
          style={styles.footer}
          render={({ pageNumber, totalPages }) => `SmartItin · Page ${pageNumber} of ${totalPages}`}
          fixed
        />
      </Page>
    </Document>
  )
}
