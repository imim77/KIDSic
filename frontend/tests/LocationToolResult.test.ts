import { Blob } from 'node:buffer'
import { gzipSync } from 'node:zlib'
import { afterEach, expect, it, vi } from 'vitest'
import { LocationToolResult } from '../src/shared/mcp/LocationToolResult'
import { collection, enrolmentRound, facility, historicalEvidence, programEvidence } from './fixtures'

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

it('requires one sourced program matching both age and requested program before confirming suitability', () => {
  const item = facility('confirmed')
  Object.assign(item.properties, { suitability_status: 'confirmed', programs: [programEvidence()] })
  const criteria = { city: 'Zagreb', age_months: 24, program: ' montessori ', include_unknown: false }
  expect(LocationToolResult.parse({ ...criteria, locations: collection(item) }).program).toBe('montessori')
  item.properties.programs = [programEvidence({ max_age_months_exclusive: 24 })]
  expect(() => LocationToolResult.parse({ ...criteria, locations: collection(item) })).toThrow('Missing matching program evidence')
  item.properties.programs = [programEvidence({ name: 'General' }), programEvidence({ min_age_months: 36, max_age_months_exclusive: 84 })]
  expect(() => LocationToolResult.parse({ ...criteria, locations: collection(item) })).toThrow('Missing matching program evidence')
  item.properties.programs = [programEvidence({ source_url: '' })]
  expect(() => LocationToolResult.parse({ ...criteria, locations: collection(item) })).toThrow('Invalid programs')
  item.properties.programs = [programEvidence({ scope: 'facility' })]
  item.properties.location_role = 'seat'
  expect(() => LocationToolResult.parse({ ...criteria, locations: collection(item) })).toThrow('Invalid seat program scope')
})

it('rejects invalid age and program criteria, missing suitability and misleading counts', () => {
  for (const age_months of [-1,217,24.5,'24',true,[]]) {
    expect(() => LocationToolResult.parse({ city: 'Zagreb', age_months, locations: collection() })).toThrow('Invalid child age')
  }
  for (const program of [null,[],true,'x'.repeat(201)]) {
    expect(() => LocationToolResult.parse({ city: 'Zagreb', program, locations: collection() })).toThrow('Invalid search program')
  }
  expect(() => LocationToolResult.parse({ city: 'Zagreb', include_unknown: 'false', locations: collection() })).toThrow('Invalid unknown filter')
  const item = facility('unknown')
  const criteria = { city: 'Zagreb', age_months: 0 }
  expect(() => LocationToolResult.parse({ ...criteria, locations: collection(item) })).toThrow('Missing suitability')
  item.properties.suitability_status = 'unknown'
  expect(LocationToolResult.parse({ ...criteria, locations: collection(item) }).age_months).toBe(0)
  expect(() => LocationToolResult.parse({ ...criteria, include_unknown: false, locations: collection(item) })).toThrow('Unexpected unknown result')
  const locations = collection(item)
  locations.metadata.confirmed = 1
  expect(() => LocationToolResult.parse({ ...criteria, locations })).toThrow('Invalid suitability counts')
})
