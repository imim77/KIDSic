import { Blob } from 'node:buffer'
import { gzipSync } from 'node:zlib'
import { afterEach, expect, it, vi } from 'vitest'
import { LocationToolResult } from '@/mvvm/features/Locations/utils/LocationToolResult'
import { collection, enrolmentRound, facility, historicalEvidence } from '@test-support/fixtures'

afterEach(() => vi.unstubAllGlobals())

it('accepts dated enrolment rounds and rejects inconsistent status, periods or channels', () => {
  const data = collection(facility('enrolment'))
  data.features[0].properties.enrolment = [enrolmentRound(), enrolmentRound({ round: 'rolling', status: 'open', opens_at: null })]
  expect(LocationToolResult.parse({ city: 'Zagreb', locations: data }).locations).toEqual(data)
  for (const invalid of [{ status: 'not_accepting' }, { accepting: false }, { closes_at: '2026-05-01T00:00:00Z' },
    { opens_at: '2026-05-13 09:00' }, { application_url: 'javascript:alert(1)' }, { channel: 'email' },
    { academic_year: '2026' }, { reference_date: '2026-02-30' }]) {
    data.features[0].properties.enrolment = [{ ...enrolmentRound(), ...invalid } as never]
    expect(() => LocationToolResult.parse({ city: 'Zagreb', locations: data })).toThrow('Invalid enrolment')
  }
})

it('validates historical snapshots independently of current eligibility', () => {
  const data = collection(facility('history'))
  data.features[0].properties.historical_data = [historicalEvidence()]
  expect(LocationToolResult.parse({ city: 'Zagreb', locations: data }).locations).toEqual(data)
  for (const invalid of [{ reference_date: '2025-02-30' }, { scope: 'unknown' },
    { vacancies: [{ age_label: null, program: null, free_places: -1 }] }, { programs: [123] }]) {
    Object.assign(data.features[0].properties, { historical_data: [{ ...historicalEvidence(), ...invalid }] })
    expect(() => LocationToolResult.parse({ city: 'Zagreb', locations: data })).toThrow('Invalid historical data')
  }
})

function compressed(data: unknown) {
  return { encoding: 'gzip+base64', data: gzipSync(JSON.stringify(data)).toString('base64') }
}

it('decodes a large city losslessly, including Unicode, coordinates and provenance', async () => {
  vi.stubGlobal('Blob', Blob)
  const locations = collection(...Array.from({ length: 461 }, (_, index) => facility(String(index))))
  locations.features[0].properties.location_name = 'Dječji vrtić Čarobna kućica'
  const result = await LocationToolResult.fromResult({
    structuredContent: { city: 'Zagreb', metadata: locations.metadata },
    _meta: { locations: compressed(locations) },
  })
  expect(result).toEqual({ city: 'Zagreb', locations })
})

it('rejects damaged compression and mismatched summary counts', async () => {
  vi.stubGlobal('Blob', Blob)
  const locations = collection(facility('one'))
  const structuredContent = { city: 'Zagreb', metadata: { ...locations.metadata, total: 2 } }
  await expect(LocationToolResult.fromResult({ structuredContent, _meta: { locations: compressed(locations) } })).rejects.toThrow('Mismatched summary')
  await expect(LocationToolResult.fromResult({ structuredContent, _meta: { locations: { encoding: 'gzip+base64', data: 'broken' } } })).rejects.toThrow()
})

it('rejects malformed contact values before rendering host results', () => {
  const locations = collection(facility('contact'))
  Object.assign(locations.features[0].properties, { phone: { unexpected: true } })
  expect(() => LocationToolResult.parse({ city: 'Zagreb', locations })).toThrow('Invalid contact')
})

it('keeps applied city and name and rejects malformed search criteria', async () => {
  const locations = collection()
  const parsed = await LocationToolResult.fromResult({
    structuredContent: { city: ' Rijeka ', name: ' Zamet ', metadata: locations.metadata }, _meta: { locations },
  })
  expect(parsed).toEqual({ city: 'Rijeka', name: 'Zamet', locations })
  for (const name of [null, 1, [], 'x'.repeat(201)]) {
    expect(() => LocationToolResult.parse({ city: 'Rijeka', name, locations })).toThrow('Invalid search name')
  }
})

