import type { LocationCollection, LocationFeature } from '../src/shared/locations/types'

// These deliberately synthetic fixtures must never be presented as real facilities.
export function facility(id: string, located = true): LocationFeature {
  return {
    type: 'Feature',
    id,
    geometry: located ? { type: 'Point', coordinates: [15.98, 45.81] } : null,
    properties: {
      location_id: id,
      kindergarten_id: `institution-${id}`,
      name: `Synthetic institution ${id}`,
      location_name: `Synthetic facility ${id}`,
      address: 'Synthetic address 1',
      city: 'Zagreb',
      provider_kind: 'municipal',
      website_url: null,
      email: null,
      phone: null,
      district: null,
      location_role: 'facility',
      age_groups: null,
      sources: [{
        name: 'Synthetic source',
        url: 'https://example.invalid/source',
        license: 'Synthetic license',
        reference_date: null,
        retrieved_at: '2026-11-02T10:00:00Z',
      }],
    },
  }
}

export function collection(...features: LocationFeature[]): LocationCollection {
  const mapped = features.filter((feature) => feature.geometry !== null).length
  return {
    type: 'FeatureCollection',
    features,
    metadata: { total: features.length, mapped, unmapped: features.length - mapped, scope: 'city', complete: true },
  }
}

export function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason: Error) => void
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, resolve, reject }
}
