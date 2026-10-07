// @vitest-environment jsdom
import {expect,it} from 'vitest'
import {parseStagedJob,driveStagedJob,readStagedRequest,persistStagedRequest,clearStagedRequest,stagedRequestKey,stagedProgressText,stagedPausedText,stagedFailureText,stagedCapRefusal,STAGED_WORKER_BACKOFF_MS,type StagedJob,type StagedReply} from './nativeStagedJob'
import {stagedJobFixture,type StagedJobState} from '../tests/fixtures/nativeAnalysisPages'
import fixture from '../tests/fixtures/nativeAnalysisStandin.json'
const id='00000000-0000-4000-8000-000000000095',other='33333333-3333-4333-8333-333333333333'
type J=Record<string,any>
const q={from_date:'2026-09-01',through_date:'2026-09-30',group_mode:'AS_SOLD' as const}
const ok=(data:unknown):StagedReply=>({data,error:null})
const running=(units_done:number,extra:J={})=>ok(stagedJobFixture(id,'RUNNING',{units_done,...extra}))

it('reads every job state strictly: run_id only with DONE, failure only with FAILED, worker_active only when stated',()=>{
 const r=parseStagedJob(stagedJobFixture(id,'RUNNING'),id)
 expect(r).toMatchObject({requestId:id,state:'RUNNING',stage:'HIST_ROWS',stageIndex:3,stageCount:9,unitsDone:12,unitCount:55,planFinal:false,targetsTotal:5000,targetsDoneInStage:1200,unitAttempts:0,runId:null,failure:null,workerActive:false})
 expect(r.reference).toEqual({capturedAt:'2026-10-07T09:00:00.000000Z',sourceHash:fixture.analysis.snapshot.source_hash});expect(r.lastProgressAt).toBe('2026-10-07T09:05:30.000000Z')
 expect(parseStagedJob(stagedJobFixture(id,'RUNNING',{worker_active:true}),id).workerActive).toBe(true)
 const {run_id:_run,failure:_failure,...absent}=stagedJobFixture(id,'RUNNING');expect(parseStagedJob(absent,id)).toMatchObject({runId:null,failure:null})
 expect(parseStagedJob(stagedJobFixture(id,'RUNNING',{targets_total:null,targets_done_in_stage:0}),id).targetsTotal).toBeNull()
 expect(parseStagedJob(stagedJobFixture(id,'RUNNING',{reference:{captured_at:'2026-10-07T09:00:00+00:00',source_hash:'f'.repeat(64)},last_progress_at:'2026-10-07T16:05:30+07:00'}),id).reference.sourceHash).toBe('f'.repeat(64))
 expect(parseStagedJob(stagedJobFixture(id,'DONE'),id)).toMatchObject({state:'DONE',runId:fixture.run_id,stage:null,unitsDone:55,planFinal:true})
 const f=parseStagedJob(stagedJobFixture(id,'FAILED'),id);expect(f.failure).toEqual({unit:12,sqlstate:'42501',code:'CP7_ANALYSIS_ACCESS_CHANGED'});expect(f.runId).toBeNull()
 expect(parseStagedJob(stagedJobFixture(id,'FAILED',{failure:{unit:12,sqlstate:'57014',code:'CP7_ANALYSIS_STAGE_STOPPED',message:'canceling statement due to statement timeout'}}),id).failure?.code).toBe('CP7_ANALYSIS_STAGE_STOPPED')
 expect(()=>parseStagedJob(stagedJobFixture(id,'RUNNING'),other)).toThrow()
 const bad:[StagedJobState,J][]=[
  ['RUNNING',{state:'WAITING'}],['RUNNING',{state:'running'}],['RUNNING',{run_id:fixture.run_id}],['RUNNING',{failure:{unit:1,sqlstate:'P0001',code:'CP7_ANALYSIS_JOB_ERROR'}}],['RUNNING',{stage:null}],['RUNNING',{stage:'hist rows'}],
  ['RUNNING',{stage_index:10}],['RUNNING',{stage_index:0}],['RUNNING',{stage_count:0}],['RUNNING',{units_done:56}],['RUNNING',{units_done:-1}],['RUNNING',{unit_count:0}],['RUNNING',{targets_done_in_stage:5001}],['RUNNING',{targets_total:5001}],
  ['RUNNING',{plan_final:'no'}],['RUNNING',{apply_enabled:true}],['RUNNING',{production_go:true}],['RUNNING',{document:{}}],['RUNNING',{job_id:id}],['RUNNING',{contract_version:'cp7.native-analysis-staged-job.v0'}],
  ['RUNNING',{worker_active:'yes'}],['RUNNING',{reference:null}],['RUNNING',{reference:{captured_at:'2026-10-07T09:00:00.000000Z'}}],['RUNNING',{reference:{captured_at:'kemarin',source_hash:'f'.repeat(64)}}],['RUNNING',{last_progress_at:'2026-10-07'}],['RUNNING',{unit_attempts:-1}],['RUNNING',{request_id:other}],
  ['DONE',{run_id:null}],['DONE',{run_id:undefined}],['DONE',{run_id:'bukan-uuid'}],['DONE',{units_done:54}],['DONE',{plan_final:false}],['DONE',{targets_total:null}],['DONE',{failure:{unit:1,sqlstate:'P0001',code:'CP7_ANALYSIS_JOB_ERROR'}}],
  ['FAILED',{failure:null}],['FAILED',{failure:undefined}],['FAILED',{failure:{unit:12,sqlstate:'42501'}}],['FAILED',{failure:{unit:12,sqlstate:'42501',code:'OOPS'}}],['FAILED',{failure:{unit:12,sqlstate:'4250',code:'CP7_ANALYSIS_ACCESS_CHANGED'}}],
  ['FAILED',{failure:{unit:12,sqlstate:'42501',code:'CP7_ANALYSIS_ACCESS_CHANGED',extra:1}}],['FAILED',{failure:{unit:12,sqlstate:'42501',code:'CP7_ANALYSIS_ACCESS_CHANGED',message:7}}],['FAILED',{failure:{unit:56,sqlstate:'42501',code:'CP7_ANALYSIS_ACCESS_CHANGED'}}],['FAILED',{run_id:fixture.run_id}]]
 for(const[state,extra]of bad)expect(()=>parseStagedJob(stagedJobFixture(id,state,extra),id),JSON.stringify(extra)).toThrow()
 for(const v of [null,[],'RUNNING',{}])expect(()=>parseStagedJob(v,id)).toThrow()
})

