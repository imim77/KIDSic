import type { MouseEvent } from 'react'
import { Badge } from '../ui/badge'
import type { SubsidyPolicy } from './types'
import { websiteHref } from './links'

const money = new Intl.NumberFormat('hr-HR', { style: 'currency', currency: 'EUR' })
const date = (value: string) => new Intl.DateTimeFormat('hr-HR').format(new Date(`${value}T00:00:00`))

// SubsidyDetails keeps city funding separate from the family's monthly payment.
export function SubsidyDetails({ policies, openLink }: { policies: SubsidyPolicy[]; openLink?: (url: string) => void }) {
  const open = (event: MouseEvent<HTMLAnchorElement>) => {
    if (!openLink) return
    event.preventDefault()
    openLink(event.currentTarget.href)
  }
  return <section className="subsidy-details" aria-label="Gradsko sufinanciranje">
    <h3>Gradsko sufinanciranje</h3>
    {policies.length === 0
      ? <p className="location-details-note">Za ovaj objekt nema potvrđenog podatka o gradskom sufinanciranju. Provjerite uvjete s vrtićem ili nadležnim gradskim uredom.</p>
      : policies.map((policy) => <article className="subsidy-policy" key={policy.policy_key}>
        <div className="subsidy-policy-heading">
          <h4>{policy.title}</h4>
          {policy.verification_status === 'partial' && <Badge variant="secondary">Iznos nije potvrđen</Badge>}
        </div>
        <p className="subsidy-summary">{policy.summary}</p>
        <p className="subsidy-caption">{policy.amount_kind === 'parent_fee' ? 'Roditeljska cijena' : 'Gradski udio'} · mjesečno po djetetu</p>
        <p className="subsidy-dates">Provjereno {date(policy.verified_on)}
          {(policy.valid_from || policy.valid_until) && <><br />Razdoblje: {policy.valid_from ? date(policy.valid_from) : 'početak nije potvrđen'}{policy.valid_until ? ` – ${date(policy.valid_until)}` : ' · završetak nije potvrđen'}</>}
        </p>
        <details>
          <summary>Tarife, olakšice i uvjeti</summary>
          {policy.rates.length > 0 && <ul className="subsidy-rates" aria-label="Mjesečne tarife">
            {policy.rates.map((rate, index) => <li key={index}>
              <span>{rate.label}</span>
              <strong>
                {rate.city_subsidy_cents != null && <span>Grad: {money.format(rate.city_subsidy_cents / 100)}</span>}
                {rate.parent_fee_cents != null && <span>Roditelj: {money.format(rate.parent_fee_cents / 100)}</span>}
              </strong>
            </li>)}
          </ul>}
          {policy.conditions.length > 0 && <><h5>Uvjeti</h5><ul>{policy.conditions.map((condition, i) => <li key={i}>{condition}</li>)}</ul></>}
          {policy.reliefs.length > 0 && <><h5>Olakšice</h5><ul>{policy.reliefs.map((relief, i) => <li key={i}>{relief}</li>)}</ul></>}
          {policy.notes.length > 0 && <><h5>Dodatne informacije</h5><ul>{policy.notes.map((note, i) => <li key={i}>{note}</li>)}</ul></>}
        </details>
        <p className="subsidy-caption">Pravo ovisi o programu, obiteljskim okolnostima i odobrenju Grada. Iznos nije potvrda prava vaše obitelji.</p>
        <div className="subsidy-links">{policy.sources.map((source, index) => {
          const href = websiteHref(source.url)
          return href ? <a key={index} href={href} target="_blank" rel="noreferrer" onClick={open}>{source.title} ↗</a> : null
        })}</div>
      </article>)}
  </section>
}
