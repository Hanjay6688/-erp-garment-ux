import { useCallback, useEffect, useId, useLayoutEffect, useMemo, useRef, useState } from 'react'
import type { CSSProperties, KeyboardEvent as ReactKeyboardEvent } from 'react'
import { Check, ChevronDown, Search } from 'lucide-react'
import OverlayPortal from './OverlayPortal'
import './browse-picker.css'

export type BrowseOption = {
  id: string
  label: string
  detail?: string
  meta?: string
  group?: string
  keywords?: string
  disabled?: boolean
}

type BrowsePickerProps = {
  label: string
  value: string | null
  options: BrowseOption[]
  onChange: (id: string) => void
  placeholder?: string
  searchPlaceholder?: string
  emptyText?: string
  disabled?: boolean
  className?: string
}

const PANEL_GAP = 6
const VIEWPORT_MARGIN = 8
const PANEL_MIN_WIDTH = 320
const PANEL_MAX_HEIGHT = 440

export function matchesBrowseQuery(option: BrowseOption, query: string) {
  const tokens = query.trim().toLowerCase().split(/\s+/).filter(Boolean)
  if (tokens.length === 0) return true
  const haystack = [option.label, option.detail, option.meta, option.group, option.keywords].filter(Boolean).join(' ').toLowerCase()
  return tokens.every((token) => haystack.includes(token))
}

