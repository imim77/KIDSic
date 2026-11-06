import { useEffect, useState } from 'react'
import { LocationDirectory } from '../utils/LocationDirectory'
import type { LocationCollection, LocationFilters } from '../types'

const cityDirectory = new LocationDirectory()
type Snapshot = { key: string; data: LocationCollection | null; failed: boolean }

// useLocations reads the results for `filters`, keeping only the response to
// the latest criteria; `directory` is the API adapter, replaceable in tests.
export function useLocations(filters: LocationFilters, directory = cityDirectory) {
  const [attempt, setAttempt] = useState(0)
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const { city, q, provider_kind, area = '', has_vacancies = false } = filters
  // Primitive criteria let a new nearby object with equal values reuse the request.
  const [longitude, latitude] = filters.nearby?.near ?? []
  const radius = filters.nearby?.radius_m
  const key = JSON.stringify([city, q, provider_kind, area, has_vacancies, longitude, latitude, radius, attempt])

  useEffect(() => {
    const controller = new AbortController()
    let active = true
    const nearby = longitude === undefined || latitude === undefined || radius === undefined
      ? null : { near: [longitude, latitude] as [number, number], radius_m: radius }
    const criteria: LocationFilters = { city, q, provider_kind, area, has_vacancies, nearby }
    void directory.find(criteria, controller.signal).then((data) => {
      if (active) setSnapshot({ key, data, failed: false })
    }).catch(() => {
      if (active) setSnapshot({ key, data: null, failed: true })
    })
    return () => {
      active = false
      controller.abort()
    }
  }, [city, q, provider_kind, area, has_vacancies, longitude, latitude, radius, key, directory])

  const current = snapshot?.key === key ? snapshot : null
  return {
    status: !current ? 'loading' : current.failed ? 'error' : 'ready',
    data: current?.data ?? null,
    retry: () => setAttempt((value) => value + 1),
  } as const
}
