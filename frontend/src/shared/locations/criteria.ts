import { formatDistance } from './distance'
import { providerLabels, type SearchCriteria } from './types'

// describeCriteria lists the active filters and the result order in the words
// parents see, so a short list never looks like the whole city. The order
// mirrors the API: nearest or by name.
export function describeCriteria({ name, area, provider_kind, has_vacancies, nearby }: SearchCriteria) {
  const parts = [
    provider_kind ? providerLabels[provider_kind] : '',
    name ? `naziv „${name}”` : '',
    area ? `područje „${area}”` : '',
    has_vacancies ? 's objavljenim slobodnim mjestima' : '',
    nearby ? `do ${formatDistance(nearby.radius_m)} od točke` : '',
  ]
  const order = nearby ? 'najbliži prvi' : 'abecedno'
  parts.push(order)
  return parts.filter(Boolean)
}

// results names a result count with Croatian plural agreement.
export function results(count: number) {
  return new Intl.PluralRules('hr').select(count) === 'one' ? `${count} rezultat` : `${count} rezultata`
}
