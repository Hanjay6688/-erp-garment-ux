import { describe, expect, it } from 'vitest'
import { groupPermissionRows, parseAccessAdminData } from './AccessControlPage'
import { parseWipResponse, activeBlockerLabels } from './ConnectedWipStatusPage'
import { parsePatternRows, parsePatternTotal, sortPatternRows } from './patternModel'
import { createdPatternChoice, hasCanonicalPattern, mergeCreatedPattern } from './CuttingPatternPicker'

describe('connected access, Pola, and WIP response boundaries', () => {
  it('groups only relevant permission actions by module', () => {
    const parsed = parseAccessAdminData({
      permissions: [
        { key: 'production.wip.view', module_key: 'production.wip', module_label: 'WIP', action: 'view', sort_order: 2 },
        { key: 'production.wip.adjust', module_key: 'production.wip', module_label: 'WIP', action: 'adjust', sort_order: 3 },
        { key: 'master.pattern.view', module_key: 'master.pattern', module_label: 'Pola', action: 'view', sort_order: 1 },
      ],
      roles: [], users: [], audit: [],
    })
    expect(groupPermissionRows(parsed.permissions).map((group) => group.key)).toEqual(['production.wip', 'master.pattern'])
  })

  it('sorts Pola deterministically and keeps inactive history readable', () => {
    const response = { total: 3, rows: [
      { id: 'b', code: 'B', revision: 'R2', name: 'Beta', sort_order: 10, is_active: false, row_version: 2, updated_at: '', usage_count: 3 },
      { id: 'a', code: 'A', revision: 'R1', name: 'Alpha', sort_order: 10, is_active: true, row_version: 1, updated_at: '', usage_count: 0 },
      { id: 'z', code: 'Z', revision: 'R1', name: 'Zulu', sort_order: 99, is_active: true, row_version: 1, updated_at: '', usage_count: 0 },
    ] }
    const rows = parsePatternRows(response)
    expect(sortPatternRows(rows).map((row) => row.id)).toEqual(['a', 'b', 'z'])
    expect(parsePatternTotal(response, rows)).toBe(3)
    expect(rows.find((row) => row.id === 'b')).toMatchObject({ is_active: false, usage_count: 3 })
  })

  it('supports an empty Master Pola and auto-selects one canonical quick-create result once', () => {
    const empty = parsePatternRows({ total: 0, rows: [] })
    expect(empty).toEqual([])
    const choice = createdPatternChoice({ pattern_id: 'pattern-1', code: 'REG', revision: 'R1', name: 'Regular' })
    const created = mergeCreatedPattern(empty, choice)
    expect(created).toHaveLength(1)
    expect(created[0]).toMatchObject({ id: 'pattern-1', code: 'REG', revision: 'R1', name: 'Regular' })
    expect(mergeCreatedPattern(created, choice)).toHaveLength(1)
  })

  it('keeps Potongan save fail-closed until a canonical pattern_id is selected', () => {
    expect(hasCanonicalPattern(null)).toBe(false)
    expect(hasCanonicalPattern({ id: '', code: 'REG', revision: 'R1', name: 'Regular' })).toBe(false)
    expect(hasCanonicalPattern({ id: 'pattern-1', code: 'REG', revision: 'R1', name: 'Regular' })).toBe(true)
  })

  it('preserves authoritative WIP status and exposes every active blocker', () => {
    const response = parseWipResponse({
      filter: 'ACTIVE', sort: 'PATTERN', pattern_id: null,
      rows: [{
        cutting_group_id: 'group-1', control_status: 'ACTIVE', effective_qty_pcs: 100,
        unfinished_sewing_qty_pcs: 0, unsent_ready_qty_pcs: 20, laundry_draft_qty_pcs: 0,
        laundry_in_transit_qty_pcs: 10, unresolved_laundry_issue_qty_pcs: 2,
        pending_final_sku_handoff_qty_pcs: 4, remaining_final_sku_qty_pcs: 40,
        open_bs_count: 1, open_rework_count: 0, open_flag_count: 1, open_flags: [], row_version: 1,
      }],
    })
    expect(response.rows[0].control_status).toBe('ACTIVE')
    expect(activeBlockerLabels(response.rows[0])).toEqual([
      'Siap tapi belum dikirim', 'Di perjalanan/Laundry', 'Stuck/Missing',
      'Menunggu handoff QC', 'Belum Final SKU', 'BS terbuka', 'Tindakan operator',
    ])
  })
})
