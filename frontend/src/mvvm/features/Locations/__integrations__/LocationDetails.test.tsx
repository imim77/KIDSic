import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { LocationDetails } from '@/mvvm/features/Locations/components/LocationDetails'
import { enrolmentRound, facility, historicalEvidence } from '@test-support/fixtures'
import type { SubsidyPolicy } from '@/mvvm/features/Locations/types'

const policy: SubsidyPolicy = {
  policy_key: 'rijeka-private', title: 'Rijeka – vrtići drugih osnivača',
  summary: 'Gradski udio: 335 € za jaslice i 275 € za vrtić.', verification_status: 'verified',
  verified_on: '2026-11-04', valid_from: '2026-09-01', valid_until: '2027-08-31', amount_kind: 'city_subsidy',
  rates: [{ label: 'Cjelodnevne jaslice', city_subsidy_cents: 33500, parent_fee_cents: null }],
  conditions: ['Prebivalište u Rijeci.'], reliefs: [], notes: [],
  sources: [{ title: 'Službeni program', url: 'https://sn.rijeka.hr/program/' }],
}

it('shows the newest published vacancies with date, scope and staleness, and keeps program snapshots separate', async () => {
  const item = facility('history')
  item.properties.historical_data = [historicalEvidence({ vacancies: [
    { age_label: 'od 1 do 2 godine', program: 'REDOVITI PROGRAM', free_places: 3 },
    { age_label: 'od 3 godine do OŠ', program: null, free_places: 0 },
  ] }), historicalEvidence({ reference_date: '2019-10-09',
    date_kind: 'published', scope: 'facility', vacancies: [], programs: ['Montessori', 'engleski jezik'],
    source_url: 'https://example.invalid/programs.xlsx' })]
  const openLink = vi.fn()
  const { rerender } = render(<LocationDetails feature={item} onClose={() => {}} openLink={openLink} />)
  const vacancies = screen.getByRole('region', { name: 'Objavljena slobodna mjesta' })
  expect(within(vacancies).getByText('3 slobodna mjesta')).toBeVisible()
  expect(within(vacancies).getByText('Stanje 01. 01. 2025.')).toBeVisible()
  expect(within(vacancies).getByText('Snimka je starija od godinu dana')).toBeVisible()
  expect(within(vacancies).getByText(/Broj vrijedi za cijelu ustanovu/)).toBeVisible()
  expect(within(vacancies).getByText('od 1 do 2 godine · redoviti program')).toBeVisible()
  expect(within(vacancies).getByText(/nije jamstvo upisa/)).toBeVisible()
  const history = screen.getByRole('region', { name: 'Povijesni otvoreni podaci' })
  expect(within(history).getByText(/Objavljeno 09\. 10\. 2019\./)).toBeVisible()
  expect(within(history).getByText('Montessori')).toBeVisible()
  expect(within(history).queryByText(/Stanje na dan 01\. 01\. 2025\./)).toBeNull()
  await userEvent.click(within(vacancies).getByRole('link', { name: /Synthetic open snapshot/ }))
  expect(openLink).toHaveBeenCalledWith('https://example.invalid/historical.csv')
  rerender(<LocationDetails feature={facility('other')} onClose={() => {}} />)
  expect(screen.queryByText('Povijesni otvoreni podaci')).toBeNull()
})

it('keeps a published zero, a blank count and an unpublished count apart', () => {
  const zero = facility('zero')
  zero.properties.historical_data = [historicalEvidence()]
  const { rerender } = render(<LocationDetails feature={zero} onClose={() => {}} />)
  expect(screen.getByText('0 slobodnih mjesta')).toBeVisible()
  const partial = facility('partial')
  partial.properties.historical_data = [historicalEvidence({ vacancies: [{ age_label: null, program: null, free_places: null }] })]
  rerender(<LocationDetails feature={partial} onClose={() => {}} />)
  expect(screen.getByText('Broj nije potpuno objavljen')).toBeVisible()
  expect(screen.getByText('nije objavljeno')).toBeVisible()
  expect(screen.queryByText('0 slobodnih mjesta')).toBeNull()
  const unpublished = facility('unpublished')
  rerender(<LocationDetails feature={unpublished} onClose={() => {}} />)
  expect(screen.getByText(/slobodna mjesta nisu objavljena u uvezenim izvorima/)).toBeVisible()
  expect(screen.getByRole('link', { name: /Službeni pregled slobodnih mjesta/ })).toHaveAttribute('href', expect.stringContaining('data.zagreb.hr'))
  unpublished.properties.provider_kind = 'private'
  rerender(<LocationDetails feature={{ ...unpublished }} onClose={() => {}} />)
  expect(screen.queryByRole('link', { name: /Službeni pregled slobodnih mjesta/ })).toBeNull()
})


