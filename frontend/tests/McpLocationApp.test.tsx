import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { McpLocationApp } from '../src/views/mcp/McpLocationApp'
import { collection, deferred, facility } from './fixtures'
import { LocationToolResult } from '../src/shared/mcp/LocationToolResult'

const host = vi.hoisted(() => ({
  instance: null as unknown as {
    ontoolinput: (value: { arguments?: Record<string, unknown> }) => void
    ontoolresult: (value: unknown) => void
    onhostcontextchanged: () => void
    ontoolcancelled: () => void
  },
  call: vi.fn(), close: vi.fn(), display: vi.fn(), link: vi.fn(),
  context: { availableDisplayModes: ['inline', 'fullscreen'], displayMode: 'inline' },
}))
vi.mock('@modelcontextprotocol/ext-apps', () => ({ App: class {
  constructor() { host.instance = this as unknown as typeof host.instance }
  connect = async () => {}
  close = host.close
  callServerTool = host.call
  requestDisplayMode = host.display
  openLink = host.link
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

async function result(city: string, id?: string, name?: string) {
  const locations = collection(...(id ? [facility(id)] : []))
  if (locations.features[0]) locations.features[0].properties.website_url = 'https://example.invalid/kindergarten'
  await act(async () => host.instance.ontoolresult({ structuredContent: { city, name, metadata: locations.metadata }, _meta: { locations } }))
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

it('rejects malformed results, and a chosen card opens host fullscreen details', async () => {
  render(<McpLocationApp />)
  await act(async () => host.instance.ontoolresult({ structuredContent: { city: 'Zagreb', locations: {} } }))
  expect(screen.getByRole('alert')).toBeVisible()
  await result('Zagreb', 'first')
  await waitFor(() => expect(screen.getByRole('button', { name: 'Prikaži preko cijelog ekrana' })).toBeVisible())
  await userEvent.click(screen.getByRole('button', { name: /Synthetic facility first.*Synthetic address/ }))
  expect(host.display).toHaveBeenCalledWith({ mode: 'fullscreen' })
  expect(screen.getByRole('button', { name: 'Vrati prikaz' })).toBeVisible()
  expect(screen.getByRole('list', { name: 'Svi vrtići' })).toBeVisible()
  expect(screen.getByRole('region', { name: 'Detalji: Synthetic facility first' })).toBeVisible()
  expect(screen.getByText('Grad: Zagreb')).toBeVisible()
  // Sandboxed hosts block navigation, so outbound links go through the bridge.
  await userEvent.click(screen.getByRole('link', { name: 'Web stranica vrtića' }))
  expect(host.link).toHaveBeenCalledWith({ url: 'https://example.invalid/kindergarten' })
  expect(screen.queryByText('Izvori podataka')).toBeNull()
  expect(screen.queryByRole('link', { name: 'Otvori u Google kartama' })).toBeNull()
  host.context.displayMode = 'inline'
  await act(async () => host.instance.onhostcontextchanged())
  expect(screen.getByRole('button', { name: 'Prikaži preko cijelog ekrana' })).toBeVisible()
  expect(screen.getByRole('list', { name: 'Vrtićki objekti' })).toBeVisible()
  expect(screen.queryByRole('region', { name: /Detalji:/ })).toBeNull()
})

it('ignores decompression finishing after results for another city', async () => {
  const pending = deferred<{ city: string; locations: ReturnType<typeof collection> }>()
  vi.spyOn(LocationToolResult, 'fromResult').mockReturnValueOnce(pending.promise)
  render(<McpLocationApp />)
  await act(async () => { host.instance.ontoolresult({}) })
  await act(async () => host.instance.ontoolinput({ arguments: { city: 'Split' } }))
  await result('Split', 'latest')
  await act(async () => pending.resolve({ city: 'Zagreb', locations: collection(facility('old')) }))
  expect(screen.getByRole('main', { name: 'Vrtići: Split' })).toBeVisible()
  expect(screen.queryByText('Synthetic facility old')).toBeNull()
})

it('shows applied name and city, preserves both on retry and explains empty name matches', async () => {
  render(<McpLocationApp />)
  await act(async () => host.instance.ontoolinput({ arguments: { city: 'Rijeka', name: ' Zamet ' } }))
  expect(screen.getByText('Grad: Rijeka')).toBeVisible()
  expect(screen.getByText('Naziv: „Zamet”')).toBeVisible()
  await act(async () => host.instance.ontoolresult({ isError: true }))
  const locations = collection()
  host.call.mockResolvedValueOnce({ structuredContent: { city: 'Rijeka', name: 'Zamet', metadata: locations.metadata }, _meta: { locations } })
  await userEvent.click(screen.getByRole('button', { name: 'Pokušaj ponovno' }))
  expect(host.call).toHaveBeenLastCalledWith({ name: 'prikazi_vrtice', arguments: { city: 'Rijeka', name: 'Zamet' } })
  expect(screen.getByText(/Nema rezultata za grad Rijeka, naziv „Zamet”/)).toBeVisible()
  expect(screen.queryByRole('alert')).toBeNull()
  await result('Rijeka', 'bajka', 'Bajka')
  expect(screen.getByText('Naziv: „Bajka”')).toBeVisible()
  expect(screen.queryByText('Naziv: „Zamet”')).toBeNull()
  expect(fetch).not.toHaveBeenCalled()
})

it('keeps all three filters on retry and clears the type when the next search omits it', async () => {
  render(<McpLocationApp />)
  await act(async () => host.instance.ontoolinput({ arguments: { city: 'Rijeka', name: 'Bajka', provider_kind: 'private' } }))
  expect(screen.getByText('Vrsta: Privatni vrtić')).toBeVisible()
  await act(async () => host.instance.ontoolresult({ isError: true }))
  const locations = collection()
  host.call.mockResolvedValueOnce({ structuredContent: {
    city: 'Rijeka', name: 'Bajka', provider_kind: 'private', metadata: locations.metadata }, _meta: { locations } })
  await userEvent.click(screen.getByRole('button', { name: 'Pokušaj ponovno' }))
  expect(host.call).toHaveBeenLastCalledWith({ name: 'prikazi_vrtice', arguments: {
    city: 'Rijeka', name: 'Bajka', provider_kind: 'private' } })
  expect(screen.getByText(/Nema rezultata za grad Rijeka, naziv „Bajka”, vrstu „Privatni vrtić”/)).toBeVisible()
  await act(async () => host.instance.ontoolinput({ arguments: { city: 'Rijeka' } }))
  await result('Rijeka', 'any')
  expect(screen.getByText('Vrsta: Sve vrste')).toBeVisible()
  expect(screen.queryByText('Vrsta: Privatni vrtić')).toBeNull()
  expect(screen.queryByText('Naziv: „Bajka”')).toBeNull()
})
