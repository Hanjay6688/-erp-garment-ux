// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, expect, it } from 'vitest'
import { createAnalysisReadPort, projectShell } from '../../../../../src/cp7/workspace'
import { CuttingYieldAnalyzer, type YieldReadPort } from './CuttingYieldAnalyzer'
import { readYieldFixture } from './cuttingYieldFixtures'
import type { YieldReview } from './cuttingYieldContract'

let host: HTMLDivElement; let root: Root
beforeEach(() => { ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true; host = document.createElement('div'); document.body.append(host); root = createRoot(host) })
afterEach(async () => { await act(async () => root.unmount()); host.remove() })
async function mount(read: YieldReadPort = readYieldFixture, stale = false) { const view = projectShell(await createAnalysisReadPort('DEMO_SIMULATION').read('FRAMEWORK'), 'OWNER'); await act(async () => root.render(<CuttingYieldAnalyzer view={view} stale={stale} read={read} />)) }
async function click() { await act(async () => host.querySelector<HTMLButtonElement>('button')!.click()) }
async function mix(value: string) { await act(async () => { const select = host.querySelector('select')!; select.value = value; select.dispatchEvent(new Event('change', { bubbles: true })) }) }
it('starts with width blank and can load a comparison without it', async () => {
  await mount(); expect(host.querySelector('input')!.value).toBe(''); expect(host.querySelector('[data-yield-range]')).toBeNull()
  await click(); expect(host.textContent).toContain('80–120 PCS'); expect(host.textContent).toContain('Basis: tanpa lebar')
})
it('changing size mix withholds previous numbers instead of applying the same range', async () => {
  await mount(); await click(); await mix('unique'); expect(host.querySelector('[data-yield-range]')).toBeNull(); await click()
  expect(host.textContent).toContain('74–114 PCS'); await mix('all30'); await click(); expect(host.querySelector('[data-yield-range]')).toBeNull()
})
it('does not accept a delayed response for a previous mix', async () => {
  let resolve!: (review: YieldReview) => void; let supplied!: YieldReview
  await mount(async (...args) => { supplied = await readYieldFixture(...args); return new Promise(done => { resolve = done }) })
  await click(); await mix('jumbo'); await act(async () => resolve(supplied)); expect(host.querySelector('[data-yield-range]')).toBeNull()
})
it('stale snapshot blocks fixture reads and ranges', async () => { await mount(undefined, true); await click(); expect(host.querySelector('button')!.disabled).toBe(true); expect(host.querySelector('[data-yield-range]')).toBeNull() })
it.each(['completed', 'pending'])('withholds the %s result when the analyzer reader is replaced', async state => {
  let resolve!: (review: YieldReview) => void; let supplied!: YieldReview
  const old: YieldReadPort = async (...args) => { supplied = await readYieldFixture(...args); return state === 'completed' ? supplied : new Promise(done => { resolve = done }) }
  await mount(old); await click()
  if (state === 'completed') expect(host.querySelector('[data-yield-range]')).not.toBeNull()
  const next: YieldReadPort = async (...args) => ({ ...await readYieldFixture(...args), modelVersion: 'fixture-replacement-reader' })
  await mount(next)
  if (state === 'pending') await act(async () => resolve(supplied))
  expect(host.querySelector('[data-yield-range]')).toBeNull()
  await mount(old); expect(host.querySelector('[data-yield-range]')).toBeNull()
  await mount(next)
  await click(); expect(host.textContent).toContain('fixture-replacement-reader')
})
