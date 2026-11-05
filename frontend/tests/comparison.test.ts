import { describe, expect, it } from 'vitest'
import { compareOptions } from '../src/shared/locations/comparison'
import { enrolmentRound, facility, programEvidence } from './fixtures'

describe('compareOptions', () => {
  it('credits only the nearest option and a program no other option confirms', () => {
    const near = facility('near')
    near.properties.distance_m = 320
    near.properties.programs = [programEvidence({ name: 'Montessori' }), programEvidence({ program_id: 'b', name: 'Engleski' })]
    const far = facility('far')
    far.properties.distance_m = 900
    far.properties.programs = [programEvidence({ name: 'montessori' })]
    const notes = compareOptions([near, far])
    expect(notes.get('near')!.strengths).toEqual(['Najbliži odabranoj točki (320 m zračno)', 'Jedini s potvrđenim programom „Engleski”'])
    expect(notes.get('far')!.strengths).toEqual([])
  })

  it('lists missing data as things to check and never as a shortfall', () => {
    const unknown = facility('unknown')
    expect(compareOptions([unknown]).get('unknown')).toEqual({
      strengths: [],
      checks: ['Kanal upisa nije potvrđen', 'Programi i dobni uvjeti nisu potvrđeni',
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
})
