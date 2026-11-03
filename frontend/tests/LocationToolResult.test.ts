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
