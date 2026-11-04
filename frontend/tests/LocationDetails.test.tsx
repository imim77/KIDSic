import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { LocationDetails } from '../src/shared/locations/LocationDetails'
import { facility } from './fixtures'

it('states missing facts instead of inventing them and closes on Escape', async () => {
  const location = facility('unmapped', false)
  location.properties.name = 'Synthetic parent institution'
  location.properties.sources = [{ ...location.properties.sources[0], url: 'javascript:alert(1)', license: null }]
  const onClose = vi.fn()
  render(<LocationDetails feature={location} onClose={onClose} />)
  expect(screen.getByRole('heading', { name: 'Synthetic facility unmapped' })).toBeVisible()
  expect(screen.getByText('Ustanova: Synthetic parent institution')).toBeVisible()
  expect(screen.getByText(/Koordinate nisu poznate/)).toBeVisible()
  expect(screen.getByText(/Dobne skupine, slobodna mjesta i cijene nisu dio otvorenih podataka/)).toBeVisible()
  // Without coordinates the directions search falls back to the address.
  expect(screen.getByRole('link', { name: 'Otvori u Google kartama' }))
    .toHaveAttribute('href', 'https://www.google.com/maps/search/?api=1&query=Synthetic%20address%201%2C%20Zagreb')
  expect(screen.queryByRole('link', { name: 'Synthetic source' })).toBeNull()
  expect(screen.getByText(/Licenca nije navedena/)).toBeVisible()
  screen.getByRole('button', { name: 'Zatvori detalje' }).focus()
  await userEvent.keyboard('{Escape}')
  expect(onClose).toHaveBeenCalledOnce()
})

it('omits directions when neither coordinates nor an address are known', () => {
  const location = facility('unknown', false)
  location.properties.address = null
  location.properties.city = ''
  location.properties.sources = []
  render(<LocationDetails feature={location} onClose={() => {}} />)
  expect(screen.getByText('Adresa nije poznata')).toBeVisible()
  expect(screen.queryByRole('link', { name: 'Otvori u Google kartama' })).toBeNull()
  expect(screen.getByText('Podrijetlo podatka nije dostupno.')).toBeVisible()
})
