// @vitest-environment jsdom
import {afterEach,it,expect,vi} from 'vitest'
import {reportCrypto,reportBodyDigest} from '../tests/fixtures/reportCrypto.mjs'
import {ruleSourceFixture,payrollRuleSourceFixture,localWorkspaceFixture,ruleFixtureActor,ruleFixtureId,ruleFixtureClock} from '../tests/fixtures/nativeRuleSource'
import {parseRuleSource,parseRuleObservations,parseLocalWorkspace,localPreviewBody,persistRuleRequest,readRuleRequest,clearRuleRequest,ruleRequestKey,type RuleRequest} from './nativeRuleSource'
import original from '../tests/fixtures/nativeAnalysisStandin.json'
import type {NativeDemandQuery} from './nativeDemandHistory'
const q=original.query as NativeDemandQuery,finance={ownerReports:false,preflight:false},rights={ar:true,ap:true}
afterEach(()=>{localStorage.clear();vi.unstubAllGlobals()})
it('archives a proven inactive source without calling it paid and rejects false closure or old-contract archives',()=>{
 const source=ruleSourceFixture(),c=source.rows[2]
 c.economic_state='INACTIVE';c.state='NO_CURRENT_GAP';c.reason='INACTIVE_DOCUMENT';c.eligibility='NO_CURRENT_ALERT'
 const request:RuleRequest={id:ruleFixtureId(84),query:q,operation:'EPISODES',payload:{run_id:original.run_id,source_hash:source.source_hash}}
 const wire={contract_version:'cp7.native-rule-observations.v2',actor_scope_id:ruleFixtureActor,source,
  result:{request_id:request.id,status:'COMMITTED',source_hash:source.source_hash,rows:source.rows.map(condition=>({condition,
   episode:condition===c?{id:ruleFixtureId(85),number:'1',previous_id:null,state:'ARCHIVED',freshness:'KNOWN',first_observed_at:ruleFixtureClock,last_observed_at:ruleFixtureClock,resolved_at:null,archived_at:ruleFixtureClock}:null,
   transition:condition===c?'ARCHIVED_INACTIVE_DOCUMENT':'OBSERVED_NO_ACTIVE_EPISODE'}))},
  result_freshness:'CURRENT_SOURCE',external_delivery_enabled:false,business_DML:false}
 const parsed=parseRuleObservations(wire,request,ruleFixtureActor,finance,rights)
 expect(parsed.rows[2].episode).toMatchObject({state:'ARCHIVED',resolved_at:null,archived_at:ruleFixtureClock})
 expect(parsed.rows[2].condition.business_resolved).toBe(false)
 for(const mutate of [
  (v:typeof wire)=>{v.contract_version='cp7.native-rule-observations.v1'},
  (v:typeof wire)=>{v.result.rows[2].episode!.freshness='UNKNOWN'},
  (v:typeof wire)=>{v.result.rows[2].condition.economic_state='UNKNOWN'},
  (v:typeof wire)=>{v.result.rows[2].condition.reason='SOURCE_MISSING'},
  (v:typeof wire)=>{v.result.rows[2].transition='RESOLVED'},
  (v:typeof wire)=>{v.result.rows[2].episode!.archived_at='2026-09-01T00:00:00Z'},
 ]){const invalid=structuredClone(wire);mutate(invalid);expect(()=>parseRuleObservations(invalid,request,ruleFixtureActor,finance,rights)).toThrow()}
})
it('preserves exact Native decimal text and an open debt whose due date is unknown',()=>{
 const wire=payrollRuleSourceFixture(),r=parseRuleSource(wire,q,ruleFixtureActor,finance,{...rights,payroll:true}).rows.at(-1)!
 expect(r.financial_source?.remaining).toMatchObject({state:'KNOWN',value:'9007199254740993.01',unit:'IDR'})
 expect(r.economic_state).toBe('OPEN');expect(r.value.state).toBe('UNKNOWN');expect(r.business_resolved).toBe(false)
 const invalid=structuredClone(wire);invalid.rows.at(-1)!.business_resolved=true
 expect(()=>parseRuleSource(invalid,q,ruleFixtureActor,finance,{...rights,payroll:true})).toThrow()
 expect(()=>parseRuleSource(wire,q,ruleFixtureActor,finance,rights)).toThrow()
})
it('refuses lossy numeric money, fabricated Native revision and allocation described as settlement',()=>{
 for(const change of [
  (r:Record<string,unknown>)=>{const f=r.financial_source as Record<string,unknown>;f.document={remaining_amount:9007199254740993}},
  (r:Record<string,unknown>)=>{const f=r.financial_source as Record<string,unknown>;f.revision_basis='NATIVE_ROW_VERSION'},
  (r:Record<string,unknown>)=>{r.economic_state='SETTLED'},
  (r:Record<string,unknown>)=>{r.state='ACTIVE';r.eligibility='LOCAL_PREVIEW_ELIGIBLE'},
  (r:Record<string,unknown>)=>{const f=r.financial_source as Record<string,unknown>;f.remaining={...(f.remaining as object),value:'400.00'}},
  (r:Record<string,unknown>)=>{const f=r.financial_source as Record<string,unknown>;f.recorded_due_date='2026-09-26'},
  (r:Record<string,unknown>)=>{const f=r.financial_source as Record<string,unknown>;const m=f.remaining as Record<string,unknown>;f.remaining={state:'UNKNOWN',unit:'IDR',reason:'NOT_AVAILABLE',refs:m.refs};r.economic_state='UNKNOWN'},
 ]){const wire=payrollRuleSourceFixture();change(wire.rows.at(-1)! as unknown as Record<string,unknown>);expect(()=>parseRuleSource(wire,q,ruleFixtureActor,finance,{...rights,payroll:true})).toThrow()}
})
it('preserves assumed zero as scenario-only and unknown accessory supply as unresolved',()=>{const s=parseRuleSource(ruleSourceFixture(),q,ruleFixtureActor,finance,rights);expect(s.rows[0].state).toBe('NO_CURRENT_GAP');expect(s.rows[0].business_resolved).toBe(false);expect(s.rows[1].state).toBe('DATA_REVIEW');expect(s.rows[1].value.state).toBe('UNKNOWN');expect(s.rows[1].business_resolved).toBe(false);expect(s.analysis.analysis).toEqual(original.analysis);const altered=ruleSourceFixture();altered.rows[0].business_resolved=true;expect(()=>parseRuleSource(altered,q,ruleFixtureActor,finance,rights)).toThrow()})
it('refuses hidden domains, forged Original values, duplicate conditions, partial coverage and changed threshold units',()=>{const base=ruleSourceFixture();const changes:[string,(v:typeof base)=>void][]=[['actor',v=>{v.actor_scope_id=ruleFixtureId(989)}],['duplicate',v=>{v.rows.push(v.rows[0]);v.total='4'}],['partial',v=>{v.page_complete=false}],['coverage',v=>{v.coverage.opening_ar='COMPLETE_NATIVE_DOCUMENT_SCOPE'}],['unit',v=>{v.rows[2].policy_binding.policy!.config.threshold_unit='PCS'}]];for(const[label,alter]of changes){const v=structuredClone(base);alter(v);expect(()=>parseRuleSource(v,q,ruleFixtureActor,finance,rights),label).toThrow()}expect(()=>parseRuleSource(base,q,ruleFixtureActor,finance,{ar:false,ap:true}),'current AR rights').toThrow()})
it('recovers a historical exact episode receipt with its old policy version without making it current',()=>{const source=ruleSourceFixture(),r:RuleRequest={id:ruleFixtureId(74),query:q,operation:'EPISODES',payload:{run_id:original.run_id,source_hash:source.source_hash}},old=structuredClone(source.rows[2]),row=source.policy_rows[0];row.policy_id=ruleFixtureId(75);row.revision='2';row.previous_id=old.policy_binding.policy!.policy_id;row.config.enabled=false;source.source_hash='5'.repeat(64);source.rows[2].policy_binding.policy=row;source.rows[2].policy_timing.status='DISABLED';source.rows[2].policy_timing.ready=false;source.rows[2].eligibility='DISABLED';const wire={contract_version:'cp7.native-rule-observations.v1',actor_scope_id:ruleFixtureActor,source,result:{request_id:r.id,status:'COMMITTED',source_hash:r.payload.source_hash,rows:[{condition:old,episode:{id:ruleFixtureId(76),number:'1',previous_id:null,state:'ACTIVE',freshness:'KNOWN',first_observed_at:ruleFixtureClock,last_observed_at:ruleFixtureClock,resolved_at:null},transition:'OPENED'}]},result_freshness:'HISTORICAL_SOURCE_CHANGED',external_delivery_enabled:false,business_DML:false};const e=parseRuleObservations(wire,r,ruleFixtureActor,finance,rights);expect(e.freshness).toBe('HISTORICAL_SOURCE_CHANGED');expect(e.rows[0].episode?.state).toBe('ACTIVE');expect(e.source.rows[2].eligibility).toBe('DISABLED')})
it('checks local UTF-8 body against current condition, its byte hash and source; UNKNOWN stays separate from manual confirmation',async()=>{vi.stubGlobal('crypto',reportCrypto);const source=parseRuleSource(ruleSourceFixture(),q,ruleFixtureActor,finance,rights),row=source.rows[2],body=localPreviewBody(row),claim={id:ruleFixtureId(77),run_id:original.run_id,status:'UNKNOWN',occurrence_key:'6'.repeat(64),binding_id:ruleFixtureId(73),environment:'LOCAL_TEST_SINK',condition_key:row.key,rule_id:row.rule_id,episode_id:ruleFixtureId(78),policy_id:row.policy_binding.policy!.policy_id,source_hash:source.hash,body_sha256:reportBodyDigest(body),body,fence:ruleFixtureId(79),created_at:ruleFixtureClock,finished_at:ruleFixtureClock,reason:'LOCAL_OUTCOME_UNCERTAIN_NO_AUTOMATIC_RESEND',resolution:{id:ruleFixtureId(80),outcome:'NOT_CAPTURED_CONFIRMED',reason:'Operator memeriksa hasil lokal',created_at:ruleFixtureClock}};expect((await parseLocalWorkspace(localWorkspaceFixture(null,[claim]),q,ruleFixtureActor,finance,rights)).claims[0].status).toBe('UNKNOWN');await expect(parseLocalWorkspace(localWorkspaceFixture(null,[{...claim,body_sha256:'0'.repeat(64)}]),q,ruleFixtureActor,finance,rights)).rejects.toThrow();const changed=body+' salah';await expect(parseLocalWorkspace(localWorkspaceFixture(null,[{...claim,body:changed,body_sha256:reportBodyDigest(changed)}]),q,ruleFixtureActor,finance,rights)).rejects.toThrow();await expect(parseLocalWorkspace(localWorkspaceFixture(null,[{...claim,source_hash:'7'.repeat(64)}]),q,ruleFixtureActor,finance,rights)).rejects.toThrow()})
it('stores only exact actor-scoped command intent and preserves corrupt or conflicting recovery',()=>{const r:RuleRequest={id:ruleFixtureId(81),query:q,operation:'EPISODES',payload:{run_id:original.run_id,source_hash:'4'.repeat(64)}};persistRuleRequest('s',r);expect(readRuleRequest('s').pending).toEqual(r);expect(localStorage.getItem(ruleRequestKey('s'))).not.toContain('policy_rows');expect(()=>persistRuleRequest('s',{...r,id:ruleFixtureId(82)})).toThrow();expect(()=>clearRuleRequest('s',ruleFixtureId(83))).toThrow();clearRuleRequest('s',r.id);localStorage.setItem(ruleRequestKey('s'),'{broken');expect(readRuleRequest('s').error).toBeTruthy();expect(()=>persistRuleRequest('s',r)).toThrow();expect(localStorage.getItem(ruleRequestKey('s'))).toBe('{broken')})
