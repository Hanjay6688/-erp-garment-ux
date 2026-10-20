import { describe, expect, it } from 'vitest'
import { alertAnalysisLine, alertSummary, parseSystemAlerts, waKindLabel } from './waContract'

const id = (n: number) => `a0000000-0000-4000-8000-${String(n).padStart(12, '0')}`
const detail = () => ({ run_id: id(1), data_as_of: '2026-10-20T01:00:00Z', checked_at: '2026-10-20T02:00:00Z',
  label: 'Kemeja M', target_key: `${id(2)}:${id(3)}`, category_key: `ACCESSORY_CATEGORY:${id(4)}`, category_name: 'Kancing',
  state: 'DATA_REVIEW', verdict: 'REVIEW_REQUIRED_NOW', gross_state: 'ASSUMED', gross_qty: '186', unit: 'PCS',
  installed_state: 'UNKNOWN', installed_proven: null, unused_allocated_state: 'UNKNOWN', unused_allocated_proven: null,
  additional_external_state: 'UNKNOWN', additional_external: null, threshold_status: 'NOT_EVALUATED_UNKNOWN',
  reason: 'INSTALLATION_AND_ELIGIBLE_UNUSED_SUPPLY_NOT_PROVEN' })
function reply(change: Record<string, unknown> = {}) {
  const d = { ...detail(), ...change }
  return { contract_version: 'cp7.system-alerts.v1', read_at: '2026-10-20T02:00:00Z', configured: true,
    collector: null, analysis: { run: null, request: null, tick: null },
    kinds: ['PRODUCTION_GAP', 'FABRIC_NEED', 'ACCESSORY_NEED'].map(kind => ({ kind, last_try_at: null, last_ok_at: null, last_error: null, open_count: null })),
    rows: [{ id: id(5), kind: 'ACCESSORY_NEED', subject_key: `ACCESSORY_NEED:${d.target_key}:${d.category_key}`, episode: 1,
      title: 'Kebutuhan aksesori perlu diperiksa', detail: d, party_names: [] as string[], state: 'OPEN', opened_at: '2026-10-20T02:00:00Z',
      refreshed_at: '2026-10-20T02:00:00Z', resolved_at: null, resolution: null, wa: null }] }
}

describe('ACCESSORY_NEED review notice, never a purchase quantity', () => {
  it('retains unknown external quantity and labels gross186 as assumed BOM need', () => {
    const a = parseSystemAlerts(reply(), { owner: true }).rows[0]
    expect(a.detail.kind).toBe('ACCESSORY_NEED')
    const text = alertSummary(a)
    expect(text).toContain('jumlah tambahan belum diketahui')
    expect(text).toContain('Kancing')
    expect(text).toContain('kebutuhan BOM (perkiraan) 186 PCS')
    expect(text).not.toMatch(/(?:perlu dibeli|perlu beli|tambahan 186|tambahan 0|ambang pengingat)/)
    expect(alertAnalysisLine(a)).toContain('dicek ulang')
    expect(waKindLabel.ACCESSORY_NEED).toContain('perlu diperiksa')
  })

  it('keeps exact small and large BOM decimal strings in the display', () => {
    for (const [gross_qty, shown] of [['0.001', '0,001'], ['9007199254740993', '9.007.199.254.740.993']]) {
      const a = parseSystemAlerts(reply({gross_qty}), { owner: true }).rows[0]
      expect(alertSummary(a)).toContain(`kebutuhan BOM (perkiraan) ${shown} PCS`)
      expect(alertSummary(a)).toContain('jumlah tambahan belum diketahui')
    }
  })

  it.each(['BOM_NOT_RECORDED', 'BOM_AMBIGUOUS'])('can describe complete-source %s without fabricated gross or external amount', reason => {
    const a = parseSystemAlerts(reply({ category_key: 'UNKNOWN_BOM', category_name: null, gross_state: 'UNKNOWN', gross_qty: null, reason }), { owner: true }).rows[0]
    expect(alertSummary(a)).toContain('jumlah tambahan belum diketahui')
    expect(alertSummary(a)).not.toMatch(/186|0 PCS|perlu dibeli|perlu beli/)
  })

  it('describes an unavailable category truthfully', () => {
    const a = parseSystemAlerts(reply({ gross_state: 'UNKNOWN', gross_qty: null, reason: 'CATEGORY_UNAVAILABLE' }), { owner: true }).rows[0]
    expect(alertSummary(a)).toContain('Kategori aksesori tidak tersedia')
  })

  it.each([
    { unit: '' }, { unit: '   ' }, { gross_qty: 186 }, { gross_qty: '0' }, { gross_qty: '-1' }, { gross_qty: null },
    { gross_state: 'UNKNOWN', gross_qty: '186' }, { installed_state: 'KNOWN' }, { installed_proven: '0' },
    { unused_allocated_state: 'KNOWN' }, { unused_allocated_proven: '80' }, { additional_external_state: 'KNOWN' },
    { additional_external: '0' }, { additional_external: '186' }, { verdict: 'STILL_OPEN' },
    { threshold_status: 'REACHED' }, { material_id: id(8) }, { category_key: 'UNKNOWN_BOM' }, { reason: 'UNREVIEWED_FREE_TEXT' },
  ])('fails closed on incompatible review facts %j', extra => {
    expect(() => parseSystemAlerts(reply(extra), { owner: true })).toThrow()
  })

  it('rejects a notice bound to another target/category or carrying party data', () => {
    const a = reply(); a.rows[0].subject_key += ':OTHER'
    expect(() => parseSystemAlerts(a, { owner: true })).toThrow()
    const b = reply(); b.rows[0].party_names = ['Restricted party']
    expect(() => parseSystemAlerts(b, { owner: true })).toThrow()
  })
})
