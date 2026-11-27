import NumberEntry from '../../../src/components/NumberEntry'
import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'

export const countNumber = (value: number) => value.toLocaleString('id-ID', { maximumFractionDigits: 6 })

export function CountHeading({ icon: Icon, title, children }: { icon: LucideIcon; title: string; children?: ReactNode }) {
  return <header className="count-panel-head">
    <i aria-hidden="true"><Icon/></i><h2>{title}</h2>{children}
  </header>
}

export function CountAmount({ label, unit, value, onChange, invalid = false, row }: {
  label: string; unit: string; value: string; onChange: (value: string) => void; invalid?: boolean; row?: number
}) {
  return <span className="count-amount" data-invalid={invalid || undefined}>
    <NumberEntry integerError="Masukkan jumlah pcs bulat." aria-label={label} aria-invalid={invalid || undefined} inputMode={unit === 'pcs' ? 'numeric' : 'decimal'}
      data-grid-row={row} data-grid-col={row === undefined ? undefined : 0} autoComplete="off" value={value} placeholder="—" onValueChange={rawInput => onChange(rawInput)}
      onFocus={event => event.currentTarget.select()}/>
    <span aria-hidden="true">{unit}</span>
  </span>
}

export function CountDifference({ value, unit }: { value: number | null; unit: string }) {
  return <span className="count-difference" data-tone={value === null ? 'empty' : value < 0 ? 'short' : value > 0 ? 'over' : 'match'}>
    {value === null ? '—' : value === 0 ? 'Sesuai' : (value < 0 ? 'Kurang ' : 'Lebih ') + countNumber(Math.abs(value)) + ' ' + unit}
  </span>
}
