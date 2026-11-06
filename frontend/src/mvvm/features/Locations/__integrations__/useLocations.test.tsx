import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { LocationDirectory } from '@/mvvm/features/Locations/utils/LocationDirectory'
import type { LocationCollection, LocationFilters } from '@/mvvm/features/Locations/types'
import { useLocations } from '@/mvvm/features/Locations/hooks/use-locations'
import { collection, deferred, facility } from '@test-support/fixtures'

const filters: LocationFilters = { city: 'Zagreb', q: '', provider_kind: '' }

describe('location requests', () => {
  it('cancels superseded requests and ignores late responses even when a transport ignores abort', async () => {
    const first = deferred<LocationCollection>()
    const second = deferred<LocationCollection>()
    const find = vi.spyOn(LocationDirectory.prototype, 'find')
      .mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
    const { result, rerender, unmount } = renderHook(useLocations, { initialProps: filters })
    const firstSignal = find.mock.calls[0][1]
    rerender({ ...filters, q: 'new query' })
    expect(firstSignal.aborted).toBe(true)
    expect(result.current).toMatchObject({ status: 'loading', data: null })
    const latest = collection(facility('latest'))
    await act(async () => { second.resolve(latest) })
    expect(result.current.data).toEqual(latest)
    await act(async () => { first.resolve(collection(facility('outdated'))) })
    expect(result.current.data).toEqual(latest)
    const latestSignal = find.mock.calls[1][1]
    unmount()
    expect(latestSignal.aborted).toBe(true)
  })

  it('hides earlier results immediately while new criteria load and can retry a failure', async () => {
    const retry = deferred<LocationCollection>()
    vi.spyOn(LocationDirectory.prototype, 'find')
      .mockResolvedValueOnce(collection(facility('previous')))
      .mockRejectedValueOnce(new Error('offline'))
      .mockReturnValueOnce(retry.promise)
    const { result, rerender } = renderHook(useLocations, { initialProps: filters })
    await waitFor(() => expect(result.current.status).toBe('ready'))
    rerender({ ...filters, city: 'Split' })
    expect(result.current.data).toBeNull()
    await waitFor(() => expect(result.current.status).toBe('error'))
    act(() => result.current.retry())
    expect(result.current.status).toBe('loading')
    await act(async () => { retry.resolve(collection()) })
    expect(result.current).toMatchObject({ status: 'ready', data: collection() })
  })
})
