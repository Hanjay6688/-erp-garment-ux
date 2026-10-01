// @vitest-environment jsdom
import{beforeEach,it,expect}from'vitest'
import{attentionFixture}from'../tests/fixtures/nativeAttention'
import fixture from'../tests/fixtures/nativeAnalysisStandin.json'
import{parseNativeAttention,persistAttentionRequest,readAttentionRequest,clearAttentionRequest,attentionRequestKey,type AttentionRequest}from'./nativeAnalysisAttention'
import type{NativeDemandQuery}from'./nativeDemandHistory'
const q=fixture.query as NativeDemandQuery,actor=fixture.analysis.scope.actor_scope_id,access={ownerReports:false,preflight:false},scope='test-actor'
const request=():AttentionRequest=>({id:'00000000-0000-4000-8000-000000000001',query:q,semanticHash:fixture.analysis.semantic_hash,payload:{run_id:fixture.run_id,action_key:fixture.analysis.actions[0].key,action:'ACK',expected_revision:'0',details:{}}})
beforeEach(()=>localStorage.clear())
it('keeps review state separate from the immutable original and refuses invented closure or missing action rows',()=>{
 const v=attentionFixture();expect(parseNativeAttention(v,q,actor,access).analysis.analysis).toEqual(fixture.analysis)
 v.rows[0].attention={state:'DONE',resume_at:null,resume_due:false,revision:'9007199254740993',updated_at:v.read_at};expect(parseNativeAttention(v,q,actor,access).rows[0].attention.revision).toBe('9007199254740993')
 expect(()=>parseNativeAttention({...v,rows:v.rows.map(r=>({...r,business_resolved:true}))},q,actor,access)).toThrow();expect(()=>parseNativeAttention({...v,rows:[]},q,actor,access)).toThrow()
})
it('rejects malformed attention states, impossible time, unsafe revisions and unknown delivery',()=>{
 for(const change of[{state:'BOGUS'},{resume_at:vTime()},{revision:'9223372036854775808'},{resume_due:true},{revision:'1',updated_at:null},{state:'SNOOZED',resume_at:'2026-02-30T08:00:00+07:00'}]){const v=attentionFixture();Object.assign(v.rows[0].attention,change);expect(()=>parseNativeAttention(v,q,actor,access)).toThrow()}
 const v=attentionFixture();expect(()=>parseNativeAttention({...v,delivery:{status:'SENT',sent:true}},q,actor,access)).toThrow()
})
function vTime(){return'2026-10-02T08:00:00+07:00'}
it('requires bound committed receipt or a sealed absent receipt, with exact revision typing',()=>{
 const v=attentionFixture(),r=request(),receipt={request_id:r.id,run_id:r.payload.run_id,action_key:r.payload.action_key,revision:'1',status:'COMMITTED'}
 expect(parseNativeAttention({...v,request_result:receipt},q,actor,access).result?.status).toBe('COMMITTED')
 expect(()=>parseNativeAttention({...v,request_result:{...receipt,status:'UNKNOWN'}},q,actor,access)).toThrow();expect(()=>parseNativeAttention({...v,request_result:{...receipt,revision:'0'}},q,actor,access)).toThrow()
 expect(parseNativeAttention({...v,request_result:{...receipt,status:'NOT_COMMITTED',revision:null}},q,actor,access).result?.status).toBe('NOT_COMMITTED')
 expect(()=>parseNativeAttention({...v,request_result:{...receipt,status:'NOT_COMMITTED'}},q,actor,access)).toThrow()
})
it('stores the exact own-user intent before send; changed retry and corrupt storage stay fenced',()=>{
 const r=request();persistAttentionRequest(scope,r);expect(readAttentionRequest(scope).pending).toEqual(r);expect(localStorage.getItem(attentionRequestKey(scope))).not.toContain('recommendations')
 expect(()=>persistAttentionRequest(scope,{...r,payload:{...r.payload,action:'DONE'}})).toThrow();expect(()=>clearAttentionRequest(scope,'00000000-0000-4000-8000-000000000009')).toThrow()
 clearAttentionRequest(scope,r.id);expect(readAttentionRequest(scope).pending).toBeNull();localStorage.setItem(attentionRequestKey(scope),'broken');expect(readAttentionRequest(scope).error).toBeTruthy();expect(()=>persistAttentionRequest(scope,r)).toThrow();expect(localStorage.getItem(attentionRequestKey(scope))).toBe('broken')
})
