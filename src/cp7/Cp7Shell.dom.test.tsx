// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, expect, it } from 'vitest'
import Cp7Shell from './Cp7Shell'

let host: HTMLDivElement
let root: Root
beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  host = document.createElement('div'); document.body.append(host); root = createRoot(host)
})
afterEach(async () => { await act(async () => root.unmount()); host.remove() })
it.each(['UAT_AUTH_SIMULATION', 'DISPOSABLE_TEST'] as const)('does not mount a fixture selector or business figures in %s', async runtimeMode => {
  await act(async () => root.render(<Cp7Shell runtimeMode={runtimeMode} />))
  expect(host.textContent).toContain('Integrasi CP7 belum dibuka')
  expect(host.querySelector('select')).toBeNull()
  expect(host.textContent).not.toContain('18 PCS')
})
it('opens demo with no fabricated data and an explicit fixture choice', async () => {
  await act(async () => root.render(<Cp7Shell runtimeMode="DEMO_SIMULATION" />))
  expect(host.textContent).toContain('Ruang kerja siap menerima data')
  expect(host.querySelector('select')?.value).toBe('EMPTY')
  expect(host.querySelector('[data-fact-state]')).toBeNull()
})
