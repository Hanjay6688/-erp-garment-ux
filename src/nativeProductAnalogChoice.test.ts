import {it,expect,vi} from 'vitest'
import choiceSQL from '../scripts/cp7_product_analog_choice_stage/choice.sql?raw'
import {analogId} from '../tests/fixtures/nativeProductAnalog'
import {analogChoiceFixture} from '../tests/fixtures/nativeProductAnalogChoice'
import {parseAnalogChoiceWorkspace,prepareAnalogConfirmation,prepareAnalogClear,parseAnalogChoiceOutcome,readProductAnalogChoice,saveProductAnalogChoice} from './nativeProductAnalogChoice'

const setup=analogChoiceFixture
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
it('sends exact facade arguments, preserves the retry UUID and keeps pending payload isolated',async()=>{
 const{context,raw,command,outcome}=setup()
 const rpc=vi.fn(async(name:string,args:Record<string,unknown>)=>{
  const signature=choiceSQL.match(new RegExp('create function public\\.'+name+'\\(([^)]+)\\)'))![1]
  expect(Object.keys(args).sort()).toEqual(signature.split(',').map(p=>p.trim().split(/\s+/)[0]).sort())
  if(name==='erp_cp7_get_product_analog_choices_v1')return{data:raw,error:null}
  expect(args.p_request).toBe(command.requestId)
  ;(args.p_payload as {reason:string}).reason='transport mutation'
  return{data:outcome,error:null}
 })
 expect((await readProductAnalogChoice({rpc},context.actor,context.targetKey)).choice.state).toBe('UNREVIEWED')
 expect(await saveProductAnalogChoice({rpc},command)).toEqual(await saveProductAnalogChoice({rpc},command))
 expect(command.payload.reason).toBe('Ukuran dan model ditinjau')
 expect(rpc.mock.calls.filter(([name])=>name==='erp_cp7_save_product_analog_choice_v1')).toHaveLength(2)
})
