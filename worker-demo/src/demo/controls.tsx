import { Icon } from '../components/AppIcon'
import { useState } from 'react'
import type { ReactNode } from 'react'

export function MultiCheckFilter({ label, options, selected, onChange }: {
  label: string; options: string[]; selected: string[]; onChange: (values: string[]) => void
}) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const allSelected = selected.length === options.length
  const shownOptions = options.filter((option) => option.toLowerCase().includes(query.toLowerCase()))
  const toggle = (option: string) => onChange(selected.includes(option) ? selected.filter((value) => value !== option) : [...selected, option])

  return <div className={`multi-filter ${open ? 'is-open' : ''}`}>
    <button className="filter-trigger" aria-expanded={open} onClick={() => setOpen(!open)}>
      <Icon name="filter" /><span>{label}</span><b>{allSelected ? 'Semua' : selected.length}</b><Icon name="chevron" />
    </button>
    {open && <>
      <button className="filter-page-shield" aria-label={`Tutup filter ${label}`} onClick={() => setOpen(false)} />
      <div className="filter-sheet" role="dialog" aria-label={`Filter ${label}`}>
        <div className="filter-sheet-handle" />
        <div className="filter-sheet-head"><div><small>FILTER</small><strong>{label}</strong></div><button aria-label="Tutup" onClick={() => setOpen(false)}><Icon name="close" /></button></div>
        <div className="filter-option-search"><Icon name="search" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={`Cari ${label.toLowerCase()}...`} /></div>
        <div className="filter-bulk"><label><input type="checkbox" checked={allSelected} onChange={() => onChange(allSelected ? [] : [...options])} /> Pilih semua</label><button onClick={() => onChange([])}>Kosongkan</button></div>
        <div className="filter-options">{shownOptions.map((option) => <label key={option}><input type="checkbox" checked={selected.includes(option)} onChange={() => toggle(option)} /><span>{option}</span></label>)}</div>
        <button className="filter-apply" onClick={() => setOpen(false)}>Terapkan · {selected.length} dipilih</button>
      </div>
    </>}
  </div>
}

export function Field({ label, children }: { label: string; children: ReactNode }) { return <label className="field"><span>{label}</span>{children}</label> }
