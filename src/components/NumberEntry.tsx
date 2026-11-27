import { useEffect, useId, useRef, useState, type InputHTMLAttributes } from 'react'
import { NumericFormat } from 'react-number-format'

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, 'value' | 'defaultValue' | 'onChange' | 'children'> & {
  value: string | number
  onValueChange: (value: string) => void
  signed?: boolean
  rupiahDraft?: boolean
  integerError?: string
}

// Only the integer part may contain groups. Never round through a JS number here.
const groupedInteger = /^-?\d{1,3}(?:\.\d{3})+(?:,\d*)?$/
const localNumber = /^-?(?:(?:\d+|\d{1,3}(?:\.\d{3})+)(?:,\d*)?|,\d+)$/
const decimalKeys = [',']
const formatHint = 'Gunakan titik untuk ribuan dan koma untuk desimal, misalnya 1.250,75.'

function isLocalNumber(text: string, decimal: boolean, signed = false) {
  return localNumber.test(text) && (decimal || !text.includes(',')) && (signed || !text.startsWith('-'))
}

export function pastedPieceCounts(text: string): number[][] | null {
  const rows: number[][] = []
  for (const line of text.split('\n')) {
    const row: number[] = []
    for (const value of line.split('\t')) {
      const cell = value.trim()
      const count = Number(cell.replaceAll('.', ''))
      if ((cell && !isLocalNumber(cell, false)) || !Number.isSafeInteger(count)) return null
      row.push(count)
    }
    rows.push(row)
  }
  return rows
}

function storedDigits(value: string | number, rupiahDraft: boolean) {
  // Earlier rupiah drafts can already contain Indonesian thousands separators.
  // Other numeric drafts and server values use an ungrouped decimal point.
  const raw = String(value)
  return (rupiahDraft && typeof value === 'string' && groupedInteger.test(raw) ? raw.replaceAll('.', '') : raw).replace(',', '.')
}

function nativeNumber(value: string, min: Props['min'], max: Props['max'], step: Props['step']) {
  const field = document.createElement('input')
  field.type = 'number'
  if (min !== undefined) field.min = String(min)
  if (max !== undefined) field.max = String(max)
  if (step !== undefined) field.step = String(step)
  field.value = value
  return field
}

export default function NumberEntry(props: Props) {
  const { inputMode, type, signed, rupiahDraft, integerError, onValueChange, ...native } = props
  // Schema-driven editors also use the same slot for dates, codes and free text.
  if (type !== 'number' && inputMode !== 'numeric' && inputMode !== 'decimal') {
    return <input {...native} type={type} inputMode={inputMode} onChange={event => onValueChange(event.currentTarget.value)}/>
  }
  return <GroupedEntry {...props}/>
}

