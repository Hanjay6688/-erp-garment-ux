// @vitest-environment jsdom

import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { Cp6Kpi } from './Cp6Kpi'

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
})

describe('CP6-06: a KPI the page has not read is unknown, not 0', () => {
  it('shows no number while the workspace is missing', async () => {
    await act(async () => { root.render(<Cp6Kpi label="SIAP DIKIRIM" value={undefined} note="pcs"/>) })
    const value = container.querySelector('strong')?.textContent ?? ''
    expect(value).toBe('—')
    expect(Number.isNaN(Number(value))).toBe(true)
    expect(container.textContent).toContain('belum diketahui')
    expect(container.querySelector('article')?.getAttribute('data-kpi-state')).toBe('UNKNOWN')
  })
  it('keeps a real zero from the server', async () => {
    await act(async () => { root.render(<Cp6Kpi label="SIAP DIKIRIM" value={0} note="pcs"/>) })
    expect(container.querySelector('strong')?.textContent).toBe('0')
    expect(container.textContent).not.toContain('belum diketahui')
  })
})
