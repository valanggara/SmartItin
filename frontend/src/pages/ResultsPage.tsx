import { pdf } from '@react-pdf/renderer'
import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { startTrip } from '../api'
import { BrandLogo } from '../components/BrandLogo'
import { CostSummaryContent } from '../components/CostSummaryContent'
import { FlightsContent } from '../components/FlightsContent'
import {
  BuildingIcon,
  CalendarIcon,
  CompassIcon,
  DownloadIcon,
  PlaneIcon,
  ShareIcon,
  WalletIcon,
} from '../components/icons'
import { ItineraryContent } from '../components/ItineraryContent'
import { ResearchContent } from '../components/ResearchContent'
import { SectionShell } from '../components/SectionShell'
import { StayFoodContent } from '../components/StayFoodContent'
import { TripPlanPdf } from '../components/TripPlanPdf'
import { formatShortDate } from '../format'
import { usePageTitle } from '../hooks/usePageTitle'
import { useTripPoll } from '../hooks/useTripPoll'
import { isError } from '../types'
import type { DayPlan, TripRequest } from '../types'

export function ResultsPage() {
  usePageTitle('SmartItin - Your Travel Plan')
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const jobId = searchParams.get('job')
  const { status, pollError } = useTripPoll(jobId)
  const [regenerating, setRegenerating] = useState(false)
  const [shareState, setShareState] = useState<'idle' | 'copied'>('idle')
  const [currentItinerary, setCurrentItinerary] = useState<DayPlan[] | null>(null)
  const [generatingPdf, setGeneratingPdf] = useState(false)

  async function handleDownloadPdf() {
    if (!status?.request) return
    setGeneratingPdf(true)
    try {
      const sections = status.sections
      const blob = await pdf(
        <TripPlanPdf
          request={status.request}
          flights={sections.flights && !isError(sections.flights) ? sections.flights : null}
          research={sections.research && !isError(sections.research) ? sections.research : null}
          accommodation={
            sections.accommodation && !isError(sections.accommodation) ? sections.accommodation : null
          }
          itinerary={
            currentItinerary ??
            (sections.itinerary && !isError(sections.itinerary) ? sections.itinerary.itinerary : null)
          }
          costSummary={sections.cost_summary && !isError(sections.cost_summary) ? sections.cost_summary : null}
        />,
      ).toBlob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `SmartItin-${status.request.origin}-${status.request.destination}.pdf`
      link.click()
      URL.revokeObjectURL(url)
    } finally {
      setGeneratingPdf(false)
    }
  }

  async function handleShare() {
    const url = window.location.href
    if (navigator.share) {
      try {
        await navigator.share({ title: 'My Travel Plan', url })
      } catch {
        // User cancelled the native share sheet — not an error to surface.
      }
      return
    }
    await navigator.clipboard.writeText(url)
    setShareState('copied')
    setTimeout(() => setShareState('idle'), 2000)
  }

  async function handleRegenerate() {
    const raw = sessionStorage.getItem('lastTripRequest')
    if (!raw) return
    const payload = JSON.parse(raw) as TripRequest
    setRegenerating(true)
    try {
      const newJobId = await startTrip(payload)
      navigate(`/results?job=${newJobId}`, { replace: true })
    } finally {
      setRegenerating(false)
    }
  }

  if (!jobId) {
    return (
      <main className="mx-auto max-w-2xl px-4 py-16 text-center">
        <p className="text-teal-700">No trip in progress.</p>
        <button onClick={() => navigate('/')} className="mt-4 text-coral-600 underline">
          Plan a trip
        </button>
      </main>
    )
  }

  const sections = status?.sections

  return (
    <main className="mx-auto min-h-screen max-w-4xl px-4 py-12 sm:py-16">
      <header className="mb-8 flex items-center justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-3 font-display text-3xl text-teal-700 sm:text-4xl">
            <BrandLogo className="h-10 w-auto" />
            Your Travel Plan
          </h1>
          {status?.status === 'running' && <p className="text-sm text-teal-700/60">Building your plan…</p>}
        </div>
        <div className="print:hidden flex shrink-0 gap-2">
          <button
            onClick={() => navigate('/')}
            className="whitespace-nowrap rounded-lg border border-sand-300 px-4 py-2 text-sm font-medium text-teal-700/70 transition hover:bg-sand-100"
          >
            New Trip
          </button>
          <button
            onClick={handleRegenerate}
            disabled={regenerating || !sessionStorage.getItem('lastTripRequest')}
            className="whitespace-nowrap rounded-lg border border-teal-500 px-4 py-2 text-sm font-medium text-teal-600 transition hover:bg-teal-500 hover:text-cream disabled:opacity-50"
          >
            {regenerating ? 'Regenerating…' : 'Regenerate'}
          </button>
          <button
            onClick={handleShare}
            className="flex items-center gap-1.5 whitespace-nowrap rounded-lg border border-sand-300 px-4 py-2 text-sm font-medium text-teal-700/70 transition hover:bg-sand-100"
          >
            <ShareIcon className="h-4 w-4" />
            {shareState === 'copied' ? 'Link copied!' : 'Share'}
          </button>
        </div>
      </header>

      {status?.request && (
        <div className="mb-8 hidden border-b border-sand-300 pb-4 print:block">
          <p className="font-display text-2xl text-teal-700">
            {status.request.origin} → {status.request.destination}
          </p>
          <p className="mt-1 text-sm text-teal-700/70">
            {formatShortDate(status.request.start_date)} – {formatShortDate(status.request.end_date)} ·{' '}
            {status.request.theme} · {status.request.budget_tier} tier · {status.request.travel_pace} pace
          </p>
          <p className="mt-1 text-xs text-teal-700/50">Generated {formatShortDate(new Date().toISOString())}</p>
        </div>
      )}

      {pollError && <p className="mb-4 text-sm text-coral-600">{pollError}</p>}
      {status?.status === 'error' && (
        <p className="mb-4 text-sm text-coral-600">Something went wrong: {status.error}</p>
      )}

      <div className="space-y-6">
        <SectionShell
          title="Flights"
          icon={<PlaneIcon className="h-5 w-5" />}
          loading={!sections?.flights}
          errorMessage={sections?.flights && isError(sections.flights) ? sections.flights.error : null}
        >
          {sections?.flights && !isError(sections.flights) && <FlightsContent data={sections.flights} />}
        </SectionShell>

        <SectionShell
          title="Destination Guide"
          icon={<CompassIcon className="h-5 w-5" />}
          loading={!sections?.research}
          errorMessage={sections?.research && isError(sections.research) ? sections.research.error : null}
        >
          {sections?.research && !isError(sections.research) && <ResearchContent data={sections.research} />}
        </SectionShell>

        <SectionShell
          title="Stay & Food"
          icon={<BuildingIcon className="h-5 w-5" />}
          loading={!sections?.accommodation}
          errorMessage={
            sections?.accommodation && isError(sections.accommodation) ? sections.accommodation.error : null
          }
        >
          {sections?.accommodation && !isError(sections.accommodation) && (
            <StayFoodContent data={sections.accommodation} />
          )}
        </SectionShell>

        <SectionShell
          title="Day-by-Day Itinerary"
          icon={<CalendarIcon className="h-5 w-5" />}
          loading={!sections?.itinerary}
          errorMessage={sections?.itinerary && isError(sections.itinerary) ? sections.itinerary.error : null}
        >
          {sections?.itinerary && !isError(sections.itinerary) && (
            <ItineraryContent
              data={sections.itinerary}
              extensions={
                sections.research && !isError(sections.research) ? sections.research.trip_extensions : []
              }
              jobId={jobId}
              onItineraryChange={setCurrentItinerary}
            />
          )}
        </SectionShell>

        <SectionShell
          title="Cost Summary"
          icon={<WalletIcon className="h-5 w-5" />}
          loading={!sections?.cost_summary}
          errorMessage={
            sections?.cost_summary && isError(sections.cost_summary) ? sections.cost_summary.error : null
          }
        >
          {sections?.cost_summary && !isError(sections.cost_summary) && (
            <CostSummaryContent data={sections.cost_summary} />
          )}
        </SectionShell>
      </div>

      {status?.status === 'done' && (
        <div className="print:hidden mt-8 flex justify-center">
          <button
            onClick={handleDownloadPdf}
            disabled={generatingPdf}
            className="flex items-center gap-1.5 whitespace-nowrap rounded-lg border border-sand-300 px-4 py-2 text-sm font-medium text-teal-700/70 transition hover:bg-sand-100 disabled:opacity-50"
          >
            <DownloadIcon className="h-4 w-4" />
            {generatingPdf ? 'Generating…' : 'Download PDF'}
          </button>
        </div>
      )}
    </main>
  )
}