it('validates applied type and rejects results from a different category', () => {
  for (const kind of ['municipal', 'private', 'religious', 'childminder', 'other', 'unknown'] as const) {
    const item = facility(kind)
    item.properties.provider_kind = kind
    const locations = collection(item)
    expect(LocationToolResult.parse({ city: 'Zagreb', provider_kind: kind, locations }).provider_kind).toBe(kind)
    expect(LocationToolResult.parse({ city: 'Zagreb', provider_kind: null, locations }).provider_kind).toBeNull()
  }
  for (const kind of ['', 'gradski', ['private'], 1, {}, '__proto__']) {
    expect(() => LocationToolResult.parse({ city: 'Zagreb', provider_kind: kind, locations: collection() })).toThrow('Invalid provider kind')
  }
  expect(() => LocationToolResult.parse({ city: 'Zagreb', provider_kind: 'private', locations: collection(facility('municipal')) }))
    .toThrow('Mismatched provider kind')
})

it('validates attested areas, matching diacritics and the optional administrative prefix', async () => {
  const item = facility('area')
  item.properties.areas = ['Mjesni odbor Pećine', 'Vulkan']
  const locations = collection(item)
  for (const area of [' pecine ', 'Mjesni odbor PEĆINE', 'Vulkan']) {
    const parsed = await LocationToolResult.fromResult({ structuredContent: { city: 'Rijeka', area, metadata: locations.metadata }, _meta: { locations } })
    expect(parsed.area).toBe(area.trim())
  }
  for (const area of [null, 1, [], {}, 'x'.repeat(201)]) {
    expect(() => LocationToolResult.parse({ city: 'Rijeka', area, locations })).toThrow('Invalid search area')
  }
  for (const area of ['Peć', 'Missing', '%']) {
    expect(() => LocationToolResult.parse({ city: 'Rijeka', area, locations })).toThrow('Mismatched area')
  }
  delete item.properties.areas
  expect(() => LocationToolResult.parse({ city: 'Rijeka', area: 'Pećine', locations })).toThrow('Mismatched area')
  Object.assign(item.properties, { areas: ['Pećine', 1] })
  expect(() => LocationToolResult.parse({ city: 'Rijeka', locations })).toThrow('Invalid areas')
})



it('requires a radius scope with in-range distances when the result names a point', () => {
  const locations = collection(facility('near'))
  locations.metadata.scope = 'radius'
  locations.features[0].properties.distance_m = 900
  expect(LocationToolResult.parse({ city: 'Zagreb', near: [15.98, 45.81], radius_m: 1000, locations }).nearby)
    .toEqual({ near: [15.98, 45.81], radius_m: 1000 })
  expect(LocationToolResult.parse({ city: 'Zagreb', near: null, radius_m: null, locations: collection() }).nearby).toBeNull()
  expect(() => LocationToolResult.parse({ city: 'Zagreb', near: [15.98, 45.81], radius_m: 800, locations })).toThrow('Invalid distance')
  expect(() => LocationToolResult.parse({ city: 'Zagreb', locations })).toThrow('Invalid locations')
  expect(() => LocationToolResult.parse({ city: 'Zagreb', near: [15.98, 45.81], radius_m: 1000, locations: collection() })).toThrow('Invalid locations')
  for (const [near, radius_m] of [[[15.98], 1000], [[181, 45], 1000], [[15.98, 45.81], 0], [[15.98, 45.81], null], [null, 1000]]) {
    expect(() => LocationToolResult.parse({ city: 'Zagreb', near, radius_m, locations })).toThrow('Invalid nearby')
  }
  const unlocated = collection(facility('unlocated', false))
  unlocated.metadata.scope = 'radius'
  expect(() => LocationToolResult.parse({ city: 'Zagreb', near: [15.98, 45.81], radius_m: 1000, locations: unlocated })).toThrow('Invalid distance')
})


it('rejects retired filters even when their values were previously valid', async () => {
  for (const criteria of [{ age_months: 24 }, { program: 'Montessori' }, { include_unknown: true }]) {
    expect(() => LocationToolResult.parse({ city: 'Zagreb', ...criteria, locations: collection() }))
      .toThrow('Unsupported search criteria')
    await expect(LocationToolResult.fromResult({ structuredContent: { city: 'Zagreb', ...criteria,
      metadata: collection().metadata }, _meta: { locations: collection() } })).rejects.toThrow('Unsupported search criteria')
  }
})
