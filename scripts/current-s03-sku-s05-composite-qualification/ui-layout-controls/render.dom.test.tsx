// @vitest-environment jsdom
// Offline visual preparation only. Auth and RPC are fixture adapters, not ERP proof.
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { expect, it, vi } from 'vitest'
import { readFileSync, mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import Page from '../../../src/ConnectedAccessoryStandardReportPage'
import { recoveryIdentity } from '../../../tests/fixtures/productionRecovery'
const mocks = vi.hoisted(() => ({ rpc: vi.fn() }))
vi.mock('../../../src/auth/AuthProvider', () => ({ useAuth: () => ({ ...recoveryIdentity, identity: { ...recoveryIdentity.identity,
  permissions: ['finance.contractor_accessory.view', 'finance.hpp.view'] } }) }))
vi.mock('../../../src/lib/supabase', () => ({ getUatSupabaseClient: () => mocks }))
type Row = Record<string, any>
it.skipIf(!process.env.S05_LAYOUT_FIXTURE)('renders the unchanged page from the four retained Native report originals for offline visual checks', async () => {
  const input = JSON.parse(readFileSync(process.env.S05_LAYOUT_FIXTURE!, 'utf8'))
  expect(input.status).toBe('ACTUAL_NATIVE_BROWSER_PREREQUISITES_PREPARED')
  const out = process.env.S05_LAYOUT_OUTPUT!
  expect(out).toBeTruthy(); mkdirSync(out, { recursive: true })
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  for (const [label, fixture] of Object.entries(input.fixtures) as [string, Row][]) {
    const contractor = { id: fixture.contractor_id, name: fixture.contractor_name, active: true }
    mocks.rpc.mockImplementation(async (name: string, args: Row) => {
      expect(name).toBe('erp_cp7_get_accessory_standard_report_v1')
      const query = { period_start: args.p_start, period_end: args.p_end, contractor_id: args.p_contractor,
        po_id: args.p_po, q: args.p_query, offset: args.p_offset, limit: args.p_limit }
      // The empty navigation answer is synthetic. Only the final PO-specific
      // screen below receives the exact retained Native report, byte-for-value.
      const report = args.p_po === fixture.po_id ? structuredClone(fixture.expected_report) : {
        ...fixture.expected_report, period_start: args.p_start, period_end: args.p_end, po_filter: null,
        counts: { issue_items: 0, snapshots: 0, lots: 0, unknown_lots: 0, unallocated_lots: 0, issues_without_po: 0 },
        status: 'NO_GOOD_OUTPUT', rows: [], actual_sources: [], standard_sources: [], lot_sources: [],
      }
      return { error: null, data: { contract_version: 'cp7.accessory-standard-report.v1', business_DML: false,
        captured_at: '2026-11-01T11:48:00.000000Z', query,
        contractors: { offset: 0, limit: 30, total: 1, next_offset: null, rows: [contractor] },
        selected_contractor: args.p_contractor === null ? null : contractor,
        po_options: args.p_contractor === null ? [] : Object.values(input.fixtures).map((f: any) => ({ id: f.po_id, number: f.po_number })),
        report: args.p_contractor === null ? null : report } }
    })
    const container = document.createElement('div'); document.body.append(container); const root = createRoot(container)
    const settle = () => act(async () => { await new Promise(r => setTimeout(r, 0)) })
    const set = async (aria: string, value: string) => {
      const el = container.querySelector<HTMLInputElement | HTMLSelectElement>(`[aria-label="${aria}"]`)!
      expect(el).not.toBeNull()
      const proto = el instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype
      await act(async () => { Object.getOwnPropertyDescriptor(proto, 'value')!.set!.call(el, value)
        el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })) })
      await settle()
    }
    try {
      await act(async () => root.render(<Page/>)); await settle()
      await set('Mulai periode aksesori', fixture.day); await set('Akhir periode aksesori', fixture.day)
      const submit = container.querySelector<HTMLFormElement>('form')!
      await act(async () => submit.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))); await settle()
      const button = [...container.querySelectorAll<HTMLButtonElement>('.asr-contractors li button')].find(b => b.textContent === contractor.name)!
      expect(button).toBeTruthy(); await act(async () => button.click()); await settle()
      await set('PO laporan aksesori', fixture.po_id)
      expect(mocks.rpc.mock.calls.at(-1)![1]).toMatchObject({ p_start: fixture.day, p_end: fixture.day, p_po: fixture.po_id })
      expect(container.querySelector('[aria-label="Hasil laporan aksesori"]')).not.toBeNull()
      expect(container.querySelectorAll('tbody > tr')).toHaveLength(fixture.expected_report.rows.length)
      // HTML serialization must retain controlled form properties. innerHTML
      // alone loses a select's current value and would display its first option.
      for (const input of container.querySelectorAll('input')) input.setAttribute('value', input.value)
      const select = container.querySelector<HTMLSelectElement>('[aria-label="PO laporan aksesori"]')!
      expect(select.value).toBe(fixture.po_id)
      for (const option of select.options) option.toggleAttribute('selected', option.selected)
      expect(select.querySelector('option[selected]')?.getAttribute('value')).toBe(fixture.po_id)
      writeFileSync(resolve(out, label + '.html'), container.innerHTML)
    } finally { await act(async () => root.unmount()); container.remove() }
  }
})
