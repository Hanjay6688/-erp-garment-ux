// @vitest-environment jsdom
// Searchable pickers on the demo (dark) pages: search → pick drives the same
// state the old <select> did, defaults stay as they were, locks stay locked.

import { act, useState } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { LaundryPage, MandorWipPage, SewingWipPage, laundryDeliverySeeds, laundryReadySeeds, type LaundryDelivery, type LaundryReadyBatch } from './App'
import QcFinalPage, { type QcFinalResult, type QcSeed } from './QcFinalPage'
import BsReworkPage, { type BsReworkWorkspace } from './BsReworkPage'
import FgNotaPage from './FgNotaPage'
import type { ReadyFgNotaCard } from './fgNota'
import SalesPages from './SalesPages'
import FinancePages from './FinancePages'
import {
  choosePickerOption, openPicker, pickerOptionLabels, pickerPanel, pickerTrigger, pickerValue, pressInPicker, typeInPicker,
} from './components/browsePickerDom.test.support'

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

const render = async (node: React.ReactNode) => { await act(async () => { root.render(node) }) }
const buttonWith = (text: string, scope: ParentNode = container) => [...scope.querySelectorAll<HTMLButtonElement>('button')]
  .find((button) => button.textContent?.includes(text))!
const setValue = (control: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement, value: string) => act(async () => {
  const prototype = control instanceof HTMLSelectElement ? HTMLSelectElement.prototype
    : control instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype
  Object.getOwnPropertyDescriptor(prototype, 'value')!.set!.call(control, value)
  control.dispatchEvent(new Event(control instanceof HTMLSelectElement ? 'change' : 'input', { bubbles: true }))
})

describe('Bagi Potongan (demo)', () => {
  it('Pola filter: search → pick narrows the queue; "Semua Pola" brings everything back', async () => {
    await render(<MandorWipPage batchNotes={[]} setBatchNotes={vi.fn()}/>)
    const all = container.querySelectorAll('.wip-queue-card').length
    const filter = pickerTrigger('Filter Pola Bagi Potongan', container)
    expect(pickerValue(filter)).toBe('Semua Pola')
    await openPicker(filter)
    await typeInPicker('lucy')
    expect(pickerOptionLabels()).toEqual(['Semua Pola', 'LCY-REG · R1'])
    await pressInPicker('Enter')
    expect(container.querySelectorAll('.wip-queue-card')).toHaveLength(1)
    expect(container.querySelector('.wip-queue-pattern')?.textContent).toContain('LCY-REG · R1 · Kulot Lucy Regular')
    await choosePickerOption(filter, 'Semua Pola')
    expect(container.querySelectorAll('.wip-queue-card')).toHaveLength(all)
  })

  it('Mandor who picks up: default unchanged, the picked Mandor goes to the review', async () => {
    await render(<MandorWipPage batchNotes={[]} setBatchNotes={vi.fn()}/>)
    const mandor = pickerTrigger('Diambil oleh / mandor', container)
    expect(pickerValue(mandor)).toBe('Mandor Afat')
    await choosePickerOption(mandor, 'Mandor Dedi', 'dedi')
    const review = container.querySelector('[aria-label="Review akhir pickup"]')!
    expect(review.textContent).toContain('MANDORMandor Dedi')
  })
})

describe('WIP & Sewing / Laundry Pola filters (demo)', () => {
  it('WIP & Sewing: the picked Pola keeps only its production batch', async () => {
    await render(<SewingWipPage batchNotes={[]} deliveries={laundryDeliverySeeds} finalizedResults={[]} laundryDrafts={{}} reverseNotice={null}
      onClearReverseNotice={vi.fn()} onClearLaundryDraft={vi.fn()} onConfirmLaundry={vi.fn()} onOpenLaundry={vi.fn()} onOpenQc={vi.fn()}/>)
    await choosePickerOption(pickerTrigger('Filter Pola WIP', container), 'ZDK-JUMBO · R3', 'zodiak')
    expect(container.querySelectorAll('.sewing-parent-card')).toHaveLength(1)
    expect(container.querySelector('.sewing-parent-pattern')?.textContent).toContain('ZDK-JUMBO · R3 · Zodiak Jumbo')
  })

  it('Laundry: the picked Pola keeps only its batches', async () => {
    function Harness() {
      const [ready, setReady] = useState<LaundryReadyBatch[]>(laundryReadySeeds)
      const [deliveries, setDeliveries] = useState<LaundryDelivery[]>(laundryDeliverySeeds)
      return <LaundryPage prefill={null} readyBatches={ready} setReadyBatches={setReady} deliveries={deliveries} setDeliveries={setDeliveries} onPosted={vi.fn()} onReturnToWip={vi.fn()} onOpenQc={vi.fn()}/>
    }
    await render(<Harness/>)
    await choosePickerOption(pickerTrigger('Filter Pola Laundry', container), 'ZDK-JUMBO · R3', 'ZDK')
    expect(container.querySelectorAll('.laundry-parent-card')).toHaveLength(1)
    expect(container.querySelector('.laundry-pattern-snapshot')?.textContent).toContain('ZDK-JUMBO · R3 · Zodiak Jumbo')
  })
})

