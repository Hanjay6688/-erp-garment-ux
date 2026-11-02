// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import MandorShopCards, { type MandorShopCardsProps } from './MandorShopCards'
import { parseMandorShopWorkspace } from './mandorShopContract'
import { shopAllocation, shopId, shopMandor, shopPayroll, shopWorkspace } from '../tests/fixtures/mandorShop'

let root: Root, container: HTMLDivElement, props: MandorShopCardsProps
const originalShow = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'showModal')
const originalClose = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'close')
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true })
  // jsdom26 omits these browser methods; this DOM-only model is not a browser qualification.
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value(this: HTMLDialogElement) { this.setAttribute('open', '') } })
  Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value(this: HTMLDialogElement) { this.removeAttribute('open') } })
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
  props = { open: true, payrollId: shopPayroll, payrollNumber: 'PAY-EPI-W2', contractorId: shopMandor, contractorName: 'Epi',
    workspace: parseMandorShopWorkspace(shopWorkspace(), shopPayroll, shopMandor), ready: true, busy: false,
    onClose: vi.fn(), onReload: vi.fn(async () => true), onNext: vi.fn(async () => true),
    onReserve: vi.fn(async () => true), onRelease: vi.fn(async () => true) }
})
afterEach(async () => {
  await act(async () => root.unmount()); container.remove(); vi.restoreAllMocks()
  for (const [name, descriptor] of [['showModal', originalShow], ['close', originalClose]] as const) {
    if (descriptor) Object.defineProperty(HTMLDialogElement.prototype, name, descriptor)
    else Reflect.deleteProperty(HTMLDialogElement.prototype, name)
  }
})
async function render(patch: Partial<MandorShopCardsProps> = {}) { props = { ...props, ...patch }; await act(async () => root.render(<MandorShopCards {...props}/>)) }
const button = (name: string) => [...container.querySelectorAll('button')].find(b => b.textContent === name)
async function click(name: string) { await act(async () => button(name)!.click()) }
async function review() { await act(async () => container.querySelector<HTMLInputElement>('input[type=checkbox]')!.click()) }
async function fill(value: string) {
  await act(async () => { const el = container.querySelector<HTMLInputElement>('[aria-label="Nominal potongan belanja"]')!
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(el, value); el.dispatchEvent(new Event('input', { bubbles: true })) })
}
it('shows the selected next week, original invoice date, balance and allocation history', async () => {
  const w = shopWorkspace(true); w.cards[0].allocations[0].allocation.payroll_id = shopId(8); w.cards[0].allocations[0].payroll_number = 'PAY-EPI-W3'
  await render({ workspace: parseMandorShopWorkspace(w, shopPayroll, shopMandor) })
  expect(container.querySelector('dialog')!.open).toBe(true)
  expect(container.textContent).toContain('2026-11-09 sampai 2026-11-15'); expect(container.textContent).toContain('INV-EPI-01')
  expect(container.textContent).toContain('PAY-EPI-W3'); expect(container.textContent).toContain('Rp300.000,00')
  expect(button('Lepas nota INV-EPI-01')).toBeUndefined(); expect(props.onReserve).not.toHaveBeenCalled()
})
it('requires renewed review after amount changes and sends exact cents for the chosen source card', async () => {
  await render(); await click('Pilih nota INV-EPI-01'); expect(button('Pasang tagihan ke payroll')!.disabled).toBe(true)
  await review(); await fill('100000,19'); expect(button('Pasang tagihan ke payroll')!.disabled).toBe(true)
  expect(container.textContent).toContain('Rp1.899.999,81'); await review(); await click('Pasang tagihan ke payroll')
  expect(props.onReserve).toHaveBeenCalledOnce(); expect(props.onReserve).toHaveBeenCalledWith(expect.objectContaining({ number: 'INV-EPI-01' }), '100000.19')
  expect(button('Pasang tagihan ke payroll')).toBeUndefined()
})
it('refuses an over-capacity or fractional-cent input before invoking the owner', async () => {
  await render(); await click('Pilih nota INV-EPI-01')
  for (const amount of ['300000.01', '0', '1.001', '1e3']) {
    await fill(amount); await review(); expect(button('Pasang tagihan ke payroll')!.disabled).toBe(true)
  }
  expect(props.onReserve).not.toHaveBeenCalled()
})
it('releases only the reserved card on this payroll after explicit confirmation', async () => {
  await render({ workspace: parseMandorShopWorkspace(shopWorkspace(true), shopPayroll, shopMandor) })
  expect(button('Pilih nota INV-EPI-01')).toBeUndefined(); await click('Lepas nota INV-EPI-01'); await review(); await click('Lepas tagihan dari payroll')
  expect(props.onRelease).toHaveBeenCalledWith(expect.objectContaining({ number: 'INV-EPI-01' }), expect.objectContaining({ id: shopAllocation, payroll_id: shopPayroll }))
  expect(props.onReserve).not.toHaveBeenCalled()
})
it('retires every displayed financial value and old review when source readiness or selected payroll changes', async () => {
  await render(); await click('Pilih nota INV-EPI-01'); await review(); await render({ ready: false })
  expect(container.textContent).not.toContain('Rp'); expect(button('Pasang tagihan ke payroll')).toBeUndefined()
  await render({ ready: true, payrollId: shopId(9) }); expect(container.textContent).not.toContain('Rp')
  expect(props.onReserve).not.toHaveBeenCalled()
})
it('prevents a double click while the same selection is in flight', async () => {
  let finish: ((v: boolean) => void) | undefined
  const pending = vi.fn(() => new Promise<boolean>(resolve => { finish = resolve }))
  await render({ onReserve: pending }); await click('Pilih nota INV-EPI-01'); await review()
  await act(async () => { const save = button('Pasang tagihan ke payroll')!; save.click(); save.click() })
  expect(pending).toHaveBeenCalledOnce(); await act(async () => finish!(true))
  expect(button('Pasang tagihan ke payroll')).toBeUndefined()
})
it('shows approved payroll history without offering a new allocation or release', async () => {
  const w = shopWorkspace(true); w.status = 'APPROVED'; w.can_change = false
  await render({ workspace: parseMandorShopWorkspace(w, shopPayroll, shopMandor) })
  expect(button('Pilih nota INV-EPI-01')).toBeUndefined(); expect(button('Lepas nota INV-EPI-01')).toBeUndefined()
  expect(container.textContent).toContain('Payroll ini sudah dibekukan')
})
