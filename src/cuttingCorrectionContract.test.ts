import { describe, expect, it } from 'vitest'
import { cuttingReopenPayload, parseCuttingCorrection, validateCuttingReopen } from './cuttingCorrectionContract'
import type { ProductionEnvelope } from './productionRecovery'
import { parseProductionEnvelope } from './productionRecovery'
const group = '11111111-1111-4111-8111-111111111111', po = '22222222-2222-4222-8222-222222222222'
const request = '33333333-3333-4333-8333-333333333333'
const source = { groupId: group, poId: po, number: 'CUT-NATIVE', rowVersion: 4 }
const workspace = () => ({ contract_version: 'cp7.cutting-reopen-workspace.v1', group_id: group, po_id: po, number: 'CUT-NATIVE', row_version: '4', review_token: 'a'.repeat(32), eligible: true, blockers: [], business_DML: false })
const envelope = (): ProductionEnvelope => {
  const canonical = { action: 'REOPEN_POSTED', payload: cuttingReopenPayload(parseCuttingCorrection(workspace(), source), 'Bahan asal sudah diperiksa'), expectedVersion: 4 }
  return { ...canonical, fingerprint: JSON.stringify(canonical), id: request, createdAt: '2026-10-05T00:00:00Z' }
}
const outcome = () => ({ contract_version: 'cp7.cutting-reopen-outcome.v1', kind: 'COMMITTED_OUTCOME', action: 'REOPEN_POSTED', request_id: request,
  group_id: group, po_id: po, number: 'CUT-NATIVE', status: 'DRAFT_FOR_CORRECTION', row_version: '5',
  Native_response: { cutting_group_id: group, status: 'CUT', row_version: 5, reversed_movement_count: 1, reversed_journal_count: 1, presewing_reversible: true } })
describe('exact posted cutting reopen contract', () => {
  it('admits only the exact source and reviewed four-field intent', () => {
    const w = parseCuttingCorrection(workspace(), source)
    expect(cuttingReopenPayload(w, '  Bahan asal sudah diperiksa  ')).toEqual({ group_id: group, po_id: po, review_token: 'a'.repeat(32), change_reason: 'Bahan asal sudah diperiksa' })
    expect(validateCuttingReopen(outcome(), envelope())).toEqual({ ...source, rowVersion: 5 })
  })
  it.each(['group_id','po_id','number','row_version','review_token','business_DML','extra'])('retires a mismatched %s without authorizing an inverse', key => {
    const w = { ...workspace(), [key]: key === 'business_DML' ? true : 'wrong' }
    expect(() => parseCuttingCorrection(w, source)).toThrow()
  })
  it('requires known empty dependencies and exact safe bigint transport', () => {
    expect(() => parseCuttingCorrection({ ...workspace(), blockers: null }, source)).toThrow()
    expect(() => parseCuttingCorrection({ ...workspace(), eligible: false }, source)).toThrow()
    expect(() => parseCuttingCorrection({ ...workspace(), row_version: '9007199254740993' }, { ...source, rowVersion: 9007199254740992 })).toThrow()
  })
  it('shows actual pickup dependencies and forbids inverse payload creation', () => {
    const w = parseCuttingCorrection({ ...workspace(), eligible: false, blockers: [{ kind: 'PICKUP', id: request, label: source.number, status: 'POSTED' }] }, source)
    expect(w.blockers[0].id).toBe(request)
    expect(() => cuttingReopenPayload(w, 'Bahan asal sudah diperiksa')).toThrow()
    expect(() => parseCuttingCorrection({ ...workspace(), eligible: false, blockers: [...w.blockers, ...w.blockers] }, source)).toThrow()
  })
  it.each(['request_id','group_id','po_id','action','status','row_version'])('retains the pending command when the receipt has wrong %s', key => {
    expect(() => validateCuttingReopen({ ...outcome(), [key]: 'wrong' }, envelope())).toThrow()
  })
  it('keeps Native response identity and a separate exact recovery owner', () => {
    expect(() => validateCuttingReopen({ ...outcome(), Native_response: { ...outcome().Native_response, cutting_group_id: po } }, envelope())).toThrow()
    expect(parseProductionEnvelope(JSON.stringify(envelope()), 'CUTTING_CORRECTION')).toEqual(envelope())
    expect(() => parseProductionEnvelope(JSON.stringify(envelope()), 'CUTTING')).toThrow()
  })
})