const qcSeed = (parentId: string, mandor: string, laundry: string, pattern: QcSeed['pattern']): QcSeed => ({
  parentId, batchId: `${parentId.slice(-3)}-01`, plannedBrand: 'Vivo', pattern, model: 'Kulot', material: 'Denim', mandor, laundry,
  sizes: ['28', '29', '30'], expected: [2, 2, 2], returnedGoodBySize: [2, 2, 2], returnedBsBySize: [0, 0, 0], stuckBySize: [0, 0, 0],
})
const qcSeeds = [
  qcSeed('POT-A-001', 'Mandor Afat', 'Laundry Berkah', { id: 'p-1', code: 'LCY-REG', revision: 'R1', name: 'Kulot Lucy Regular' }),
  qcSeed('POT-B-002', 'Mandor Asep', 'Laundry Intan', { id: 'p-2', code: 'ZDK-JUMBO', revision: 'R3', name: 'Zodiak Jumbo' }),
]
const renderQc = (onFinish = vi.fn()) => render(<QcFinalPage seeds={qcSeeds} initialSeedId="POT-A-001::001-01" finalizedResults={[]} postedFgCardIds={[]} canPostFinalSku onBack={vi.fn()} onFinish={onFinish} onOpenNota={vi.fn()}/>)

describe('QC & Final SKU (demo)', () => {
  it('Mandor, Laundry and Pola filters narrow the queue', async () => {
    await renderQc()
    expect(container.querySelectorAll('.qc-browser-list > button')).toHaveLength(2)
    await choosePickerOption(pickerTrigger('MANDOR', container), 'Mandor Asep', 'asep')
    expect(container.querySelectorAll('.qc-browser-list > button')).toHaveLength(1)
    await choosePickerOption(pickerTrigger('MANDOR', container), 'Semua mandor')
    await choosePickerOption(pickerTrigger('LAUNDRY', container), 'Laundry Berkah', 'berkah')
    expect(container.querySelectorAll('.qc-browser-list > button')).toHaveLength(1)
    await choosePickerOption(pickerTrigger('LAUNDRY', container), 'Semua laundry')
    await choosePickerOption(pickerTrigger('Filter Pola QC', container), 'ZDK-JUMBO · R3', 'jumbo')
    expect(container.querySelectorAll('.qc-browser-list > button')).toHaveLength(1)
    expect(container.querySelector('.qc-browser-pattern')?.textContent).toContain('ZDK-JUMBO · R3')
    expect(container.textContent).toContain('POLA · DATA SIMULASI')
  })

  it('SKU: first SKU of the brand stays the default; the picked SKU is the posted final SKU; brand change resets it', async () => {
    const onFinish = vi.fn()
    await renderQc(onFinish)
    const sku = pickerTrigger('2 · SKU', container)
    expect(pickerValue(sku)).toBe('73001')
    await openPicker(sku)
    expect(pickerOptionLabels()).toEqual(['73001', '73004'])
    expect(pickerPanel()!.textContent).toContain('Range 28–30')
    await typeInPicker('straight')
    await pressInPicker('Enter')
    expect(pickerValue(sku)).toBe('73004')
    await act(async () => { buttonWith('Review').click() })
    await act(async () => { buttonWith('Post FG').click() })
    expect(onFinish).toHaveBeenCalledTimes(1)
    expect(onFinish.mock.calls[0]![0]).toMatchObject({ brand: 'Vivo', finalSku: '73004', finalProductName: 'Vivo Straight' })
  })

  it('SKU: changing the brand resets the SKU to that brand\'s first one, as before', async () => {
    await renderQc()
    await choosePickerOption(pickerTrigger('2 · SKU', container), '73004')
    await setValue(container.querySelector<HTMLSelectElement>('.qc-final-fields select')!, 'Widie')
    expect(pickerValue(pickerTrigger('2 · SKU', container))).toBe('73001')
    await openPicker(pickerTrigger('2 · SKU', container))
    expect(pickerOptionLabels()).toEqual(['73001'])
  })
})

