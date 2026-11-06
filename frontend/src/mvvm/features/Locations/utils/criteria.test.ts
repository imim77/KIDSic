import { describe, expect, it } from 'vitest'
import { describeCriteria, describeEmptySearch } from './criteria'

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

describe('describeEmptySearch', () => {
  it('leaves a plain city search to the default notice', () => {
    expect(describeEmptySearch({ city: 'Rijeka', name: '', area: '', provider_kind: null, nearby: null })).toBeUndefined()
  })

  it('names every criterion and says an unmatched area is not proof of absence', () => {
    expect(describeEmptySearch({ city: 'Rijeka', area: 'Trsat', provider_kind: 'private' }))
      .toBe('Nema rezultata za grad Rijeka, vrstu „Privatni vrtić”, područje „Trsat”. Provjerite ili promijenite kriterije u razgovoru.'
        + ' Nema zapisa s potvrđenim podudaranjem područja; to ne znači da ondje nema vrtića.')
  })
})
