import { describe, expect, it } from 'vitest'
import { describeCriteria, results } from '../src/shared/locations/criteria'

describe('describeCriteria', () => {
  it('names the alphabetical order when nothing narrows the city', () => {
    expect(describeCriteria({ city: 'Zagreb' })).toEqual(['abecedno'])
  })

  it('lists filters in reading order and puts the nearest results first', () => {
    expect(describeCriteria({ city: 'Zagreb', provider_kind: 'municipal', name: 'Bajka', area: 'Trnje',
      nearby: { near: [15.97, 45.81], radius_m: 1500 } }))
      .toEqual(['Gradski vrtić', 'naziv „Bajka”', 'područje „Trnje”', 'do 1,5 km od točke', 'najbliži prvi'])
  })


})

describe('results', () => {
  it('agrees the noun with the count', () => {
    expect([1, 2, 5, 21].map(results)).toEqual(['1 rezultat', '2 rezultata', '5 rezultata', '21 rezultat'])
  })
})