// A field that opens a searchable, grouped list (popdown) instead of one long
// flat <select>: type to narrow, arrow keys to move, Enter to pick, Esc to close.
export default function BrowsePicker({
  label,
  value,
  options,
  onChange,
  placeholder = 'Pilih…',
  searchPlaceholder = 'Cari…',
  emptyText = 'Tidak ada yang cocok. Coba kata lain.',
  disabled = false,
  className = '',
}: BrowsePickerProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [activeId, setActiveId] = useState<string | null>(null)
  const [panelStyle, setPanelStyle] = useState<CSSProperties>({})
  const triggerRef = useRef<HTMLButtonElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLUListElement>(null)
  const baseId = useId()
  const labelId = `${baseId}-label`
  const listId = `${baseId}-list`
  const optionDomId = (id: string) => `${baseId}-opt-${id.replace(/[^A-Za-z0-9_-]/g, '_')}`

  const selected = options.find((option) => option.id === value) ?? null
  const filtered = useMemo(() => options.filter((option) => matchesBrowseQuery(option, query)), [options, query])
  const selectable = useMemo(() => filtered.filter((option) => !option.disabled), [filtered])
  const groups = useMemo(() => {
    const result: { name: string; items: BrowseOption[] }[] = []
    for (const option of filtered) {
      const name = option.group ?? ''
      const current = result[result.length - 1]
      if (current && current.name === name) current.items.push(option)
      else result.push({ name, items: [option] })
    }
    return result
  }, [filtered])

  const place = useCallback(() => {
    const trigger = triggerRef.current
    if (!trigger) return
    const rect = trigger.getBoundingClientRect()
    const width = Math.min(Math.max(rect.width, PANEL_MIN_WIDTH), window.innerWidth - VIEWPORT_MARGIN * 2)
    const left = Math.min(Math.max(rect.left, VIEWPORT_MARGIN), window.innerWidth - width - VIEWPORT_MARGIN)
    const below = window.innerHeight - rect.bottom - PANEL_GAP - VIEWPORT_MARGIN
    const above = rect.top - PANEL_GAP - VIEWPORT_MARGIN
    const openUp = below < 260 && above > below
    const maxHeight = Math.max(180, Math.min(PANEL_MAX_HEIGHT, openUp ? above : below))
    setPanelStyle(openUp
      ? { left, width, maxHeight, bottom: window.innerHeight - rect.top + PANEL_GAP }
      : { left, width, maxHeight, top: rect.bottom + PANEL_GAP })
  }, [])

  const close = useCallback((refocus: boolean) => {
    setOpen(false)
    setQuery('')
    if (refocus) triggerRef.current?.focus()
  }, [])

  const choose = (option: BrowseOption) => {
    if (option.disabled) return
    onChange(option.id)
    close(true)
  }

  useLayoutEffect(() => {
    if (!open) return
    place()
    inputRef.current?.focus()
  }, [open, place])

  useEffect(() => {
    if (!open) return
    const onPointer = (event: MouseEvent) => {
      const target = event.target as Node
      if (panelRef.current?.contains(target) || triggerRef.current?.contains(target)) return
      close(false)
    }
    const onReflow = () => place()
    document.addEventListener('mousedown', onPointer)
    window.addEventListener('resize', onReflow)
    window.addEventListener('scroll', onReflow, true)
    return () => {
      document.removeEventListener('mousedown', onPointer)
      window.removeEventListener('resize', onReflow)
      window.removeEventListener('scroll', onReflow, true)
    }
  }, [open, place, close])

  // Keep the highlighted row valid while the list narrows.
  useEffect(() => {
    if (!open) return
    if (activeId && selectable.some((option) => option.id === activeId)) return
    const preferred = selectable.find((option) => option.id === value) ?? selectable[0]
    setActiveId(preferred?.id ?? null)
  }, [open, selectable, activeId, value])

  useEffect(() => {
    if (!open || !activeId) return
    const row = document.getElementById(`${baseId}-opt-${activeId.replace(/[^A-Za-z0-9_-]/g, '_')}`)
    row?.scrollIntoView?.({ block: 'nearest' })
  }, [open, activeId, baseId])

  const move = (step: number) => {
    if (selectable.length === 0) return
    const index = selectable.findIndex((option) => option.id === activeId)
    const next = index < 0 ? 0 : (index + step + selectable.length) % selectable.length
    setActiveId(selectable[next].id)
  }

  const onSearchKey = (event: ReactKeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'ArrowDown') { event.preventDefault(); move(1) }
    else if (event.key === 'ArrowUp') { event.preventDefault(); move(-1) }
    else if (event.key === 'Home' && selectable.length) { event.preventDefault(); setActiveId(selectable[0].id) }
    else if (event.key === 'End' && selectable.length) { event.preventDefault(); setActiveId(selectable[selectable.length - 1].id) }
    else if (event.key === 'Enter') {
      event.preventDefault()
      const option = selectable.find((item) => item.id === activeId)
      if (option) choose(option)
    } else if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close(true) }
    else if (event.key === 'Tab') close(false)
  }

  return <div className={`browse-picker ${open ? 'open' : ''} ${className}`.trim()}>
    <span className="browse-picker-label" id={labelId}>{label}</span>
    <button
      ref={triggerRef}
      type="button"
      className="browse-picker-trigger"
      aria-haspopup="listbox"
      aria-expanded={open}
      aria-labelledby={labelId}
      aria-describedby={selected ? `${baseId}-value` : undefined}
      disabled={disabled}
      onClick={() => (open ? close(false) : setOpen(true))}
      onKeyDown={(event) => {
        if (!open && (event.key === 'ArrowDown' || event.key === 'ArrowUp')) { event.preventDefault(); setOpen(true) }
      }}
    >
      <span className="browse-picker-value" id={`${baseId}-value`}>
        {selected ? <><strong>{selected.label}</strong>{selected.detail ? <small>{selected.detail}</small> : null}</> : <em>{placeholder}</em>}
      </span>
      {selected?.meta ? <b className="browse-picker-meta">{selected.meta}</b> : null}
      <ChevronDown aria-hidden="true"/>
    </button>
    {open ? <OverlayPortal>
      <div ref={panelRef} className="browse-picker-panel" style={panelStyle}>
        <label className="browse-picker-search">
          <Search aria-hidden="true"/>
          <input
            ref={inputRef}
            role="combobox"
            aria-expanded="true"
            aria-controls={listId}
            aria-autocomplete="list"
            aria-activedescendant={activeId ? optionDomId(activeId) : undefined}
            aria-label={`Cari ${label.toLowerCase()}`}
            value={query}
            placeholder={searchPlaceholder}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={onSearchKey}
          />
          <small>{filtered.length} / {options.length}</small>
        </label>
        <ul ref={listRef} id={listId} role="listbox" aria-labelledby={labelId} className="browse-picker-list">
          {groups.map((group) => <li key={group.name || '—'} role="presentation" className="browse-picker-group">
            {group.name ? <span className="browse-picker-group-name" aria-hidden="true">{group.name}</span> : null}
            <ul role="group" aria-label={group.name || undefined}>
              {group.items.map((option) => {
                const isSelected = option.id === value
                return <li
                  key={option.id}
                  id={optionDomId(option.id)}
                  role="option"
                  aria-selected={isSelected}
                  aria-disabled={option.disabled || undefined}
                  className={`browse-picker-option${option.id === activeId ? ' active' : ''}${isSelected ? ' selected' : ''}${option.disabled ? ' disabled' : ''}`}
                  onMouseDown={(event) => event.preventDefault()}
                  onMouseEnter={() => { if (!option.disabled) setActiveId(option.id) }}
                  onClick={() => choose(option)}
                >
                  <span><strong>{option.label}</strong>{option.detail ? <small>{option.detail}</small> : null}</span>
                  {option.meta ? <b>{option.meta}</b> : null}
                  {isSelected ? <Check aria-hidden="true"/> : <i aria-hidden="true"/>}
                </li>
              })}
            </ul>
          </li>)}
          {filtered.length === 0 ? <li role="presentation" className="browse-picker-empty">{emptyText}</li> : null}
        </ul>
      </div>
    </OverlayPortal> : null}
  </div>
}
