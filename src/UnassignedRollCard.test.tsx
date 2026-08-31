// @vitest-environment jsdom

import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MandorWipPage, UnassignedRollCard } from './App'

let container: HTMLDivElement
let root: Root

const rollRow = {
  roll: {
    id: 'LCY-001',
    sequence: 1,
    supplier: 'Sinaran',
    material: 'Lucy',
    yards: 101.5,
    receivedAt: '25 Agu 2026',
    allocation: [13, 13, 12, 11, 10, 10] as [number, number, number, number, number, number],
  },
  sizes: [26, 23, 20] as [number, number, number],
  quantity: 69,
}

const callbacks = () => ({
  onAssignWhole: vi.fn(),
  onOpenSplit: vi.fn(),
  onDragStart: vi.fn(),
  onDragMove: vi.fn(),
  onDragEnd: vi.fn(),
  onDragCancel: vi.fn(),
})

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

describe('UnassignedRollCard', () => {
  it('shows a readable roll summary and all source sizes', () => {
    const handlers = callbacks()
    act(() => root.render(<UnassignedRollCard row={rollRow} batchCount={3} {...handlers}/>))

    expect(container.querySelector('article')?.getAttribute('aria-labelledby')).toBe('wip-roll-LCY-001-instruction-title')
    expect(container.querySelector('.wip-roll-token-total')?.textContent).toContain('101,5yd')
    expect(container.querySelector('.wip-roll-token-total')?.textContent).toContain('69 pcs hasil potong')
    expect(container.querySelector('.wip-roll-token-code')?.textContent).toBe('Roll 01 · LCY-001')
    expect(container.textContent).toContain('SIZE 31')
    expect(container.textContent).toContain('SIZE 32')
    expect(container.textContent).toContain('SIZE 33')
    const dragHandle = container.querySelector('[aria-label="Tarik Roll 01 ke batch"]')
    expect(dragHandle).toBeInstanceOf(HTMLButtonElement)
    expect(dragHandle?.querySelector('.sr-only')?.textContent).toBe('Tarik ke batch')
    expect(dragHandle?.nextElementSibling).toBeNull()
  })

  it('reuses the current batch menu as the mobile-safe alternative to dragging', () => {
    const handlers = callbacks()
    act(() => root.render(<UnassignedRollCard row={rollRow} batchCount={3} {...handlers}/>))
    const select = container.querySelector<HTMLSelectElement>('[aria-label="Pilih batch untuk LCY-001"]')!

    expect([...select.options].map((option) => option.textContent)).toEqual(['Batch: Pilih', 'Batch: 1', 'Batch: 2', 'Batch: 3'])
    act(() => {
      select.value = '1'
      select.dispatchEvent(new Event('change', { bubbles: true }))
    })

    expect(handlers.onAssignWhole).toHaveBeenCalledOnce()
    expect(handlers.onAssignWhole).toHaveBeenCalledWith('LCY-001', 1)
  })

  it('keeps the split editor as a separate explicit action', () => {
    const handlers = callbacks()
    act(() => root.render(<UnassignedRollCard row={rollRow} batchCount={3} {...handlers}/>))
    const splitButton = [...container.querySelectorAll('button')].find((button) => button.textContent?.includes('Atur pecahan'))!

    act(() => splitButton.click())

    expect(handlers.onOpenSplit).toHaveBeenCalledOnce()
    expect(handlers.onOpenSplit).toHaveBeenCalledWith('LCY-001')
    expect(handlers.onAssignWhole).not.toHaveBeenCalled()
  })
})

describe('MandorWipPage roll placement', () => {
  it('routes the batch menu through whole-roll allocation without duplicating the source', () => {
    act(() => root.render(<MandorWipPage batchNotes={['', '', '']} setBatchNotes={vi.fn()}/>))
    const select = container.querySelector<HTMLSelectElement>('[aria-label="Pilih batch untuk LCY-001"]')!

    act(() => {
      select.value = '1'
      select.dispatchEvent(new Event('change', { bubbles: true }))
    })

    expect(container.querySelectorAll('.wip-roll-token')).toHaveLength(8)
    const batchCards = container.querySelectorAll('.wip-batch-card')
    expect(batchCards[0].textContent).not.toContain('LCY-001')
    expect(batchCards[1].textContent).toContain('LCY-001')
    expect(batchCards[1].textContent).toContain('69 pcs')
    expect(batchCards[2].textContent).not.toContain('LCY-001')
    expect(container.querySelector('[role="status"]')?.textContent).toBe('Roll 01 masuk ke Batch 02.')
  })
})
