import type { ReactNode } from 'react'
import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { McpLocationApp } from '@/mvvm/features/Locations/screens/McpLocation/McpLocationApp'
import { collection, deferred, facility } from '@test-support/fixtures'
import { LocationToolResult } from '@/mvvm/features/Locations/utils/LocationToolResult'
import type { LocationCollection } from '@/mvvm/features/Locations/types'

const host = vi.hoisted(() => ({
  instance: null as unknown as {
    ontoolinput: (value: { arguments?: Record<string, unknown> }) => void
    ontoolresult: (value: unknown) => void
    onhostcontextchanged: () => void
    ontoolcancelled: () => void
  },
  call: vi.fn(), close: vi.fn(), display: vi.fn(), link: vi.fn(),
  model: vi.fn<(message: { content: { type: string; text: string }[] }) => Promise<object>>().mockResolvedValue({}),
  context: { availableDisplayModes: ['inline', 'fullscreen'], displayMode: 'inline' },
}))
vi.mock('@modelcontextprotocol/ext-apps', () => ({ App: class {
  constructor() { host.instance = this as unknown as typeof host.instance }
  connect = async () => {}
  close = host.close
  callServerTool = host.call
  requestDisplayMode = host.display
  openLink = host.link
  updateModelContext = host.model
  getHostContext = () => host.context
} }))
vi.mock('@/mvvm/features/Locations/components/map/KindergartenMap', () => ({
  KindergartenMap: ({ overlay, picking, onPick, collection, onSelect }: {
    overlay?: (mapReady: boolean) => ReactNode
    picking?: boolean
    onPick?: (near: [number, number]) => void
    collection?: LocationCollection | null
    onSelect?: (id: string) => void
  }) => <div aria-label="Test map">
    {overlay?.(true)}
    {collection?.features.filter(feature => feature.geometry).map(feature =>
      <button key={feature.id} onClick={() => onSelect?.(feature.id)}>Oznaka {feature.id}</button>)}
    {picking && <button onClick={() => onPick?.([16, 45.8])}>Map pick</button>}
  </div>,
}))

beforeEach(() => {
  host.call.mockReset()
  host.model.mockReset().mockResolvedValue({})
  vi.stubGlobal('fetch', vi.fn())
  host.context.displayMode = 'inline'
  host.display.mockImplementation(async ({ mode }) => ({ mode }))
})

async function result(city: string, id?: string, name?: string) {
  const locations = collection(...(id ? [facility(id)] : []))
  if (locations.features[0]) locations.features[0].properties.website_url = 'https://example.invalid/kindergarten'
  await act(async () => host.instance.ontoolresult({ structuredContent: { city, name, metadata: locations.metadata }, _meta: { locations } }))
}

