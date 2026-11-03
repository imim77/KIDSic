import { StrictMode } from 'react'
import { act, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { collection, facility } from './fixtures'

type Listener = (...args: unknown[]) => void

const mock = vi.hoisted(() => {
  function createMap() {
    const listeners = new Map<string, Set<Listener>>()
    const sources = new Map<string, { setData: ReturnType<typeof vi.fn>; getClusterExpansionZoom: ReturnType<typeof vi.fn> }>()
    const api = {
      on: vi.fn((event: string, layerOrListener: string | Listener, handler?: Listener) => {
        const key = typeof layerOrListener === 'string' ? `${event}:${layerOrListener}` : event
        if (!listeners.has(key)) listeners.set(key, new Set())
        listeners.get(key)?.add(handler ?? layerOrListener as Listener)
        return api
      }),
      off: vi.fn((event: string, layerOrListener: string | Listener, handler?: Listener) => {
        const key = typeof layerOrListener === 'string' ? `${event}:${layerOrListener}` : event
        listeners.get(key)?.delete(handler ?? layerOrListener as Listener)
        return api
      }),
      emit(event: string, ...args: unknown[]) { listeners.get(event)?.forEach((listener) => listener(...args)) },
      resetStyle() { sources.clear() },
      listenerCount(event: string) { return listeners.get(event)?.size ?? 0 },
      isStyleLoaded: vi.fn(() => false),
      getSource: vi.fn((id = 'kindergarten-locations') => sources.get(id)),
      addSource: vi.fn((id: string) => {
        sources.set(id, { setData: vi.fn(), getClusterExpansionZoom: vi.fn() })
      }),
      addLayer: vi.fn(),
      addControl: vi.fn(),
      fitBounds: vi.fn(),
      easeTo: vi.fn(),
      flyTo: vi.fn(),
      getZoom: vi.fn(() => 11),
      jumpTo: vi.fn(),
      setFilter: vi.fn(),
      setPaintProperty: vi.fn(),
      getCanvas: vi.fn(() => ({ style: { cursor: '' } })),
      getContainer: vi.fn(() => document.createElement('div')),
      setPadding: vi.fn(),
      resize: vi.fn(),
      remove: vi.fn(),
    }
    return api
  }
  return {
    createMap,
    maps: [] as ReturnType<typeof createMap>[],
    Map: vi.fn(),
    supported: vi.fn(() => true),
    NavigationControl: vi.fn(),
    observers: [] as { callback: ResizeObserverCallback; disconnect: ReturnType<typeof vi.fn> }[],
  }
})

vi.mock('mapbox-gl', () => ({ default: mock }))

let KindergartenMap: typeof import('../src/shared/map/KindergartenMap').KindergartenMap

beforeAll(async () => {
  vi.stubEnv('VITE_MAPBOX_ACCESS_TOKEN', 'pk.synthetic-unit-test-token')
  KindergartenMap = (await import('../src/shared/map/KindergartenMap')).KindergartenMap
})

beforeEach(() => {
  mock.maps.length = 0
  mock.observers.length = 0
  mock.supported.mockReturnValue(true)
  mock.Map.mockImplementation(function () {
    const map = mock.createMap()
    mock.maps.push(map)
    return map
  })
  vi.stubGlobal('ResizeObserver', class {
    disconnect = vi.fn()
    observe = vi.fn()
    unobserve = vi.fn()
    constructor(callback: ResizeObserverCallback) { mock.observers.push({ callback, disconnect: this.disconnect }) }
  })
})

afterEach(() => vi.unstubAllGlobals())

describe('Mapbox lifecycle and data', () => {
  it('mounts data arriving before the style and updates the same source without reallocating the map', async () => {
    const beforeStyle = collection(facility('first'), facility('unlocated', false))
    const { rerender, unmount } = render(<KindergartenMap collection={beforeStyle} />)
    await waitFor(() => expect(mock.maps).toHaveLength(1))
    const map = mock.maps[0]
    expect(map.addSource).not.toHaveBeenCalled()
    act(() => map.emit('style.load'))
    expect(screen.queryByText('Legenda karte')).toBeNull()
    expect(map.addSource).toHaveBeenCalledTimes(2)
    expect(map.addSource).toHaveBeenCalledWith('kindergarten-locations', expect.objectContaining({
      cluster: true,
      data: expect.objectContaining({ features: [beforeStyle.features[0]] }),
    }))
    const afterStyle = collection(facility('replacement'))
    rerender(<KindergartenMap collection={afterStyle} />)
    expect(map.getSource()?.setData).toHaveBeenLastCalledWith(expect.objectContaining({ features: afterStyle.features }))
    expect(mock.maps).toHaveLength(1)
    expect(map.addSource).toHaveBeenCalledTimes(2)
    unmount()
    expect(map.listenerCount('click:kindergarten-points')).toBe(0)
    expect(map.remove).toHaveBeenCalledOnce()
  })

  it('forwards point selection to the latest callback and resizes when its panel changes', async () => {
    const original = vi.fn()
    const latest = vi.fn()
    const { rerender } = render(<KindergartenMap onSelect={original} />)
    await waitFor(() => expect(mock.maps).toHaveLength(1))
    const map = mock.maps[0]
    rerender(<KindergartenMap onSelect={latest} />)
    act(() => map.emit('click:kindergarten-points', { features: [{ id: 'selected-facility' }] }))
    expect(latest).toHaveBeenCalledWith('selected-facility')
    expect(original).not.toHaveBeenCalled()
    mock.observers[0].callback([], {} as ResizeObserver)
    expect(map.resize).toHaveBeenCalledOnce()
  })

  it('refreshes viewport padding in both rotation directions without resetting the selected camera or map', async () => {
    const payload = collection(facility('mapped'))
    const { getByTestId } = render(<div className="kindergarten-explorer" data-testid="explorer">
      <KindergartenMap collection={payload} selectedId="mapped" />
      <section className="location-carousel" data-testid="deck" />
    </div>)
    await waitFor(() => expect(mock.maps).toHaveLength(1))
    const map = mock.maps[0]
    act(() => map.emit('style.load'))
    const frame = getByTestId('explorer')
    const deck = getByTestId('deck')
    map.getContainer.mockReturnValue(frame.querySelector<HTMLElement>('.map-canvas')!)
    let height = 680
    let deckHeight = 230
    Object.defineProperty(frame, 'clientHeight', { get: () => height })
    deck.getBoundingClientRect = () => ({ height: deckHeight } as DOMRect)
    map.fitBounds.mockClear()
    map.jumpTo.mockClear()
    map.easeTo.mockClear()
    const sourceWrites = map.getSource()?.setData.mock.calls.length

    act(() => mock.observers[0].callback([], {} as ResizeObserver))
    expect(map.setPadding).toHaveBeenLastCalledWith({ top: 90, bottom: 275, left: 45, right: 45 })
    height = 296
    deckHeight = 174
    act(() => mock.observers[0].callback([], {} as ResizeObserver))
    expect(map.setPadding).toHaveBeenLastCalledWith({ top: 59.2, bottom: 177.6, left: 45, right: 45 })
    height = 680
    deckHeight = 230
    act(() => mock.observers[0].callback([], {} as ResizeObserver))
    expect(map.setPadding).toHaveBeenLastCalledWith({ top: 90, bottom: 275, left: 45, right: 45 })
    expect(map.resize).toHaveBeenCalledTimes(3)
    expect(map.resize.mock.invocationCallOrder.at(-1)).toBeLessThan(map.setPadding.mock.invocationCallOrder.at(-1)!)
    expect(map.fitBounds).not.toHaveBeenCalled()
    expect(map.jumpTo).not.toHaveBeenCalled()
    expect(map.easeTo).not.toHaveBeenCalled()
    expect(map.getSource()?.setData).toHaveBeenCalledTimes(sourceWrites!)
    expect(mock.maps).toHaveLength(1)
    expect(map.remove).not.toHaveBeenCalled()
  })

  it('selects the canonical location property when rendered vector tiles omit the UUID feature id', async () => {
    const onSelect = vi.fn()
    render(<KindergartenMap onSelect={onSelect} />)
    await waitFor(() => expect(mock.maps).toHaveLength(1))
    const map = mock.maps[0]
    act(() => map.emit('click:kindergarten-points', {
      features: [{ properties: { location_id: 'canonical-location-uuid' } }],
    }))
    expect(onSelect).toHaveBeenCalledWith('canonical-location-uuid')
  })

  it('leaves exactly one live map under StrictMode and disposes its listeners and observer', async () => {
    const { unmount } = render(<StrictMode><KindergartenMap /></StrictMode>)
    await waitFor(() => expect(mock.maps).toHaveLength(1))
    const map = mock.maps[0]
    expect(map.remove).not.toHaveBeenCalled()
    expect(map.listenerCount('click:kindergarten-points')).toBe(1)
    unmount()
    expect(mock.observers[0].disconnect).toHaveBeenCalledOnce()
    expect(map.remove).toHaveBeenCalledOnce()
    expect(map.listenerCount('click:kindergarten-points')).toBe(0)
  })

  it('does not allocate a map when the component unmounts before the lazy import resolves', async () => {
    const { unmount } = render(<KindergartenMap />)
    unmount()
    await act(async () => { await Promise.resolve() })
    expect(mock.maps).toHaveLength(0)
  })

  it('shows a fallback when WebGL is unsupported', async () => {
    mock.supported.mockReturnValue(false)
    render(<KindergartenMap />)
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('nije moguće pokrenuti'))
    expect(mock.maps).toHaveLength(0)
  })

  it('removes a partially initialized map when observing the panel fails', async () => {
    vi.stubGlobal('ResizeObserver', class { constructor() { throw new Error('observer failed') } })
    const { unmount } = render(<KindergartenMap />)
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('nije moguće pokrenuti'))
    const map = mock.maps[0]
    expect(map.remove).toHaveBeenCalledOnce()
    expect(map.listenerCount('click:kindergarten-points')).toBe(0)
    unmount()
    expect(map.remove).toHaveBeenCalledOnce()
  })

  it('highlights and focuses list selection above clusters, but never places a seat or an unlocated object', async () => {
    const payload = collection(facility('mapped'), facility('unlocated', false))
    const { rerender } = render(<KindergartenMap collection={payload} selectedId="mapped" />)
    await waitFor(() => expect(mock.maps).toHaveLength(1))
    const map = mock.maps[0]
    act(() => map.emit('style.load'))
    expect(map.addSource).toHaveBeenCalledWith('kindergarten-selection', expect.objectContaining({
      data: expect.objectContaining({ features: [payload.features[0]] }),
    }))
    expect(map.jumpTo).toHaveBeenCalledWith({ center: [15.98, 45.81], zoom: 15, padding: { top: 50, bottom: 50, left: 50, right: 50 } })
    map.jumpTo.mockClear()
    rerender(<KindergartenMap collection={payload} selectedId="unlocated" />)
    expect(map.getSource('kindergarten-selection')?.setData).toHaveBeenLastCalledWith(expect.objectContaining({ features: [] }))
    expect(map.jumpTo).not.toHaveBeenCalled()
    rerender(<KindergartenMap collection={payload} selectedId={null} />)
    expect(map.getSource('kindergarten-selection')?.setData).toHaveBeenLastCalledWith(expect.objectContaining({ features: [] }))
    expect(mock.maps).toHaveLength(1)
  })

  it('restores the latest data and selection after a style reload', async () => {
    const payload = collection(facility('first'))
    render(<KindergartenMap collection={payload} selectedId="first" />)
    await waitFor(() => expect(mock.maps).toHaveLength(1))
    const map = mock.maps[0]
    act(() => map.emit('style.load'))
    map.resetStyle()
    act(() => map.emit('style.load'))
    expect(map.addSource).toHaveBeenLastCalledWith('kindergarten-selection', expect.objectContaining({
      data: expect.objectContaining({ features: payload.features }),
    }))
    expect(mock.maps).toHaveLength(1)
    expect(map.listenerCount('click:kindergarten-points')).toBe(1)
  })

  it('expands a clicked cluster and ignores expansion callbacks after disposal', async () => {
    const { unmount } = render(<KindergartenMap />)
    await waitFor(() => expect(mock.maps).toHaveLength(1))
    const map = mock.maps[0]
    act(() => map.emit('style.load'))
    const zoom = map.getSource()?.getClusterExpansionZoom
    const callbacks: ((error: Error | null, zoom: number) => void)[] = []
    zoom?.mockImplementation((_id: number, callback: (error: Error | null, zoom: number) => void) => { callbacks.push(callback) })
    const feature = { geometry: { type: 'Point', coordinates: [16, 45.8] }, properties: { cluster_id: 7 } }
    act(() => map.emit('click:kindergarten-clusters', { features: [feature] }))
    callbacks[0](null, 13)
    expect(map.easeTo).toHaveBeenCalledWith({ center: [16, 45.8], zoom: 13 })
    act(() => map.emit('click:kindergarten-clusters', { features: [feature] }))
    map.easeTo.mockClear()
    unmount()
    callbacks[1](null, 14)
    expect(map.easeTo).not.toHaveBeenCalled()
  })

  it('ignores pending cluster expansion from a superseded filter result', async () => {
    const { rerender } = render(<KindergartenMap collection={collection(facility('previous'))} />)
    await waitFor(() => expect(mock.maps).toHaveLength(1))
    const map = mock.maps[0]
    act(() => map.emit('style.load'))
    let finish!: (error: Error | null, zoom: number) => void
    map.getSource()?.getClusterExpansionZoom.mockImplementation((_id: number, callback: typeof finish) => { finish = callback })
    act(() => map.emit('click:kindergarten-clusters', {
      features: [{ geometry: { type: 'Point', coordinates: [16, 45.8] }, properties: { cluster_id: 7 } }],
    }))
    rerender(<KindergartenMap collection={collection(facility('current'))} />)
    finish(null, 14)
    expect(map.easeTo).not.toHaveBeenCalled()
  })
})
