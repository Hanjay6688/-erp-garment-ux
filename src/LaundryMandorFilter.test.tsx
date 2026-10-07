// @vitest-environment jsdom

import { act, useState } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  LAUNDRY_ALL_MANDORS,
  LAUNDRY_NO_MANDOR,
  LaundryPage,
  laundryDeliverySeeds,
  laundryMandorOf,
  laundryMandorOptions,
  laundryReadySeeds,
  matchesLaundryMandor,
  type LaundryDelivery,
  type LaundryReadyBatch,
} from './App'
import { choosePickerOption, openPicker, pickerOptionLabels, pickerTrigger, pickerValue, pressInPicker } from './components/browsePickerDom.test.support'

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

function Harness() {
  const [ready, setReady] = useState<LaundryReadyBatch[]>(laundryReadySeeds)
  const [deliveries, setDeliveries] = useState<LaundryDelivery[]>(laundryDeliverySeeds)
  return <LaundryPage
    prefill={null}
    readyBatches={ready}
    setReadyBatches={setReady}
    deliveries={deliveries}
    setDeliveries={setDeliveries}
    onPosted={vi.fn()}
    onReturnToWip={vi.fn()}
    onOpenQc={vi.fn()}
  />
}

const mandorPicker = () => pickerTrigger('Filter Mandor Laundry', container)
const chooseMandor = (value: string) => choosePickerOption(mandorPicker(), value)
const parentTitles = () => [...container.querySelectorAll('.laundry-parent-card h3')].map((node) => node.textContent)
const returnTitles = () => [...container.querySelectorAll('.laundry-return-card h3')].map((node) => node.textContent)
const kpi = (label: string) => [...container.querySelectorAll('.laundry-kpi-grid > .panel')]
  .find((panel) => panel.querySelector('span')?.textContent === label)?.querySelector('strong')?.textContent
const clickButton = (text: string) => act(() => {
  [...container.querySelectorAll('button')].find((button) => button.textContent?.trim() === text)!.click()
})

describe('laundry mandor helpers', () => {
  it('uses the batch mandor, then the source sewing batch, then an explicit "Tanpa mandor"', () => {
    expect(laundryMandorOf({ mandor: 'Mandor Asep', parentId: 'POT-X' })).toBe('Mandor Asep')
    expect(laundryMandorOf({ mandor: '  ', parentId: 'POT-260827-042' })).toBe('Mandor Afat')
    expect(laundryMandorOf({ mandor: '', parentId: 'POT-UNKNOWN' })).toBe(LAUNDRY_NO_MANDOR)
  })

  it('lists distinct mandors alphabetically with "Tanpa mandor" last and matches the filter', () => {
    const rows = [...laundryReadySeeds, ...laundryDeliverySeeds, { mandor: '', parentId: 'POT-UNKNOWN' }]
    expect(laundryMandorOptions(rows)).toEqual(['Mandor Afat', 'Mandor Asep', 'Mandor Dedi', LAUNDRY_NO_MANDOR])
    expect(matchesLaundryMandor(laundryReadySeeds[0], LAUNDRY_ALL_MANDORS)).toBe(true)
    expect(matchesLaundryMandor(laundryReadySeeds[0], 'Mandor Asep')).toBe(false)
  })
})

describe('LaundryPage mandor filter', () => {
  it('filters the send list, the return list and the summary by mandor', async () => {
    act(() => root.render(<Harness/>))

    await openPicker(mandorPicker())
    expect(pickerOptionLabels()).toEqual(['Semua mandor', 'Mandor Afat', 'Mandor Asep', 'Mandor Dedi'])
    await pressInPicker('Escape')
    expect(parentTitles()).toHaveLength(3)
    expect(container.querySelector('.laundry-summary-scope')?.textContent).toContain('semua mandor')
    expect(kpi('SIAP DIKIRIM')).toBe('583 pcs')

    await chooseMandor('Mandor Asep')
    expect(parentTitles()).toEqual(['POT-260826-041 · Malibu Regular'])
    expect(kpi('SIAP DIKIRIM')).toBe('244 pcs')
    expect(kpi('SEDANG DI LUAR')).toBe('64 pcs')
    expect(kpi('LAUNDRY BS')).toBe('6 pcs')
    const scope = container.querySelector('.laundry-summary-scope')
    expect(scope?.classList.contains('filtered')).toBe(true)
    expect(scope?.textContent).toContain('difilter untuk Mandor Asep')
    expect(container.querySelector('.laundry-kpi-grid')?.getAttribute('aria-label')).toBe('Ringkasan Laundry · Mandor Asep')

    clickButton('Terima kembali')
    expect(returnTitles()).toEqual(['POT-260826-041 · Batch 041-02'])

    await chooseMandor('Mandor Afat')
    expect(returnTitles()).toEqual(['POT-260824-038 · Batch 038-01'])
    expect(kpi('LAUNDRY BS')).toBe('4 pcs')

    clickButton('Tampilkan semua mandor')
    expect(pickerValue(mandorPicker())).toBe(LAUNDRY_ALL_MANDORS)
    expect(returnTitles()).toHaveLength(3)
    expect(kpi('LAUNDRY BS')).toBe('12 pcs')
  })

  it('shows an actionable empty state when a mandor has no return letters', () => {
    act(() => root.render(<Harness/>))
    clickButton('Terima kembali')
    act(() => {
      const search = container.querySelector<HTMLInputElement>('.laundry-search input')!
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(search, 'tidak-ada-batch-ini')
      search.dispatchEvent(new Event('input', { bubbles: true }))
    })
    expect(returnTitles()).toHaveLength(0)
    expect(container.textContent).toContain('Surat kirim tidak ditemukan')
    expect(container.textContent).toContain('Coba ganti laundry, mandor, Pola, atau kata pencarian.')
  })
})
