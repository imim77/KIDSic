import { describe, expect, it, vi } from 'vitest'
import { LocationDirectory } from '@/mvvm/features/Locations/utils/LocationDirectory'
import { collection, facility } from '@test-support/fixtures'


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

  it('sends a nearby point and radius and requires a radius-scoped response', async () => {
    const payload = collection(facility('near'))
    payload.metadata.scope = 'radius'
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => payload })
    vi.stubGlobal('fetch', fetch)
    const filters = { city: 'Zagreb', q: '', provider_kind: '' as const, nearby: { near: [15.98, 45.81] as [number, number], radius_m: 2000 } }
    await new LocationDirectory().find(filters, new AbortController().signal)
    expect(Object.fromEntries(new URL(fetch.mock.calls[0][0], 'http://localhost').searchParams))
      .toEqual({ city: 'Zagreb', near: '15.98,45.81', radius_m: '2000' })
    fetch.mockResolvedValue({ ok: true, json: async () => collection(facility('city')) })
    await expect(new LocationDirectory().find(filters, new AbortController().signal))
      .rejects.toThrow('Incomplete location response')
  })

  it.each([
    ['incomplete coverage', { complete: false }],
    ['unexpected scope', { scope: 'bbox' }],
    ['wrong total', { total: 2 }],
    ['wrong mapped count', { mapped: 0 }],
  ])('rejects %s instead of claiming complete coverage', async (_, metadata) => {
    const payload = collection(facility('one'))
    Object.assign(payload.metadata, metadata)
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
