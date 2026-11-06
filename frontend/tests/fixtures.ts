import type { HistoricalEvidence, LocationCollection, LocationEnrolment, LocationFeature } from '../src/shared/locations/types'

export function enrolmentRound(overrides: Partial<LocationEnrolment> = {}): LocationEnrolment {
  return { round: 'main', academic_year: '2026./2027.', channel: 'city_system',
    application_url: 'https://upis.example.invalid/', accepting: true,
    opens_at: '2026-05-13T07:00:00Z', closes_at: '2026-05-22T14:00:00Z', status: 'closed',
    source_title: 'Synthetic enrolment notice', source_url: 'https://example.invalid/notice.pdf',
    license: 'Ponovna uporaba uz navođenje izvora', reference_date: '2026-05-11', date_kind: 'published', ...overrides }
}

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
