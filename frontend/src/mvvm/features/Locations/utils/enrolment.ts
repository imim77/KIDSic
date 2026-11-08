import type { EnrolmentStatus, LocationEnrolment } from '../types'

export const enrolmentStatusLabels: Record<EnrolmentStatus, string> = {
  open: 'Otvoreno', upcoming: 'Uskoro', closed: 'Rok završen', not_accepting: 'Upisi se ne provode',
  dates_unknown: 'Rok nije objavljen',
}



export function currentRound(rounds: LocationEnrolment[]) {
  return rounds.find((round) => round.status === 'open')
    ?? rounds.find((round) => round.status === 'upcoming')
    ?? rounds.find((round) => round.round === 'main')
    ?? rounds[0]
}
