import { formatDistance } from './distance'
import { providerLabels, type SearchCriteria } from './types'

// describeCriteria lists the active filters and the result order in the words
// parents see, so a short list never looks like the whole city. The order
// mirrors the API: confirmed suitability first, then nearest or by name.
export function describeCriteria({ name, area, provider_kind, age_months, program, include_unknown, has_vacancies, nearby }: SearchCriteria) {
  const evaluated = age_months != null || !!program
  const parts = [
    provider_kind ? providerLabels[provider_kind] : '',
    name ? `naziv „${name}”` : '',
    area ? `područje „${area}”` : '',
    age_months != null ? `dob ${age_months} mj.` : '',
    program ? `program „${program}”` : '',
    evaluated && include_unknown === false ? 'samo potvrđeni' : '',
    has_vacancies ? 's objavljenim slobodnim mjestima' : '',
    nearby ? `do ${formatDistance(nearby.radius_m)} od točke` : '',
  ]
  const order = nearby ? 'najbliži prvi' : 'abecedno'
  parts.push(evaluated && include_unknown !== false ? `potvrđeni prvi, zatim ${order}` : order)
  return parts.filter(Boolean)
}

// results names a result count with Croatian plural agreement.
export function results(count: number) {
  return new Intl.PluralRules('hr').select(count) === 'one' ? `${count} rezultat` : `${count} rezultata`
}
