// @vitest-environment jsdom

import { act, useState } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import BrowsePicker, { type BrowseOption } from './BrowsePicker'
import {
  choosePickerOption, openPicker, pickerOptionLabels, pickerPanel, pickerSearch, pickerTrigger, pickerValue,
  pressInPicker, typeInPicker,
} from './browsePickerDom.test.support'

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

const mandors: BrowseOption[] = [
  { id: 'all', label: 'Semua mandor', pinned: true },
  { id: 'm-afat', label: 'Mandor Afat', detail: 'M-01', group: 'Jahit' },
  { id: 'm-asep', label: 'Mandor Asep', detail: 'M-02', group: 'Jahit' },
  { id: 'm-dedi', label: 'Mandor Dedi', detail: 'M-03', meta: 'tidak aktif', group: 'Rework', disabled: true },
]

function Harness(props: Partial<Parameters<typeof BrowsePicker>[0]> & { initial?: string | null; onPicked?: (id: string) => void }) {
  const { initial = null, onPicked, ...rest } = props
  const [value, setValue] = useState<string | null>(initial)
  return <BrowsePicker
    label="Mandor"
    value={value}
    options={mandors}
    onChange={(id) => { setValue(id); onPicked?.(id) }}
    {...rest}
  />
}

describe('BrowsePicker', () => {
  it('keeps the dark default markup: no tone or size modifier classes', async () => {
    act(() => root.render(<Harness/>))
    expect(container.querySelector('.browse-picker')?.className).toBe('browse-picker')
    await openPicker(pickerTrigger('Mandor', container))
    expect(pickerPanel()?.className).toBe('browse-picker-panel')
    expect(pickerPanel()?.parentElement).toBe(document.body)
  })

  it('light tone and compact size mark both the field and the portalled popdown', async () => {
    act(() => root.render(<Harness tone="light" size="compact"/>))
    expect(container.querySelector('.browse-picker')?.classList.contains('tone-light')).toBe(true)
    expect(container.querySelector('.browse-picker')?.classList.contains('size-compact')).toBe(true)
    await openPicker(pickerTrigger('Mandor', container))
    expect(pickerPanel()?.classList.contains('tone-light')).toBe(true)
    expect(pickerPanel()?.classList.contains('size-compact')).toBe(true)
  })

  it('searches, groups, shows meta, and never offers a disabled row', async () => {
    const picked = vi.fn()
    act(() => root.render(<Harness onPicked={picked}/>))
    const trigger = pickerTrigger('Mandor', container)
    expect(pickerValue(trigger)).toBe('Pilih…')
    await openPicker(trigger)
    expect([...pickerPanel()!.querySelectorAll('.browse-picker-group-name')].map((node) => node.textContent)).toEqual(['Jahit', 'Rework'])
    expect(pickerPanel()!.querySelector('[aria-disabled="true"] b')?.textContent).toBe('tidak aktif')
    await typeInPicker('asep')
    // the pinned "Semua mandor" stays reachable while the list narrows
    expect(pickerOptionLabels()).toEqual(['Semua mandor', 'Mandor Asep'])
    await typeInPicker('dedi')
    expect(pickerOptionLabels()).toEqual(['Semua mandor', 'Mandor Dedi'])
    await act(async () => { (pickerPanel()!.querySelector('[aria-disabled="true"]') as HTMLElement).click() })
    expect(picked).not.toHaveBeenCalled()
    await typeInPicker('zzz')
    expect(pickerPanel()!.textContent).toContain('Tidak ada yang cocok')
  })

  it('Enter picks the highlighted row, Escape closes without a change and returns focus', async () => {
    const picked = vi.fn()
    act(() => root.render(<Harness onPicked={picked}/>))
    const trigger = pickerTrigger('Mandor', container)
    await openPicker(trigger)
    await typeInPicker('M-02')
    await pressInPicker('Enter')
    expect(picked).toHaveBeenCalledWith('m-asep')
    expect(pickerPanel()).toBeNull()
    expect(pickerValue(trigger)).toBe('Mandor Asep')
    expect(document.activeElement).toBe(trigger)

    await openPicker(trigger)
    await pressInPicker('ArrowDown')
    await pressInPicker('Escape')
    expect(pickerPanel()).toBeNull()
    expect(picked).toHaveBeenCalledTimes(1)
    expect(pickerValue(trigger)).toBe('Mandor Asep')
    expect(document.activeElement).toBe(trigger)
  })

  it('a disabled field does not open', async () => {
    act(() => root.render(<Harness disabled initial="m-afat"/>))
    const trigger = pickerTrigger('Mandor', container)
    expect(trigger.disabled).toBe(true)
    expect(pickerValue(trigger)).toBe('Mandor Afat')
    await act(async () => { trigger.click() })
    expect(pickerPanel()).toBeNull()
  })

  it('aria-label names the trigger, list and search when the visible caption is hidden', async () => {
    act(() => root.render(<Harness label="POLA" hideLabel aria-label="Filter Pola Laundry"/>))
    const trigger = pickerTrigger('Filter Pola Laundry', container)
    expect(trigger.hasAttribute('aria-labelledby')).toBe(false)
    expect(container.querySelector('.browse-picker-label')?.classList.contains('is-hidden')).toBe(true)
    await openPicker(trigger)
    expect(pickerSearch().getAttribute('aria-label')).toBe('Cari filter pola laundry')
    expect(pickerPanel()!.querySelector('[role="listbox"]')?.getAttribute('aria-label')).toBe('Filter Pola Laundry')
  })

  it('server-side search hands the typed text to the host and shows its status instead of filtering', async () => {
    const queries: string[] = []
    act(() => root.render(<Harness filterOptions={false} status="3 hasil" onQueryChange={(query) => queries.push(query)}/>))
    await openPicker(pickerTrigger('Mandor', container))
    await typeInPicker('zzz')
    expect(pickerOptionLabels()).toEqual(['Semua mandor', 'Mandor Afat', 'Mandor Asep', 'Mandor Dedi'])
    expect(pickerPanel()!.querySelector('.browse-picker-search small')?.textContent).toBe('3 hasil')
    await pressInPicker('Escape')
    expect(queries).toEqual(['zzz', ''])
  })

  it('a pinned choice can be picked back', async () => {
    const picked = vi.fn()
    act(() => root.render(<Harness initial="m-afat" onPicked={picked}/>))
    await choosePickerOption(pickerTrigger('Mandor', container), 'Semua mandor', 'afat')
    expect(picked).toHaveBeenCalledWith('all')
  })
})