it('keeps the staged request under its own key with the single job request protocol, never trusting a broken record',()=>{
 localStorage.clear();const scope='analysis:cp6-disposable:actor-1'
 expect(stagedRequestKey(scope)).toBe('erp.cp7.analysis-staged.v1:'+scope);expect(readStagedRequest(scope)).toEqual({pending:null,error:''})
 persistStagedRequest(scope,{id,q});expect(readStagedRequest(scope).pending).toEqual({id,q});expect(localStorage.getItem('erp.cp7.analysis-job.v1:'+scope)).toBeNull();expect(localStorage.getItem('erp.cp7.native-demand-request.v1:'+scope)).toBeNull()
 expect(()=>persistStagedRequest(scope,{id:other,q})).toThrow();expect(()=>clearStagedRequest(scope,other)).toThrow();expect(readStagedRequest(scope).pending?.id).toBe(id)
 clearStagedRequest(scope,id);expect(readStagedRequest(scope).pending).toBeNull();expect(()=>clearStagedRequest(scope,id)).toThrow()
 localStorage.setItem(stagedRequestKey(scope),'{broken');expect(readStagedRequest(scope).error).toContain('belum bisa dibaca');expect(()=>persistStagedRequest(scope,{id,q})).toThrow();expect(localStorage.getItem(stagedRequestKey(scope))).toBe('{broken')
 for(const v of [{id,q,finance:'INCLUDED'},{id:'x',q},{id,q:{...q,group_mode:'ALL'}},{id,q:{...q,through_date:'2026-08-01'}}]){localStorage.setItem(stagedRequestKey(scope),JSON.stringify(v));expect(readStagedRequest(scope)).toMatchObject({pending:null});expect(readStagedRequest(scope).error).toBeTruthy()}
 localStorage.clear()
})

