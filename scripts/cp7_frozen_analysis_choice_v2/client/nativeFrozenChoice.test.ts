// @vitest-environment jsdom
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import choiceSQL from '../choice.prepared.sql?raw'
import {analogId} from '../../../tests/fixtures/nativeProductAnalog'
import {analogChoiceFixture} from '../../../tests/fixtures/nativeProductAnalogChoice'
import {parseAnalogChoiceWorkspace,prepareAnalogConfirmation,prepareAnalogClear,parseAnalogChoiceOutcome,readProductAnalogChoice,saveProductAnalogChoice,parsePreparedAnalogChoice,analogChoiceRequestKey,persistAnalogChoiceRequest,clearAnalogChoiceRequest,readAnalogChoiceRequest} from './nativeFrozenChoice'

const setup=()=>{
 const f=analogChoiceFixture(),context={...f.context,sourceMethod:'FROZEN_V2' as const},candidates={...f.candidates,sourceMethod:'FROZEN_V2' as const}
 const command=prepareAnalogConfirmation(context,candidates,f.workspace,candidates.rows[0].key,'1.2500',' Ukuran dan model ditinjau ',true,analogId(500))
 return{...f,context,candidates,command,outcome:{...f.outcome,contract_version:'cp7.product-analog-choice-outcome.v2'}}
}
beforeEach(()=>{
 const tails=new Map<string,Promise<void>>()
 vi.stubGlobal('navigator',{locks:{request:vi.fn(async(name:string,_options:unknown,action:()=>unknown)=>{
  const prior=tails.get(name)??Promise.resolve();let release!:()=>void
  const hold=new Promise<void>(resolve=>{release=resolve}),tail=prior.then(()=>hold);tails.set(name,tail)
  await prior
  try{return await action()}finally{release();if(tails.get(name)===tail)tails.delete(name)}
 })}})
})
afterEach(()=>{localStorage.clear();vi.restoreAllMocks();vi.unstubAllGlobals()})
it('reads the shared authorized append-only choice workspace through its unchanged method',async()=>{
 const f=setup(),rpc=vi.fn(async()=>({data:f.raw,error:null}))
 expect((await readProductAnalogChoice({rpc},f.context.actor,f.context.targetKey)).choice.revision).toBe('0')
 expect(rpc).toHaveBeenCalledWith('erp_cp7_get_product_analog_choices_v1',{p_targets:[f.context.targetKey]})
})
it('refuses silent storage failure before sending',async()=>{
 const f=setup(),rpc=vi.fn();vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{})
 await expect(persistAnalogChoiceRequest('work',f.command)).rejects.toThrow('belum tercatat')
 await expect(saveProductAnalogChoice({rpc},'work',f.context.actor,f.context.targetKey)).rejects.toThrow('belum tercatat')
 expect(rpc).not.toHaveBeenCalled()
})
it('rejects old command, old source method and old outcome without relabeling',()=>{
 const f=setup(),old=analogChoiceFixture()
 expect(()=>parsePreparedAnalogChoice(old.command,f.context.actor,f.context.targetKey)).toThrow()
 expect(()=>prepareAnalogConfirmation(old.context,f.candidates,f.workspace,f.candidates.rows[0].key,'1','reviewed',true,analogId(500))).toThrow()
 expect(()=>prepareAnalogConfirmation(f.context,old.candidates,f.workspace,f.candidates.rows[0].key,'1','reviewed',true,analogId(500))).toThrow()
 expect(()=>parseAnalogChoiceOutcome(old.outcome,f.command)).toThrow()
 const changed=structuredClone(f.command);delete changed.review!.context.sourceMethod
 expect(()=>parsePreparedAnalogChoice(changed,f.context.actor,f.context.targetKey)).toThrow()
})
it('requires a durable exact command, sends only named SQL parameters and preserves reply-loss bytes',async()=>{
 const f=setup(),rpc=vi.fn(async(name:string,args:Record<string,unknown>)=>{
  const signature=choiceSQL.match(new RegExp('create function public\\.'+name+'\\(([^)]+)\\)'))![1]
  expect(Object.keys(args).sort()).toEqual(signature.split(',').map(p=>p.trim().split(/\s+/)[0]).sort())
  expect(args.p_request).toBe(f.command.requestId)
  ;(args.p_payload as {reason:string}).reason='transport mutation'
  return{data:f.outcome,error:null}
 })
 const send=()=>saveProductAnalogChoice({rpc},'work',f.context.actor,f.context.targetKey)
 await expect(send()).rejects.toThrow();expect(rpc).not.toHaveBeenCalled()
 await persistAnalogChoiceRequest('work',f.command)
 const key=analogChoiceRequestKey('work',f.context.actor,f.context.targetKey),bytes=localStorage.getItem(key)
 rpc.mockRejectedValueOnce(Error('reply lost'))
 await expect(send()).rejects.toThrow('reply lost');expect(localStorage.getItem(key)).toBe(bytes)
 const answer=await send();expect(answer.state).toBe('CONFIRMED_ASSUMPTION')
 expect(f.command.payload.reason).toBe('Ukuran dan model ditinjau');expect(localStorage.getItem(key)).toBe(bytes)
 expect(rpc.mock.calls.every(c=>c[0]==='erp_cp7_save_product_analog_choice_v2')).toBe(true)
 await clearAnalogChoiceRequest('work',f.command);expect(localStorage.getItem(key)).toBeNull()
})
it('serializes competing creates and waits for an in-flight send before clearing',async()=>{
 const f=setup(),other=structuredClone(f.command);other.requestId=analogId(999)
 const creates=await Promise.allSettled([persistAnalogChoiceRequest('work',f.command),persistAnalogChoiceRequest('work',other)])
 expect(creates.map(x=>x.status).sort()).toEqual(['fulfilled','rejected'])
 expect(readAnalogChoiceRequest('work',f.context.actor,f.context.targetKey).pending).toEqual(f.command)
 let release!:(v:{data:unknown;error:null})=>void,entered!:()=>void
 const started=new Promise<void>(r=>{entered=r}),reply=new Promise<{data:unknown;error:null}>(r=>{release=r})
 const rpc=vi.fn(()=>{entered();return reply})
 const sending=saveProductAnalogChoice({rpc},'work',f.context.actor,f.context.targetKey);await started
 let cleared=false;const clearing=clearAnalogChoiceRequest('work',f.command).then(()=>{cleared=true})
 await Promise.resolve();expect(cleared).toBe(false)
 expect(readAnalogChoiceRequest('work',f.context.actor,f.context.targetKey).pending).toEqual(f.command)
 release({data:f.outcome,error:null});await sending;await clearing;expect(cleared).toBe(true)
})
it('preserves corrupt commands and refuses actor, method or stale-command replacement',async()=>{
 const f=setup(),key=analogChoiceRequestKey('work',f.context.actor,f.context.targetKey)
 const bad={...f.command,payload:{...f.command.payload,contract_version:'cp7.product-analog-choice-command.v1'}},bytes=JSON.stringify(bad)
 localStorage.setItem(key,bytes);const rpc=vi.fn()
 await expect(persistAnalogChoiceRequest('work',f.command)).rejects.toThrow()
 await expect(clearAnalogChoiceRequest('work',f.command)).rejects.toThrow()
 await expect(saveProductAnalogChoice({rpc},'work',f.context.actor,f.context.targetKey)).rejects.toThrow()
 await expect(saveProductAnalogChoice({rpc},'work',analogId(999),f.context.targetKey)).rejects.toThrow()
 expect(rpc).not.toHaveBeenCalled();expect(localStorage.getItem(key)).toBe(bytes)
 expect(analogChoiceRequestKey('work',analogId(999),f.context.targetKey)).not.toBe(key)
})
it('fails before storage or network when the browser lock or durable write is unavailable',async()=>{
 const f=setup(),rpc=vi.fn();vi.stubGlobal('navigator',{})
 await expect(persistAnalogChoiceRequest('work',f.command)).rejects.toThrow('dikunci')
 await expect(saveProductAnalogChoice({rpc},'work',f.context.actor,f.context.targetKey)).rejects.toThrow('dikunci')
 expect(rpc).not.toHaveBeenCalled();expect(localStorage.length).toBe(0)
})
it('requires deliberate review, a visible candidate, explicit positive scale and a reason',()=>{
 const{context,candidates,workspace}=setup()
 const make=(scale:string,reason:string,reviewed=true,key=candidates.rows[0].key)=>prepareAnalogConfirmation(context,candidates,workspace,key,scale,reason,reviewed,analogId(500))
 for(const scale of['','0','0.000000000000','-1','1e2','0.1234567890123'])expect(()=>make(scale,'reviewed')).toThrow()
 expect(()=>make('1','')).toThrow();expect(()=>make('1','reviewed',false)).toThrow()
 expect(()=>make('1','reviewed',true,analogId(999)+':'+analogId(5))).toThrow()
 expect(make('0.000000000001','reviewed').payload.scale_factor).toBe('0.000000000001')
 expect(make('9007199254740993.123456789012','reviewed').payload.scale_factor).toBe('9007199254740993.123456789012')
})
it('keeps exact source clocks and decimal strings, and allows equal decimal formatting',()=>{
 const{command,outcome}=setup(),parsed=parseAnalogChoiceOutcome(outcome,command)
 expect(parsed.evidence?.totalPcs).toBe('0');expect(parsed.evidence?.scale).toBe('1.25')
 expect(parsed.evidence?.capturedAt).toBe('2026-10-24T00:00:00.123456Z')
 expect(command.payload.reason).toBe('Ukuran dan model ditinjau')
})
it.each(['actor','request','target','revision','source','size','history','producer','sourceHash','identity','profile','minimum','clock','recorded','days','scale','reviewed','applied'])('rejects an outcome with mismatched %s evidence',field=>{
 const{command,outcome:r}=setup()
 if(field==='actor')r.actor_scope_id=analogId(999)
 if(field==='request')r.request_id=analogId(999)
 if(field==='target')r.target_key=analogId(999)+':'+analogId(5)
 if(field==='revision')r.revision='9007199254740993'
 if(field==='source')r.evidence.source_request=analogId(999)
 if(field==='size')r.evidence.source_product.size_id=analogId(999)
 if(field==='history')r.evidence.history_hash='9'.repeat(64)
 if(field==='producer')r.evidence.producer_hash='9'.repeat(64)
 if(field==='sourceHash')r.evidence.analysis_source_hash='9'.repeat(64)
 if(field==='identity')r.evidence.identity_hash='9'.repeat(64)
 if(field==='profile')r.evidence.profile_revision='2'
 if(field==='minimum')r.evidence.minimum_available_days='2'
 if(field==='clock')r.evidence.captured_at=r.evidence.captured_at.replace('123456','123457')
 if(field==='recorded')r.recorded_at='2026-10-24T00:00:00.123455Z'
 if(field==='days')r.evidence.available_days='0'
 if(field==='scale')r.evidence.scale_factor='1.250000000001'
 if(field==='reviewed')r.evidence.reviewed=false
 if(field==='applied')r.forecast_applied=true
 expect(()=>parseAnalogChoiceOutcome(r,command)).toThrow('pembanding')
})
it('shares authorized configuration while binding the workspace to its current reader',()=>{
 const{context,raw,outcome}=setup()
 const selected={...raw,rows:[{...outcome,actor_scope_id:analogId(800)}]}
 const parsed=parseAnalogChoiceWorkspace(selected,context.actor,context.targetKey)
 expect(parsed.choice.actor).toBe(analogId(800))
 expect(()=>parseAnalogChoiceWorkspace({...selected,actor_scope_id:analogId(900)},context.actor,context.targetKey)).toThrow()
 expect(()=>parseAnalogChoiceWorkspace({...selected,rows:[]},context.actor,context.targetKey)).toThrow()
 expect(()=>parseAnalogChoiceWorkspace({...selected,rows:[outcome,outcome]},context.actor,context.targetKey)).toThrow()
})
it('clears by appending a new revision without needing the old source snapshot',()=>{
 const{context,raw,outcome}=setup()
 const workspace=parseAnalogChoiceWorkspace({...raw,rows:[outcome]},context.actor,context.targetKey)
 const command=prepareAnalogClear(workspace,'Cabut pembanding',true,analogId(600))
 expect(command.payload).toMatchObject({action:'CLEAR',expected_revision:'1',source_request:null,source_hash:null,source_key:null,scale_factor:null})
 const reply={...outcome,choice_id:analogId(601),request_id:command.requestId,revision:'2',action:'CLEAR',state:'CLEARED',evidence:null,reason:command.payload.reason}
 expect(parseAnalogChoiceOutcome(reply,command).state).toBe('CLEARED')
 expect(()=>parseAnalogChoiceOutcome({...reply,evidence:outcome.evidence},command)).toThrow()
})
