// @vitest-environment jsdom
import {beforeEach,it,expect} from 'vitest'
import ready from '../tests/fixtures/initialAnalysisReadyActual.json'
import running from '../tests/fixtures/initialAnalysisRunningActual.json'
import expired from '../tests/fixtures/initialAnalysisActual.json'
import {parseInitialAnalysis,initialStagedRequest,adoptInitialStagedRequest} from './nativeInitialAnalysis'
import {persistStagedRequest,readStagedRequest,stagedRequestKey} from './nativeStagedJob'
const actor=running.actor,scope='analysis:cp6-disposable:owner',parse=(v:unknown)=>parseInitialAnalysis(v,actor)
beforeEach(()=>localStorage.clear())
it('reads the actual SQL READY, RUNNING and EXPIRED replies with the same server request',()=>{
 expect(parse(ready).state).toBe('READY');expect(parse(ready).job).toBeNull()
 const r=parse(running);expect(r.job?.requestId).toBe(running.job.request_id);expect(r.eligibleTargets).toBe(1)
 expect(initialStagedRequest(r)).toEqual({id:running.job.request_id,q:running.job_query,finance:'DEFERRED'})
 expect(parse(expired).state).toBe('EXPIRED');expect(()=>initialStagedRequest(parse(expired))).toThrow()
})
it('binds actor, contract, automation scope and closed top-level fields',()=>{
 for(const patch of[{actor:'99999999-1111-4111-8111-111111111111'},{contract_version:'other'},{automatic_scope:'REPEAT_FOREVER'},
  {production_go:true},{apply_enabled:true},{unknown:0}])expect(()=>parse({...running,...patch})).toThrow()
 const missing=structuredClone(running)as Record<string,unknown>;delete missing.actor;expect(()=>parse(missing)).toThrow()
})
it('rejects inconsistent readiness counts, unknown reasons and duplicate product candidates',()=>{
 for(const patch of[{ready:false},{active_products:0},{eligible_targets:2},{products_total:'1'},{products_total:1.2},
  {reasons:['UNREVIEWED_NEW_POLICY']},{candidate_limit:200},{candidates:[]},
  {active_products:2,products_total:2,candidates:[running.readiness.candidates[0],running.readiness.candidates[0]]}]){
  expect(()=>parse({...running,readiness:{...running.readiness,...patch}})).toThrow()
 }
})
it('rejects invalid dates, mixed grouping and unknown query fields',()=>{
 for(const patch of[{from_date:'2026-02-31'},{through_date:'2026-09-01'},{group_mode:'RESTATED'},{hidden:true}]){
  expect(()=>parse({...running,query:{...running.query,...patch}})).toThrow()
 }
 expect(()=>parse({...running,checked_at:'not-a-time'})).toThrow()
})
it('requires a real job only with its bound query/hash, matching state and retention',()=>{
 for(const patch of[{job:null},{job_query:null},{job_semantic_hash:null},{source_changed:true},{state:'READY'},
  {state:'DONE'},{state:'EXPIRED'},{semantic_hash:'broken'}])expect(()=>parse({...running,...patch})).toThrow()
 expect(()=>parse({...running,job_query:{...running.job_query,from_date:'2026-09-24'}})).toThrow()
 expect(()=>parse({...ready,job_query:running.query})).toThrow()
})
it('refuses a finance sidecar on the operational-only initial job',()=>{
 expect(()=>parse({...running,job:{...running.job,finance_capture:{state:'READY'}}})).toThrow()
})
it('adopts the same server UUID idempotently without replacing another pending request',()=>{
 const r=parse(running),first=adoptInitialStagedRequest(scope,r),raw=localStorage.getItem(stagedRequestKey(scope))
 expect(adoptInitialStagedRequest(scope,r)).toEqual(first);expect(localStorage.getItem(stagedRequestKey(scope))).toBe(raw)
 expect(readStagedRequest(scope).pending).toEqual(first)
 localStorage.clear();const other={...first,id:'99999999-1111-4111-8111-111111111111'};persistStagedRequest(scope,other)
 expect(()=>adoptInitialStagedRequest(scope,r)).toThrow('tersimpan');expect(readStagedRequest(scope).pending).toEqual(other)
})
it('holds corrupt storage and a same-UUID changed query or financial intent',()=>{
 const r=parse(running),req=initialStagedRequest(r),key=stagedRequestKey(scope)
 localStorage.setItem(key,'broken');expect(()=>adoptInitialStagedRequest(scope,r)).toThrow();expect(localStorage.getItem(key)).toBe('broken')
 localStorage.clear();persistStagedRequest(scope,{...req,q:{...req.q,from_date:'2026-09-24'}});expect(()=>adoptInitialStagedRequest(scope,r)).toThrow()
 localStorage.clear();persistStagedRequest(scope,{...req,finance:'STAGED'});expect(()=>adoptInitialStagedRequest(scope,r)).toThrow()
})
