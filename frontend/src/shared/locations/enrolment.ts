import type { EnrolmentStatus, LocationEnrolment } from './types'

export const enrolmentStatusLabels: Record<EnrolmentStatus, string> = {
  open: 'Otvoreno', upcoming: 'Uskoro', closed: 'Rok završen', not_accepting: 'Upisi se ne provode',
  dates_unknown: 'Rok nije objavljen',
}

// Deadlines are Zagreb times whatever the viewer's zone.
export const enrolmentInstant = (value: string) => new Intl.DateTimeFormat('hr-HR', { day: '2-digit', month: '2-digit',
  year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Zagreb' }).format(new Date(value))

// currentRound picks the round a parent can act on: an open or upcoming one
// first, otherwise the newest main call. Rounds arrive newest year first.
export function currentRound(rounds: LocationEnrolment[]) {
  return rounds.find((round) => round.status === 'open')
    ?? rounds.find((round) => round.status === 'upcoming')
    ?? rounds.find((round) => round.round === 'main')
    ?? rounds[0]
}
