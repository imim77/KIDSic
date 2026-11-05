import type { HistoricalEvidence, LocationProperties } from './types'

// A snapshot older than this is shown as stale; free places change monthly.
const staleAfterDays = 365

export type PublishedVacancies =
  | { state: 'unpublished' }
  | {
    state: 'published'
    total: number | null // null when some group's count is blank, never a guessed sum
    record: HistoricalEvidence
    stale: boolean
  }

// publishedVacancies reads the newest snapshot that publishes vacancies. A
// published zero stays zero and a blank count stays unknown, so "no free
// places" and "not published" never collapse into one message.
export function publishedVacancies(location: LocationProperties, today = new Date()): PublishedVacancies {
  const record = (location.historical_data ?? []).filter((item) => item.vacancies.length)
    .sort((a, b) => b.reference_date.localeCompare(a.reference_date))[0]
  if (!record) return { state: 'unpublished' }
  const total = record.vacancies.some((group) => group.free_places === null) ? null
    : record.vacancies.reduce((sum, group) => sum + (group.free_places ?? 0), 0)
  const age = (today.getTime() - new Date(`${record.reference_date}T00:00:00`).getTime()) / 86_400_000
  return { state: 'published', total, record, stale: age > staleAfterDays }
}

export const vacancyDate = (value: string) => new Intl.DateTimeFormat('hr-HR').format(new Date(`${value}T00:00:00`))

// vacancyLabel names a count with Croatian plural agreement.
export function vacancyLabel(total: number) {
  const rule = new Intl.PluralRules('hr').select(total)
  return `${total} ${rule === 'one' ? 'slobodno mjesto' : rule === 'few' ? 'slobodna mjesta' : 'slobodnih mjesta'}`
}

// Zagreb publishes counts for its municipal kindergartens and childminders.
export const zagrebVacancyOverview = 'https://data.zagreb.hr/dataset/slobodna-mjesta-u-vrticima-i-obrtima-za-cuvanje-djece-grada-zagreba'

export function officialVacancyOverview(location: LocationProperties) {
  return location.city === 'Zagreb' && (location.provider_kind === 'municipal' || location.provider_kind === 'childminder')
    ? zagrebVacancyOverview : undefined
}
