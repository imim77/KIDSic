import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { LocationDetails } from '../src/shared/locations/LocationDetails'
import { facility } from './fixtures'

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
