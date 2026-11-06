// formatDistance renders whole metres below a kilometre and one decimal above.
export function formatDistance(metres: number) {
  if (metres < 1000) return `${metres} m`
  return `${(metres / 1000).toLocaleString('hr', { maximumFractionDigits: 1 })} km`
}

// formatDay renders a calendar date (YYYY-MM-DD) in the viewer's local day,
// so a published date never shifts by a time-zone offset.
export const formatDay = (value: string) => new Intl.DateTimeFormat('hr-HR').format(new Date(`${value}T00:00:00`))

// Deadlines and timetables are Zagreb times whatever the viewer's zone.
export const formatInstant = (value: string) => new Intl.DateTimeFormat('hr-HR', { day: '2-digit', month: '2-digit',
  year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Zagreb' }).format(new Date(value))

export const formatTime = (value: string) => new Intl.DateTimeFormat('hr-HR', {
  timeZone: 'Europe/Zagreb', hour: '2-digit', minute: '2-digit',
}).format(new Date(value))
