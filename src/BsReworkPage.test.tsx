// @vitest-environment jsdom

import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import BsReworkPage, { ResolutionRoutePicker, calculateSusulanResolution, cleanQuantity, normalizeSkuCode, validateNewSkuDraft, type BsReworkWorkspace } from './BsReworkPage'

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

const setField = (label: string, value: string) => act(() => {
  const field = container.querySelector<HTMLInputElement | HTMLTextAreaElement>(`[aria-label="${label}"]`)!
  const prototype = field instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype
  Object.getOwnPropertyDescriptor(prototype, 'value')!.set!.call(field, value)
  field.dispatchEvent(new Event('input', { bubbles: true }))
})
const buttonByText = (text: string) => [...container.querySelectorAll<HTMLButtonElement>('button')].find((button) => button.textContent?.trim() === text)

describe('validateNewSkuDraft', () => {
  const sizes: [string, string, string] = ['31', '32', '33']
  const used = new Set(['73001', '73002'])
  it('requires every field, a free SKU code and qty within the remaining BS', () => {
    expect(validateNewSkuDraft({ code: '', name: '', gradeNote: '', qty: ['', '', ''], reason: '' }, [1, 1, 0], sizes, used)).toEqual({
      code: 'Kode SKU baru wajib diisi.',
      name: 'Nama produk SKU baru wajib diisi.',
      gradeNote: 'Catatan size / grade wajib diisi.',
      qty: 'Isi minimal 1 pcs yang dipindah ke SKU baru.',
      reason: 'Alasan wajib diisi supaya jejak audit jelas.',
    })
    const draft = { code: ' 73002 ', name: 'X', gradeNote: 'Grade B', qty: ['2', '0', '0'] as [string, string, string], reason: 'Noda' }
    const errors = validateNewSkuDraft(draft, [1, 1, 0], sizes, used)
    expect(errors.code).toContain('sudah dipakai')
    expect(errors.qty).toBe('Qty melebihi sisa BS: Size 31 maks 1 pcs.')
    expect(validateNewSkuDraft({ ...draft, code: '73001-b', qty: ['1', '1', '0'] }, [1, 1, 0], sizes, used)).toEqual({})
    expect(normalizeSkuCode(' 73001 b ')).toBe('73001-B')
  })
})

describe('BsReworkPage SKU identity and BS → SKU baru', () => {
  it('shows the SKU code and product name on every case row and in the detail', () => {
    act(() => root.render(<BsReworkPage onBack={vi.fn()}/>))
    const rows = [...container.querySelectorAll('[data-testid="bs-case-sku"]')].map((node) => node.textContent)
    expect(rows).toHaveLength(3)
    expect(rows[0]).toContain('SKU 73001')
    expect(rows[0]).toContain('Widie Daily · Dark Navy')
    expect(rows[2]).toContain('SKU 73002')
    expect(rows[2]).toContain('Vivo Regular · Washed Blue')
    const identity = container.querySelector('[data-testid="bs-sku-identity"]')?.textContent
    expect(identity).toContain('Widie · SKU 73001')
    expect(identity).toContain('Widie Daily · Dark Navy')
    expect(identity).toContain('31: 2 · 32: 1')
  })

  it('validates, asks for confirmation, then moves the BS qty to the new SKU with a history line', () => {
    const onWorkspaceChange = vi.fn()
    act(() => root.render(<BsReworkPage onBack={vi.fn()} onWorkspaceChange={onWorkspaceChange}/>))

    act(() => buttonByText('Jadikan SKU baru')!.click())
    const form = () => container.querySelector('[data-testid="bs-new-sku-form"]')
    expect(form()).not.toBeNull()
    expect(form()?.textContent).toContain('Sisa fisik 2 pcs')

    setField('Kode SKU baru', '73002')
    expect(form()?.textContent).toContain('Kode 73002 sudah dipakai di katalog demo')
    act(() => buttonByText('Review SKU baru')!.click())
    expect(form()?.textContent).toContain('Nama produk SKU baru wajib diisi.')
    expect(form()?.textContent).toContain('Alasan wajib diisi')
    expect(container.querySelector('[aria-label="Konfirmasi SKU baru"]')).toBeNull()

    setField('Qty SKU baru size 31', '5')
    expect(form()?.textContent).toContain('Qty melebihi sisa BS: Size 31 maks 1 pcs.')

    setField('Kode SKU baru', '73001-b')
    setField('Nama produk SKU baru', 'Widie Daily Grade B')
    setField('Qty SKU baru size 31', '1')
    setField('Alasan jadi SKU baru', 'Noda permanen, layak jual grade B')
    act(() => buttonByText('Review SKU baru')!.click())
    const confirmation = container.querySelector('[aria-label="Konfirmasi SKU baru"]')
    expect(confirmation?.textContent).toContain('2 pcs Widie SKU 73001 jadi SKU baru 73001-B')
    expect(confirmation?.textContent).toContain('Minus Mandor asal (Mandor Asep) tidak berubah')

    onWorkspaceChange.mockClear()
    act(() => buttonByText('Ya, jadikan SKU baru')!.click())
    expect(form()).toBeNull()
    expect(container.querySelector('.bsr-notice')?.textContent).toContain('dipindah ke SKU baru 73001-B · Widie Daily Grade B')
    expect(container.querySelector('.bsr-case-list')?.textContent).toContain('Jadi SKU 73001-B · 2 pcs')
    expect(container.querySelector('.bsr-sku-conversions')?.textContent).toContain('Sudah jadi SKU 73001-B · Widie Daily Grade B')
    expect(container.querySelector('.bsr-case-history')?.textContent).toContain('BS → SKU baru 73001-B')
    expect(container.textContent).toContain('Sudah jadi SKU baru')
    expect(buttonByText('Jadikan SKU baru')?.disabled).toBe(true)

    const workspace = onWorkspaceChange.mock.calls.at(-1)?.[0] as BsReworkWorkspace
    const converted = workspace.cases.find((item) => item.id === 'BS-260827-018')
    expect(converted).toMatchObject({ status: 'CONVERTED_SKU', conversions: [{ newSku: '73001-B', qtyBySize: [1, 1, 0] }] })
    expect(workspace.ledger.some((item) => item.kind === 'BS_TO_NEW_SKU' && item.amount === 0)).toBe(true)

    // The new code is now taken for the rest of the demo session.
    act(() => [...container.querySelectorAll<HTMLButtonElement>('.bsr-case-list > button')].find((button) => button.textContent?.includes('BS-LEG-0007'))!.click())
    act(() => buttonByText('Jadikan SKU baru')!.click())
    setField('Kode SKU baru', '73001-B')
    expect(form()?.textContent).toContain('Kode 73001-B sudah dipakai')
  })
})