it('states progress, pause and failure from the server status, with the failure code verbatim',()=>{
 const r=parseStagedJob(stagedJobFixture(id,'RUNNING'),id)
 expect(stagedProgressText(r).startsWith('Analisis bertahap: tahap 3 dari 9 (HIST_ROWS) · unit 12 dari 55')).toBe(true);expect(stagedProgressText(r)).toContain('target 1.200 dari 5.000');expect(stagedProgressText(r)).toContain('dimulai jam 16.00.00 WIB')
 expect(stagedProgressText(parseStagedJob(stagedJobFixture(id,'RUNNING',{unit_attempts:2,worker_active:true}),id))).toContain('percobaan ulang 2')
 expect(stagedPausedText(r).startsWith('Analisis bertahap dijeda sejak jam 16.05.30 WIB')).toBe(true)
 const f=parseStagedJob(stagedJobFixture(id,'FAILED'),id);expect(stagedFailureText(f.failure!)).toContain('CP7_ANALYSIS_ACCESS_CHANGED');expect(stagedFailureText(f.failure!)).toContain('SQLSTATE 42501');expect(stagedFailureText(f.failure!)).toContain('Hak akses berubah')
 expect(stagedFailureText({unit:3,sqlstate:'P0001',code:'CP7_SOMETHING_NEW'})).toContain('CP7_SOMETHING_NEW');expect(stagedFailureText({unit:3,sqlstate:'P0001',code:'CP7_ANALYSIS_STAGE_STOPPED'})).toContain('batas waktu server')
 expect(stagedCapRefusal({code:'P0001',message:'CP7_NETTING_MATCH_SOURCE_LIMIT'})).toBe(true);expect(stagedCapRefusal({code:'CP7_NETTING_WORK_LIMIT'})).toBe(true);expect(stagedCapRefusal({sqlstate:'P0001',code:'CP7_PLANNING_CAPTURE_INCOMPLETE'})).toBe(true)
 expect(stagedCapRefusal({message:'CP7_ANALYSIS_ACCESS_CHANGED'})).toBe(false);expect(stagedCapRefusal(null)).toBe(false);expect(stagedCapRefusal(Error('fetch failed'))).toBe(false)
})

// A scripted server: each RPC answers from its queue, in order, and refuses
// whatever was not scripted.
function server(script:{request?:unknown[];step?:unknown[];get?:unknown[]}){
 const calls:string[]=[],queues={request:[...(script.request??[])],step:[...(script.step??[])],get:[...(script.get??[])]}
 const take=(k:'request'|'step'|'get')=>{calls.push(k);const next=queues[k].shift();if(next===undefined)throw Error('unexpected '+k);return next instanceof Error?Promise.reject(next):Promise.resolve(next as StagedReply)}
 return{calls,rpc:{request:()=>take('request'),step:()=>take('step'),get:()=>take('get')}}
}
const noSleep=async(_ms:number)=>{throw Error('no wait expected')}

it('drives request → step × n → DONE, reporting each server status as it comes, without waiting between steps',async()=>{
 const s=server({request:[running(12)],step:[running(13),running(14),ok(stagedJobFixture(id,'DONE'))]}),seen:StagedJob[]=[]
 const done=await driveStagedJob({rpc:s.rpc,request:{id,q},start:true,sleep:noSleep,onStatus:j=>seen.push(j)})
 expect(done?.state).toBe('DONE');expect(done?.runId).toBe(fixture.run_id);expect(s.calls).toEqual(['request','step','step','step'])
 expect(seen.map(j=>[j.state,j.unitsDone])).toEqual([['RUNNING',12],['RUNNING',13],['RUNNING',14],['DONE',55]])
})

