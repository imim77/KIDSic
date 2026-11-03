import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { LocationCollection } from '../src/shared/locations/types'
import App from '../src/views/welcome/Welcome'
import { collection, facility } from './fixtures'

vi.mock('../src/shared/map/KindergartenMap', () => ({
  KindergartenMap: ({ collection, selectedId, onSelect }: {
    collection: LocationCollection | null
    selectedId: string | null
    onSelect: (id: string) => void
  }) => <div aria-label="Test map">
    <output data-testid="map-selection">{selectedId}</output>
    {collection?.features.filter((feature) => feature.geometry).map((feature) => (
      <button key={feature.id} onClick={() => onSelect(feature.id)}>Map select {feature.id}</button>
    ))}
  </div>,
}))

beforeEach(() => { Element.prototype.scrollIntoView = vi.fn(); Element.prototype.scrollTo = vi.fn() })
afterEach(() => {
  vi.unstubAllGlobals()
  Reflect.deleteProperty(Element.prototype, 'scrollIntoView')
  Reflect.deleteProperty(Element.prototype, 'scrollTo')
})

describe('directory interactions', () => {
  it('shares keyboard/list and map selection, preserving details for a seat without inventing a pin', async () => {
    const seat = facility('seat', false)
    seat.properties.location_role = 'seat'
    seat.properties.location_id = null
    const payload = collection(facility('first'), facility('second'), seat)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => payload }))
    const user = userEvent.setup()
    render(<App />)
    const first = await screen.findByRole('button', { name: /Synthetic facility first.*Synthetic address/ })
    first.focus()
    await user.keyboard('{Enter}')
    expect(first).toHaveAttribute('aria-pressed', 'true')
    const details = screen.getByRole('button', { name: 'Detalji i izvori: Synthetic facility first' })
    await user.click(details)
    expect(screen.getByTestId('map-selection')).toHaveTextContent('first')
    expect(screen.getByRole('region', { name: 'Detalji: Synthetic facility first' })).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Map select second' }))
    expect(first).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByRole('button', { name: /Synthetic facility second.*Synthetic address/ })).toHaveAttribute('aria-pressed', 'true')
    await user.click(screen.getByRole('button', { name: 'Detalji i izvori: Synthetic facility second' }))
    expect(screen.getByRole('region', { name: 'Detalji: Synthetic facility second' })).toBeVisible()
    expect(Element.prototype.scrollIntoView).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: /Synthetic facility seat.*Synthetic address/ }))
    expect(screen.getByText(/Sjedište ustanove/)).toBeVisible()
    expect(screen.getByRole('region', { name: 'Detalji: Synthetic facility seat' })).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Map select seat' })).toBeNull()
    expect(screen.getByText('Dobna prikladnost nije provjerena u ovom prikazu.')).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Zatvori detalje' }))
    expect(screen.getByTestId('map-selection')).toHaveTextContent('seat')
    expect(screen.getByRole('button', { name: /Synthetic facility seat.*Synthetic address/ })).toHaveFocus()
    expect(screen.queryByRole('region', { name: /Detalji:/ })).toBeNull()
  })

  it('preserves cards, selection, open details and requests when expanding the same explorer', async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => collection(facility('first'), facility('second')) })
    vi.stubGlobal('fetch', fetch)
    const user = userEvent.setup()
    render(<App />)
    const title = await screen.findByRole('button', { name: /Synthetic facility second.*Synthetic address/ })
    await user.click(title)
    const details = screen.getByRole('button', { name: 'Detalji i izvori: Synthetic facility second' })
    await user.click(details)
    const track = screen.getByRole('list', { name: 'Vrtićki objekti' })
    track.scrollLeft = 240
    await user.click(screen.getByRole('button', { name: 'Prikaži preko cijelog ekrana' }))
    expect(screen.getByRole('dialog')).toBeVisible()
    expect(screen.getByRole('list', { name: 'Vrtićki objekti' })).toBe(track)
    expect(track.scrollLeft).toBe(240)
    expect(screen.getByRole('region', { name: 'Detalji: Synthetic facility second' })).toBeVisible()
    expect(title).toHaveAttribute('aria-pressed', 'true')
    expect(fetch).toHaveBeenCalledOnce()
    await user.click(screen.getByRole('button', { name: 'Vrati prikaz' }))
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(track.scrollLeft).toBe(240)
    expect(fetch).toHaveBeenCalledOnce()
  })

  it('provides an embedded map without website chrome, filters or a legend', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => collection(facility('first')) }))
    render(<App />)
    await screen.findByRole('button', { name: /Synthetic facility first.*Synthetic address/ })
    expect(screen.getByRole('main', { name: 'Karta vrtićkih objekata' })).toBeVisible()
    expect(screen.queryByRole('navigation', { hidden: true })).toBeNull()
    expect(screen.queryByRole('banner', { hidden: true })).toBeNull()
    expect(screen.queryByRole('contentinfo', { hidden: true })).toBeNull()
    expect(screen.queryByRole('heading', { level: 1, hidden: true })).toBeNull()
    expect(screen.queryByRole('link', { name: /KIDSic/, hidden: true })).toBeNull()
    expect(screen.queryByRole('form', { hidden: true })).toBeNull()
    expect(screen.queryByRole('button', { name: /Filtri|Zatvori filtre|Prikaži rezultate|Poništi|Legenda karte/, hidden: true })).toBeNull()
    expect(screen.queryByText('Legenda karte')).toBeNull()
    expect(screen.queryByText('Vrtići u susjedstvu.')).toBeNull()
    expect(screen.queryByText(/Broj objekata ne predstavlja broj slobodnih mjesta/)).toBeNull()
  })

  it('keeps a successful empty result distinct from a failed request', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => collection() }))
    render(<App />)
    expect(await screen.findByText('Nema dostupnih vrtićkih objekata.')).toBeVisible()
    expect(screen.queryByRole('alert')).toBeNull()
    expect(screen.queryByRole('list', { name: 'Vrtićki objekti' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Pokušaj ponovno' })).toBeNull()
    expect(screen.getByTestId('map-selection')).toBeEmptyDOMElement()
  })

  it('retries an API failure while preserving the default request contract', async () => {
    const fetch = vi.fn()
      .mockResolvedValueOnce({ ok: false, status: 503 })
      .mockResolvedValueOnce({ ok: true, json: async () => collection(facility('recovered')) })
    vi.stubGlobal('fetch', fetch)
    const user = userEvent.setup()
    render(<App />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Podatke nije moguće učitati')
    expect(screen.queryByText('Nema dostupnih vrtićkih objekata.')).toBeNull()
    await user.click(screen.getByRole('button', { name: 'Pokušaj ponovno' }))
    await waitFor(() => expect(screen.getByRole('button', { name: /Synthetic facility recovered.*Synthetic address/ })).toBeVisible())
    expect(screen.queryByRole('alert')).toBeNull()
    expect(fetch).toHaveBeenCalledTimes(2)
    for (const [url] of fetch.mock.calls) {
      expect(Object.fromEntries(new URL(url, 'http://localhost').searchParams)).toEqual({ city: 'Zagreb' })
    }
  })
})
