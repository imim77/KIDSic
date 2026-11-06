import { useEffect, useId, useRef, type KeyboardEvent } from 'react'
import { Building2, Route, X } from 'lucide-react'
import type { OpenLink } from '@/mvvm/utils/links'
import { LocationDetails } from '../../Locations/components/LocationDetails'
import type { LocationFeature } from '../../Locations/types'
import type { CommuteTab } from '../hooks/use-commute'
import { RouteDetails } from './RouteDetails'
import type { CommuteOption, CommuteResult } from '../types'

const tabs: { id: CommuteTab; label: string; Icon: typeof Route }[] = [
  { id: 'route', label: 'Put', Icon: Route },
  { id: 'kindergarten', label: 'Vrtić', Icon: Building2 },
]

// CommuteDetails splits the details column into the route to the selected
// kindergarten and the same kindergarten details a city search shows. The tab
// is owned by the caller so it survives choosing another kindergarten.
export function CommuteDetails({ result, option, rank, feature, tab, onTab, onClose, openLink }: {
  result: CommuteResult; option: CommuteOption; rank: number; feature: LocationFeature
  tab: CommuteTab; onTab: (tab: CommuteTab) => void; onClose: () => void
  openLink?: OpenLink
}) {
  const id = useId()
  const panel = useRef<HTMLElement>(null)
  useEffect(() => {
    // A card that expanded the frame may have unmounted with keyboard focus.
    if (!document.activeElement || document.activeElement === document.body) panel.current?.focus({ preventScroll: true })
  }, [])
  const close = () => {
    // Return focus to the result that opened the details before they unmount.
    const rows = panel.current?.closest('.explorer-layout')?.querySelectorAll<HTMLElement>('[data-location-row], [data-location-card]')
    Array.from(rows ?? []).find(row => (row.dataset.locationRow ?? row.dataset.locationCard) === option.facility_id)?.focus({ preventScroll: true })
    onClose()
  }
  // Arrow keys move between tabs, as the ARIA tabs pattern expects.
  const keys = (event: KeyboardEvent<HTMLDivElement>) => {
    const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key]
    if (!step) return
    event.preventDefault()
    const next = tabs[(tabs.findIndex(t => t.id === tab) + step + tabs.length) % tabs.length].id
    onTab(next)
    event.currentTarget.querySelector<HTMLElement>(`[data-tab="${next}"]`)?.focus()
  }
  return <section ref={panel} tabIndex={-1} className="location-details commute-details" aria-label={`Vrtić na putu: ${option.name}`}
    onKeyDown={event => { if (event.key === 'Escape' && !event.defaultPrevented) { event.preventDefault(); close() } }}>
    <div className="commute-tabs-bar">
      <div className="commute-tabs" role="tablist" aria-label="Prikaz detalja" onKeyDown={keys}>
        {tabs.map(({ id: key, label, Icon }) => <button key={key} type="button" role="tab" data-tab={key}
          id={`${id}-${key}`} aria-controls={`${id}-panel`} aria-selected={tab === key} tabIndex={tab === key ? 0 : -1}
          onClick={() => onTab(key)}><Icon aria-hidden="true" />{label}</button>)}
      </div>
      <button type="button" className="location-details-close" aria-label="Zatvori detalje" onClick={close}><X aria-hidden="true" /></button>
    </div>
    <div className="commute-tab-panel" role="tabpanel" id={`${id}-panel`} aria-labelledby={`${id}-${tab}`}>
      {tab === 'route'
        ? <RouteDetails result={result} option={option} rank={rank} />
        : <LocationDetails key={feature.id} feature={feature} openLink={openLink} />}
    </div>
  </section>
}
