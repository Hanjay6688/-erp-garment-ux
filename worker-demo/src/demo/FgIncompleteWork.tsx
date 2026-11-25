import { useState } from 'react'
import type { ReadyFgNotaComponent, RegularFgNotaSnapshot } from '../fgNota'
import { amountText } from './accessoryPricing'
import { laborBomComponents } from './laundryModel'
import { ReasonDialog } from './planner/ReasonDialog'
import './fgIncompleteWork.css'

type Selections = Pick<RegularFgNotaSnapshot, 'bsComponents' | 'stuckComponents'>

const sumRate = (rows: ReadyFgNotaComponent[]) => rows.reduce((sum, row) => sum + row.rate, 0)
const common = laborBomComponents.filter(row => row.id !== 'jahit-utama')
const finishing = common.filter(row => !row.required || row.id === 'finishing-detail')

export function FgIncompleteWork({ source, bs, hold, value, onClose, onSave }: {
  source: string; bs: number; hold: number; value: Selections
  onClose: () => void; onSave: (next: Selections) => void
}) {
  const [chosen, setChosen] = useState(value)
  function group(key: keyof Selections, label: string, qty: number, catalog: ReadyFgNotaComponent[]) {
    const selected = chosen[key]
    const options = [...new Map([...catalog, ...value[key]].map(row => [row.id, row])).values()]
    return <fieldset className="fg-incomplete-group" aria-label={label}>
      <legend>{label} · <strong>{qty} pcs</strong></legend>
      {options.map(row => <label key={row.id}>
        <input type="checkbox" checked={selected.some(c => c.id === row.id)} onChange={e => {
          const next = e.target.checked ? [...selected, row] : selected.filter(c => c.id !== row.id)
          setChosen(current => ({ ...current, [key]: next }))
        }}/>
        <span>{row.name}</span><strong>{amountText(row.rate)}/pcs</strong>
      </label>)}
      <p>{qty} pcs × {amountText(sumRate(selected))} = <strong>{amountText(qty * sumRate(selected))}</strong></p>
    </fieldset>
  }
  return <ReasonDialog title="Atur komponen BS & Stuck" closeLabel="Kembali" onClose={onClose}>
    <div className="fg-incomplete-work">
      <p>{source}</p>
      <p>Centang pekerjaan yang belum selesai untuk tiap kelompok.</p>
      {bs > 0 && group('bsComponents', 'BS belum dikerjakan', bs, common)}
      {hold > 0 && group('stuckComponents', 'Stuck belum dipasang', hold, finishing)}
      <button type="button" className="primary-btn" onClick={() => onSave(chosen)}>Terapkan ke kartu</button>
    </div>
  </ReasonDialog>
}
