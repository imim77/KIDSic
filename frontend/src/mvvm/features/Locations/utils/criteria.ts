import { formatDistance } from '@/mvvm/utils/format'
import { providerLabels, type SearchCriteria } from '../types'




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




export function describeEmptySearch({ city, name, area, provider_kind, nearby }: SearchCriteria) {
  if (!name && !provider_kind && !area && !nearby) return undefined
  return `Nema rezultata za grad ${city}${nearby ? `, zračno do ${formatDistance(nearby.radius_m)} od odabrane točke` : ''}`
    + `${name ? `, naziv „${name}”` : ''}${provider_kind ? `, vrstu „${providerLabels[provider_kind]}”` : ''}`
    + `${area ? `, područje „${area}”` : ''}. Provjerite ili promijenite kriterije u razgovoru.`
    + `${area ? ' Nema zapisa s potvrđenim podudaranjem područja; to ne znači da ondje nema vrtića.' : ''}`
}
