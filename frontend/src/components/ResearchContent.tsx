import type { ResearchResponse } from '../types'
import { FallbackImage, MapsLink } from './FallbackImage'
import { BookOpenIcon, GemIcon, GlobeIcon, LandmarkIcon, ShieldIcon, SunIcon } from './icons'

export function ResearchContent({ data }: { data: ResearchResponse }) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="mb-2 flex items-center gap-1.5 font-display text-lg text-teal-700">
          <BookOpenIcon className="h-5 w-5 text-teal-600" />
          Why visit?
        </h3>
        <p className="text-teal-700/90">{data.why_visit}</p>
      </div>

      <div>
        <h3 className="mb-2 flex items-center gap-1.5 font-display text-lg text-teal-700">
          <SunIcon className="h-5 w-5 text-teal-600" />
          Weather
        </h3>
        <p className="text-teal-700/90">{data.climate}</p>
      </div>

      <div className="grid gap-6 sm:grid-cols-2">
        <div>
          <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold uppercase tracking-wide text-teal-600">
            <GlobeIcon className="h-4 w-4" />
            Culture notes
          </h3>
          <ul className="list-inside list-disc space-y-1 text-sm text-teal-700/90">
            {data.culture_notes.map((note, i) => (
              <li key={i}>{note}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold uppercase tracking-wide text-teal-600">
            <ShieldIcon className="h-4 w-4" />
            Safety tips
          </h3>
          <ul className="list-inside list-disc space-y-1 text-sm text-teal-700/90">
            {data.safety_tips.map((tip, i) => (
              <li key={i}>{tip}</li>
            ))}
          </ul>
        </div>
      </div>

      <div>
        <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold uppercase tracking-wide text-teal-600">
          <LandmarkIcon className="h-4 w-4" />
          Top attractions
        </h3>
        <div className="grid gap-3 sm:grid-cols-2">
          {data.top_attractions.map((a, i) => (
            <div key={i} className="overflow-hidden rounded-lg bg-sand-50">
              <FallbackImage src={a.image_url} alt={a.name} className="h-28 w-full object-cover" />
              <div className="p-3">
                <p className="font-medium text-teal-700">{a.name}</p>
                <p className="text-sm text-teal-700/70">{a.description}</p>
                <MapsLink href={a.maps_link} className="mt-1 inline-block" />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold uppercase tracking-wide text-coral-500">
          <GemIcon className="h-4 w-4" />
          Hidden gems
        </h3>
        <div className="grid gap-3 sm:grid-cols-2">
          {data.hidden_gems.map((a, i) => (
            <div key={i} className="overflow-hidden rounded-lg bg-coral-400/10">
              <FallbackImage src={a.image_url} alt={a.name} className="h-28 w-full object-cover" />
              <div className="p-3">
                <p className="font-medium text-teal-700">{a.name}</p>
                <p className="text-sm text-teal-700/70">{a.description}</p>
                <MapsLink href={a.maps_link} className="mt-1 inline-block" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
