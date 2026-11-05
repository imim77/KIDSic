import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'
import type { LocationCollection, LocationFeature, Nearby } from '../src/shared/locations/types'
import App from '../src/views/welcome/Welcome'
import { collection, facility, historicalEvidence } from './fixtures'

vi.mock('../src/shared/map/KindergartenMap', () => ({
  KindergartenMap: ({ collection, selectedId, onSelect, picking, onPick, nearby, overlay }: {
    collection: LocationCollection | null
    selectedId: string | null
    onSelect: (id: string) => void
    picking?: boolean
    onPick?: (near: [number, number]) => void
    nearby?: Nearby | null
    overlay?: (mapReady: boolean) => ReactNode
  }) => <div aria-label="Test map">
    {overlay?.(true)}
    <output data-testid="map-selection">{selectedId}</output>
    <output data-testid="map-nearby">{nearby ? `${nearby.near.join(',')}@${nearby.radius_m}` : ''}</output>
    {picking && <button onClick={() => onPick?.([16, 45.8])}>Map pick</button>}
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

  it('searches around a point chosen on the map and refetches when the radius changes', async () => {
    const near = facility('near')
    near.properties.distance_m = 1112
    const radiusResult = (...features: LocationFeature[]) => {
      const payload = collection(...features)
      payload.metadata.scope = 'radius'
      return payload
    }
    const fetch = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => collection(facility('city')) })
      .mockResolvedValueOnce({ ok: true, json: async () => radiusResult(near) })
      .mockResolvedValueOnce({ ok: true, json: async () => radiusResult() })
      .mockResolvedValueOnce({ ok: true, json: async () => collection(facility('city')) })
    vi.stubGlobal('fetch', fetch)
    const user = userEvent.setup()
    render(<App />)
    await screen.findByRole('button', { name: /^Synthetic facility city/ })
    expect(screen.queryByRole('button', { name: 'Odaberi na karti' })).toBeNull()
    await user.click(screen.getByRole('button', { name: 'U blizini' }))
    expect(screen.getByRole('button', { name: 'U blizini' })).toHaveAttribute('aria-expanded', 'true')
    await user.click(screen.getByRole('button', { name: 'Odaberi na karti' }))
    expect(screen.getByRole('button', { name: 'Kliknite na kartu' })).toHaveAttribute('aria-pressed', 'true')
    await user.click(screen.getByRole('button', { name: 'Map pick' }))
    expect(screen.getByTestId('map-nearby')).toHaveTextContent('16,45.8@1000')
    expect(await screen.findByRole('button', { name: /Synthetic facility near.*1,1 km zračno/ })).toBeVisible()
    expect(screen.getByText('1 rezultat · do 1 km od točke · najbliži prvi')).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Map pick' })).toBeNull()
    expect(Object.fromEntries(new URL(fetch.mock.calls[1][0], 'http://localhost').searchParams))
      .toEqual({ city: 'Zagreb', near: '16,45.8', radius_m: '1000' })
    await user.selectOptions(screen.getByRole('combobox', { name: 'Radijus' }), '500 m')
    expect(await screen.findByText(/Nema objekata s potvrđenim koordinatama unutar 500 m/)).toBeVisible()
    expect(new URL(fetch.mock.calls[2][0], 'http://localhost').searchParams.get('radius_m')).toBe('500')
    await user.click(screen.getByRole('button', { name: 'Ukloni' }))
    await screen.findByRole('button', { name: /^Synthetic facility city/ })
    expect(screen.getByText('1 rezultat · abecedno')).toBeVisible()
    expect(screen.getByTestId('map-nearby')).toBeEmptyDOMElement()
    expect(Object.fromEntries(new URL(fetch.mock.calls[3][0], 'http://localhost').searchParams)).toEqual({ city: 'Zagreb' })
  })

  it('compares up to three options side by side and marks unknown data as unconfirmed', async () => {
    const options = ['a', 'b', 'c', 'd'].map((id) => facility(id))
    options[0].properties.phone = '01 111 222'
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => collection(...options) }))
    const user = userEvent.setup()
    render(<App />)
    await screen.findByRole('button', { name: /^Synthetic facility a/ })
    expect(screen.queryByRole('region', { name: 'Usporedba' })).toBeNull()
    for (const id of ['a', 'b', 'c']) await user.click(screen.getByRole('button', { name: `Dodaj u usporedbu: Synthetic facility ${id}` }))
    expect(screen.getByRole('region', { name: 'Usporedba' })).toHaveTextContent('Usporedba 3/3')
    expect(screen.getByRole('button', { name: 'Dodaj u usporedbu: Synthetic facility d' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Usporedi' }))
    expect(screen.getByRole('button', { name: 'Zatvori usporedbu' })).toHaveFocus()
    const cards = () => within(screen.getByRole('list', { name: 'Vrtići u usporedbi' })).getAllByRole('listitem', { name: /^Synthetic facility/ })
    expect(cards().map((card) => card.getAttribute('aria-label')))
      .toEqual(['Synthetic facility a', 'Synthetic facility b', 'Synthetic facility c'])
    for (const card of cards()) expect(within(card).getByText('Gradski vrtić')).toHaveClass('comparison-kind')
    expect(within(cards()[0]).getByText('Nazovi vrtić: 01 111 222')).toBeVisible()
    expect(within(cards()[1]).getAllByText('Nije potvrđeno').length).toBeGreaterThan(0)
    await user.click(within(cards()[2]).getByRole('button', { name: 'Ukloni iz usporedbe: Synthetic facility c' }))
    expect(cards()).toHaveLength(2)
    await user.click(within(cards()[1]).getByRole('button', { name: 'Ukloni iz usporedbe: Synthetic facility b' }))
    expect(screen.queryByRole('list', { name: 'Vrtići u usporedbi' })).toBeNull()
    expect(screen.getByRole('region', { name: 'Usporedba' })).toHaveTextContent('Usporedba 1/3')
    await user.click(screen.getByRole('button', { name: 'Očisti usporedbu' }))
    expect(screen.queryByRole('region', { name: 'Usporedba' })).toBeNull()
  })

  it('filters by published vacancies and shows the snapshot date on the control', async () => {
    const free = facility('free')
    free.properties.historical_data = [historicalEvidence({ vacancies: [{ age_label: null, program: null, free_places: 2 }] })]
    const fetch = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => collection(free, facility('none')) })
      .mockResolvedValueOnce({ ok: true, json: async () => collection(free) })
    vi.stubGlobal('fetch', fetch)
    const user = userEvent.setup()
    render(<App />)
    await screen.findByRole('button', { name: /^Synthetic facility none/ })
    const toggle = screen.getByRole('button', { name: /^Slobodna mjesta stanje 01\. 01\. 2025\./ })
    expect(toggle).toHaveAttribute('aria-pressed', 'false')
    await user.click(toggle)
    await screen.findByText('1 rezultat · s objavljenim slobodnim mjestima · abecedno')
    expect(new URL(fetch.mock.calls[1][0], 'http://localhost').searchParams.get('has_vacancies')).toBe('true')
    expect(screen.getByRole('button', { name: /^Slobodna mjesta/ })).toHaveAttribute('aria-pressed', 'true')
  })

  it('filters by a recorded district and says which objects the filter cannot include', async () => {
    const inDistrict = (id: string, district: string) => {
      const feature = facility(id)
      feature.properties.district = district
      return feature
    }
    const city = collection(inDistrict('trnje', 'Trnje'), inDistrict('dubrava', 'Donja Dubrava'), facility('unknown'))
    const fetch = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => city })
      .mockResolvedValueOnce({ ok: true, json: async () => collection(inDistrict('trnje', 'Trnje')) })
      .mockResolvedValueOnce({ ok: true, json: async () => city })
    vi.stubGlobal('fetch', fetch)
    const user = userEvent.setup()
    render(<App />)
    await screen.findByRole('button', { name: /^Synthetic facility unknown/ })
    const picker = screen.getByRole('combobox', { name: 'Četvrt' })
    expect([...picker.querySelectorAll('option')].map((option) => option.textContent))
      .toEqual(['Sve četvrti', 'Donja Dubrava', 'Trnje'])
    await user.selectOptions(picker, 'Trnje')
    await screen.findByText('1 rezultat · područje „Trnje” · abecedno')
    expect(screen.queryByRole('button', { name: /^Synthetic facility unknown/ })).toBeNull()
    expect(new URL(fetch.mock.calls[1][0], 'http://localhost').searchParams.get('area')).toBe('Trnje')
    expect(screen.getByText('Nisu uključeni objekti bez potvrđene četvrti (1).')).toBeVisible()
    expect(screen.getByRole('combobox', { name: 'Četvrt' }).querySelectorAll('option')).toHaveLength(3)
    await user.selectOptions(screen.getByRole('combobox', { name: 'Četvrt' }), 'Sve četvrti')
    await screen.findByRole('button', { name: /^Synthetic facility unknown/ })
    expect(new URL(fetch.mock.calls[2][0], 'http://localhost').searchParams.has('area')).toBe(false)
    expect(screen.queryByText(/Nisu uključeni objekti/)).toBeNull()
  })

  it('uses the device location and explains a denied permission without searching', async () => {
    const fetch = vi.fn().mockImplementation(async (url: string) => {
      const payload = collection(facility('result'))
      if (url.includes('near=')) payload.metadata.scope = 'radius'
      return { ok: true, json: async () => payload }
    })
    vi.stubGlobal('fetch', fetch)
    const getCurrentPosition = vi.fn()
      .mockImplementationOnce((_: PositionCallback, failure: PositionErrorCallback) => failure({ code: 1, PERMISSION_DENIED: 1 } as GeolocationPositionError))
      .mockImplementationOnce((success: PositionCallback) => success({ coords: { longitude: 15.97, latitude: 45.8 } } as GeolocationPosition))
    vi.stubGlobal('navigator', { ...navigator, geolocation: { getCurrentPosition } })
    const user = userEvent.setup()
    render(<App />)
    await screen.findByRole('button', { name: /^Synthetic facility result/ })
    await user.click(screen.getByRole('button', { name: 'U blizini' }))
    await user.click(screen.getByRole('button', { name: 'Moja lokacija' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Pristup lokaciji nije dopušten')
    expect(fetch).toHaveBeenCalledOnce()
    await user.click(screen.getByRole('button', { name: 'Moja lokacija' }))
    expect(screen.queryByRole('alert')).toBeNull()
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2))
    expect(new URL(fetch.mock.calls[1][0], 'http://localhost').searchParams.get('near')).toBe('15.97,45.8')
    expect(screen.getByText(/Zračna udaljenost do 1 km/)).toBeVisible()
    await user.click(screen.getByRole('button', { name: /U blizini/ }))
    expect(screen.queryByRole('button', { name: 'Moja lokacija' })).toBeNull()
    expect(screen.getByRole('button', { name: 'U blizini 1 km' })).toHaveAttribute('aria-expanded', 'false')
  })
})
