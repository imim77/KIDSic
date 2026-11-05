import { useEffect, useRef, type ComponentType, type CSSProperties, type MouseEvent, type ReactNode } from 'react'
import gsap from 'gsap'
import { useGSAP } from '@gsap/react'
import {
  ArrowRight, BookOpen, Building2, CalendarCheck, Check, Link2, MapPin, Phone, Ruler, Search, Sparkles, Users,
  Wallet, X,
} from 'lucide-react'
import { reducedMotion } from '../motion/reducedMotion'
import { compareOptions } from './comparison'
import { currentRound, enrolmentInstant, enrolmentStatusLabels } from './enrolment'
import { formatDistance } from './distance'
import { websiteHref } from './links'
import { providerLabels, type LocationFeature, type LocationProgram } from './types'
import { publishedVacancies, vacancyDate, vacancyLabel } from './vacancies'

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

// ComparisonView sets up to three options side by side, each one coloured card
// holding every criterion. Subgrid rows keep the same criterion level across
// cards; phones swipe between cards. Unknown values say so explicitly; they
// are things to check, not a "no".
export function ComparisonView({ features, onRemove, onClose, openLink }: ComparisonViewProps) {
  const rootRef = useRef<HTMLElement>(null)
  const closeRef = useRef<HTMLButtonElement>(null)
  useEffect(() => { closeRef.current?.focus({ preventScroll: true }) }, [])
  // Cards rise in one after another, then their criteria settle in; clearing
  // props afterwards leaves hover styles and scrolling untouched.
  useGSAP(() => {
    if (reducedMotion()) return
    gsap.timeline({ defaults: { ease: 'power3.out', clearProps: 'opacity,transform' } })
      .from('.comparison-card', { opacity: 0, y: 36, rotate: (index) => [-2, 1.5, -1][index] ?? 0, duration: 0.5, stagger: 0.09 })
      // Stagger by criterion, not DOM order, so all cards fill in together.
      .from('.comparison-field', { opacity: 0, x: -10, duration: 0.3,
        stagger: (_, target: Element) => [...target.parentElement!.children].indexOf(target) * 0.035 }, '-=0.35')
  }, { scope: rootRef })
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
    { label: 'Slobodna mjesta', icon: Users, tone: 'sky', cell: (feature) => {
      const vacancies = publishedVacancies(feature.properties)
      if (vacancies.state === 'unpublished') return unknown('Nisu objavljena')
      const { total, record, stale } = vacancies
      return <>
        <strong className="comparison-figure">{total === null ? 'Nepotpuno' : vacancyLabel(total)}</strong>
        <span className="comparison-sticker" data-stale={stale}>Stanje {vacancyDate(record.reference_date)}</span>
        {record.scope === 'institution' && <p className="comparison-fine">Za cijelu ustanovu</p>}
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

  return <section ref={rootRef} className="comparison-view" aria-label="Usporedba vrtića"
    onKeyDown={(event) => { if (event.key === 'Escape') { event.preventDefault(); onClose() } }}>
    <button ref={closeRef} type="button" className="location-details-close comparison-close" aria-label="Zatvori usporedbu" onClick={onClose}><X aria-hidden="true" /></button>
    <div className="comparison-scroll">
      <ul className="comparison-grid" aria-label="Vrtići u usporedbi"
        style={{ '--options': features.length, '--fields': rows.length } as CSSProperties}>
        {features.map((feature, index) => <li key={feature.id} className="comparison-card" data-col={index}
          style={{ gridColumn: index + 1 }} aria-label={feature.properties.location_name}>
          <div className="comparison-card-head">
            <span className="comparison-option-icon" aria-hidden="true"><Building2 /></span>
            <span className="comparison-option-text">
              <span className="comparison-kind">{providerLabels[feature.properties.provider_kind]}</span>
              <span className="comparison-option-name">{feature.properties.location_name}</span>
            </span>
            <button type="button" className="comparison-remove" onClick={() => onRemove(feature.id)}
              aria-label={`Ukloni iz usporedbe: ${feature.properties.location_name}`}><X aria-hidden="true" /></button>
          </div>
          <dl className="comparison-fields">
            {rows.map(({ label, icon: Icon, tone, cell }) => <div key={label} className="comparison-field">
              <dt><span className="comparison-row-icon" data-tone={tone}><Icon aria-hidden /></span>{label}</dt>
              <dd>{cell(feature)}</dd>
            </div>)}
          </dl>
        </li>)}
      </ul>
    </div>
  </section>
}
