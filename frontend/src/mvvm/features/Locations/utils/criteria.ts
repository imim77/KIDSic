import { formatDistance } from '@/mvvm/utils/format'
import { providerLabels, type SearchCriteria } from '../types'

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

// describeEmptySearch explains an empty host search by its criteria, so it
// never reads as "no kindergartens in the city"; a plain city search needs no
// explanation and returns undefined.
export function describeEmptySearch({ city, name, area, provider_kind, nearby }: SearchCriteria) {
  if (!name && !provider_kind && !area && !nearby) return undefined
  return `Nema rezultata za grad ${city}${nearby ? `, zračno do ${formatDistance(nearby.radius_m)} od odabrane točke` : ''}`
    + `${name ? `, naziv „${name}”` : ''}${provider_kind ? `, vrstu „${providerLabels[provider_kind]}”` : ''}`
    + `${area ? `, područje „${area}”` : ''}. Provjerite ili promijenite kriterije u razgovoru.`
    + `${area ? ' Nema zapisa s potvrđenim podudaranjem područja; to ne znači da ondje nema vrtića.' : ''}`
}
