import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { McpLocationApp } from '../src/views/mcp/McpLocationApp'
import { collection, deferred, facility } from './fixtures'

const host = vi.hoisted(() => ({
  instance: null as unknown as {
    ontoolinput: (value: { arguments?: Record<string, unknown> }) => void
    ontoolresult: (value: unknown) => void
    onhostcontextchanged: () => void
    ontoolcancelled: () => void
  },
  call: vi.fn(), close: vi.fn(), display: vi.fn(),
  context: { availableDisplayModes: ['inline', 'fullscreen'], displayMode: 'inline' },
}))
vi.mock('@modelcontextprotocol/ext-apps', () => ({ App: class {
  constructor() { host.instance = this as unknown as typeof host.instance }
  connect = async () => {}
  close = host.close
  callServerTool = host.call
  requestDisplayMode = host.display
  getHostContext = () => host.context
} }))
vi.mock('../src/shared/map/KindergartenMap', () => ({ KindergartenMap: () => <div aria-label="Test map" /> }))

beforeEach(() => {
  Element.prototype.scrollTo = vi.fn()
  vi.stubGlobal('fetch', vi.fn())
  host.context.displayMode = 'inline'
  host.display.mockImplementation(async ({ mode }) => ({ mode }))
})
afterEach(() => { vi.unstubAllGlobals(); Reflect.deleteProperty(Element.prototype, 'scrollTo') })

async function result(city: string, id?: string) {
  const locations = collection(...(id ? [facility(id)] : []))
  await act(async () => host.instance.ontoolresult({ structuredContent: { city, metadata: locations.metadata }, _meta: { locations } }))
}

it('asks for a city and never fetches default Zagreb from the embedded UI', async () => {
  const { unmount } = render(<McpLocationApp />)
  expect(screen.getByText('U kojem gradu želiš prikaz vrtića?')).toBeVisible()
  await act(async () => host.instance.ontoolinput({ arguments: {} }))
  await act(async () => host.instance.ontoolresult({ isError: true }))
  expect(screen.getByText('U kojem gradu želiš prikaz vrtića?')).toBeVisible()
  expect(fetch).not.toHaveBeenCalled()
  expect(host.call).not.toHaveBeenCalled()
  unmount()
  expect(host.close).toHaveBeenCalled()
})

it('shows host results, clears cards on a new city, and renders a successful empty map', async () => {
  render(<McpLocationApp />)
  await result('Zagreb', 'first')
  expect(screen.getByRole('button', { name: /Synthetic facility first.*Synthetic address/ })).toBeVisible()
  await act(async () => host.instance.ontoolinput({ arguments: { city: 'Split' } }))
  expect(screen.queryByText('Synthetic facility first')).toBeNull()
  expect(screen.getByRole('main', { name: 'Vrtići: Split' })).toBeVisible()
  await result('Split')
  expect(screen.getByText('Nema dostupnih vrtićkih objekata.')).toBeVisible()
  expect(screen.queryByRole('alert')).toBeNull()
  expect(fetch).not.toHaveBeenCalled()
})

it('retries failures through the explicit city tool and ignores a stale retry after new input', async () => {
  const pending = deferred<unknown>()
  host.call.mockReturnValue(pending.promise)
  render(<McpLocationApp />)
  await act(async () => host.instance.ontoolinput({ arguments: { city: 'Split' } }))
  await act(async () => host.instance.ontoolresult({ isError: true }))
  await userEvent.click(screen.getByRole('button', { name: 'Pokušaj ponovno' }))
  expect(host.call).toHaveBeenCalledWith({ name: 'prikazi_vrtice', arguments: { city: 'Split' } })
  await act(async () => host.instance.ontoolinput({ arguments: { city: 'Rijeka' } }))
  await result('Rijeka', 'new')
  const stale = collection(facility('stale'))
  await act(async () => pending.resolve({ structuredContent: { city: 'Split', metadata: stale.metadata }, _meta: { locations: stale } }))
  expect(screen.queryByText('Synthetic facility stale')).toBeNull()
  expect(screen.getByRole('main', { name: 'Vrtići: Rijeka' })).toBeVisible()
})

it('rejects malformed results and requests host fullscreen without replacing cards', async () => {
  render(<McpLocationApp />)
  await act(async () => host.instance.ontoolresult({ structuredContent: { city: 'Zagreb', locations: {} } }))
  expect(screen.getByRole('alert')).toBeVisible()
  await result('Zagreb', 'first')
  const track = screen.getByRole('list', { name: 'Vrtićki objekti' })
  await waitFor(() => expect(screen.getByRole('button', { name: 'Prikaži preko cijelog ekrana' })).toBeVisible())
  await userEvent.click(screen.getByRole('button', { name: 'Prikaži preko cijelog ekrana' }))
  expect(host.display).toHaveBeenCalledWith({ mode: 'fullscreen' })
  expect(screen.getByRole('button', { name: 'Vrati prikaz' })).toBeVisible()
  expect(screen.getByRole('list', { name: 'Vrtićki objekti' })).toBe(track)
  host.context.displayMode = 'inline'
  await act(async () => host.instance.onhostcontextchanged())
  expect(screen.getByRole('button', { name: 'Prikaži preko cijelog ekrana' })).toBeVisible()
})