it('shows the selected policy, expands rates and opens the official source through the host', async () => {
  const location = facility('subsidy')
  location.properties.subsidy_policies = [policy]
  const openLink = vi.fn()
  render(<LocationDetails feature={location} onClose={() => {}} openLink={openLink} />)
  expect(screen.getByText(policy.summary)).toBeVisible()
  expect(screen.getByText(/Gradski udio · mjesečno po djetetu/)).toBeVisible()
  expect(screen.getByText('Cjelodnevne jaslice')).not.toBeVisible()
  await userEvent.click(screen.getByText('Tarife, olakšice i uvjeti'))
  expect(screen.getByText('Cjelodnevne jaslice')).toBeVisible()
  expect(screen.getByText('Prebivalište u Rijeci.')).toBeVisible()
  await userEvent.click(screen.getByRole('link', { name: /Službeni program/ }))
  expect(openLink).toHaveBeenLastCalledWith('https://sn.rijeka.hr/program/')
})

it('keeps unconfirmed amounts distinct from free care and replaces policy when selection changes', () => {
  const location = facility('partial')
  location.properties.subsidy_policies = [{ ...policy, title: 'Varaždin – dadilje',
    summary: 'Aktualni iznos nije potvrđen.', verification_status: 'partial', rates: [] }]
  const { rerender } = render(<LocationDetails feature={location} onClose={() => {}} />)
  expect(screen.getByText('Iznos nije potvrđen')).toBeVisible()
  expect(screen.queryByText(/0,00/)).toBeNull()
  const other = facility('other')
  other.properties.provider_kind = 'unknown'
  rerender(<LocationDetails feature={other} onClose={() => {}} />)
  expect(screen.queryByText('Aktualni iznos nije potvrđen.')).toBeNull()
  expect(screen.getByText(/nema potvrđenog podatka o gradskom sufinanciranju/)).toBeVisible()
})

it('labels a public tariff as a parent fee rather than a city subsidy', async () => {
  const location = facility('municipal')
  location.properties.subsidy_policies = [{ ...policy, amount_kind: 'parent_fee',
    rates: [{ label: 'Cjelodnevni', city_subsidy_cents: null, parent_fee_cents: 1991 }] }]
  render(<LocationDetails feature={location} onClose={() => {}} />)
  expect(screen.getByText(/Roditeljska cijena · mjesečno po djetetu/)).toBeVisible()
  await userEvent.click(screen.getByText('Tarife, olakšice i uvjeti'))
  expect(screen.getByText(/Roditelj: 19,91/)).toBeVisible()
  expect(screen.queryByText(/Grad:/)).toBeNull()
})

it('shows published contacts, removes directions and sources, and closes on Escape', async () => {
  const location = facility('unmapped', false)
  Object.assign(location.properties, {
    name: 'Synthetic parent institution', website_url: 'www.example.invalid',
    email: 'info@example.invalid', phone: '+385 (1) 234-5678',
  })
  const onClose = vi.fn()
  render(<LocationDetails feature={location} onClose={onClose} />)
  expect(screen.getByRole('heading', { name: 'Synthetic facility unmapped' })).toBeVisible()
  expect(screen.getByText('Ustanova: Synthetic parent institution')).toBeVisible()
  expect(screen.getByText(/Koordinate nisu poznate/)).toBeVisible()
  expect(screen.getByRole('link', { name: 'Web stranica vrtića' })).toHaveAttribute('href', 'https://www.example.invalid/')
  expect(screen.getByRole('link', { name: 'info@example.invalid' })).toHaveAttribute('href', 'mailto:info@example.invalid')
  expect(screen.getByRole('link', { name: '+385 (1) 234-5678' })).toHaveAttribute('href', 'tel:+38512345678')
  expect(screen.queryByRole('link', { name: 'Otvori u Google kartama' })).toBeNull()
  expect(screen.queryByText('Izvori podataka')).toBeNull()
  expect(screen.queryByRole('link', { name: 'Synthetic source' })).toBeNull()
  screen.getByRole('button', { name: 'Zatvori detalje' }).focus()
  await userEvent.keyboard('{Escape}')
  expect(onClose).toHaveBeenCalledOnce()
})

