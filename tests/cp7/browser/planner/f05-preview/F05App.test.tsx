// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import F05App from './F05App'
import { createAnalysisReadPort, type AnalysisReadPort } from '../../../../../src/cp7/workspace'

let host: HTMLDivElement; let root: Root
beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  host = document.createElement('div'); document.body.append(host); root = createRoot(host)
})
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks() })
async function mount(readPort?: AnalysisReadPort) { await act(async () => root.render(<F05App runtimeMode="DEMO_SIMULATION" readPort={readPort} />)) }
async function select(label: string, value: string, wait = true) {
  const input = [...host.querySelectorAll('label')].find(item => item.textContent?.startsWith(label))!.querySelector('select')!
  await act(async () => { input.value = value; input.dispatchEvent(new Event('change', { bubbles: true })) })
  if (wait) await vi.waitFor(async () => { await act(async () => {}); expect(host.textContent).not.toContain('Memuat snapshot contoh') }, { interval: 10 })
}
function button(label: string) { return [...host.querySelectorAll<HTMLButtonElement>('button')].find(item => item.textContent === label)! }
async function click(label: string) { await act(async () => button(label).click()) }
it.each(['UAT_AUTH_SIMULATION', 'DISPOSABLE_TEST'] as const)('never reads fixture data in %s', async runtimeMode => {
  const read = vi.fn(); await act(async () => root.render(<F05App runtimeMode={runtimeMode} readPort={{ read }} />))
  expect(read).not.toHaveBeenCalled(); expect(host.querySelector('select')).toBeNull(); expect(host.textContent).toContain('Integrasi F05 belum dibuka')
})
it('starts empty and requires an explicit fixture choice', async () => {
  await mount(); expect(host.textContent).toContain('Cangkang siap menerima data'); expect(host.querySelector('[data-fact-state]')).toBeNull()
})
it.each(['PARTIAL', 'ERROR', 'EMPTY'])('withholds all values and children in %s', async mode => {
  await mount(); await select('Data contoh', 'FRAMEWORK'); expect(host.querySelector('[data-fact-state]')).not.toBeNull()
  await select('Data contoh', mode); expect(host.querySelector('[data-fact-state]')).toBeNull(); expect(host.querySelector('textarea')).toBeNull()
})
it('purges archives and queue when access is denied or narrowed', async () => {
  await mount(); await select('Data contoh', 'FRAMEWORK'); await click('Buat arsip contoh'); await click('Antrekan simulasi')
  expect(host.textContent).toContain('local-report-1'); expect(host.textContent).toContain('Antrean simulasi (1)')
  await select('Hak akses contoh', 'DENIED'); expect(host.querySelector('textarea')).toBeNull(); expect(host.textContent).not.toContain('fixture-O02-run1')
  await select('Hak akses contoh', 'OPERATIONS'); expect(host.textContent).not.toContain('local-report-1'); expect(host.textContent).not.toContain('GROSS_MARGIN'); expect(host.textContent).toContain('Antrean simulasi (0)')
})
it('preserves immutable archives across a stale refresh and blocks new simulated publication', async () => {
  await mount(); await select('Data contoh', 'FRAMEWORK'); await click('Buat arsip contoh')
  const old = host.querySelector<HTMLTextAreaElement>('[aria-label="Isi arsip contoh"]')!.value
  await select('Data contoh', 'STALE')
  expect(host.querySelector<HTMLTextAreaElement>('[aria-label="Isi arsip contoh"]')!.value).toBe(old)
  expect(button('Buat arsip contoh').disabled).toBe(true); expect(button('Antrekan simulasi').disabled).toBe(true)
})
it('fences delayed readers so an old result cannot overwrite a newer error', async () => {
  const fixture = await createAnalysisReadPort('DEMO_SIMULATION').read('FRAMEWORK')
  let resolve!: (value: typeof fixture) => void
  await mount({ read: mode => mode === 'FRAMEWORK' ? new Promise(done => { resolve = done }) : Promise.resolve({ kind: 'ERROR', analysis: null, message: 'new error' }) })
  await select('Data contoh', 'FRAMEWORK', false); await select('Data contoh', 'ERROR'); await act(async () => resolve(fixture))
  expect(host.textContent).toContain('new error'); expect(host.querySelector('[data-fact-state]')).toBeNull()
})
it('reports clipboard failure and blocked popup with a manual fallback', async () => {
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: vi.fn().mockRejectedValue(new Error('denied')) } })
  vi.spyOn(window, 'open').mockReturnValue(null)
  await mount(); await select('Data contoh', 'FRAMEWORK'); await click('Salin prompt')
  expect(host.textContent).toContain('Salin otomatis gagal'); await click('Buka ChatGPT'); expect(host.textContent).toContain('Tab diblokir')
})
it('does not show a late clipboard success after scope removal', async () => {
  let resolve!: () => void; Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: () => new Promise<void>(done => { resolve = done }) } })
  await mount(); await select('Data contoh', 'FRAMEWORK'); await click('Salin prompt'); await select('Hak akses contoh', 'DENIED'); await act(async () => resolve())
  expect(host.textContent).not.toContain('Prompt berhasil disalin')
})
