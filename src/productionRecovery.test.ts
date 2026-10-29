// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  clearProductionEnvelope, isDefiniteInitialRejection, parseProductionEnvelope,
  persistProductionEnvelope, productionKey, readProductionRecovery, type ProductionEnvelope,
} from './productionRecovery'
import bdRouterSql from '../scripts/cp6_bd_objects_router.sql?raw'
import bcRouterSql from '../scripts/cp6_bc_objects_router.sql?raw'

const scope = 'disposable:actor-1'
const key = productionKey(scope, 'BS')
const payload = { bs_case_id: 'case-1', change_reason: 'Verifikasi fisik' }
const envelope: ProductionEnvelope = {
  action: 'HOLD_BS', payload, expectedVersion: 1, id: '00000000-0000-4000-8000-000000000001',
  createdAt: '2026-09-21T00:00:00Z', fingerprint: JSON.stringify({ action: 'HOLD_BS', payload, expectedVersion: 1 }),
}
beforeEach(() => localStorage.clear())
afterEach(() => { vi.restoreAllMocks(); localStorage.clear() })

describe('recovery storage is durable and isolated', () => {
  it.each(['', '{', 'null', '[]', JSON.stringify({ ...envelope, fingerprint: 'wrong' }), JSON.stringify({ ...envelope, id: 'bad' }), JSON.stringify({ ...envelope, createdAt: 'yesterday' })])('quarantines corrupt storage %s without deleting it', (raw) => {
    localStorage.setItem(key, raw)
    expect(readProductionRecovery(scope).corrupted).toBe(true)
    expect(localStorage.getItem(key)).toBe(raw)
    expect(persistProductionEnvelope(scope, 'BS', envelope)).toBe(false)
    expect(localStorage.getItem(key)).toBe(raw)
  })
  it('distinguishes storage failure from an empty envelope', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('unavailable') })
    expect(readProductionRecovery(scope).corrupted).toBe(true)
  })
  it('never overwrites or clears another pending UUID', () => {
    expect(persistProductionEnvelope(scope, 'BS', envelope)).toBe(true)
    const next = { ...envelope, id: '00000000-0000-4000-8000-000000000002' }
    expect(persistProductionEnvelope(scope, 'BS', next)).toBe(false)
    expect(clearProductionEnvelope(scope, 'BS', next)).toBe(false)
    expect(readProductionRecovery(scope).pending.BS).toEqual(envelope)
  })
  it('retains the exact legacy envelope and isolates actors and projects', () => {
    localStorage.setItem(key, JSON.stringify(envelope))
    expect(parseProductionEnvelope(localStorage.getItem(key)!, 'BS')).toEqual(envelope)
    expect(readProductionRecovery('other:actor-1').pending).toEqual({})
    expect(readProductionRecovery('disposable:actor-2').pending).toEqual({})
    expect(readProductionRecovery(scope).pending.BS).toEqual(envelope)
  })
  it('retains the original envelope when remove fails', () => {
    expect(persistProductionEnvelope(scope, 'BS', envelope)).toBe(true)
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => { throw new Error('unavailable') })
    expect(clearProductionEnvelope(scope, 'BS', envelope)).toBe(false)
    expect(readProductionRecovery(scope).pending.BS).toEqual(envelope)
  })
  it('changes the read generation even after an envelope is resolved', () => {
    const before = readProductionRecovery(scope).signature
    expect(persistProductionEnvelope(scope, 'BS', envelope)).toBe(true)
    expect(clearProductionEnvelope(scope, 'BS', envelope)).toBe(true)
    expect(readProductionRecovery(scope).signature).not.toEqual(before)
    expect(readProductionRecovery(scope).pending).toEqual({})
  })
})
describe('only known statement errors retire an initial request', () => {
  it.each([{ status: 503 }, { status: 408 }, { status: 429 }, { status: 400 }, { status: 403 }, { code: 'PGRST000' }, { code: '08006' }, { code: '57P01' }, { code: '53300' }, { code: 'XX000' }])('keeps uncertainty for %j', (error) => {
    expect(isDefiniteInitialRejection(error)).toBe(false)
  })
  it.each(['23514', 'P0001', '42501', '40001', '40P01', '22P02'])('recognizes initial database rejection %s', (code) => {
    expect(isDefiniteInitialRejection({ code })).toBe(true)
  })
})

