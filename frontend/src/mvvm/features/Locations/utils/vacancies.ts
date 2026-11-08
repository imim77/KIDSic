import type { HistoricalEvidence, LocationProperties } from '../types'


const staleAfterDays = 365

export type PublishedVacancies =
  | { state: 'unpublished' }
  | {
    state: 'published'
    total: number | null
    record: HistoricalEvidence
    stale: boolean
  }




export function publishedVacancies(location: LocationProperties, today = new Date()): PublishedVacancies {
  const record = (location.historical_data ?? []).filter((item) => item.vacancies.length)
    .sort((a, b) => b.reference_date.localeCompare(a.reference_date))[0]
  if (!record) return { state: 'unpublished' }
  const total = record.vacancies.some((group) => group.free_places === null) ? null
    : record.vacancies.reduce((sum, group) => sum + (group.free_places ?? 0), 0)
  const age = (today.getTime() - new Date(`${record.reference_date}T00:00:00`).getTime()) / 86_400_000
  return { state: 'published', total, record, stale: age > staleAfterDays }
}


export function vacancyLabel(total: number) {
  const rule = new Intl.PluralRules('hr').select(total)
  return `${total} ${rule === 'one' ? 'slobodno mjesto' : rule === 'few' ? 'slobodna mjesta' : 'slobodnih mjesta'}`
}


const zagrebVacancyOverview = 'https://data.zagreb.hr/dataset/slobodna-mjesta-u-vrticima-i-obrtima-za-cuvanje-djece-grada-zagreba'

export function officialVacancyOverview(location: LocationProperties) {
  return location.city === 'Zagreb' && (location.provider_kind === 'municipal' || location.provider_kind === 'childminder')
    ? zagrebVacancyOverview : undefined
}
