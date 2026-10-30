import type { ItineraryModifyResponse, JobStatus, TripRequest } from './types'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function startTrip(payload: TripRequest): Promise<string> {
  const res = await fetch(`${API_BASE}/run-async`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    throw new Error(`Failed to start trip planning (HTTP ${res.status})`)
  }
  const data = (await res.json()) as { job_id: string }
  return data.job_id
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API_BASE}/status/${jobId}`)
  if (!res.ok) {
    throw new Error(`Failed to fetch trip status (HTTP ${res.status})`)
  }
  return res.json()
}

export async function modifyItinerary(
  jobId: string,
  action: string,
  actionParams: Record<string, unknown>,
): Promise<ItineraryModifyResponse> {
  const res = await fetch(`${API_BASE}/modify-itinerary`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_id: jobId, action, action_params: actionParams }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail || `Failed to modify itinerary (HTTP ${res.status})`)
  }
  return res.json()
}
