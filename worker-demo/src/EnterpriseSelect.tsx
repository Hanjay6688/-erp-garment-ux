import { useEffect, useId, useRef, useState } from 'react'
import { Check, ChevronDown } from 'lucide-react'
import './enterprise-select.css'

type EnterpriseSelectProps = {
  label: string
  value: string
  options: string[]
  onChange: (value: string) => void
  className?: string
  disabled?: boolean
}

export default function EnterpriseSelect({
  label,
  value,
  options,
  onChange,
  className = '',
  disabled = false,
}: EnterpriseSelectProps) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const labelId = useId()

  useEffect(() => {
    if (!open) return
    const closeOnOutside = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', closeOnOutside)
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('mousedown', closeOnOutside)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [open])

  return (
    <div className={`enterprise-select ${open ? 'open' : ''} ${className}`} ref={rootRef}>
      <span id={labelId}>{label}</span>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-labelledby={labelId}
        disabled={disabled}
        onClick={() => setOpen((current) => !current)}
      >
        <strong>{value}</strong>
        <ChevronDown />
      </button>
      {open && (
        <div className="enterprise-select-menu" role="listbox" aria-labelledby={labelId}>
          {options.map((option) => {
            const active = option === value
            return (
              <button
                type="button"
                role="option"
                aria-selected={active}
                className={active ? 'active' : ''}
                key={option}
                onClick={() => {
                  onChange(option)
                  setOpen(false)
                }}
              >
                <span>{option}</span>
                {active && <Check />}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
