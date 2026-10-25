import {expect,it,vi} from 'vitest'
import type {ProductionEnvelope} from './productionRecovery'
import {CUTTING_SAVE_CONTRACT,cuttingSuggestionPayload,isCuttingSuggestionSave,sendCuttingSuggestion,validateCuttingSuggestion} from './nativeCuttingSuggestion'
import * as f from '../tests/fixtures/nativePlan'

// Synthetic client wire, not Native feasibility or a real production order.
const envelope=():ProductionEnvelope=>({action:'SAVE_DRAFT',id:f.order,createdAt:'2026-10-23T00:00:00Z',fingerprint:'fixture',expectedVersion:null,
 payload:cuttingSuggestionPayload({run_id:f.run,target_key:f.stagedContext.targetKey,identity_hash:f.identityHash})})
function wire(){return{...f.stagedSaveOutcome(f.order),cutting_save_guard:{contract_version:CUTTING_SAVE_CONTRACT,run_id:f.run,
 target_key:f.stagedContext.targetKey,identity_hash:f.identityHash,checked_at:'2026-10-23T00:00:00Z',feasible:true}}}
it('preserves the exact staged payload and binds its guarded route inside recovery',async()=>{
 const e=envelope(),rpc=vi.fn(async()=>({data:wire(),error:null}))
 expect(isCuttingSuggestionSave(e)).toBe(true);await sendCuttingSuggestion({rpc},e)
 expect(rpc).toHaveBeenCalledWith('erp_cp7_save_cutting_suggestion_v1',{p_payload:e.payload,p_request:e.id})
 expect(validateCuttingSuggestion(wire(),e,f.actor).id).toBe(f.draft)
})
it('leaves ordinary staged save and apply recovery on their existing routes',()=>{
 const e=envelope();expect(isCuttingSuggestionSave({...e,payload:{}})).toBe(false)
 expect(isCuttingSuggestionSave({...e,action:'APPLY'})).toBe(false)
})
it('passes the original database rejection unchanged to the recovery classifier',async()=>{
 const error={code:'40001',message:'CP7_CUTTING_SUGGESTION_SOURCE_CHANGED',details:'source changed',hint:null}
 const rpc=vi.fn(async()=>({data:null,error}))
 expect((await sendCuttingSuggestion({rpc},envelope())).error).toBe(error)
})
it('rejects invalid recovery mode before any RPC call',async()=>{
 const e=envelope(),rpc=vi.fn();e.payload={...e.payload as object,cutting_save_contract:'OTHER'}
 await expect(sendCuttingSuggestion({rpc},e)).rejects.toThrow();expect(rpc).not.toHaveBeenCalled()
})
it.each(['missing','run','target','identity','feasible','time','older','extra'] as const)('refuses an unproved checked-save receipt: %s',kind=>{
 const w=wire()as unknown as Record<string,unknown>,g=w.cutting_save_guard as Record<string,unknown>
 if(kind==='missing')delete w.cutting_save_guard
 else if(kind==='run')g.run_id=f.pattern
 else if(kind==='target')g.target_key=f.pattern+':'+f.size
 else if(kind==='identity')g.identity_hash='f'.repeat(64)
 else if(kind==='feasible')g.feasible=false
 else if(kind==='time')g.checked_at='2026-10-23'
 else if(kind==='older')g.checked_at='2000-01-01T00:00:00Z'
 else g.unproved=true
 expect(()=>validateCuttingSuggestion(w,envelope(),f.actor)).toThrow()
})
it.each([
 ['2026-10-23T00:00:00.123456Z','2026-10-23T00:00:00.123455Z'],
 ['2026-10-23T07:00:00.000001+07:00','2026-10-23T00:00:00Z'],
 ['2026-10-22T17:00:00.999999-07:00','2026-10-23T00:00:00.999998+00:00'],
])('rejects a check one microsecond before its source (%s)',(source,checked)=>{
 const w=wire();w.data_as_of=source;w.cutting_save_guard.checked_at=checked
 expect(()=>validateCuttingSuggestion(w,envelope(),f.actor)).toThrow()
})
it.each([
 ['2026-10-23T00:00:00.123456Z','2026-10-23T00:00:00.123456+00:00'],
 ['2026-10-23T00:00:00.123456Z','2026-10-23T07:00:00.123457+07:00'],
 ['2026-10-23T00:00:00.1Z','2026-10-22T17:00:00.100000-07:00'],
 ['2026-10-23T23:59:59.999999Z','2026-10-24T00:00:00Z'],
])('accepts equal or later exact instants without rewriting the receipt (%s)',(source,checked)=>{
 const w=wire();w.data_as_of=source;w.cutting_save_guard.checked_at=checked;const original=structuredClone(w)
 expect(validateCuttingSuggestion(w,envelope(),f.actor).id).toBe(f.draft)
 expect(w).toEqual(original)
})
it.each(['2026-02-30T00:00:00Z','2026-10-23T24:00:00Z','2026-10-23T00:00:00.1234567Z','2026-10-23T00:00:00'])('refuses an invalid or overprecision instant on either side: %s',time=>{
 const w=wire();w.data_as_of='2026-01-01T00:00:00Z';w.cutting_save_guard.checked_at=time
 expect(()=>validateCuttingSuggestion(w,envelope(),f.actor)).toThrow()
 w.data_as_of=time;w.cutting_save_guard.checked_at='2027-01-01T00:00:00Z'
 expect(()=>validateCuttingSuggestion(w,envelope(),f.actor)).toThrow()
})
