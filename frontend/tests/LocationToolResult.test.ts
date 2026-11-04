import { Blob } from 'node:buffer'
import { gzipSync } from 'node:zlib'
import { afterEach, expect, it, vi } from 'vitest'
import { LocationToolResult } from '../src/shared/mcp/LocationToolResult'
import { collection, facility } from './fixtures'

afterEach(() => vi.unstubAllGlobals())

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
