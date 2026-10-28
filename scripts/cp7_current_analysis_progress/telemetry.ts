import {projectCombinedProgress,PROGRESS_POLICY,type CombinedProgress} from './progress'
import {parseStagedJob,type StagedRequest} from '../cp7_current_frozen_finance_ui/vendor/src/nativeStagedJob'
import {planInstantMicros} from '../cp7_current_frozen_finance_ui/vendor/src/nativePlanInstant'

type Clock={createdAt:string;lastActivityAt:string;finishedAt:string|null;elapsedMs:number;idleMs:number}
type WorkProgress=Omit<CombinedProgress,'elapsedSinceCaptureMs'|'elapsedClock'|'terminalDurationMs'|'clockBeforeCapture'>
export type ProgressTelemetry={progress:WorkProgress;observedAt:string;operational:Clock;
 finance:(Clock&{captureId:string;attempts:number;reportMs:number|null;activity:'WORKER_OBSERVED'|'NO_WORKER_OBSERVED'|'TERMINAL'})|null;
 elapsedMs:number|null;processingFinished:boolean;finishedAt:string|null;clock:'SERVER';
 overallPercent:null;queuePosition:null;stallState:'NOT_INFERRED';originalStatus:unknown}
const fail=():never=>{throw Error('Informasi kemajuan tidak sesuai dengan analisis tersimpan.')}
const object=(v:unknown):Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:fail()
const keys=(v:Record<string,unknown>,expected:readonly string[])=>{if(Object.keys(v).length!==expected.length||expected.some(k=>!Object.hasOwn(v,k)))fail()}
const instant=(v:unknown):string=>{planInstantMicros(v);return v as string}
const millis=(end:string,start:string)=>{const n=planInstantMicros(end)-planInstantMicros(start);if(n<0n||n/1000n>BigInt(Number.MAX_SAFE_INTEGER))return fail();return Number(n/1000n)}
const count=(v:unknown):number=>typeof v==='number'&&Number.isSafeInteger(v)&&v>=0?v:fail()
const duration=(v:unknown):number|null=>v===null?null:typeof v==='number'&&Number.isFinite(v)&&v>=0?v:fail()
function clocks(m:Record<string,unknown>,observedAt:string,terminal:boolean):Clock{
 const createdAt=instant(m.created_at),lastActivityAt=instant(m.last_activity_at),finishedAt=m.finished_at===null?null:instant(m.finished_at)
 millis(lastActivityAt,createdAt);const idleMs=millis(observedAt,lastActivityAt)
 if(terminal!==(finishedAt!==null))fail()
 if(finishedAt!==null){millis(finishedAt,createdAt);millis(lastActivityAt,finishedAt)}
 return{createdAt,lastActivityAt,finishedAt,elapsedMs:millis(finishedAt??observedAt,createdAt),idleMs}
}

export function readProgressTelemetry(raw:unknown,request:StagedRequest):ProgressTelemetry{
 const e=object(raw);keys(e,['contract_version','policy_id','observed_at','status','operational','finance','production_go'])
 if(e.contract_version!=='cp7.frozen-analysis-progress.v1'||e.policy_id!==PROGRESS_POLICY||e.production_go!==false)fail()
 const observedAt=instant(e.observed_at),job=parseStagedJob(e.status,request.id,request)
 // Consumers get one authoritative server clock. Do not retain a competing
 // client-observation duration from the status-only fallback projection.
 const {elapsedSinceCaptureMs:_elapsed,elapsedClock:_clock,terminalDurationMs:_terminal,
  clockBeforeCapture:_before,...progress}=projectCombinedProgress(e.status,request,observedAt)
 const op=object(e.operational);keys(op,['created_at','last_activity_at','finished_at','worker_observation'])
 if(op.worker_observation!=='NOT_EXPOSED'||planInstantMicros(op.last_activity_at)!==planInstantMicros(job.lastProgressAt))fail()
 const operational=clocks(op,observedAt,job.state!=='RUNNING'),side=job.financeCapture
 let finance:ProgressTelemetry['finance']=null
 if(!side||side.state==='ACCESS_REVOKED'){if(e.finance!==null)fail()}
 else{
  const m=object(e.finance);keys(m,['capture_id','created_at','last_activity_at','finished_at','unit_attempts','report_ms','worker_observation'])
  const capture=side.capture
  if(!capture)return fail()
  if(m.capture_id!==capture.id||!['LOCK_HELD','NO_LOCK_OBSERVED'].includes(String(m.worker_observation)))fail()
  const time=clocks(m,observedAt,side.state!=='RUNNING')
  finance={...time,captureId:capture.id,attempts:count(m.unit_attempts),reportMs:duration(m.report_ms),
   activity:side.state!=='RUNNING'?'TERMINAL':m.worker_observation==='LOCK_HELD'?'WORKER_OBSERVED':'NO_WORKER_OBSERVED'}
 }
 const processingFinished=job.state!=='RUNNING'&&(!side||finance!==null&&finance.finishedAt!==null)
 let finishedAt:string|null=null
 if(processingFinished){finishedAt=operational.finishedAt!;if(finance?.finishedAt&&planInstantMicros(finance.finishedAt)>planInstantMicros(finishedAt))finishedAt=finance.finishedAt}
 return{progress,observedAt,operational,finance,processingFinished,finishedAt,
  elapsedMs:side?.state==='ACCESS_REVOKED'?null:millis(finishedAt??observedAt,operational.createdAt),
  clock:'SERVER',overallPercent:null,queuePosition:null,stallState:'NOT_INFERRED',originalStatus:e.status}
}
