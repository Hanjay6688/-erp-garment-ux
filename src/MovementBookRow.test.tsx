// @vitest-environment jsdom

import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MovementBookRow } from './App'

let container: HTMLDivElement
let root: Root

const movement = {
  id: 'MV-TEST',
  sku: '73001',
  brand: 'Vivo',
  customer: 'Nusantara Fashion',
  date: '1 Sep 2026 · 10:00',
  ref: 'INV-TEST',
  type: 'Penjualan',
  note: 'Regression',
  delta: [-8, -8, -8] as [number, number, number],
  balance: [96, 84, 108] as [number, number, number],
  before: [104, 92, 116] as [number, number, number],
  after: [96, 84, 108] as [number, number, number],
}

beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  container = document.createElement('div')
  document.body.append(container)
  root = createRoot(container)
})

afterEach(() => {
  act(() => root.unmount())
  container.remove()
})

describe('MovementBookRow', () => {
  it('renders the compact summary without imperative DOM enhancement', () => {
    act(() => {
      root.render(<MovementBookRow
        movement={movement}
        index={0}
        rowCount={1}
        expanded={false}
        dragged={false}
        onToggle={vi.fn()}
        onDragStart={vi.fn()}
        onDrop={vi.fn()}
        onDragEnd={vi.fn()}
        onMove={vi.fn()}
      />)
    })

    expect(container.querySelector('.compact-identity')?.textContent).toContain('Vivo')
    expect(container.querySelector('.compact-book-summary')?.textContent).toContain('-24 pcs')
    expect(container.querySelector('.compact-details-grid')).toBeNull()
    expect(container.querySelector('.compact-detail-toggle')?.getAttribute('aria-expanded')).toBe('false')
  })

  it('renders exactly three size cards plus one total card when expanded', () => {
    const onToggle = vi.fn()
    act(() => {
      root.render(<MovementBookRow
        movement={movement}
        index={0}
        rowCount={1}
        expanded
        dragged={false}
        onToggle={onToggle}
        onDragStart={vi.fn()}
        onDrop={vi.fn()}
        onDragEnd={vi.fn()}
        onMove={vi.fn()}
      />)
    })

    expect(container.querySelectorAll('.compact-details-grid .size-book-flow')).toHaveLength(3)
    expect(container.querySelectorAll('.compact-details-grid .compact-total-card')).toHaveLength(1)
    const toggle = container.querySelector<HTMLButtonElement>('.compact-detail-toggle')
    expect(toggle?.getAttribute('aria-expanded')).toBe('true')
    act(() => toggle?.click())
    expect(onToggle).toHaveBeenCalledOnce()
  })
})
