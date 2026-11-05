import { StrictMode } from 'react'
import L from 'leaflet'
import { act, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { KindergartenMap } from '../src/shared/map/KindergartenMap'
import { collection, facility } from './fixtures'

let maps: L.Map[]
let observers: { callback: ResizeObserverCallback; disconnect: ReturnType<typeof vi.fn> }[]

beforeEach(() => {
  maps = []
  observers = []
  const createMap = L.map
  vi.spyOn(L, 'map').mockImplementation((...args) => {
    const map = createMap(...args)
    maps.push(map)
    return map
  })
  // jsdom supports SVG elements but does not expose createSVGRect for detection.
  L.Browser.svg = true
  vi.spyOn(HTMLElement.prototype, 'clientWidth', 'get').mockReturnValue(900)
  vi.spyOn(HTMLElement.prototype, 'clientHeight', 'get').mockReturnValue(700)
  vi.stubGlobal('ResizeObserver', class {
    disconnect = vi.fn()
    observe = vi.fn()
    unobserve = vi.fn()
    constructor(callback: ResizeObserverCallback) { observers.push({ callback, disconnect: this.disconnect }) }
  })
})

afterEach(() => vi.unstubAllGlobals())

async function ready() {
  await waitFor(() => expect(maps).toHaveLength(1))
  await waitFor(() => expect(screen.queryByText('Karta se učitava…')).not.toBeInTheDocument())
  return maps[0]
}

function layers<T extends L.Layer>(map: L.Map, kind: new (...args: never[]) => T): T[] {
  const found: T[] = []
  map.eachLayer((layer) => { if (layer instanceof kind) found.push(layer) })
  return found
}

function markers(map: L.Map) { return clusters(map).getLayers() as L.Marker[] }
function clusters(map: L.Map) { return layers(map, L.MarkerClusterGroup)[0] }

describe('Leaflet/OpenStreetMap lifecycle and data', () => {
  it('loads OpenStreetMap without credentials and keeps attribution visible', async () => {
    render(<KindergartenMap collection={collection(facility('public'))} />)
    const map = await ready()
    const tile = layers(map, L.TileLayer)[0]
    expect(tile.getTileUrl({ x: 1, y: 2, z: 3 } as L.Coords)).toContain('tile.openstreetmap.org/')
    expect(tile.options.maxZoom).toBe(19)
    expect(screen.getByRole('link', { name: 'OpenStreetMap' })).toHaveAttribute('href', 'https://www.openstreetmap.org/copyright')
    expect(screen.getByRole('list', { name: 'Vrste pružatelja na karti' })).toBeVisible()
  })

  it('keeps only located results and replaces cluster data without reallocating the map', async () => {
    const { rerender, unmount } = render(<KindergartenMap collection={collection(facility('first'), facility('unlocated', false))} />)
    const map = await ready()
    const group = clusters(map)
    expect(group.getLayers()).toHaveLength(1)
    expect((group.getLayers()[0] as L.Marker).getLatLng()).toEqual(L.latLng(45.81, 15.98))
    rerender(<KindergartenMap collection={collection(facility('replacement'))} />)
    expect(group.getLayers()).toHaveLength(1)
    expect((group.getLayers()[0] as L.Marker).options.alt).toBe('replacement')
    expect(maps).toHaveLength(1)
    const remove = vi.spyOn(map, 'remove')
    unmount()
    expect(group.getLayers()).toHaveLength(0)
    expect(remove).toHaveBeenCalledOnce()
    expect(map.listens('click')).toBe(false)
  })

  it('preserves provider colours for both normal and selected markers', async () => {
    const item = facility('private')
    item.properties.provider_kind = 'private'
    const { container } = render(<KindergartenMap collection={collection(item)} selectedId="private" />)
    await ready()
    const normal = container.querySelector<HTMLElement>('.location-pin:not(.location-pin-selected) span')!
    const selected = container.querySelector<HTMLElement>('.location-pin-selected span')!
    expect(normal.style.backgroundColor).toBe('rgb(200, 140, 253)')
    expect(selected.style.backgroundColor).toBe(normal.style.backgroundColor)
    expect(container.querySelector<HTMLElement>('.location-pin-selected')!.style.width).toBe('26px')
  })

  it('forwards canonical selection to the latest callback and suppresses it while picking', async () => {
    const original = vi.fn(), latest = vi.fn(), onPick = vi.fn()
    const item = facility('rendered')
    item.properties.location_id = 'canonical'
    const payload = collection(item)
    const { rerender } = render(<KindergartenMap collection={payload} onSelect={original} />)
    const map = await ready()
    rerender(<KindergartenMap collection={payload} onSelect={latest} />)
    act(() => markers(map)[0].fire('click', {}, true))
    expect(latest).toHaveBeenCalledWith('canonical')
    expect(original).not.toHaveBeenCalled()
    rerender(<KindergartenMap collection={payload} onSelect={latest} picking onPick={onPick} />)
    latest.mockClear()
    act(() => {
      markers(map)[0].fire('click', {}, true)
      map.fire('click', { latlng: L.latLng(45.8, 16) })
    })
    expect(latest).not.toHaveBeenCalled()
    expect(onPick).toHaveBeenCalledWith([16, 45.8])
    expect(map.getContainer().style.cursor).toBe('crosshair')
  })

  it('draws the radius in metres and clears it when the filter is removed', async () => {
    const onPick = vi.fn()
    const { rerender } = render(<KindergartenMap onPick={onPick} nearby={{ near: [15.98, 45.81], radius_m: 1000 }} />)
    const map = await ready()
    const area = layers(map, L.Circle)[0]
    expect(area.getRadius()).toBe(1000)
    expect(area.getLatLng()).toEqual(L.latLng(45.81, 15.98))
    act(() => map.fire('click', { latlng: L.latLng(45.8, 16) }))
    expect(onPick).not.toHaveBeenCalled()
    rerender(<KindergartenMap onPick={onPick} />)
    expect(layers(map, L.Circle)).toHaveLength(0)
  })

  it('clears selection for unlocated results and resizes without recreating the map', async () => {
    const payload = collection(facility('mapped'), facility('unlocated', false))
    const { rerender, container } = render(<KindergartenMap collection={payload} selectedId="mapped" />)
    const map = await ready()
    expect(map.getZoom()).toBe(15)
    expect(container.querySelector('.location-pin-selected')).toBeInTheDocument()
    const resize = vi.spyOn(map, 'invalidateSize')
    act(() => observers[0].callback([], {} as ResizeObserver))
    expect(resize).toHaveBeenCalledWith({ pan: false })
    rerender(<KindergartenMap collection={payload} selectedId="unlocated" />)
    expect(container.querySelector('.location-pin-selected')).not.toBeInTheDocument()
    expect(maps).toHaveLength(1)
  })

  it('shows a tile failure and recovers after a successful tile load', async () => {
    render(<KindergartenMap />)
    const map = await ready()
    const tile = layers(map, L.TileLayer)[0]
    act(() => tile.fire('tileerror'))
    expect(screen.getByRole('status')).toHaveTextContent('Podlogu karte nije moguće učitati')
    act(() => tile.fire('tileload'))
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('leaves one live map in StrictMode and releases observers on unmount', async () => {
    const { unmount } = render(<StrictMode><KindergartenMap /></StrictMode>)
    const map = await ready()
    const remove = vi.spyOn(map, 'remove')
    unmount()
    expect(remove).toHaveBeenCalledOnce()
    expect(observers[0].disconnect).toHaveBeenCalledOnce()
  })

  it('does not allocate a map after unmounting before initialization', async () => {
    const { unmount } = render(<KindergartenMap />)
    unmount()
    await act(async () => { await Promise.resolve() })
    expect(maps).toHaveLength(0)
  })

  it('removes a partially initialized map once if observing the panel fails', async () => {
    vi.stubGlobal('ResizeObserver', class { constructor() { throw new Error('observer failed') } })
    const remove = vi.spyOn(L.Map.prototype, 'remove')
    const { unmount } = render(<KindergartenMap />)
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('nije moguće pokrenuti'))
    expect(remove).toHaveBeenCalledOnce()
    unmount()
    expect(remove).toHaveBeenCalledOnce()
  })
})

it('draws the selected route, fits all ranked pins and endpoints, and replaces shapes on the same map', async () => {
  const payload = collection(facility('first'), facility('second'))
  payload.features[0].geometry = { type: 'Point', coordinates: [14.42, 45.335] }
  payload.features[1].geometry = { type: 'Point', coordinates: [14.43, 45.34] }
  const route = {
    home: [14.410, 45.338] as [number, number], work: [14.4422, 45.3271] as [number, number],
    legs: [{ mode: 'BUS', geometry: 'oavsGom}vAvQo}@jp@wiC' }, { mode: 'WALK', geometry: null }],
  }
  const { rerender, unmount } = render(<KindergartenMap collection={payload} selectedId="first" route={route} />)
  const map = await ready()
  const paths = () => layers(map, L.Polyline)
  expect(paths()).toHaveLength(1)
  expect(paths()[0].getLatLngs()).toEqual([L.latLng(45.338, 14.410), L.latLng(45.335, 14.42), L.latLng(45.3271, 14.4422)])
  expect(paths()[0].options.color).toBe('#376fbe')
  expect(screen.getByText('Dom')).toBeInTheDocument()
  expect(screen.getByText('Posao')).toBeInTheDocument()
  for (const [lng, lat] of [route.home, route.work, ...payload.features.map(f => f.geometry!.coordinates)]) {
    expect(map.getBounds().contains([lat, lng])).toBe(true)
  }
  const first = paths()[0]
  rerender(<KindergartenMap collection={payload} selectedId="second" route={{ ...route,
    legs: [{ mode: 'WALK', geometry: 'oavsGom}vAoK_|BroAgkA' }, { mode: 'BUS', geometry: '_' }],
  }} />)
  expect(paths()).toHaveLength(1)
  expect(map.hasLayer(first)).toBe(false)
  expect(paths()[0].options.dashArray).toBe('6 8')
  expect(maps).toHaveLength(1)
  rerender(<KindergartenMap collection={payload} />)
  expect(paths()).toHaveLength(0)
  expect(screen.queryByText('Dom')).not.toBeInTheDocument()
  unmount()
  expect(map.listens('click')).toBe(false)
})
