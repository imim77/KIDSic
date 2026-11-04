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
  it('expands a chosen card into list, details and map that share one selection', async () => {
    const seat = facility('seat', false)
    seat.properties.location_role = 'seat'
    seat.properties.location_id = null
    seat.properties.provider_kind = 'unknown'
    const payload = collection(facility('first'), facility('second'), seat)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => payload }))
    const user = userEvent.setup()
    render(<App />)
    const first = await screen.findByRole('button', { name: /Synthetic facility first.*Synthetic address/ })
    first.focus()
    await user.keyboard('{Enter}')
    expect(screen.getByRole('dialog')).toBeVisible()
    expect(screen.queryByRole('list', { name: 'Vrtićki objekti' })).toBeNull()
    expect(screen.getByRole('list', { name: 'Svi vrtići' })).toBeVisible()
    expect(screen.getByRole('region', { name: 'Detalji: Synthetic facility first' })).toHaveFocus()
    expect(screen.getByTestId('map-selection')).toHaveTextContent('first')
    await user.click(screen.getByRole('button', { name: 'Map select second' }))
    expect(screen.getByRole('region', { name: 'Detalji: Synthetic facility second' })).toBeVisible()
    expect(screen.getByRole('button', { name: /Synthetic facility second.*Synthetic address/ })).toHaveAttribute('aria-pressed', 'true')
    expect(Element.prototype.scrollIntoView).not.toHaveBeenCalled()
    const seatRow = screen.getByRole('button', { name: /Synthetic facility seat.*Synthetic address/ })
    await user.click(seatRow)
    expect(screen.queryByRole('button', { name: 'Map select seat' })).toBeNull()
    expect(screen.getByTestId('map-selection')).toHaveTextContent('seat')
    expect(screen.getByText(/adresa sjedišta ustanove/)).toBeVisible()
    expect(screen.getAllByText('Vrsta nije navedena').length).toBeGreaterThan(0)
    await user.click(screen.getByRole('button', { name: 'Zatvori detalje' }))
    expect(screen.queryByRole('region', { name: /Detalji:/ })).toBeNull()
    expect(screen.getByTestId('map-selection')).toBeEmptyDOMElement()
    expect(seatRow).toHaveFocus()
  })

  it('opens details for an earlier map selection and restores the card deck on exit', async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => collection(facility('first'), facility('second')) })
    vi.stubGlobal('fetch', fetch)
    const user = userEvent.setup()
    render(<App />)
    await screen.findByRole('list', { name: 'Vrtićki objekti' })
    await user.click(screen.getByRole('button', { name: 'Map select second' }))
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(screen.queryByRole('region', { name: /Detalji:/ })).toBeNull()
    await user.click(screen.getByRole('button', { name: 'Prikaži preko cijelog ekrana' }))
    expect(screen.getByRole('dialog')).toBeVisible()
    expect(screen.getByRole('region', { name: 'Detalji: Synthetic facility second' })).toBeVisible()
    expect(fetch).toHaveBeenCalledOnce()
    await user.click(screen.getByRole('button', { name: 'Vrati prikaz' }))
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(screen.queryByRole('region', { name: /Detalji:/ })).toBeNull()
    expect(screen.getByRole('button', { name: /Synthetic facility second.*Synthetic address/ })).toHaveAttribute('aria-pressed', 'true')
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
