import { useEffect, useRef, type ComponentType, type MouseEvent, type ReactNode } from 'react'
import {
  ArrowRight, BookOpen, Building2, CalendarCheck, Check, Info, Link2, MapPin, Phone, Ruler, Search, Sparkles,
  Wallet, X,
} from 'lucide-react'
import { useMediaQuery } from '../explorer/useMediaQuery'
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

type Row = { label: string; icon: ComponentType<{ 'aria-hidden'?: boolean }>; tone: string; cell: (feature: LocationFeature) => ReactNode }

const unknown = (text = 'Nije potvrđeno') => <span className="comparison-unknown">{text}</span>

function ages(program: LocationProgram) {
  const { min_age_months: min, max_age_months_exclusive: max } = program
  if (min == null && max == null) return 'dob nije potvrđena'
  return `${min == null ? '?' : min}–${max == null ? '?' : max} mj.`
}

// ComparisonView sets up to three options side by side, one criterion per row.
// Each option keeps one card colour from header to last row so the eye can
// follow it. Phones get one criterion per section instead of a wide table.
// Unknown values say so explicitly; they are things to check, not a "no".
export function ComparisonView({ features, onRemove, onClose, openLink }: ComparisonViewProps) {
  const headingRef = useRef<HTMLHeadingElement>(null)
  const stacked = useMediaQuery('(max-width: 650px)', false)
  useEffect(() => { headingRef.current?.focus({ preventScroll: true }) }, [])
  const notes = compareOptions(features)
  // Sandboxed MCP hosts block plain navigation, so links go through the host.
  const open = (event: MouseEvent<HTMLAnchorElement>) => {
    if (!openLink) return
    event.preventDefault()
    openLink(event.currentTarget.href)
  }
  const link = (href: string, text: string, className?: string) =>
    <a className={className} href={href} target="_blank" rel="noreferrer" onClick={open}>{text} ↗</a>
  const anyDistance = features.some((feature) => feature.properties.distance_m != null)
  const rows: Row[] = [
    ...(anyDistance ? [{ label: 'Udaljenost', icon: Ruler, tone: 'sky', cell: (feature: LocationFeature) =>
      feature.properties.distance_m == null ? unknown('Bez potvrđenih koordinata')
        : <><strong className="comparison-figure">{formatDistance(feature.properties.distance_m)}</strong> zračno</> }] : []),
    { label: 'Adresa', icon: MapPin, tone: 'blush', cell: (feature) => <>
      <span className="comparison-address">{feature.properties.address ?? 'Adresa nije poznata'}</span>
      {feature.properties.district && <span className="comparison-sticker">{feature.properties.district}</span>}
    </> },
    { label: 'Programi i dob', icon: BookOpen, tone: 'lilac', cell: (feature) => (feature.properties.programs ?? []).length
      ? <ul className="comparison-tags">{feature.properties.programs!.map((program) =>
        <li key={program.program_id}>{program.name} <small>{ages(program)}</small></li>)}</ul>
      : unknown() },
    { label: 'Upis', icon: CalendarCheck, tone: 'mint', cell: (feature) => {
      const round = currentRound(feature.properties.enrolment ?? [])
      if (!round) return unknown()
      return <>
        <span className="enrolment-status" data-status={round.status}>{enrolmentStatusLabels[round.status]}</span>
        <p>{round.round === 'main' ? 'Glavni upis' : 'Upis tijekom godine'} {round.academic_year}</p>
        {round.closes_at && <p className="comparison-fine">Rok {enrolmentInstant(round.closes_at)}</p>}
      </>
    } },
    { label: 'Sufinanciranje', icon: Wallet, tone: 'apricot', cell: (feature) => (feature.properties.subsidy_policies ?? []).length
      ? <ul className="comparison-plain">{feature.properties.subsidy_policies!.map((policy) => <li key={policy.policy_key}>{policy.summary}</li>)}</ul>
      : unknown() },
    { label: 'Kontakt', icon: Phone, tone: 'sky', cell: (feature) => {
      const { phone, email } = feature.properties
      const website = websiteHref(feature.properties.website_url)
      if (!phone && !email && !website) return unknown()
      return <ul className="comparison-plain">
        {phone && <li>{phone}</li>}
        {email && <li className="comparison-wrap">{email}</li>}
        {website && <li>{link(website, 'Web stranica')}</li>}
      </ul>
    } },
    { label: 'Prednosti', icon: Sparkles, tone: 'lemon', cell: (feature) => {
      const strengths = notes.get(feature.id)!.strengths
      return strengths.length
        ? <ul className="comparison-marks" data-kind="strength">{strengths.map((text) => <li key={text}><Check aria-hidden="true" />{text}</li>)}</ul>
        : unknown('Nema istaknutih prednosti u dostupnim podacima')
    } },
    { label: 'Provjeriti', icon: Search, tone: 'blush', cell: (feature) => {
      const checks = notes.get(feature.id)!.checks
      return checks.length
        ? <ul className="comparison-marks" data-kind="check">{checks.map((text) => <li key={text}><Search aria-hidden="true" />{text}</li>)}</ul>
        : '—'
    } },
    { label: 'Sljedeći korak', icon: ArrowRight, tone: 'mint', cell: (feature) => {
      const next = notes.get(feature.id)!.next
      return next.href ? link(next.href, next.label, 'comparison-next') : <span className="comparison-next">{next.label}</span>
    } },
    { label: 'Izvori', icon: Link2, tone: 'lilac', cell: (feature) => <ul className="comparison-plain comparison-fine">
      {feature.properties.sources.map((source, index) => {
        const href = websiteHref(source.url)
        return <li key={index}>{href ? link(href, source.name) : source.name}</li>
      })}
    </ul> },
  ]

  const option = (feature: LocationFeature, index: number) => <div className="comparison-option" data-col={index}>
    <span className="comparison-option-icon" aria-hidden="true"><Building2 /></span>
    <span className="comparison-option-text">
      <span className="comparison-kind">{providerLabels[feature.properties.provider_kind]}</span>
      <span className="comparison-option-name">{feature.properties.location_name}</span>
    </span>
    <button type="button" className="comparison-remove" onClick={() => onRemove(feature.id)}
      aria-label={`Ukloni iz usporedbe: ${feature.properties.location_name}`}><X aria-hidden="true" /></button>
  </div>

  return <section className="comparison-view" aria-labelledby="comparison-title"
    onKeyDown={(event) => { if (event.key === 'Escape') { event.preventDefault(); onClose() } }}>
    <header className="comparison-header">
      <div>
        <h2 id="comparison-title" ref={headingRef} tabIndex={-1}>Usporedba vrtića</h2>
        <p>{features.length} vrtića jedan uz drugi · samo potvrđeni podaci</p>
      </div>
      <button type="button" className="location-details-close" aria-label="Zatvori usporedbu" onClick={onClose}><X aria-hidden="true" /></button>
    </header>
    {stacked
      ? <div className="comparison-sheet comparison-stack">
        <ul className="comparison-options" aria-label="Vrtići u usporedbi">
          {features.map((feature, index) => <li key={feature.id}>{option(feature, index)}</li>)}
        </ul>
        {rows.map(({ label, icon: Icon, tone, cell }) => <section key={label} className="comparison-criterion" aria-label={label}>
          <h3 className="comparison-row-label"><span className="comparison-row-icon" data-tone={tone}><Icon aria-hidden /></span>{label}</h3>
          {features.map((feature, index) => <div key={feature.id} className="comparison-cell" data-col={index}>
            <p className="comparison-cell-name">{feature.properties.location_name}</p>
            {cell(feature)}
          </div>)}
        </section>)}
      </div>
      : <div className="comparison-sheet">
        <div className="comparison-scroll">
          <table>
            <thead>
              <tr>
                <td />
                {features.map((feature, index) => <th key={feature.id} scope="col">{option(feature, index)}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map(({ label, icon: Icon, tone, cell }) => <tr key={label}>
                <th scope="row"><span className="comparison-row-label"><span className="comparison-row-icon" data-tone={tone}><Icon aria-hidden /></span>{label}</span></th>
                {features.map((feature, index) => <td key={feature.id}><div className="comparison-cell" data-col={index}>{cell(feature)}</div></td>)}
              </tr>)}
            </tbody>
          </table>
        </div>
      </div>}
    <p className="comparison-footnote"><Info aria-hidden="true" />Objavljena slobodna mjesta još nisu dio podataka. „Nije potvrđeno” znači da podatak treba provjeriti, a ne da uvjet nije ispunjen. Usporedba nije jamstvo upisa.</p>
  </section>
}
