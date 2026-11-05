import { render, screen, within } from '@testing-library/react'
import { expect, it } from 'vitest'
import { ComparisonView } from '../src/shared/locations/ComparisonView'
import { facility } from './fixtures'

it('keeps every criterion of one kindergarten inside its own card', () => {
  const first = facility('a')
  first.properties.district = 'Trnje'
  render(<ComparisonView features={[first, facility('b')]} onRemove={() => {}} onClose={() => {}} />)
  const cards = within(screen.getByRole('list', { name: 'Vrtići u usporedbi' })).getAllByRole('listitem', { name: /^Synthetic facility/ })
  expect(cards).toHaveLength(2)
  const terms = within(cards[0]).getAllByRole('term').map((term) => term.textContent)
  expect(terms).toEqual(['Adresa', 'Programi i dob', 'Upis', 'Slobodna mjesta', 'Sufinanciranje', 'Kontakt', 'Prednosti', 'Provjeriti', 'Sljedeći korak', 'Izvori'])
  expect(within(cards[0]).getByText('Trnje')).toHaveClass('comparison-sticker')
  expect(within(cards[1]).queryByText('Trnje')).toBeNull()
  expect(screen.queryByRole('heading', { name: 'Usporedba vrtića' })).toBeNull()
  expect(screen.queryByText(/Objavljena slobodna mjesta/)).toBeNull()
})
