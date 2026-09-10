// @vitest-environment jsdom

import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { LaundryBsProductSelector } from './ConnectedLaundryPage'
import { ProductSelector, qcCompletionMode } from './ConnectedQcFinalPage'
import type { Cp6Product, Cp6QcQueueRow } from './laundryQcModel'

const uuid = (suffix: number) => `00000000-0000-4000-8000-${String(suffix).padStart(12, '0')}`
const physicalAt = '2026-09-04T10:00:00Z'
const product: Cp6Product = {
  id: uuid(700), sku: 'CP6-SKU-0700', name: 'SKU di luar lookup awal',
  model_id: uuid(1), brand_id: uuid(2), model_code: 'MOD-1', model_name: 'Model 1',
  brand_code: 'BR-1', brand_name: 'Brand 1', size_id: uuid(3), size_code: '31',
  color: 'Navy', effective_from: '2026-01-01T00:00:00Z', effective_to: null,
}
const qcRow: Cp6QcQueueRow = {
  source_batch_size_line_id: uuid(10), receipt_line_id: uuid(11), receipt_id: uuid(12),
  receipt_number: 'LRC-1', receipt_physical_at: '2026-09-03T00:00:00Z',
  distribution_batch_id: uuid(13), batch_no: 1, delivery_line_id: uuid(14),
  delivery_id: uuid(15), delivery_number: 'LDR-1', vendor_name: 'Laundry',
  cutting_group_id: uuid(16), group_number: 'P-1', cutting_group_row_version: 3,
  po_id: uuid(17), po_number: 'PO-1', model_id: product.model_id,
  model_code: product.model_code, model_name: product.model_name,
  size_id: product.size_id, size_code: product.size_code, size_sort: 1,
  qty_good_received: 10, qc_accounted_qty_pcs: 0, available_for_qc_qty_pcs: 5,
  completion_status: 'PARTIAL', remaining_qc_qty_pcs: 10,
}

let container: HTMLDivElement
let root: Root
beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  container = document.createElement('div')
  document.body.append(container)
  root = createRoot(container)
})
afterEach(async () => {
  await act(async () => { root.unmount() })
  container.remove()
  vi.restoreAllMocks()
})

const settle = async () => act(async () => {
  await new Promise((resolve) => globalThis.setTimeout(resolve,0))
})
const setInput = async (input: HTMLInputElement,value: string) => act(async () => {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')?.set
  setter?.call(input,value)
  input.dispatchEvent(new Event('input',{ bubbles: true }))
})

describe('CP6 source-bound selectors and completion intent', () => {
  it('keeps filtered QC selection partial when global authoritative remaining is larger', () => {
    expect(qcCompletionMode(5,10)).toBe('PARTIAL_SELECTION')
    expect(qcCompletionMode(10,10)).toBe('ALL_READY')
    expect(qcCompletionMode(0,0)).toBe('PARTIAL_SELECTION')
  })

  it('clears a stale Final-SKU loading state when the query invalidates an in-flight request', async () => {
    let resolveSearch!: (value: Awaited<ReturnType<Parameters<typeof ProductSelector>[0]['searchProducts']>>) => void
    const searchProducts = vi.fn(() => new Promise<Awaited<ReturnType<Parameters<typeof ProductSelector>[0]['searchProducts']>>>((resolve) => {
      resolveSearch = resolve
    }))
    await act(async () => { root.render(<ProductSelector row={qcRow} physicalIso={physicalAt}
      disabled={false} value="" catalog={[]} searchProducts={searchProducts}
      onResolved={vi.fn()} onChange={vi.fn()}/>) })
    const button = container.querySelector<HTMLButtonElement>('button')!
    await act(async () => { button.click() })
    expect(button.disabled).toBe(true)
    await setInput(container.querySelector<HTMLInputElement>('input')!,'new query')
    expect(button.disabled).toBe(false)
    resolveSearch({
      contract_version: 'CP6_PRODUCT_SEARCH_V2620B',
      source_laundry_receipt_batch_size_line_id: qcRow.source_batch_size_line_id,
      physical_at: physicalAt, query: null, page_limit: 50,
      products: [product], has_more: false, next_cursor: null,
    })
    await settle()
    expect(container.querySelector('option[value="'+product.id+'"]')).toBeNull()
    expect(button.disabled).toBe(false)
  })

  it('finds and selects a valid Laundry-BS SKU beyond the bounded initial lookup', async () => {
    const onChange = vi.fn()
    const searchProducts = vi.fn(async () => ({
      contract_version: 'CP6_LAUNDRY_BS_PRODUCT_SEARCH_V2620C' as const,
      source_delivery_batch_size_line_id: uuid(20), physical_at: physicalAt,
      query: '0700', page_limit: 50, products: [product], has_more: false, next_cursor: null,
    }))
    await act(async () => { root.render(<LaundryBsProductSelector sourceId={uuid(20)}
      modelId={product.model_id} sizeId={product.size_id} sizeCode={product.size_code}
      physicalIso={physicalAt} disabled={false} value="" catalog={[]}
      searchProducts={searchProducts} onResolved={vi.fn()} onChange={onChange}/>) })
    await setInput(container.querySelector<HTMLInputElement>('input')!,'0700')
    await act(async () => { container.querySelector<HTMLButtonElement>('button')!.click() })
    await settle()
    expect(searchProducts).toHaveBeenCalledWith(uuid(20),physicalAt,'0700',null)
    const option = container.querySelector<HTMLOptionElement>(`option[value="${product.id}"]`)
    expect(option?.textContent).toContain('CP6-SKU-0700')
    const select = container.querySelector<HTMLSelectElement>('select')!
    await act(async () => {
      select.value=product.id
      select.dispatchEvent(new Event('change',{ bubbles: true }))
    })
    expect(onChange).toHaveBeenCalledWith(product.id)
  })

  it('rejects a Laundry-BS resolver response outside the exact source Model/size', async () => {
    const wrong = { ...product, id: uuid(701), model_id: uuid(99) }
    const searchProducts = vi.fn(async () => ({
      contract_version: 'CP6_LAUNDRY_BS_PRODUCT_SEARCH_V2620C' as const,
      source_delivery_batch_size_line_id: uuid(20), physical_at: physicalAt,
      query: null, page_limit: 50, products: [wrong], has_more: false, next_cursor: null,
    }))
    await act(async () => { root.render(<LaundryBsProductSelector sourceId={uuid(20)}
      modelId={product.model_id} sizeId={product.size_id} sizeCode={product.size_code}
      physicalIso={physicalAt} disabled={false} value="" catalog={[]}
      searchProducts={searchProducts} onResolved={vi.fn()} onChange={vi.fn()}/>) })
    await act(async () => { container.querySelector<HTMLButtonElement>('button')!.click() })
    await settle()
    expect(container.textContent).toContain('di luar Model/ukuran sumber Laundry')
    expect(container.querySelector(`option[value="${wrong.id}"]`)).toBeNull()
  })
})
