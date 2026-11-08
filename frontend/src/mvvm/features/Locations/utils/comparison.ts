import { formatDay, formatDistance, formatInstant } from '@/mvvm/utils/format'
import { websiteHref } from '@/mvvm/utils/links'
import type { LocationFeature } from '../types'
import { currentRound } from './enrolment'
import { publishedVacancies, vacancyLabel } from './vacancies'

export const comparisonLimit = 3

export type NextStep = { label: string; href?: string }

export interface ComparisonNotes {
  strengths: string[]
  checks: string[]
  next: NextStep
}




export function compareOptions(features: LocationFeature[]): Map<string, ComparisonNotes> {
  const distances = features.flatMap((feature) => feature.properties.distance_m ?? [])
  const nearest = distances.length > 1 ? Math.min(...distances) : null
  return new Map(features.map((feature) => {
    const location = feature.properties
    const strengths: string[] = []
    const checks: string[] = []
    if (nearest != null && location.distance_m === nearest) strengths.push(`Najbliži odabranoj točki (${formatDistance(nearest)} zračno)`)
    const round = currentRound(location.enrolment ?? [])
    if (!round) checks.push('Kanal upisa nije potvrđen')
    else if (round.status === 'open') strengths.push(`${round.round === 'main' ? 'Upis' : 'Upis tijekom godine'} je otvoren${round.closes_at ? ` do ${formatInstant(round.closes_at)}` : ''}`)
    else if (round.status === 'upcoming') strengths.push(`Upis počinje ${formatInstant(round.opens_at!)}`)
    else if (round.status === 'closed') checks.push(`Rok upisa za ${round.academic_year} je završio`)
    else if (round.status === 'not_accepting') checks.push(`Upisi za ${round.academic_year} se ne provode`)
    else checks.push('Rok upisa nije objavljen')

    const vacancies = publishedVacancies(location)
    if (vacancies.state === 'unpublished') checks.push('Slobodna mjesta nisu objavljena')
    else {
      const date = formatDay(vacancies.record.reference_date)
      if (vacancies.total === null) checks.push(`Broj slobodnih mjesta nije potpuno objavljen (stanje ${date})`)
      else if (vacancies.total > 0) strengths.push(`Objavljeno ${vacancyLabel(vacancies.total)} (stanje ${date})`)
      else checks.push(`Objavljeno 0 slobodnih mjesta (stanje ${date})`)
      if (vacancies.stale) checks.push('Podatak o slobodnim mjestima stariji je od godinu dana')
    }
    if (!(location.subsidy_policies ?? []).length) checks.push('Gradsko sufinanciranje nije potvrđeno')
    if (location.location_role === 'seat') checks.push('Prikazana je adresa sjedišta; lokacija objekta nije potvrđena')
    if (!location.phone && !location.email && !websiteHref(location.website_url)) checks.push('Nema potvrđenog kontakta')
    return [feature.id, { strengths, checks, next: nextStep(feature) }]
  }))
}



function nextStep(feature: LocationFeature): NextStep {
  const location = feature.properties
  const round = currentRound(location.enrolment ?? [])
  const application = round && (round.status === 'open' || round.status === 'upcoming') ? websiteHref(round.application_url) : undefined
  if (application) return { label: round!.status === 'open' ? 'Otvori službeni upis' : 'Pripremi se za službeni upis', href: application }
  const phone = location.phone?.trim()
  if (phone) return { label: `Nazovi vrtić: ${phone}` }
  const email = location.email?.trim()
  if (email) return { label: `Pošalji upit: ${email}` }
  const website = websiteHref(location.website_url)
  if (website) return { label: 'Provjeri na web stranici vrtića', href: website }
  return { label: 'Provjeri kod nadležnog gradskog ureda' }
}
