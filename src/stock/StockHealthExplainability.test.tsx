// @vitest-environment jsdom

import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { StockHealthExplainability } from './StockHealthExplainability'
import { calculateStockHealth, createUnconfiguredPrototypeStock } from './stockHealth'

let container: HTMLDivElement
let root: Root

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

describe('StockHealthExplainability', () => {
  it('opens an accessible dialog, exposes unknown operands, and returns focus on Escape', () => {
    const result = calculateStockHealth(createUnconfiguredPrototypeStock({
      itemKind: 'FG',
      physicalStock: 42,
      uom: 'pcs',
      sourceSystem: 'SIMULASI — component test',
    }))

    act(() => {
      root.render(<StockHealthExplainability
        itemName="Vivo 73001 · Size 28"
        result={result}
        lineage={[{ label:'Kartu stok FG', source:'Mutasi posted', href:'#fg-stock-card' }]}
      />)
    })

    const badge = container.querySelector<HTMLButtonElement>('[aria-haspopup="dialog"]')
    expect(badge).not.toBeNull()
    expect(badge?.textContent).toContain('Belum cukup data')
    expect(badge?.textContent).toContain('Batas belum diatur')

    badge?.focus()
    act(() => badge?.dispatchEvent(new MouseEvent('click', { bubbles: true })))

    const dialog = container.querySelector<HTMLElement>('[role="dialog"]')
    const recommendationRow = [...(dialog?.querySelectorAll<HTMLElement>('.wh-stock-calc-grid > div') ?? [])]
      .find((row) => row.textContent?.includes('Recommended qty'))
    expect(dialog).not.toBeNull()
    expect(badge?.getAttribute('aria-expanded')).toBe('true')
    expect(recommendationRow?.textContent).toContain('Belum tersedia')
    expect(dialog?.textContent).toContain('Data simulasi frontend — belum tersambung backend')
    expect(dialog?.textContent).not.toMatch(/Rekomendasi tambahan\s+[0-9]/)
    expect(document.activeElement?.getAttribute('aria-label')).toBe('Tutup dasar perhitungan')

    act(() => document.dispatchEvent(new KeyboardEvent('keydown', { key:'Escape', bubbles:true })))

    expect(container.querySelector('[role="dialog"]')).toBeNull()
    expect(document.activeElement).toBe(badge)
    expect(badge?.getAttribute('aria-expanded')).toBe('false')
  })
})
