import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import type { AnalysisResult } from '../../src/cp7/contract'
import { frameworkExample } from '../../src/cp7/fixture'
import { assertFixtureCoherence, createAnalysisReadPort, formatFact, integrationGate, projectShell, refuseOperationalCommand } from '../../src/cp7/workspace'
import { channelReadiness, previewWhatsApp, sendWhatsApp } from '../../src/cp7/notification'

const fixture = (): AnalysisResult => structuredClone(frameworkExample)

describe('CP7 S0: boundary and shared presentation, not ERP runtime acceptance', () => {
  it('keeps the bundled example and types equal to the pinned v2 contract', () => {
    expect(frameworkExample).toEqual(JSON.parse(readFileSync('docs/cp7/contracts/analysis.example.json', 'utf8')))
    expect(readFileSync('src/cp7/contract.ts', 'utf8')).toBe(readFileSync('docs/cp7/contracts/backbone.ts', 'utf8'))
    expect(readFileSync('src/cp7/notificationContract.ts', 'utf8')).toBe(readFileSync('docs/cp7/contracts/notification.ts', 'utf8'))
  })
  it.each(['UAT_AUTH_SIMULATION', 'DISPOSABLE_TEST'] as const)('refuses every fixture in %s without a connected reader', async runtime => {
    for (const mode of ['EMPTY', 'FRAMEWORK', 'PARTIAL', 'STALE', 'ERROR'] as const) {
      expect(await createAnalysisReadPort(runtime).read(mode)).toMatchObject({ kind: 'UNAVAILABLE', analysis: null })
    }
  })
  it.each(['EMPTY', 'PARTIAL', 'ERROR'] as const)('%s never substitutes zero or a successful example', async mode => {
    const state = await createAnalysisReadPort('DEMO_SIMULATION').read(mode)
    expect(state.kind).toBe(mode)
    const view = projectShell(state, 'OWNER')
    expect(view.analysis).toBeNull(); expect(view.rows).toEqual([]); expect(view.prompt).toBe('')
  })
  it('preserves the framework oracle 18/8 and unknown feasibility in every consumer', async () => {
    const state = await createAnalysisReadPort('DEMO_SIMULATION').read('FRAMEWORK')
    const view = projectShell(state, 'OWNER')
    expect(view.rows[0].q_base).toMatchObject({ value: '18', state: 'ASSUMED' })
    expect(view.rows[0].q_conditional).toMatchObject({ value: '8', state: 'ASSUMED' })
    expect(view.report).toContain('Kebutuhan dasar 18 PCS · asumsi; kebutuhan bersyarat 8 PCS · asumsi')
    expect(view.report).toContain('Produksi baru yang layak Belum diketahui')
    expect(view.prompt).toContain(view.report)
    expect(previewWhatsApp(view)).toContain(view.report)
    expect(view.prompt).toContain('10 PCS · asumsi')
    expect(state.analysis).toEqual(frameworkExample)
  })
  it('removes financial values before report, AI and notification formatting', () => {
    const result = fixture()
    result.metrics[0].value = { state: 'KNOWN', unit: 'IDR', value: '987654321.09', refs: [{ kind: 'TEST', id: 'private', revision: '1' }] }
    const state = { kind: 'READY', analysis: result, message: 'fixture' } as const
    const owner = projectShell(state, 'OWNER')
    const operations = projectShell(state, 'OPERATIONS')
    expect(owner.report).toContain('987.654.321,09')
    expect(operations.analysis?.metrics).toEqual([])
    expect(JSON.stringify(operations)).not.toContain('987')
    expect(previewWhatsApp(operations)).not.toContain('987')
    expect(projectShell(state, 'DENIED')).toMatchObject({ analysis: null, rows: [], actions: [], prompt: '', report: '' })
    expect(result.metrics).toHaveLength(1)
  })
  it('preserves stale snapshot values but marks all exported text stale', async () => {
    const state = await createAnalysisReadPort('DEMO_SIMULATION').read('STALE')
    expect(state.kind).toBe('STALE')
    const view = projectShell(state, 'OWNER')
    expect(view.report).toContain('DATA BERUBAH')
    expect(view.prompt).toContain('DATA BERUBAH')
    expect(previewWhatsApp(view)).toContain('DATA BERUBAH')
    expect(view.rows[0].actual_fg).toMatchObject({ value: '18' })
  })
  it('never presents unknown as zero and preserves large decimal strings', () => {
    expect(formatFact({ state: 'UNKNOWN', unit: 'IDR', reason: 'pending', refs: [] })).toBe('Belum diketahui')
    expect(formatFact({ state: 'KNOWN', unit: 'PCS', value: '0', refs: [] })).toBe('0 PCS')
    expect(formatFact({ state: 'KNOWN', unit: 'IDR', value: '9007199254740993.01', refs: [] })).toBe('Rp9.007.199.254.740.993,01')
  })
  it.each(['partial', 'duplicate', 'size', 'fractional', 'overallocated', 'missing-assumption', 'stop'] as const)('rejects %s counterexample in bundled fixture guard', variation => {
    const result = fixture()
    if (variation === 'partial') result.snapshot.capture_complete = false
    if (variation === 'duplicate') result.sources.push(structuredClone(result.sources[0]))
    if (variation === 'size') result.allocation_edges[0].size_id = '31'
    if (variation === 'fractional') result.sources[0].physical_remaining = { state: 'KNOWN', value: '12.5', unit: 'PCS', refs: [{ kind: 'TEST', id: 'x', revision: '1' }] }
    if (variation === 'overallocated') result.allocation_edges[0].input_qty = { state: 'KNOWN', value: '13', unit: 'PCS', refs: [{ kind: 'TEST', id: 'x', revision: '1' }] }
    if (variation === 'missing-assumption') result.assumptions = []
    if (variation === 'stop') { result.recommendations[0].production_state = 'STOPPED'; result.actions[0].intent = 'START_NEW' }
    expect(() => assertFixtureCoherence(result)).toThrow()
    expect(() => assertFixtureCoherence(fixture())).not.toThrow()
  })
  it('keeps exact singleton, four-size and alphanumeric membership intact without parsing ranges', () => {
    const result = fixture()
    result.sources = []; result.allocation_edges = []; result.actions = []
    result.recommendations = ['27', '31', '32', '33', '34', 'XL'].map(size => {
      const row = structuredClone(result.recommendations[0])
      row.target.key = `physical-${size}`; row.target.size_id = size
      if (row.target.kind === 'PRODUCT') { row.target.product_id = `product-${size}`; row.target.product_version_id = `version-${size}` }
      return row
    })
    expect(projectShell({ kind: 'READY', analysis: result, message: 'fixture' }, 'OWNER').rows.map(row => row.target.size_id)).toEqual(['27', '31', '32', '33', '34', 'XL'])
  })
  it('keeps all operational and delivery gates closed despite successful fixture reads', async () => {
    await createAnalysisReadPort('DEMO_SIMULATION').read('FRAMEWORK')
    expect(integrationGate).toMatchObject({ acceptedExecutionBase: null, connected: false, apply: false, publish: false, whatsapp: false })
    expect(refuseOperationalCommand()).toMatchObject({ ok: false, code: 'CP6_ACCEPTANCE_REQUIRED' })
    expect(sendWhatsApp()).toMatchObject({ ok: false, code: 'DELIVERY_DISABLED' })
    expect(channelReadiness).toMatchObject({ live_enabled: false, provider: 'NOT_SELECTED', authorized_test: 'NOT_RUN', delivery: 'NOT_RUN' })
  })
})