it('omits absent contacts and unsafe websites without inventing a link', () => {
  const location = facility('unknown', false)

  Object.assign(location.properties, { provider_kind: 'private', address: null, website_url: 'javascript:alert(1)', email: ' ', phone: null })
  render(<LocationDetails feature={location} onClose={() => {}} />)
  expect(screen.getByText(/Adresa nije poznata/)).toBeVisible()
  expect(screen.queryByRole('heading', { name: 'Kontakt' })).toBeNull()
  expect(screen.queryAllByRole('link')).toHaveLength(0)
})

it('keeps multiple published contacts readable instead of dialing a concatenated number', () => {
  const location = facility('multiple')
  location.properties.provider_kind = 'private'
  location.properties.phone = '01/234-5678, 091/234-5678'
  location.properties.email = 'one@example.invalid; two@example.invalid'
  render(<LocationDetails feature={location} onClose={() => {}} />)
  expect(screen.getByText(location.properties.phone)).toBeVisible()
  expect(screen.getByText(location.properties.email)).toBeVisible()
  expect(screen.queryAllByRole('link')).toHaveLength(0)
})

it('opens website, email and phone through the MCP host when supplied', async () => {
  const location = facility('host')
  Object.assign(location.properties, {
    website_url: 'https://example.invalid', email: 'info@example.invalid', phone: '01/234-5678',
  })
  const openLink = vi.fn()
  render(<LocationDetails feature={location} onClose={() => {}} openLink={openLink} />)
  for (const [name, url] of [
    ['Web stranica vrtića', 'https://example.invalid/'],
    ['info@example.invalid', 'mailto:info@example.invalid'],
    ['01/234-5678', 'tel:012345678'],
  ]) {
    await userEvent.click(screen.getByRole('link', { name }))
    expect(openLink).toHaveBeenLastCalledWith(url)
  }
})

it('links an open round to the official channel and keeps closed and refused rounds without a link', async () => {
  const item = facility('enrolment')
  item.properties.enrolment = [enrolmentRound(), enrolmentRound({ round: 'rolling', status: 'open', opens_at: null,
    closes_at: '2027-08-31T21:59:59Z', reference_date: '2026-11-05', date_kind: 'observed',
    source_title: 'Synthetic enrolment page', source_url: 'https://example.invalid/page' })]
  const openLink = vi.fn()
  const { rerender } = render(<LocationDetails feature={item} onClose={() => {}} openLink={openLink} />)
  expect(screen.getByText('Upisi za 2026./2027.')).toBeVisible()
  expect(screen.getByText('Rok završen')).toBeVisible()
  expect(screen.getByText(/Rok je završio 22\. 05\. 2026\./)).toBeVisible()
  expect(screen.getByText('Upis tijekom pedagoške godine 2026./2027.')).toBeVisible()
  expect(screen.getByText(/Stanje izvora 05\. 11\. 2026\./)).toBeVisible()
  expect(screen.getAllByRole('link', { name: /Otvori službeni upis/ })).toHaveLength(1)
  expect(screen.getByText(/KIDSic ne predaje zahtjev i ne jamči mjesto/)).toBeVisible()
  await userEvent.click(screen.getByRole('link', { name: /Otvori službeni upis/ }))
  expect(openLink).toHaveBeenLastCalledWith('https://upis.example.invalid/')
  await userEvent.click(screen.getByRole('link', { name: /Synthetic enrolment notice/ }))
  expect(openLink).toHaveBeenLastCalledWith('https://example.invalid/notice.pdf')

  item.properties.enrolment = [enrolmentRound({ accepting: false, status: 'not_accepting' })]
  rerender(<LocationDetails feature={item} onClose={() => {}} openLink={openLink} />)
  expect(screen.getByText(/upisi u ovaj vrtić za 2026\.\/2027\. ne provode se/)).toBeVisible()
  expect(screen.queryByRole('link', { name: /Otvori službeni upis/ })).toBeNull()

  item.properties.enrolment = []
  rerender(<LocationDetails feature={item} onClose={() => {}} />)
  expect(screen.getByText(/Službeni kanal upisa za ovaj vrtić nije potvrđen/)).toBeVisible()
})

it('puts the compare button beside the provider kind, above the name', async () => {
  const onToggle = vi.fn()
  render(<LocationDetails feature={facility('item')} onClose={() => {}} compare={{ selected: false, full: false, onToggle }} />)
  const button = screen.getByRole('button', { name: 'Usporedi' })
  expect(button.parentElement).toHaveTextContent(/^Gradski vrtić/)
  expect(button.compareDocumentPosition(screen.getByRole('heading', { name: 'Synthetic facility item' })))
    .toBe(Node.DOCUMENT_POSITION_FOLLOWING)
  await userEvent.click(button)
  expect(onToggle).toHaveBeenCalledOnce()
})
