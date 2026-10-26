import type {AnalogReadContext} from '../../../src/nativeProductAnalog'
import {stagedInstant} from '../../../src/nativeAnalysisPages'
import {sameBoundedReference} from '../../../src/nativeBoundedQuantity'
import {boundedFrozenReply,FROZEN_NO_PROGRESS_MS,FROZEN_STALL_MESSAGE} from '../../cp7_frozen_quantity_ui/client/nativeFrozenProgress'

type State='QUEUED'|'RUNNING'|'READY'|'FAILED'|'EXPIRED'
export type ChoicePreparation={state:State;sourceRequest:string;runId:string;createdAt:string;updatedAt:string;unitsDone:0|1;attempts:number;workerActive:boolean;failure:string|null}
type Reply={data:unknown;error:unknown}
type Client={rpc(name:`erp_cp7_${'request'|'get'|'step'}_frozen_choice_preparation_v1`,args:{p_source_request:string;p_access:string}):PromiseLike<Reply>}
const fail=():never=>{throw Error('Persiapan pilihan belum dapat dipastikan. Periksa pekerjaan pada analisis yang sama.')}
const object=(v:unknown):Record<string,unknown>=>v&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:fail()
const integer=(v:unknown,max:number)=>typeof v==='number'&&Number.isInteger(v)&&v>=0&&v<=max?v:fail()
const hash=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v)?v:fail()
const uuid=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(v)?v:fail()
export function parseChoicePreparation(value:unknown,c:AnalogReadContext):ChoicePreparation{
 const v=object(value),r=object(v.reference)
 if(c.sourceMethod!=='FROZEN_V2'||v.contract_version!=='cp7.frozen-choice-preparation.v1'||uuid(v.source_request)!==c.requestId||uuid(v.run_id)!==c.runId||v.stage!=='FROZEN_INPUTS'||v.choice_saved!==false||v.production_go!==false||v.unit_count!==1)fail()
 if(!sameBoundedReference({capturedAt:stagedInstant(r.captured_at),sourceHash:hash(r.source_hash)},c.reference))fail()
 if(!['QUEUED','RUNNING','READY','FAILED','EXPIRED'].includes(String(v.state))||typeof v.worker_active!=='boolean')fail()
 const state=v.state as State,done=integer(v.units_done,1)as 0|1,attempts=integer(v.unit_attempts,3)
 if(done!==(state==='READY'?1:0)||state==='RUNNING'&&!v.worker_active||state==='QUEUED'&&v.worker_active)fail()
 if(state==='FAILED'?(typeof v.failure_code!=='string'||!/^CP7_[A-Z0-9_]+$/.test(v.failure_code)||typeof v.failure_sqlstate!=='string'||!/^[0-9A-Z]{5}$/.test(v.failure_sqlstate)):v.failure_code!==null||v.failure_sqlstate!==null)fail()
 const createdAt=stagedInstant(v.created_at),updatedAt=stagedInstant(v.last_progress_at)
 if(Date.parse(updatedAt)<Date.parse(createdAt))fail()
 return{state,sourceRequest:c.requestId,runId:c.runId,createdAt,updatedAt,unitsDone:done,attempts,workerActive:v.worker_active as boolean,failure:v.failure_code as string|null}
}
export async function choicePreparationRPC(client:unknown,verb:'request'|'get'|'step',c:AnalogReadContext){
 if(c.sourceMethod!=='FROZEN_V2')fail();uuid(c.requestId);hash(c.accessEpoch)
 const reply=await boundedFrozenReply(()=>(client as Client).rpc(`erp_cp7_${verb}_frozen_choice_preparation_v1`,{p_source_request:c.requestId,p_access:c.accessEpoch}))
 if(reply.error)throw reply.error
 return parseChoicePreparation(reply.data,c)
}
export async function driveChoicePreparation(client:unknown,c:AnalogReadContext,options:{current:()=>boolean;status:(s:ChoicePreparation)=>void;now?:()=>number;pause?:()=>Promise<void>}){
 const now=options.now??(()=>performance.now()),pause=options.pause??(()=>new Promise(resolve=>setTimeout(resolve,2000)))
 if(!options.current())return null
 const started=now();let s=await choicePreparationRPC(client,'request',c)
 while(options.current()){
  options.status(s)
  if(!options.current())return null
  if(['READY','FAILED','EXPIRED'].includes(s.state))return s
  if(now()-started>=FROZEN_NO_PROGRESS_MS)throw Error(FROZEN_STALL_MESSAGE)
  // This is one bounded preparation unit, not a total factory-analysis limit.
  // No progress is invented while another transaction owns the same unit.
  if(s.state==='RUNNING'){await pause();if(!options.current())return null;s=await choicePreparationRPC(client,'get',c)}
  else s=await choicePreparationRPC(client,'step',c)
 }
 return null
}