describe('Barang BS & Rework (demo)', () => {
  it('Mandor filter narrows the case list', async () => {
    await render(<BsReworkPage onBack={vi.fn()}/>)
    const filter = pickerTrigger('Filter mandor', container)
    const all = container.querySelectorAll('.bsr-case-list > button').length
    await openPicker(filter)
    expect(pickerOptionLabels()[0]).toBe('Semua mandor')
    await pressInPicker('Escape')
    await choosePickerOption(filter, 'Mandor Ujang', 'ujang')
    const visible = container.querySelectorAll('.bsr-case-list > button')
    expect(visible.length).toBeLessThan(all)
    expect(visible.length).toBeGreaterThan(0)
  })

  it('rework Mandor: "Belum ditugaskan" and a Mandor can be picked; a closed case keeps it locked', async () => {
    let workspace: BsReworkWorkspace | undefined
    await render(<BsReworkPage onBack={vi.fn()} onWorkspaceChange={(next) => { workspace = next }}/>)
    const rework = pickerTrigger('Mandor rework · penerima plus', container)
    expect(pickerValue(rework)).toBe('Mandor Ujang')
    await choosePickerOption(rework, 'Belum ditugaskan', 'xyz')
    const caseId = workspace!.cases.find((item) => item.kind === 'BS')!.id
    expect(workspace!.cases.find((item) => item.id === caseId)).toMatchObject({ reworkMandor: null })
    await choosePickerOption(rework, 'Mandor Rian', 'rian')
    expect(workspace!.cases.find((item) => item.id === caseId)).toMatchObject({ reworkMandor: 'Mandor Rian' })

    const closed: BsReworkWorkspace = { ...workspace!, cases: workspace!.cases.map((item) => item.id === caseId ? { ...item, status: 'BS_FINAL' } as typeof item : item) }
    act(() => root.unmount())
    root = createRoot(container)
    await render(<BsReworkPage onBack={vi.fn()} initialWorkspace={closed}/>)
    const locked = pickerTrigger('Mandor rework · penerima plus', container)
    expect(locked.disabled).toBe(true)
  })

  it('legacy import: the picked Mandor asal owns the minus', async () => {
    let workspace: BsReworkWorkspace | undefined
    await render(<BsReworkPage onBack={vi.fn()} onWorkspaceChange={(next) => { workspace = next }}/>)
    await act(async () => { buttonWith('Impor BS legacy').click() })
    const dialog = document.querySelector<HTMLElement>('.bsr-dialog')!
    const mandor = pickerTrigger('MANDOR ASAL · PEMILIK MINUS', dialog)
    expect(pickerValue(mandor)).toBe('Mandor Asep')
    await choosePickerOption(mandor, 'Mandor Rian', 'rian')
    await setValue(dialog.querySelectorAll<HTMLInputElement>('.bsr-new-size-grid input')[0]!, '2')
    await setValue(dialog.querySelector<HTMLTextAreaElement>('.bsr-reason textarea')!, 'Arsip nota Agustus')
    expect(dialog.querySelector('.bsr-minus-preview')?.textContent).toContain('Mandor Rian')
    await act(async () => { buttonWith('Impor kasus legacy', dialog).click() })
    expect(workspace!.cases.some((item) => item.kind === 'BS' && item.source === 'LEGACY_IMPORT' && item.originalMandor === 'Mandor Rian')).toBe(true)
  })
})

