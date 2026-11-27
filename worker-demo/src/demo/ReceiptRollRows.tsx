import NumberEntry from '../../../src/components/NumberEntry'
import { useId } from 'react'
import { Icon } from '../components/AppIcon'
import { formatQuantity, parseDecimal } from './format'

type RollRow = { key: number | string; length: string }

export function ReceiptRollRows({ rows, unit, onChange, onRemove, byNumber = false, readLength = parseDecimal }: {
  rows: RollRow[]
  unit: 'yd' | 'm'
  onChange: (index: number, length: string) => void
  onRemove: (index: number) => void
  byNumber?: boolean
  readLength?: (value: string) => number
}) {
  const prefix = useId()
  const unitLabel = unit === 'm' ? 'Meter (m)' : 'Yard (yd)'
  const unitName = unit === 'm' ? 'meter' : 'yard'

  return <div className="roll-entry-list" data-keyboard-grid>
    {rows.map((row, index) => {
      const id = prefix + '-' + row.key
      const length = readLength(row.length)
      return <div className="roll-entry-row" key={row.key}>
        <span className="roll-number">{String(index + 1).padStart(2, '0')}</span>
        <div><label htmlFor={id}>{byNumber ? `Panjang (${unit})` : unitLabel + ' pada gulung'}</label>
          <div className="yard-input"><NumberEntry id={id} aria-label={byNumber ? `Panjang roll ${index + 1}` : undefined}
            data-grid-row={index} data-grid-col={0} inputMode="decimal" value={row.length} placeholder="0"
            onValueChange={rawInput => onChange(index, rawInput)}/><span>{unit}</span></div></div>
        <small>{length > 0 ? `${formatQuantity(length, byNumber ? 6 : undefined)} ${unitName} siap diterima` : row.length.trim() && byNumber ? 'Periksa panjang' : 'Belum diisi'}</small>
        <button type="button" className="remove-roll" aria-label={`Hapus roll ${index + 1}`} disabled={rows.length === 1}
          onClick={() => onRemove(index)}><Icon name="trash"/></button>
      </div>
    })}
  </div>
}
