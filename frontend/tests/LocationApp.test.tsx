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

beforeEach(() => { Element.prototype.scrollIntoView = vi.fn() })
afterEach(() => {
  vi.unstubAllGlobals()
  Reflect.deleteProperty(Element.prototype, 'scrollIntoView')
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
    const first = await screen.findByRole('button', { name: /Synthetic facility first/ })
    first.focus()
    await user.keyboard('{Enter}')
    expect(first).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByTestId('map-selection')).toHaveTextContent('first')
    expect(screen.getByRole('region', { name: 'Detalji: Synthetic facility first' })).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Map select second' }))
    expect(first).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByRole('button', { name: /Synthetic facility second/ })).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('region', { name: 'Detalji: Synthetic facility second' })).toBeVisible()
    expect(Element.prototype.scrollIntoView).toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: /Synthetic facility seat/ }))
    expect(screen.getByText(/Sjedište ustanove/)).toBeVisible()
    expect(screen.getByRole('region', { name: 'Detalji: Synthetic facility seat' })).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Map select seat' })).toBeNull()
    expect(screen.getByText('Dobna prikladnost nije provjerena u ovom prikazu.')).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Zatvori detalje' }))
    expect(screen.getByTestId('map-selection')).toBeEmptyDOMElement()
    expect(screen.queryByRole('region', { name: /Detalji:/ })).toBeNull()
  })

  it('applies city/name/provider together on submission, clears selection and distinguishes empty data from failure', async () => {
    const fetch = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => collection(facility('first')) })
      .mockResolvedValueOnce({ ok: true, json: async () => collection() })
      .mockResolvedValueOnce({ ok: false, status: 503 })
      .mockResolvedValueOnce({ ok: true, json: async () => collection(facility('recovered')) })
    vi.stubGlobal('fetch', fetch)
    const user = userEvent.setup()
    render(<App />)
    await user.click(await screen.findByRole('button', { name: /Synthetic facility first/ }))
    await user.clear(screen.getByLabelText('Grad ili općina'))
    await user.type(screen.getByLabelText('Grad ili općina'), ' Split ')
    await user.type(screen.getByLabelText('Naziv vrtića ili objekta'), ' Medo ')
    await user.selectOptions(screen.getByLabelText('Pružatelj'), 'private')
    expect(fetch).toHaveBeenCalledOnce()
    await user.click(screen.getByRole('button', { name: 'Prikaži rezultate' }))
    await screen.findByText(/Nema rezultata za odabrane filtre/)
    expect(screen.queryByRole('alert')).toBeNull()
    expect(screen.getByTestId('map-selection')).toBeEmptyDOMElement()
    const params = new URL(fetch.mock.calls[1][0], 'http://localhost').searchParams
    expect(Object.fromEntries(params)).toEqual({ city: 'Split', q: 'Medo', provider_kind: 'private' })
    await user.click(screen.getByRole('button', { name: 'Poništi' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Podatke nije moguće učitati')
    expect(screen.queryByText(/Nema rezultata za odabrane filtre/)).toBeNull()
    await user.click(screen.getByRole('button', { name: 'Pokušaj ponovno' }))
    await waitFor(() => expect(screen.getByRole('button', { name: /Synthetic facility recovered/ })).toBeVisible())
    expect(screen.queryByRole('alert')).toBeNull()
  })
})
