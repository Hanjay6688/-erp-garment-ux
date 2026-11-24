import type { ReactNode } from 'react'

export type MobileDestination = { id: string; label: string; icon: ReactNode }

/** The shell supplies only destinations admitted by its existing route/permission checks. */
export default function MobilePrimaryNavigation({ items, current, menuOpen, onNavigate, onMore }: {
  items: MobileDestination[]
  current: string
  menuOpen: boolean
  onNavigate: (id: string) => void
  onMore: () => void
}) {
  return <nav className="mobile-primary-nav" aria-label="Navigasi cepat">
    {items.slice(0, 4).map(item => <button type="button" key={item.id}
      aria-current={current === item.id ? 'page' : undefined}
      onClick={() => { if (current !== item.id) onNavigate(item.id) }}>
      {item.icon}<span>{item.label}</span>
    </button>)}
    <button type="button" aria-label="Lainnya, buka menu lengkap" aria-expanded={menuOpen} onClick={onMore}>
      <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/>
        <path d="M7 12h.01M12 12h.01M17 12h.01" strokeWidth="3" strokeLinecap="round"/></svg>
      <span>Lainnya</span>
    </button>
  </nav>
}
