import { afterEach, describe, expect, it, vi } from 'vitest'
import { LocationDirectory } from '../src/shared/locations/LocationDirectory'
import { collection, facility } from './fixtures'

afterEach(() => vi.unstubAllGlobals())

describe('complete location directory', () => {
  it('sends literal city/name/provider filters and preserves null geometry for the list', async () => {
    const payload = collection(facility('mapped'), facility('unmapped', false))
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => payload })
    vi.stubGlobal('fetch', fetch)
    const signal = new AbortController().signal
    const result = await new LocationDirectory().find({ city: 'Zagreb', q: '100% & Medo', provider_kind: 'municipal' }, signal)
    const [url, options] = fetch.mock.calls[0]
    const params = new URL(url, 'http://localhost').searchParams
    expect(Object.fromEntries(params)).toEqual({ city: 'Zagreb', q: '100% & Medo', provider_kind: 'municipal' })
    expect(options.signal).toBe(signal)
    expect(params.has('bbox')).toBe(false)
    expect(result.features[1].geometry).toBeNull()
  })

  it.each([
    { ...collection(facility('one')), metadata: { ...collection(facility('one')).metadata, complete: false } },
    { ...collection(facility('one')), metadata: { ...collection(facility('one')).metadata, scope: 'bbox' } },
    { ...collection(facility('one')), metadata: { ...collection(facility('one')).metadata, total: 2 } },
    { ...collection(facility('one')), metadata: { ...collection(facility('one')).metadata, mapped: 0 } },
  ])('rejects partial or inconsistent responses instead of claiming complete coverage', async (payload) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => payload }))
    await expect(new LocationDirectory().find({ city: 'Zagreb', q: '', provider_kind: '' }, new AbortController().signal))
      .rejects.toThrow('Incomplete location response')
  })

  it('keeps HTTP failures distinct from successful empty results', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 503 }))
    await expect(new LocationDirectory().find({ city: 'Zagreb', q: '', provider_kind: '' }, new AbortController().signal))
      .rejects.toThrow('Locations unavailable (503)')
  })
})