describe('Susun Nota FG (demo)', () => {
  const card = (id: string, mandor: string): ReadyFgNotaCard => ({
    id, kind: 'REWORK_RELEASE', caseId: `BS-${id}`, sourceLabel: `Asal ${id}`, label: 'Bikin bagus', brand: 'Widie', sku: '73001', material: 'Denim', mandor,
    sizes: ['28', '29', '30'], qtyBySize: [1, 0, 0], qty: 1, components: [{ id: 'obras', name: 'Obras', rate: 1000 }], unitRate: 1000, subtotal: 1000, createdAt: '28 Agu',
  })
  const renderNota = () => render(<FgNotaPage result={null as QcFinalResult | null} eligibleResults={[]} repairCards={[card('RW-1', 'Mandor Asep'), card('RW-2', 'Mandor Ujang')]}
    regularSnapshots={{}} focus={null} origin="MENU" postedCardIds={[]} onPost={vi.fn()} onReturn={vi.fn()} onOpenQc={vi.fn()} onOpenBs={vi.fn()}/>)

  it('Mandor nota: first Mandor by default; picking another switches the cards and empties the draft', async () => {
    await renderNota()
    const mandor = pickerTrigger('Mandor nota', container)
    expect(pickerValue(mandor)).toBe('Mandor Asep')
    await act(async () => { buttonWith('Tambah ke Nota FG').click() })
    expect(buttonWith('Keluarkan dari Draft')).toBeTruthy()
    // re-picking the same Mandor is not a change: the draft stays
    await choosePickerOption(mandor, 'Mandor Asep')
    expect(buttonWith('Keluarkan dari Draft')).toBeTruthy()
    await choosePickerOption(mandor, 'Mandor Ujang', 'ujang')
    expect(container.textContent).toContain('RW-2')
    expect(buttonWith('Keluarkan dari Draft')).toBeUndefined()
  })

  it('Mandor nota is locked once the nota is posted', async () => {
    await renderNota()
    await act(async () => { buttonWith('Tambah ke Nota FG').click() })
    await act(async () => { container.querySelector<HTMLInputElement>('input[type="checkbox"]')!.click() })
    await act(async () => { container.querySelector<HTMLButtonElement>('.handoff-submit')!.click() })
    expect(pickerTrigger('Mandor nota', container).disabled).toBe(true)
  })
})

describe('Penjualan & Keuangan customer pickers (demo)', () => {
  it('invoice customer: default unchanged; the picked customer is on the invoice summary', async () => {
    await render(<SalesPages view="sales-invoice" onNavigate={vi.fn()}/>)
    const customer = pickerTrigger('Pelanggan', container)
    expect(pickerValue(customer)).toBe('Nusantara Fashion')
    await choosePickerOption(customer, 'Sentra Denim', 'sentra')
    expect(container.textContent).toContain('Sentra Denim · NET 30')
  })

  it('all invoices, payments and history: the picked customer filters, "Semua …" resets', async () => {
    const count = (selector: string) => Number(/\d+/.exec(container.querySelector(selector)?.textContent ?? '')?.[0])
    await render(<SalesPages view="sales-allocation" onNavigate={vi.fn()}/>)
    const allInvoices = count('.biz-invoice-register header strong')
    const toko = pickerTrigger('Filter toko', container)
    await openPicker(toko)
    const firstStore = pickerOptionLabels()[1]!
    await pressInPicker('Escape')
    await choosePickerOption(toko, firstStore)
    expect(count('.biz-invoice-register header strong')).toBeLessThan(allInvoices)
    await choosePickerOption(toko, 'Semua toko')
    expect(count('.biz-invoice-register header strong')).toBe(allInvoices)

    act(() => root.unmount()); root = createRoot(container)
    await render(<SalesPages view="sales-payments" onNavigate={vi.fn()}/>)
    const allOpen = count('.biz-master-detail > aside > header strong')
    const payer = pickerTrigger('Filter pelanggan', container)
    await openPicker(payer)
    const firstCustomer = pickerOptionLabels()[1]!
    await pressInPicker('Escape')
    await choosePickerOption(payer, firstCustomer)
    expect(count('.biz-master-detail > aside > header strong')).toBeLessThan(allOpen)

    act(() => root.unmount()); root = createRoot(container)
    await render(<SalesPages view="sales-history" onNavigate={vi.fn()}/>)
    const allEvents = count('.biz-timeline header strong')
    const history = pickerTrigger('Filter pelanggan', container)
    await openPicker(history)
    const someone = pickerOptionLabels()[1]!
    await pressInPicker('Escape')
    await choosePickerOption(history, someone)
    expect(count('.biz-timeline header strong')).toBeLessThan(allEvents)
  })

  it('Piutang: the picked customer filters the AR browser', async () => {
    await render(<FinancePages view="finance-ar" onNavigate={vi.fn()} onSalesPayment={vi.fn()} onAttendance={vi.fn()}/>)
    const all = container.querySelectorAll('.biz-browser-list > button').length
    const customer = pickerTrigger('Filter pelanggan', container)
    await openPicker(customer)
    const first = pickerOptionLabels()[1]!
    await pressInPicker('Escape')
    await choosePickerOption(customer, first)
    const visible = [...container.querySelectorAll('.biz-browser-list > button')]
    expect(visible.length).toBeLessThan(all)
    expect(visible.every((row) => row.textContent?.includes(first))).toBe(true)
  })
})