it('backs off and polls get instead of stepping while another session holds the job',async()=>{
 const waits:number[]=[]
 const s=server({request:[running(12,{worker_active:true})],get:[running(13,{worker_active:true}),running(14)],step:[ok(stagedJobFixture(id,'DONE'))]})
 const done=await driveStagedJob({rpc:s.rpc,request:{id,q},start:true,sleep:async ms=>{waits.push(ms)}})
 expect(done?.state).toBe('DONE');expect(s.calls).toEqual(['request','get','get','step']);expect(waits).toEqual([STAGED_WORKER_BACKOFF_MS,STAGED_WORKER_BACKOFF_MS])
})

it('stops on FAILED with the server failure, never claiming a run',async()=>{
 const s=server({request:[running(12)],step:[running(13),ok(stagedJobFixture(id,'FAILED',{units_done:13,failure:{unit:13,sqlstate:'57014',code:'CP7_ANALYSIS_STAGE_STOPPED'}}))]})
 const failed=await driveStagedJob({rpc:s.rpc,request:{id,q},start:true,sleep:noSleep})
 expect(failed).toMatchObject({state:'FAILED',runId:null,failure:{unit:13,sqlstate:'57014',code:'CP7_ANALYSIS_STAGE_STOPPED'}});expect(s.calls).toEqual(['request','step','step'])
})

it('resumes a stored request by reading status first, then stepping; a DONE status reads nothing more',async()=>{
 const s=server({get:[running(30)],step:[ok(stagedJobFixture(id,'DONE'))]})
 expect((await driveStagedJob({rpc:s.rpc,request:{id,q},start:false,sleep:noSleep}))?.state).toBe('DONE');expect(s.calls).toEqual(['get','step'])
 const t=server({get:[ok(stagedJobFixture(id,'DONE'))]})
 expect((await driveStagedJob({rpc:t.rpc,request:{id,q},start:false,sleep:noSleep}))?.runId).toBe(fixture.run_id);expect(t.calls).toEqual(['get'])
})

it('abandons the loop once aborted: no further call, no result, even from inside a back-off wait',async()=>{
 const seen:StagedJob[]=[],s=server({request:[running(12)],step:[running(13),running(14)]})
 expect(await driveStagedJob({rpc:s.rpc,request:{id,q},start:true,sleep:noSleep,aborted:()=>seen.length>=2,onStatus:j=>seen.push(j)})).toBeNull();expect(s.calls).toEqual(['request','step'])
 let aborted=false;const t=server({request:[running(12,{worker_active:true})],get:[running(13)]})
 expect(await driveStagedJob({rpc:t.rpc,request:{id,q},start:true,aborted:()=>aborted,sleep:async()=>{aborted=true}})).toBeNull();expect(t.calls).toEqual(['request'])
 const u=server({request:[running(12)]});expect(await driveStagedJob({rpc:u.rpc,request:{id,q},start:true,aborted:()=>true,sleep:noSleep})).toBeNull();expect(u.calls).toEqual([])
})

it('throws a server refusal or a lost reply after reporting the last known status, and refuses a status of another request',async()=>{
 const seen:StagedJob[]=[],s=server({request:[running(12)],step:[{data:null,error:{code:'42501',message:'CP7_ANALYSIS_ACCESS_CHANGED'}}]})
 await expect(driveStagedJob({rpc:s.rpc,request:{id,q},start:true,sleep:noSleep,onStatus:j=>seen.push(j)})).rejects.toMatchObject({message:'CP7_ANALYSIS_ACCESS_CHANGED'});expect(seen).toHaveLength(1);expect(seen[0].state).toBe('RUNNING')
 const t=server({get:[running(12)],step:[new TypeError('Failed to fetch')]})
 await expect(driveStagedJob({rpc:t.rpc,request:{id,q},start:false,sleep:noSleep})).rejects.toThrow('Failed to fetch');expect(t.calls).toEqual(['get','step'])
 const u=server({request:[ok(stagedJobFixture(other,'RUNNING'))]})
 await expect(driveStagedJob({rpc:u.rpc,request:{id,q},start:true,sleep:noSleep})).rejects.toThrow('belum sesuai kontrak')
})
