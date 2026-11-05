import { useEffect, useRef, type MouseEvent, type ReactNode } from 'react'
import { X } from 'lucide-react'
import { compareOptions } from './comparison'
import { currentRound, enrolmentInstant, enrolmentStatusLabels } from './enrolment'
import { formatDistance } from './distance'
import { websiteHref } from './links'
import { providerLabels, type LocationFeature, type LocationProgram } from './types'

interface ComparisonViewProps {
  features: LocationFeature[]
  onRemove: (id: string) => void
  onClose: () => void
  openLink?: (url: string) => void
}

const unknown = <span className="comparison-unknown">Nije potvrđeno</span>

function ages(program: LocationProgram) {
  const { min_age_months: min, max_age_months_exclusive: max } = program
  if (min == null && max == null) return 'dob nije potvrđena'
  return `${min == null ? '?' : min}–${max == null ? '?' : max} mj.`
}

// ComparisonView sets up to three options side by side, one criterion per row.
// Unknown values say so explicitly; they are things to check, not a "no".
export function ComparisonView({ features, onRemove, onClose, openLink }: ComparisonViewProps) {
  const headingRef = useRef<HTMLHeadingElement>(null)
  useEffect(() => { headingRef.current?.focus({ preventScroll: true }) }, [])
  const notes = compareOptions(features)
  // Sandboxed MCP hosts block plain navigation, so links go through the host.
  const open = (event: MouseEvent<HTMLAnchorElement>) => {
    if (!openLink) return
    event.preventDefault()
    openLink(event.currentTarget.href)
  }
  const link = (href: string, text: string) => <a href={href} target="_blank" rel="noreferrer" onClick={open}>{text} ↗</a>
  const anyDistance = features.some((feature) => feature.properties.distance_m != null)
  const rows: [string, (feature: LocationFeature) => ReactNode][] = [
    ...(anyDistance ? [['Udaljenost', (feature: LocationFeature) => feature.properties.distance_m == null
      ? <span className="comparison-unknown">Bez potvrđenih koordinata</span>
      : `${formatDistance(feature.properties.distance_m)} zračno`] as [string, (feature: LocationFeature) => ReactNode]] : []),
    ['Vrsta', (feature) => providerLabels[feature.properties.provider_kind]],
    ['Adresa', (feature) => [feature.properties.address ?? 'Adresa nije poznata', feature.properties.district]
      .filter(Boolean).join(', ')],
    ['Programi i dob', (feature) => (feature.properties.programs ?? []).length
      ? <ul>{feature.properties.programs!.map((program) => <li key={program.program_id}>{program.name} · {ages(program)}</li>)}</ul>
      : unknown],
    ['Upis', (feature) => {
      const round = currentRound(feature.properties.enrolment ?? [])
      if (!round) return unknown
      return <>
        <span className="enrolment-status" data-status={round.status}>{enrolmentStatusLabels[round.status]}</span>
        <p>{round.round === 'main' ? 'Glavni upis' : 'Upis tijekom godine'} {round.academic_year}{round.closes_at && ` · rok ${enrolmentInstant(round.closes_at)}`}</p>
      </>
    }],
    ['Sufinanciranje', (feature) => (feature.properties.subsidy_policies ?? []).length
      ? <ul>{feature.properties.subsidy_policies!.map((policy) => <li key={policy.policy_key}>{policy.summary}</li>)}</ul>
      : unknown],
    ['Kontakt', (feature) => {
      const { phone, email } = feature.properties
      const website = websiteHref(feature.properties.website_url)
      if (!phone && !email && !website) return unknown
      return <ul>
        {phone && <li>{phone}</li>}
        {email && <li>{email}</li>}
        {website && <li>{link(website, 'Web stranica')}</li>}
      </ul>
    }],
    ['Prednosti', (feature) => {
      const strengths = notes.get(feature.id)!.strengths
      return strengths.length ? <ul>{strengths.map((text) => <li key={text}>{text}</li>)}</ul>
        : <span className="comparison-unknown">Nema istaknutih prednosti u dostupnim podacima</span>
    }],
    ['Provjeriti', (feature) => {
      const checks = notes.get(feature.id)!.checks
      return checks.length ? <ul>{checks.map((text) => <li key={text}>{text}</li>)}</ul> : '—'
    }],
    ['Sljedeći korak', (feature) => {
      const next = notes.get(feature.id)!.next
      return next.href ? link(next.href, next.label) : next.label
    }],
    ['Izvori', (feature) => <ul>{feature.properties.sources.map((source, index) => {
      const href = websiteHref(source.url)
      return <li key={index}>{href ? link(href, source.name) : source.name}</li>
    })}</ul>],
  ]

  return <section className="comparison-view" aria-labelledby="comparison-title"
    onKeyDown={(event) => { if (event.key === 'Escape') { event.preventDefault(); onClose() } }}>
    <header className="comparison-header">
      <h2 id="comparison-title" ref={headingRef} tabIndex={-1}>Usporedba vrtića</h2>
      <button type="button" className="location-details-close" aria-label="Zatvori usporedbu" onClick={onClose}><X aria-hidden="true" /></button>
    </header>
    <div className="comparison-scroll">
      <table>
        <thead>
          <tr>
            <td />
            {features.map((feature) => <th key={feature.id} scope="col">
              <span>{feature.properties.location_name}</span>
              <button type="button" className="comparison-remove" onClick={() => onRemove(feature.id)}
                aria-label={`Ukloni iz usporedbe: ${feature.properties.location_name}`}><X aria-hidden="true" /></button>
            </th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map(([label, cell]) => <tr key={label}>
            <th scope="row">{label}</th>
            {features.map((feature) => <td key={feature.id}>{cell(feature)}</td>)}
          </tr>)}
        </tbody>
      </table>
    </div>
    <p className="location-details-note comparison-footnote">Objavljena slobodna mjesta još nisu dio podataka. „Nije potvrđeno” znači da podatak treba provjeriti, a ne da uvjet nije ispunjen. Usporedba nije jamstvo upisa.</p>
  </section>
}