// Every action a writer router accepts must be accepted by the client envelope, or the page never sends it (D12 browser run
// 36219655269: "Pakai kredit klaim" did nothing because APPLY_CLAIM_CREDIT was missing here).
describe('client action lists follow the server routers', () => {
  const routerActions = (text: string, prefix: string) => [...text.matchAll(new RegExp(`when '([A-Z_]+)' then erp\\.${prefix}_`, 'g'))].map(m => m[1])
  it.each([['LAUNDRY_BD', bdRouterSql, 'bd'], ['ACCESSORY_SERVICE', bcRouterSql, 'bc']] as const)('%s accepts every router action',
    (domain, sql, prefix) => {
      const list = routerActions(sql, prefix)
      expect(list.length).toBeGreaterThan(5)
      for (const action of list) {
        const raw = JSON.stringify({ action, payload: { x: 1 }, expectedVersion: null, id: '00000000-0000-4000-8000-000000000001',
          createdAt: '2026-09-26T00:00:00Z', fingerprint: JSON.stringify({ action, payload: { x: 1 }, expectedVersion: null }) })
        expect(() => parseProductionEnvelope(raw, domain), action).not.toThrow()
      }
    })
})

// S03 UI-only recovery controls; server/Native execution is not claimed.
describe('attendance period choice joins the shared recovery boundary',()=>{
 const domain='ATTENDANCE_PERIOD_CHOICE' as const
 const choicePayload={period_start:'2026-10-01',period_end:'2026-10-07',choice:'CARRY',output_start:null,output_end:null,reason:'Keputusan periode sudah diperiksa',review_token:'a'.repeat(64)}
 const choiceEnvelope=(action='CHOOSE'):ProductionEnvelope=>({...envelope,action,payload:choicePayload,expectedVersion:null,fingerprint:JSON.stringify({action,payload:choicePayload,expectedVersion:null})})
 it.each(['CHOOSE','CORRECT','REVERSE','ALLOCATE','CANCEL_ALLOCATION'])('accepts only the documented action %s without a fake version',action=>{
  const e=choiceEnvelope(action);expect(parseProductionEnvelope(JSON.stringify(e),domain)).toEqual(e)
 })
 it.each(['CREATE','ACTIVATE','CANCEL','choose',' CHOOSE'])('refuses an unsupported attendance action %s',action=>{
  expect(()=>parseProductionEnvelope(JSON.stringify(choiceEnvelope(action)),domain)).toThrow()
 })
 it('holds exact action/payload/token/UUID across an uncertain response and reparse',()=>{
  const e=choiceEnvelope();expect(persistProductionEnvelope(scope,domain,e)).toBe(true)
  expect(isDefiniteInitialRejection({status:503,code:'P0001'})).toBe(false)
  const pending=readProductionRecovery(scope).pending[domain];expect(pending).toEqual(e);expect(parseProductionEnvelope(JSON.stringify(pending),domain)).toEqual(e)
  const nextPayload={...choicePayload,reason:'Alasan lain'},changed={...e,payload:nextPayload,fingerprint:JSON.stringify({action:e.action,payload:nextPayload,expectedVersion:null})};expect(clearProductionEnvelope(scope,domain,changed)).toBe(false);expect(readProductionRecovery(scope).pending[domain]).toEqual(e);expect(clearProductionEnvelope(scope,domain,e)).toBe(true)
 })
 it('blocks other domains while attendance is pending and attendance while another domain is pending',()=>{
  const e=choiceEnvelope();expect(persistProductionEnvelope(scope,domain,e)).toBe(true);expect(persistProductionEnvelope(scope,'BS',envelope)).toBe(false)
  expect(clearProductionEnvelope(scope,domain,e)).toBe(true);expect(persistProductionEnvelope(scope,'BS',envelope)).toBe(true);expect(persistProductionEnvelope(scope,domain,e)).toBe(false)
 })
 it('quarantines corrupt attendance recovery without deleting its old record or permitting a foreign writer',()=>{
  const k=productionKey(scope,domain);localStorage.setItem(k,'{');expect(readProductionRecovery(scope).corrupted).toBe(true);expect(persistProductionEnvelope(scope,'BS',envelope)).toBe(false);expect(localStorage.getItem(k)).toBe('{')
 })
 it('preserves legacy keys and rejects a new UUID clearing the pending choice',()=>{
  expect(productionKey(scope,'BS')).toBe('erp.cp5.pending-mutation.v1:'+scope);expect(productionKey(scope,'LAUNDRY_QC')).toBe('erp.cp6.pending-mutation.v1:'+scope)
  const e=choiceEnvelope();expect(persistProductionEnvelope(scope,domain,e)).toBe(true);expect(clearProductionEnvelope(scope,domain,{...e,id:'00000000-0000-4000-8000-000000000099'})).toBe(false);expect(readProductionRecovery(scope).pending[domain]).toEqual(e)
 })
})
