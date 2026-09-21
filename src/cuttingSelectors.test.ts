import { describe, expect, it } from 'vitest'
import { cuttingSelectionIssue, parseCuttingSelectorWorkspace } from './cuttingSelectors'
import { cuttingSelectorFixture } from '../tests/fixtures/productionRecovery'

const selected = () => cuttingSelectorFixture({ p_selected_order_id: 'po-1', p_selected_draft_id: 'group-1' })
describe('versioned cutting selector boundary', () => {
  it('keeps selected records and model outside a filtered page', () => {
    const data = selected()
    data.orders = []; data.order_page.total = 0; data.drafts = []; data.draft_page.total = 0
    const parsed = parseCuttingSelectorWorkspace(data)
    expect(parsed.selected_order?.model_id).toBe('model-1')
    expect(parsed.selected_draft?.model_id).toBe('model-1')
    expect(cuttingSelectionIssue(parsed, 'po-1', 'group-1', 1)).toBe('')
  })
  it('represents unavailable selection without inventing a replacement', () => {
    const data = selected(); data.drafts = []; data.draft_page.total = 0; data.selected_draft = null
    const parsed = parseCuttingSelectorWorkspace(data)
    expect(cuttingSelectionIssue(parsed, 'po-1', 'group-1', 1)).toMatch(/berubah tahap/)
  })
  it('refuses old contracts, wrong selected identities and missing draft models', () => {
    expect(() => parseCuttingSelectorWorkspace({ ...selected(), contract_version: 1 })).toThrow(/Versi/)
    expect(() => parseCuttingSelectorWorkspace({ ...selected(), selected_order_id: 'po-other' })).toThrow(/tidak cocok/)
    expect(() => parseCuttingSelectorWorkspace({ ...selected(), selected_draft: { ...selected().selected_draft, model_id: null } })).toThrow(/Model/)
  })
  it('refuses incomplete pages and duplicate rows', () => {
    expect(() => parseCuttingSelectorWorkspace({ ...selected(), order_page: { query: null, limit: 50, offset: 0, total: 51 } })).toThrow(/tidak lengkap/)
    const data = selected(); data.orders.push(data.orders[0]); data.order_page.total = 2
    expect(() => parseCuttingSelectorWorkspace(data)).toThrow(/berulang/)
  })
  it('does not coerce unknown counts or invalid page bounds into zero', () => {
    for (const value of [null, '1', -1, 1.5, Number.NaN]) {
      expect(() => parseCuttingSelectorWorkspace({ ...selected(), draft_page: { query: null, limit: 25, offset: 0, total: value } })).toThrow()
    }
    expect(() => parseCuttingSelectorWorkspace({ ...selected(), order_page: { query: null, limit: 201, offset: 0, total: 1 } })).toThrow()
  })
  it('requires the selected copy and current page to represent the same snapshot', () => {
    const data = selected()
    data.selected_draft = { ...data.selected_draft!, row_version: 2 }
    expect(() => parseCuttingSelectorWorkspace(data)).toThrow(/Snapshot/)
  })
  it('blocks stale row versions without changing the form version', () => {
    const parsed = parseCuttingSelectorWorkspace(selected())
    expect(cuttingSelectionIssue(parsed, 'po-1', 'group-1', 2)).toMatch(/sesi lain/)
    expect(cuttingSelectionIssue(parsed, 'po-missing', null, null)).toMatch(/PO terpilih/)
  })
})
