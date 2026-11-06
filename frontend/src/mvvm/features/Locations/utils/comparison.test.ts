import { describe, expect, it } from 'vitest'
import { compareOptions } from '@/mvvm/features/Locations/utils/comparison'
import { enrolmentRound, facility, historicalEvidence } from '@test-support/fixtures'

describe('compareOptions', () => {
  it('credits only the nearest option', () => {
    const near = facility('near')
    near.properties.distance_m = 320
    const far = facility('far')
    far.properties.distance_m = 900
    const notes = compareOptions([near, far])
    expect(notes.get('near')!.strengths).toEqual(['Najbliži odabranoj točki (320 m zračno)'])
    expect(notes.get('far')!.strengths).toEqual([])
  })

  it('lists missing data as things to check and never as a shortfall', () => {
    const unknown = facility('unknown')
    expect(compareOptions([unknown]).get('unknown')).toEqual({
      strengths: [],
      checks: ['Kanal upisa nije potvrđen', 'Slobodna mjesta nisu objavljena',
        'Gradsko sufinanciranje nije potvrđeno', 'Nema potvrđenog kontakta'],
      next: { label: 'Provjeri kod nadležnog gradskog ureda' },
    })
  })

  it('points to the official application while a round is open, otherwise to a contact', () => {
    const open = facility('open')
    open.properties.enrolment = [enrolmentRound({ status: 'open' })]
    const closed = facility('closed')
    closed.properties.enrolment = [enrolmentRound()]
    closed.properties.phone = '01 2345 678'
    const notes = compareOptions([open, closed])
    expect(notes.get('open')!.strengths[0]).toMatch(/^Upis je otvoren do 22\. ?05\. ?2026/)
    expect(notes.get('open')!.next).toEqual({ label: 'Otvori službeni upis', href: 'https://upis.example.invalid/' })
    expect(notes.get('closed')!.checks).toContain('Rok upisa za 2026./2027. je završio')
    expect(notes.get('closed')!.next).toEqual({ label: 'Nazovi vrtić: 01 2345 678' })
  })

  it('credits published free places and flags a published zero and an old snapshot', () => {
    const free = facility('free')
    free.properties.historical_data = [historicalEvidence({ vacancies: [{ age_label: null, program: null, free_places: 4 }] })]
    const full = facility('full')
    full.properties.historical_data = [historicalEvidence()]
    const notes = compareOptions([free, full])
    expect(notes.get('free')!.strengths).toContain('Objavljeno 4 slobodna mjesta (stanje 01. 01. 2025.)')
    expect(notes.get('full')!.checks).toContain('Objavljeno 0 slobodnih mjesta (stanje 01. 01. 2025.)')
    expect(notes.get('full')!.checks).toContain('Podatak o slobodnim mjestima stariji je od godinu dana')
  })
})
