// @vitest-environment jsdom
import {it,expect,beforeEach} from 'vitest'
import * as f from '../tests/fixtures/nativeStagedReminders'
import {parseConditionSet,parseConditionsPage,parseWorkspace,parseCommand,parseRecheck,verdictText,driveConditionSet,readReminderRequest,persistReminderRequest,
 clearReminderRequest,type ConditionsQuery,type ReminderRequest} from './nativeStagedReminders'

beforeEach(()=>localStorage.clear())
const q:ConditionsQuery={run_id:f.run,rule_id:null,state:'ACTIVE',offset:0,limit:25}

it('binds the condition set to the run on screen and its unit plan (pages, then the seal)',()=>{
 expect(parseConditionSet(f.setStatus('RUNNING',1),f.run,f.identityHash)).toMatchObject({state:'RUNNING',stage:'PAGE',pagesDone:1,pageCount:2})
 expect(parseConditionSet(f.setStatus('RUNNING',2),f.run,f.identityHash).stage).toBe('SEAL')
 expect(parseConditionSet(f.setStatus('DONE',3),f.run,f.identityHash).totals).toEqual({conditions:3,byRule:{PRODUCTION_GAP:{ACTIVE:3}}})
 for(const bad of[f.setStatus('DONE',3,{identity_hash:'d'.repeat(64)}),f.setStatus('RUNNING',1,{stage:'SEAL'}),f.setStatus('DONE',2),f.setStatus('DONE',3,{totals:{conditions:4,by_rule:{PRODUCTION_GAP:{ACTIVE:3}}}}),
  f.setStatus('RUNNING',1,{set_hash:'f'.repeat(64)}),f.setStatus('DONE',3,{sent:true}),f.setStatus('FAILED',1,{failure:null})])
  expect(()=>parseConditionSet(bad,f.run,f.identityHash)).toThrow()
})
it('reads snapshot conditions with their time; a filter, query or "current" label that does not match is refused',()=>{
 const p=parseConditionsPage(f.page(q),q,f.actor,f.identityHash)
 expect([p.total,p.rows.map(r=>r.value.value),p.rows[0].dataAsOf,p.rows[0].binding.basis]).toEqual([3,['4','5','6'],f.dataAsOf,'GLOBAL'])
 for(const bad of[f.page({...q,offset:25}),f.page(q,[f.condition(1,{state:'RESOLVED'})]),f.page(q,[f.condition(1,{label:'Data terkini'})]),f.page(q,[f.condition(1,{kind:'LIVE'})]),
  f.page(q,[f.condition(1,{data_as_of:'2026-10-08T03:00:00.000000+00:00'})]),f.page(q,[f.condition(1),f.condition(1)]),f.page(q,undefined,{identity_hash:'d'.repeat(64)}),
  f.page(q,undefined,{sent:true}),f.page(q,undefined,{recheck_required_before_preview:false})])
  expect(()=>parseConditionsPage(bad,q,f.actor,f.identityHash)).toThrow()
})
it('words the recheck: resolved since the analysis is not billed; never "terkini"',()=>{
 const resolved=parseRecheck(f.liveRecheck('RESOLVED_NOW'),f.run,f.actor,'PRODUCTION_GAP:'+f.keys[0])
 expect(verdictText(resolved)).toBe('Sudah selesai sejak analisis — tidak ditagih: kurang 4 PCS saat analisis; stok jadi dan barang dalam proses naik 4 PCS.')
 const open=parseRecheck(f.liveRecheck('STILL_OPEN'),f.run,f.actor,'PRODUCTION_GAP:'+f.keys[0])
 expect(verdictText(open)).toBe('Masih perlu: kurang sedikitnya 4 PCS sekarang (analisis: 4 PCS).')
 for(const v of['BELOW_THRESHOLD_NOW','UNKNOWN_NOW','CHANGED_REVIEW_REQUIRED','NO_LONGER_DUE','NOT_FOUND_NOW','CONDITION_CHANGED'])
  expect(verdictText(parseRecheck(f.liveRecheck(v),f.run,f.actor,'PRODUCTION_GAP:'+f.keys[0]))).not.toMatch(/terkini/i)
 expect(()=>parseRecheck({...f.liveRecheck('STILL_OPEN'),recorded:true},f.run,f.actor,'PRODUCTION_GAP:'+f.keys[0])).toThrow()
 expect(()=>parseRecheck(f.liveRecheck('STILL_OPEN',2),f.run,f.actor,'PRODUCTION_GAP:'+f.keys[0])).toThrow()
})
it('binds a command reply to its request and keeps the pending request until the answer is known',()=>{
 const r:ReminderRequest={id:'12345678-1234-4234-8234-123456789012',operation:'CLAIM',runId:f.run,payload:{run_id:f.run,identity_hash:f.identityHash,condition_key:'PRODUCTION_GAP:'+f.keys[0],condition_hash:'1'.repeat(64),binding_id:f.bindingId}}
 const sent=parseCommand(f.command('CLAIM',r.id,{status:'COMMITTED',outcome:'NOT_SENT',verdict:'RESOLVED_NOW',recheck_id:'dddddddd-dddd-4ddd-8ddd-dddddddddddd',claim_id:null,fence:null},null,f.recheck('RESOLVED_NOW')),r,f.actor)
 expect([sent.outcome,sent.verdict,sent.claim,sent.recheck?.verdict]).toEqual(['NOT_SENT','RESOLVED_NOW',null,'RESOLVED_NOW'])
 const claimed=parseCommand(f.command('CLAIM',r.id,{status:'COMMITTED',outcome:'CLAIMED',verdict:'STILL_OPEN',recheck_id:'dddddddd-dddd-4ddd-8ddd-dddddddddddd',claim_id:f.claimId,fence:f.fence},f.claim(),f.recheck('STILL_OPEN')),r,f.actor)
 expect([claimed.claim?.status,claimed.claim?.body.startsWith('PRATINJAU LOKAL — BELUM DIKIRIM\n')]).toEqual(['CLAIMED',true])
 for(const bad of[f.command('CLAIM','00000000-0000-4000-8000-000000000000',{status:'COMMITTED'}),f.command('OUTCOME',r.id,{status:'COMMITTED'}),
  {...f.command('CLAIM',r.id,{status:'COMMITTED',outcome:'CLAIMED',claim_id:f.claimId},f.claim()),sent:true},
  f.command('CLAIM',r.id,{status:'COMMITTED',outcome:'CLAIMED',claim_id:f.claimId},f.claim({body:'Data terkini'}))])
  expect(()=>parseCommand(bad,r,f.actor)).toThrow()
 persistReminderRequest('s',r);expect(readReminderRequest('s').pending).toEqual(r)
 expect(()=>persistReminderRequest('s',{...r,id:'12345678-1234-4234-8234-123456789013'})).toThrow()
 clearReminderRequest('s',r);expect(readReminderRequest('s')).toEqual({pending:null,error:null})
 localStorage.setItem('erp.cp7.reminder-v2-request.v1:s','{bad');expect(readReminderRequest('s').error).toBeTruthy()
})
it('steps the set until it is final and waits when another session runs the page',async()=>{
 const replies=[f.setStatus('RUNNING',1),f.setStatus('RUNNING',1,{worker_active:true}),f.setStatus('RUNNING',2),f.setStatus('DONE',3)],waits:number[]=[],seen:string[]=[]
 const last=await driveConditionSet({step:()=>Promise.resolve({data:replies.shift(),error:null}),runId:f.run,identityHash:f.identityHash,sleep:async ms=>{waits.push(ms)},onStatus:s=>seen.push(s.state+':'+s.unitsDone)})
 expect([last?.state,waits,seen]).toEqual(['DONE',[2000],['RUNNING:1','RUNNING:1','RUNNING:2','DONE:3']])
 await expect(driveConditionSet({step:()=>Promise.resolve({data:null,error:{message:'CP7_REMINDER_V2_SNAPSHOT_UNAVAILABLE'}}),runId:f.run,identityHash:f.identityHash})).rejects.toBeTruthy()
})
it('shows claims and settings only to a manager',()=>{
 expect(parseWorkspace(f.workspace(true),f.run,f.identityHash,f.actor).binding?.id).toBe(f.bindingId)
 expect(parseWorkspace(f.workspace(false),f.run,f.identityHash,f.actor).manageAllowed).toBe(false)
 expect(()=>parseWorkspace(f.workspace(false,{binding:f.binding()}),f.run,f.identityHash,f.actor)).toThrow()
 expect(()=>parseWorkspace(f.workspace(true,{external_delivery_enabled:true}),f.run,f.identityHash,f.actor)).toThrow()
})
