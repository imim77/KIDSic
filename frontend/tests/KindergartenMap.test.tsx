import { StrictMode } from 'react'
import { act, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { collection, facility } from './fixtures'

type Listener = (...args: unknown[]) => void

const mock = vi.hoisted(() => {
  function createMap() {
    const listeners = new Map<string, Set<Listener>>()
    let source: { setData: ReturnType<typeof vi.fn>; getClusterExpansionZoom: ReturnType<typeof vi.fn> } | undefined
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
      listenerCount(event: string) { return listeners.get(event)?.size ?? 0 },
      isStyleLoaded: vi.fn(() => false),
      getSource: vi.fn(() => source),
      addSource: vi.fn(() => {
        source = { setData: vi.fn(), getClusterExpansionZoom: vi.fn() }
      }),
      addLayer: vi.fn(),
      addControl: vi.fn(),
      fitBounds: vi.fn(),
      easeTo: vi.fn(),
      flyTo: vi.fn(),
      setFilter: vi.fn(),
      setPaintProperty: vi.fn(),
      getCanvas: vi.fn(() => ({ style: { cursor: '' } })),
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
    expect(map.addSource).toHaveBeenCalledOnce()
    expect(map.addSource).toHaveBeenCalledWith('kindergarten-locations', expect.objectContaining({
      cluster: true,
      data: expect.objectContaining({ features: [beforeStyle.features[0]] }),
    }))
    const afterStyle = collection(facility('replacement'))
    rerender(<KindergartenMap collection={afterStyle} />)
    expect(map.getSource()?.setData).toHaveBeenLastCalledWith(expect.objectContaining({ features: afterStyle.features }))
    expect(mock.maps).toHaveLength(1)
    expect(map.addSource).toHaveBeenCalledOnce()
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
})