function GroupedEntry({ value, onValueChange, inputMode, type, signed = false, rupiahDraft = false,
  integerError = 'Masukkan bilangan bulat.', maxLength, min, max, step, pattern, onPaste, onKeyDown, onBlur, ...props }: Props) {
  const input = useRef<HTMLInputElement>(null)
  const keyboardSelection = useRef<{ text: string; start: number; end: number } | null>(null)
  const hintId = useId()
  const [message, setMessage] = useState('')
  const [editing, setEditing] = useState<string | null>(null)
  const spin = type === 'number'
  const decimal = inputMode === 'decimal' || (spin && step !== undefined && (step === 'any' || Number(step) % 1 !== 0))
  const source = storedDigits(value, rupiahDraft)
  // A numeric parent cannot represent an empty field, a trailing comma or a final zero.
  const raw = typeof value === 'number' && editing !== null && Number(editing) === value ? editing : source

  useEffect(() => {
    if (spin) input.current?.setCustomValidity(nativeNumber(raw, min, max, step).validationMessage)
  }, [spin, raw, min, max, step])

  function change(next: string) {
    setMessage('')
    if (typeof value === 'number') setEditing(next)
    onValueChange(rupiahDraft ? next.replace('.', ',') : next)
  }

  function restoreKeyboardSelection(field: HTMLInputElement) {
    const selection = keyboardSelection.current
    if (selection?.text === field.value) field.setSelectionRange(selection.start, selection.end)
  }

  function rememberKeyboardSelection(field: HTMLInputElement, start: number, end = start) {
    const selection = { text: field.value, start, end }
    keyboardSelection.current = selection
    requestAnimationFrame(() => {
      if (keyboardSelection.current === selection && document.activeElement === field) restoreKeyboardSelection(field)
    })
  }

  return <><NumericFormat {...props} type="text" getInputRef={input} value={raw} valueIsNumericString
    inputMode={decimal ? 'decimal' : 'numeric'} thousandSeparator="." decimalSeparator="," allowedDecimalSeparators={decimalKeys}
    allowNegative={signed} pattern={pattern === '[0-9]*' ? '[0-9.]*' : pattern}
    role={spin ? 'spinbutton' : props.role} aria-valuemin={spin && min !== undefined ? Number(min) : undefined}
    aria-valuemax={spin && max !== undefined ? Number(max) : undefined} aria-valuenow={spin && raw && Number.isFinite(Number(raw)) ? Number(raw) : undefined}
    aria-describedby={[props['aria-describedby'], message && hintId].filter(Boolean).join(' ') || undefined}
    isAllowed={({ value: next }) => {
      if (!decimal && next.includes('.')) { setMessage(integerError); return false }
      if (maxLength !== undefined && next.length > maxLength) { setMessage('Angka melebihi panjang kolom.'); return false }
      return true
    }}
    onValueChange={(values, info) => { if (info.source === 'event') change(values.value) }}
    onKeyDownCapture={event => {
      props.onKeyDownCapture?.(event)
      const key = event.key.toLowerCase()
      if (event.defaultPrevented || ['control', 'meta', 'shift', 'alt'].includes(key)) return
      const field = event.currentTarget
      // A formatter may restore the mobile caret on the next tick. Keep the
      // operator's more recent navigation until the following key or paste.
      restoreKeyboardSelection(field)
      const shortcut = event.ctrlKey || event.metaKey
      if (shortcut && key === 'v') return
      keyboardSelection.current = null
      const end = field.value.length
      if (shortcut && key === 'a') {
        rememberKeyboardSelection(field, 0, end)
        return
      }
      if (shortcut || event.altKey || event.shiftKey) return
      const startAt = field.selectionStart ?? end
      const endAt = field.selectionEnd ?? end
      let position: number
      switch (key) {
        case 'home': position = 0; break
        case 'end': position = end; break
        case 'arrowleft': position = startAt === endAt ? Math.max(0, startAt - 1) : startAt; break
        case 'arrowright': position = startAt === endAt ? Math.min(end, endAt + 1) : endAt; break
        default: return
      }
      rememberKeyboardSelection(field, position)
    }}
    onPointerDownCapture={event => { keyboardSelection.current = null; props.onPointerDownCapture?.(event) }}
    onPasteCapture={event => {
      restoreKeyboardSelection(event.currentTarget)
      keyboardSelection.current = null
      props.onPasteCapture?.(event)
    }}
    onPaste={event => {
      const text = event.clipboardData.getData('text').trim()
      if (onPaste && /[\t\n]/.test(text)) { onPaste(event); return }
      if (text && !isLocalNumber(text, decimal, signed)) {
        event.preventDefault()
        setMessage(!decimal && text.includes(',') ? integerError : formatHint)
      }
    }}
    onKeyDown={event => {
      onKeyDown?.(event)
      if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey) return
      if (spin && step !== 'any' && (event.key === 'ArrowUp' || event.key === 'ArrowDown')) {
        event.preventDefault()
        const field = nativeNumber(raw, min, max, step)
        if (event.key === 'ArrowUp') field.stepUp()
        else field.stepDown()
        change(field.value)
      }
      if (event.key === '.') {
        event.preventDefault()
        if (event.code === 'NumpadDecimal' && decimal) {
          const field = event.currentTarget
          field.setRangeText(',', field.selectionStart ?? field.value.length, field.selectionEnd ?? field.value.length, 'end')
          field.dispatchEvent(new Event('input', { bubbles: true }))
        } else {
          setMessage(decimal ? 'Titik ribuan muncul otomatis. Untuk pecahan, ketik koma.' : 'Titik ribuan muncul otomatis.')
        }
      }
    }}
    onBlur={event => { keyboardSelection.current = null; setEditing(null); setMessage(''); onBlur?.(event) }}
  />{message && <small id={hintId} role="alert">{message}</small>}</>
}
