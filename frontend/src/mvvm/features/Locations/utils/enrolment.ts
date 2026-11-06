import type { EnrolmentStatus, LocationEnrolment } from '../types'

export const enrolmentStatusLabels: Record<EnrolmentStatus, string> = {
  open: 'Otvoreno', upcoming: 'Uskoro', closed: 'Rok završen', not_accepting: 'Upisi se ne provode',
  dates_unknown: 'Rok nije objavljen',
}

// currentRound picks the round a parent can act on: an open or upcoming one
// first, otherwise the newest main call. Rounds arrive newest year first.
export function currentRound(rounds: LocationEnrolment[]) {
  return rounds.find((round) => round.status === 'open')
    ?? rounds.find((round) => round.status === 'upcoming')
    ?? rounds.find((round) => round.round === 'main')
    ?? rounds[0]
}
