import type { HistoricalEvidence, LocationCollection, LocationFeature, LocationProgram } from '../src/shared/locations/types'

export function historicalEvidence(overrides: Partial<HistoricalEvidence> = {}): HistoricalEvidence {
  return { reference_date: '2025-01-01', date_kind: 'observed', scope: 'institution', programs: [],
    vacancies: [{ age_label: 'od 1 do 2 godine', program: 'REDOVITI PROGRAM', free_places: 0 }],
    source_title: 'Synthetic open snapshot', source_url: 'https://example.invalid/historical.csv',
    license: 'Otvorena dozvola (OD)', ...overrides }
}

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
    metadata: { total: features.length, mapped, unmapped: features.length - mapped, scope: 'city', complete: true,
      confirmed: features.filter((f) => f.properties.suitability_status === 'confirmed').length,
      unknown: features.filter((f) => f.properties.suitability_status === 'unknown').length },
  }
}

export function programEvidence(overrides: Partial<LocationProgram> = {}): LocationProgram {
  return { program_id: 'synthetic-program', name: 'Montessori', min_age_months: 12, max_age_months_exclusive: 36,
    verified_on: '2026-11-04', valid_until: null, source_record_id: 'synthetic-record',
    source_url: 'https://example.invalid/program', source_title: 'Synthetic program source', scope: 'facility', ...overrides }
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
