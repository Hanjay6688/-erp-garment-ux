// DOM helpers for tests that drive a BrowsePicker the way a person does:
// open the field, type in the popdown search, pick a row (click or Enter),
// or press Escape. Not a test file itself (no suites); imported by *.test.tsx.
import { act } from 'react'

function accessibleName(trigger: HTMLButtonElement) {
  const ariaLabel = trigger.getAttribute('aria-label')
  if (ariaLabel) return ariaLabel
  const labelledBy = trigger.getAttribute('aria-labelledby')
  return labelledBy ? document.getElementById(labelledBy)?.textContent ?? '' : ''
}

/** The picker trigger whose accessible name is exactly `name`. */
export function pickerTrigger(name: string, scope: ParentNode = document): HTMLButtonElement {
  const trigger = [...scope.querySelectorAll<HTMLButtonElement>('button.browse-picker-trigger')]
    .find((candidate) => accessibleName(candidate) === name)
  if (!trigger) throw new Error(`No BrowsePicker named "${name}"`)
  return trigger
}

/** Text the closed trigger shows as the current value (or its placeholder). */
export function pickerValue(trigger: HTMLButtonElement) {
  const value = trigger.querySelector('.browse-picker-value')
  return value?.querySelector('strong')?.textContent ?? value?.querySelector('em')?.textContent ?? ''
}

export function pickerPanel() {
  return document.querySelector<HTMLElement>('.browse-picker-panel')
}

export function pickerSearch() {
  const input = pickerPanel()?.querySelector<HTMLInputElement>('input[role="combobox"]')
  if (!input) throw new Error('BrowsePicker popdown is not open')
  return input
}

/** Labels (first line) of the rows currently listed in the open popdown. */
export function pickerOptionLabels() {
  return [...(pickerPanel()?.querySelectorAll<HTMLElement>('[role="option"]') ?? [])]
    .map((option) => option.querySelector('strong')?.textContent ?? '')
}

export function pickerOption(label: string) {
  const option = [...(pickerPanel()?.querySelectorAll<HTMLElement>('[role="option"]') ?? [])]
    .find((candidate) => candidate.querySelector('strong')?.textContent === label)
  if (!option) throw new Error(`No option "${label}" in the open popdown`)
  return option
}

export async function openPicker(trigger: HTMLButtonElement) {
  await act(async () => { trigger.click() })
  return pickerSearch()
}

export async function typeInPicker(text: string) {
  const input = pickerSearch()
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
  if (!setter) throw new Error('DOM value setter is unavailable.')
  await act(async () => {
    setter.call(input, text)
    input.dispatchEvent(new Event('input', { bubbles: true }))
  })
}

export async function pressInPicker(key: 'Enter' | 'Escape' | 'ArrowDown' | 'ArrowUp' | 'Home' | 'End') {
  const input = pickerSearch()
  await act(async () => { input.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true })) })
}

/** Open the picker, narrow it with `search` (optional) and click the row labelled `label`. */
export async function choosePickerOption(trigger: HTMLButtonElement, label: string, search?: string) {
  await openPicker(trigger)
  if (search !== undefined) await typeInPicker(search)
  const option = pickerOption(label)
  await act(async () => { option.click() })
}
