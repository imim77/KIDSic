import { useEffect, useState } from 'react'
import { LocationDirectory } from './LocationDirectory'
import type { LocationCollection, LocationFilters } from './types'

const directory = new LocationDirectory()
type Snapshot = { key: string; data: LocationCollection | null; failed: boolean }

export function useLocations(filters: LocationFilters) {
  const [attempt, setAttempt] = useState(0)
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const { city, q, provider_kind } = filters
  const key = JSON.stringify([city, q, provider_kind, attempt])

  useEffect(() => {
    const controller = new AbortController()
    let active = true
    void directory.find({ city, q, provider_kind }, controller.signal).then((data) => {
      if (active) setSnapshot({ key, data, failed: false })
    }).catch(() => {
      if (active) setSnapshot({ key, data: null, failed: true })
    })
    return () => {
      active = false
      controller.abort()
    }
  }, [city, q, provider_kind, key])

  const current = snapshot?.key === key ? snapshot : null
  return {
    status: !current ? 'loading' : current.failed ? 'error' : 'ready',
    data: current?.data ?? null,
    retry: () => setAttempt((value) => value + 1),
  } as const
}
