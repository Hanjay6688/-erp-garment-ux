import type { FactValue } from '../../../../../src/cp7/contract'
import { formatFact } from '../../../../../src/cp7/workspace'

export function Fact({ label, fact }: { label: string; fact: FactValue }) {
  return <div className="f05-fact" data-fact-state={fact.state}><dt>{label}</dt><dd>{formatFact(fact)}</dd>
    <small>{'reason' in fact ? fact.reason : fact.state === 'ASSUMED' ? `Asumsi: ${fact.assumption_ids.join(', ')}` : 'Fakta pada snapshot'}</small>
    {fact.refs.length > 0 ? <details><summary>Sumber angka</summary><ul>{fact.refs.map(ref => <li key={`${ref.kind}/${ref.id}/${ref.revision}`}>{ref.kind}/{ref.id}@{ref.revision}</li>)}</ul></details> : null}
  </div>
}
export function Empty({ title, text }: { title: string; text: string }) {
  return <div className="f05-empty"><span className="f05-kicker">STATUS DATA</span><h2>{title}</h2><p>{text}</p></div>
}
export function downloadText(text: string, filename: string) {
  const url = URL.createObjectURL(new Blob([text], { type: 'text/plain;charset=utf-8' }))
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = filename; anchor.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
