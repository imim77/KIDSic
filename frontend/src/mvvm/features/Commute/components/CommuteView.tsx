import { KindergartenExplorer } from '../../Locations/components/KindergartenExplorer'
import type { HostFullscreen } from '@/mvvm/components/FullscreenFrame'
import type { OpenLink } from '@/mvvm/utils/links'
import { useCommute } from '../hooks/use-commute'
import { CommuteDetails } from './CommuteDetails'
import { RouteSummary } from './RouteSummary'
import type { CommuteResult } from '../types'
import './commute.css'




export function CommuteView({ result, onSelect, hostFullscreen, openLink }: {
  result: CommuteResult; onSelect?: (id: string | null) => void; hostFullscreen?: HostFullscreen
  openLink?: OpenLink
}) {
  const commute = useCommute(result, onSelect)
  const { option, feature } = commute
  return <KindergartenExplorer data={result.locations} status="ready" selectedId={commute.selectedId}
    onSelect={commute.select} route={commute.route} hostFullscreen={hostFullscreen} openLink={openLink}
    emptyNotice="Nema dostupnog puta za zadane kriterije. Promijeni lokacije, datum ili način putovanja u razgovoru."
    summary={commute.summary}
    mapNotice={option && <RouteSummary name={option.name} rank={commute.rank} count={commute.count} onStep={commute.step} />}
    details={option && feature && <CommuteDetails result={result} option={option} rank={commute.rank} feature={feature}
      tab={commute.tab} onTab={commute.setTab} onClose={commute.close} openLink={openLink} />} />
}
