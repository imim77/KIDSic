import { currentRound, enrolmentInstant } from './enrolment'
import { formatDistance } from './distance'
import { websiteHref } from './links'
import type { LocationFeature } from './types'

export const comparisonLimit = 3

export type NextStep = { label: string; href?: string }

export interface ComparisonNotes {
  strengths: string[]
  checks: string[] // Unknowns to verify, never read as "does not meet".
  next: NextStep
}

const programKey = (name: string) => name.trim().toLocaleLowerCase('hr')

// compareOptions explains each option against the others using only fields the
// table shows. Rules stay mechanical so the comparison never invents a fact or
// a recommendation, and a missing value is something to check, not a minus.
export function compareOptions(features: LocationFeature[]): Map<string, ComparisonNotes> {
  const distances = features.flatMap((feature) => feature.properties.distance_m ?? [])
  const nearest = distances.length > 1 ? Math.min(...distances) : null
  const programOwners = new Map<string, Set<string>>()
  for (const feature of features) {
    for (const program of feature.properties.programs ?? []) {
      const key = programKey(program.name)
      programOwners.set(key, (programOwners.get(key) ?? new Set()).add(feature.id))
    }
  }

  return new Map(features.map((feature) => {
    const location = feature.properties
    const strengths: string[] = []
    const checks: string[] = []
    if (nearest != null && location.distance_m === nearest) strengths.push(`Najbliži odabranoj točki (${formatDistance(nearest)} zračno)`)
    if (location.suitability_status === 'confirmed') strengths.push('Potvrđeno podudaranje zadane dobi ili programa')
    if (features.length > 1) {
      const unique = (location.programs ?? []).map((program) => program.name)
        .filter((name, index, names) => names.indexOf(name) === index && programOwners.get(programKey(name))?.size === 1)
      for (const name of unique) strengths.push(`Jedini s potvrđenim programom „${name}”`)
    }

    const round = currentRound(location.enrolment ?? [])
    if (!round) checks.push('Kanal upisa nije potvrđen')
    else if (round.status === 'open') strengths.push(`${round.round === 'main' ? 'Upis' : 'Upis tijekom godine'} je otvoren${round.closes_at ? ` do ${enrolmentInstant(round.closes_at)}` : ''}`)
    else if (round.status === 'upcoming') strengths.push(`Upis počinje ${enrolmentInstant(round.opens_at!)}`)
    else if (round.status === 'closed') checks.push(`Rok upisa za ${round.academic_year} je završio`)
    else if (round.status === 'not_accepting') checks.push(`Upisi za ${round.academic_year} se ne provode`)
    else checks.push('Rok upisa nije objavljen')

    if (!(location.programs ?? []).length) checks.push('Programi i dobni uvjeti nisu potvrđeni')
    if (location.suitability_status === 'unknown') checks.push('Zadana dob ili program nisu potvrđeni')
    if (!(location.subsidy_policies ?? []).length) checks.push('Gradsko sufinanciranje nije potvrđeno')
    if (location.location_role === 'seat') checks.push('Prikazana je adresa sjedišta; lokacija objekta nije potvrđena')
    if (!location.phone && !location.email && !websiteHref(location.website_url)) checks.push('Nema potvrđenog kontakta')
    return [feature.id, { strengths, checks, next: nextStep(feature) }]
  }))
}

// nextStep names one concrete action: apply while a round is open, otherwise
// ask the kindergarten through the first confirmed channel.
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
