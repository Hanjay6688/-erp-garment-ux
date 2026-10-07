import type { ReactNode } from 'react'
import { createPortal } from 'react-dom'

// Modals, drawers and popdowns render at the end of <body>. Rendered in place,
// an overlay inherits its host's stacking context (a sticky list, a
// transformed card) and its descendant selectors (`.wh-browser header span`),
// so it can slide under a sticky header or pick up the host's letter-spacing.
export default function OverlayPortal({ children }: { children: ReactNode }) {
  if (typeof document === 'undefined') return <>{children}</>
  return createPortal(children, document.body)
}
