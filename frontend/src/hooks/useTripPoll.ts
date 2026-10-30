import { useEffect, useState } from 'react'
import { getJobStatus } from '../api'
import type { JobStatus } from '../types'

const POLL_INTERVAL_MS = 2000

export function useTripPoll(jobId: string | null) {
  const [status, setStatus] = useState<JobStatus | null>(null)
  const [pollError, setPollError] = useState<string | null>(null)

  useEffect(() => {
    setStatus(null)
    setPollError(null)
    if (!jobId) return

    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | undefined

    async function poll() {
      try {
        const data = await getJobStatus(jobId as string)
        if (cancelled) return
        setStatus(data)
        if (data.status === 'running') {
          timer = setTimeout(poll, POLL_INTERVAL_MS)
        }
      } catch (err) {
        if (!cancelled) {
          setPollError(err instanceof Error ? err.message : String(err))
          timer = setTimeout(poll, POLL_INTERVAL_MS)
        }
      }
    }

    poll()
    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [jobId])

  return { status, pollError }
}
