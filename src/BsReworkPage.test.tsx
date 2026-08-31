// @vitest-environment jsdom

import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import BsReworkPage, { ResolutionRoutePicker, calculateSusulanResolution, cleanQuantity } from './BsReworkPage'

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

describe('calculateSusulanResolution', () => {
  it('derives Good and clamps BS within Susulan within outstanding', () => {
    expect(calculateSusulanResolution([5, 2, 9], [6, 1, 2], [4, 3, 1])).toEqual({
      total: [4, 2, 1],
      bs: [4, 1, 1],
      good: [0, 1, 0],
      remaining: [0, 1, 0],
    })
  })

  it('normalizes negative and fractional quantities before deriving Good', () => {
    expect(calculateSusulanResolution([-2, 2.9, Number.NaN], [1, -4, 1], [3, 3, 3])).toEqual({
      total: [0, 2, 0],
      bs: [0, 0, 0],
      good: [0, 2, 0],
      remaining: [3, 1, 3],
    })
  })

  it('does not turn pasted signs or decimals into extra digits', () => {
    expect(cleanQuantity('-2')).toBe('0')
    expect(cleanQuantity('2.9')).toBe('2')
    expect(cleanQuantity('8', 5)).toBe('5')
    expect(cleanQuantity('abc')).toBe('')
  })
})

describe('ResolutionRoutePicker', () => {
  it('exposes all four honest frontend-only choices', () => {
    const onChange = vi.fn()
    act(() => root.render(<ResolutionRoutePicker value="REWORK" onChange={onChange}/>))

    for (const label of ['Rework', 'Rewash', 'Hold', 'Scrap']) {
      const route = label.toUpperCase()
      expect(container.querySelector(`[data-resolution-route="${route}"]`)).toBeInstanceOf(HTMLButtonElement)
    }
    expect(container.querySelector('[role="note"]')?.textContent).toContain('SIMULASI FRONTEND')
    expect(container.querySelector('[data-resolution-route="REWASH"]')?.textContent).toContain('Rp0')

    act(() => container.querySelector<HTMLButtonElement>('[data-resolution-route="REWASH"]')!.click())
    expect(onChange).toHaveBeenCalledOnce()
    expect(onChange).toHaveBeenCalledWith('REWASH')
  })
})

describe('BsReworkPage resolution shell', () => {
  it('keeps Rewash as a non-mutating requirements preview and removes the BS-final bypass', () => {
    const onWorkspaceChange = vi.fn()
    const onStuckReturned = vi.fn()
    const onNotaCardReady = vi.fn()

    act(() => root.render(<BsReworkPage
      onBack={vi.fn()}
      onWorkspaceChange={onWorkspaceChange}
      onStuckReturned={onStuckReturned}
      onNotaCardReady={onNotaCardReady}
    />))
    onWorkspaceChange.mockClear()

    act(() => container.querySelector<HTMLButtonElement>('[data-resolution-route="REWASH"]')!.click())

    expect(container.textContent).toContain('Fee jasa vendor Laundry tetap Rp0')
    expect(container.textContent).toContain('Belum ada tombol simpan')
    expect(container.textContent).not.toContain('Tetapkan sisa BS final')
    expect(onWorkspaceChange).not.toHaveBeenCalled()
    expect(onStuckReturned).not.toHaveBeenCalled()
    expect(onNotaCardReady).not.toHaveBeenCalled()
  })
})
