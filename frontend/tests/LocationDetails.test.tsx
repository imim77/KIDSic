import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { LocationDetails } from '../src/shared/locations/LocationDetails'
import { facility } from './fixtures'
import type { SubsidyPolicy } from '../src/shared/locations/types'

const policy: SubsidyPolicy = {
  policy_key: 'rijeka-private', title: 'Rijeka – vrtići drugih osnivača',
  summary: 'Gradski udio: 335 € za jaslice i 275 € za vrtić.', verification_status: 'verified',
  verified_on: '2026-11-04', valid_from: '2026-09-01', valid_until: '2027-08-31', amount_kind: 'city_subsidy',
  rates: [{ label: 'Cjelodnevne jaslice', city_subsidy_cents: 33500, parent_fee_cents: null }],
  conditions: ['Prebivalište u Rijeci.'], reliefs: [], notes: [],
  sources: [{ title: 'Službeni program', url: 'https://sn.rijeka.hr/program/' }],
}

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
  Object.assign(location.properties, { address: null, website_url: 'javascript:alert(1)', email: ' ', phone: null })
  render(<LocationDetails feature={location} onClose={() => {}} />)
  expect(screen.getByText(/Adresa nije poznata/)).toBeVisible()
  expect(screen.queryByRole('heading', { name: 'Kontakt' })).toBeNull()
  expect(screen.queryAllByRole('link')).toHaveLength(0)
})

it('keeps multiple published contacts readable instead of dialing a concatenated number', () => {
  const location = facility('multiple')
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