async function expectRetry(criteria: Record<string, unknown>) {
  await act(async () => host.instance.ontoolresult({ isError: true }))
  const locations = collection()
  host.call.mockResolvedValueOnce({ structuredContent: { ...criteria, metadata: locations.metadata }, _meta: { locations } })
  await userEvent.click(screen.getByRole('button', { name: 'Pokušaj ponovno' }))
  expect(host.call).toHaveBeenLastCalledWith({ name: 'prikazi_vrtice', arguments: criteria })
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

it('preserves city and name on retry and explains empty name matches', async () => {
  render(<McpLocationApp />)
  await act(async () => host.instance.ontoolinput({ arguments: { city: 'Rijeka', name: ' Zamet ' } }))
  await act(async () => host.instance.ontoolresult({ isError: true }))
  const locations = collection()
  host.call.mockResolvedValueOnce({ structuredContent: { city: 'Rijeka', name: 'Zamet', metadata: locations.metadata }, _meta: { locations } })
  await userEvent.click(screen.getByRole('button', { name: 'Pokušaj ponovno' }))
  expect(host.call).toHaveBeenLastCalledWith({ name: 'prikazi_vrtice', arguments: { city: 'Rijeka', name: 'Zamet' } })
  expect(screen.getByText(/Nema rezultata za grad Rijeka, naziv „Zamet”/)).toBeVisible()
  expect(screen.queryByRole('alert')).toBeNull()
  await result('Rijeka', 'bajka', 'Bajka')
  await expectRetry({ city: 'Rijeka', name: 'Bajka' })
  expect(fetch).not.toHaveBeenCalled()
})

it('keeps all three filters on retry and clears the type when the next search omits it', async () => {
  render(<McpLocationApp />)
  await act(async () => host.instance.ontoolinput({ arguments: { city: 'Rijeka', name: 'Bajka', provider_kind: 'private' } }))
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
  await expectRetry({ city: 'Rijeka' })
})

it('preserves the area with all filters on retry, replaces it on a follow-up and clears it when omitted', async () => {
  render(<McpLocationApp />)
  const criteria = { city: 'Varaždin', name: 'Bajka', provider_kind: 'private', area: 'Banfica' }
  await act(async () => host.instance.ontoolinput({ arguments: criteria }))
  await act(async () => host.instance.ontoolresult({ isError: true }))
  const locations = collection()
  host.call.mockResolvedValueOnce({ structuredContent: { ...criteria, metadata: locations.metadata }, _meta: { locations } })
  await userEvent.click(screen.getByRole('button', { name: 'Pokušaj ponovno' }))
  expect(host.call).toHaveBeenLastCalledWith({ name: 'prikazi_vrtice', arguments: criteria })
  expect(screen.getByText(/područje „Banfica”.*to ne znači da ondje nema vrtića/)).toBeVisible()
  await act(async () => host.instance.ontoolinput({ arguments: { ...criteria, area: 'Centar' } }))
  await expectRetry({ ...criteria, area: 'Centar' })
  await act(async () => host.instance.ontoolinput({ arguments: { city: 'Varaždin' } }))
  await result('Varaždin', 'all')
  await expectRetry({ city: 'Varaždin' })
})



function radiusResult(city: string, nearby: { near: [number, number]; radius_m: number } | null, ...ids: string[]) {
  const locations = collection(...ids.map((id) => facility(id)))
  if (nearby) {
    locations.metadata.scope = 'radius'
    locations.features.forEach((feature) => { feature.properties.distance_m = 120 })
  }
  return { structuredContent: { city, provider_kind: 'municipal', near: nearby?.near ?? null, radius_m: nearby?.radius_m ?? null,
    metadata: locations.metadata }, _meta: { locations } }
}

it('searches around a map point with the retained criteria and tells the model about the new point', async () => {
  const user = userEvent.setup()
  render(<McpLocationApp />)
  await act(async () => host.instance.ontoolinput({ arguments: { city: 'Zagreb', provider_kind: 'municipal' } }))
  await act(async () => host.instance.ontoolresult(radiusResult('Zagreb', null, 'city')))
  host.call.mockResolvedValueOnce(radiusResult('Zagreb', { near: [16, 45.8], radius_m: 1000 }, 'near'))
  await user.click(screen.getByRole('button', { name: 'U blizini' }))
  await user.click(screen.getByRole('button', { name: 'Odaberi na karti' }))
  await user.click(screen.getByRole('button', { name: 'Map pick' }))
  expect(host.call).toHaveBeenLastCalledWith({ name: 'prikazi_vrtice', arguments: {
    city: 'Zagreb', provider_kind: 'municipal', near: [16, 45.8], radius_m: 1000 } })
  expect(await screen.findByRole('button', { name: /Synthetic facility near.*120 m zračno/ })).toBeVisible()
  expect(screen.getByText('Gradski vrtić · do 1 km od točke · najbliži prvi')).toBeVisible()
  expect(host.model).toHaveBeenLastCalledWith({ content: [{ type: 'text', text: expect.stringContaining('[16, 45.8] i zračni radijus 1000 m') }] })
  host.call.mockResolvedValueOnce(radiusResult('Zagreb', null, 'city'))
  await user.click(screen.getByRole('button', { name: 'Ukloni' }))
  expect(host.call).toHaveBeenLastCalledWith({ name: 'prikazi_vrtice', arguments: { city: 'Zagreb', provider_kind: 'municipal' } })
  await screen.findByRole('button', { name: /^Synthetic facility city/ })
  expect(host.model).toHaveBeenLastCalledWith({ content: [{ type: 'text', text: expect.stringContaining('uklonio točku') }] })
})

it('shows a radius the model chose and keeps it on retry', async () => {
  const user = userEvent.setup()
  render(<McpLocationApp />)
  const nearby = { near: [15.97, 45.81] as [number, number], radius_m: 1500 }
  await act(async () => host.instance.ontoolinput({ arguments: { city: 'Zagreb', provider_kind: 'municipal', ...nearby } }))
  await act(async () => host.instance.ontoolresult(radiusResult('Zagreb', nearby)))
  await user.click(screen.getByRole('button', { name: 'U blizini 1,5 km' }))
  expect(screen.getByRole('combobox', { name: 'Radijus' })).toHaveValue('1500')
  expect(screen.getByText(/zračno do 1,5 km od odabrane točke/)).toBeVisible()
  host.model.mockClear()
  await expectRetry({ city: 'Zagreb', provider_kind: 'municipal', near: [15.97, 45.81], radius_m: 1500 })
  expect(host.model).not.toHaveBeenCalled()
})

it('shares the exact object from map, card and list selections, and clears a closed selection', async () => {
  const user = userEvent.setup()
  render(<McpLocationApp />)
  const locations = collection(facility('first'), facility('second'))
  await act(async () => host.instance.ontoolresult({ structuredContent: { city: 'Zagreb', metadata: locations.metadata }, _meta: { locations } }))
  expect(host.model).not.toHaveBeenCalled()
  const expectSelected = (index: number) => {
    const feature = locations.features[index]
    const text = host.model.mock.calls.at(-1)?.[0].content[0].text
    expect(text).toContain(JSON.stringify({ feature_id: feature.id,
      kindergarten_id: feature.properties.kindergarten_id, city: 'Zagreb',
      name: feature.properties.name, location_name: feature.properties.location_name,
      address: feature.properties.address, location_role: 'facility' }))
    expect(text).toContain('dohvati_kontekst_vrtica')
  }
  await user.click(screen.getByRole('button', { name: 'Oznaka first' }))
  expectSelected(0)
  await user.click(screen.getByRole('button', { name: /Synthetic facility second.*Synthetic address/ }))
  expectSelected(1)
  await user.click(screen.getByRole('button', { name: /Gradski vrtić\s*Synthetic facility first/ }))
  expectSelected(0)
  await user.click(screen.getByRole('button', { name: 'Zatvori detalje' }))
  expect(host.model).toHaveBeenLastCalledWith({ content: [{ type: 'text', text: expect.stringContaining('Odabir vrtića je uklonjen') }] })
  expect(host.call).not.toHaveBeenCalled()
})

it.each(['input', 'result', 'cancel'])('clears shared selection on new tool %s', async event => {
  render(<McpLocationApp />)
  await result('Zagreb', 'old')
  await userEvent.click(screen.getByRole('button', { name: 'Oznaka old' }))
  host.model.mockClear()
  await act(async () => {
    if (event === 'input') host.instance.ontoolinput({ arguments: { city: 'Rijeka' } })
    else if (event === 'cancel') host.instance.ontoolcancelled()
    else host.instance.ontoolresult({ isError: true })
  })
  expect(host.model).toHaveBeenCalledExactlyOnceWith({ content: [{ type: 'text', text: expect.stringContaining('Prethodni objekt više nije odabran') }] })
})

it('shares an unmapped seat without inventing an address and keeps selection when context delivery fails', async () => {
  render(<McpLocationApp />)
  const seat = facility('seat:synthetic', false)
  Object.assign(seat.properties, { location_id: null, location_role: 'seat', address: null })
  const locations = collection(seat)
  await act(async () => host.instance.ontoolresult({ structuredContent: { city: 'Zagreb', metadata: locations.metadata }, _meta: { locations } }))
  host.model.mockRejectedValueOnce(new Error('Host unavailable'))
  await userEvent.click(screen.getByRole('button', { name: /^Synthetic facility seat:synthetic/ }))
  expect(host.model).toHaveBeenLastCalledWith({ content: [{ type: 'text', text: expect.stringContaining('"feature_id":"seat:synthetic"') }] })
  expect(host.model.mock.calls.at(-1)?.[0].content[0].text).toContain('"address":null,"location_role":"seat"')
  expect(screen.getByRole('region', { name: 'Detalji: Synthetic facility seat:synthetic' })).toBeVisible()
})

