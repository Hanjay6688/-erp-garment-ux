// @vitest-environment jsdom
import {beforeEach,it,expect,vi} from 'vitest'
import wire from '../tests/fixtures/nativeModelPolicySql.json'
import {parseModelPolicyWorkspace,parseModelPolicyConfig,prepareModelPolicy,parsePreparedModelPolicy,parseModelPolicyOutcome,readModelPolicyRequest,persistModelPolicyRequest,clearModelPolicyRequest,modelPolicyRequestKey,readModelPolicy,saveModelPolicy} from './nativeModelPolicy'
const actor=wire.workspace.actor_scope_id,scope='disposable:policy',workspace=()=>parseModelPolicyWorkspace(wire.workspace,actor)
const prepared=()=>prepareModelPolicy(workspace(),'SET',wire.payload.config,wire.payload.reason,true,wire.requestId)
beforeEach(()=>{localStorage.clear();vi.restoreAllMocks()})
it('parses the actual SQL workspace and prospective receipt without supplying thresholds',()=>{
 expect(wire.actual_SQL).toBe(true);expect(workspace().current).toBeNull();expect(workspace().state).toBe('UNREVIEWED');expect(workspace().template.models.challengers).toHaveLength(7)
 expect(parseModelPolicyOutcome(wire.outcome,prepared())).toEqual(wire.outcome.policy)
 expect(prepared().payload).toEqual(wire.payload)
})
it.each([['missing threshold',{...wire.payload.config,minimum_training_days:undefined}],['training0',{...wire.payload.config,minimum_training_days:'0'}],['horizon91',{...wire.payload.config,maximum_horizon_days:'91'}],['method baseline',{...wire.payload.config,allowed_methods:['MEAN']}],['duplicate',{...wire.payload.config,allowed_methods:['NAIVE','NAIVE']}],['extra',{...wire.payload.config,extra:true}],['rounded number',{...wire.payload.config,promotion:{...wire.payload.config.promotion,minimum_mae_improvement:0.1}}],['scientific',{...wire.payload.config,promotion:{...wire.payload.config.promotion,minimum_mae_improvement:'1e-3'}}]])('refuses %s',(_name,value)=>{expect(()=>parseModelPolicyConfig(value)).toThrow()})
it('preserves exact decimal threshold strings and an explicitly empty method list',()=>{
 const c={...wire.payload.config,allowed_methods:[],promotion:{...wire.payload.config.promotion,minimum_mae_improvement:'9007199254740993.123456789012'}}
 expect(parseModelPolicyConfig(c)).toEqual(c)
})
it.each(['actor','state','revision','applied','extra','template']as const)('rejects an inconsistent workspace: %s',kind=>{
 const w=structuredClone(wire.workspace)as Record<string,unknown>
 if(kind==='actor')w.actor_scope_id='00000000-0000-4000-8000-000000000001'
 if(kind==='state')w.state='ACTIVE'
 if(kind==='revision')w.revision='1'
 if(kind==='applied')w.forecast_applied=true
 if(kind==='extra')w.extra=true
 if(kind==='template')(w.model_template as {models:{challengers:unknown[]}}).models.challengers.pop()
 expect(()=>parseModelPolicyWorkspace(w,actor)).toThrow()
})
it('requires review, writer access, correct prior revision and an existing policy to suspend',()=>{
 const w=workspace();expect(()=>prepareModelPolicy(w,'SET',wire.payload.config,'review',false,wire.requestId)).toThrow()
 expect(()=>prepareModelPolicy({...w,canWrite:false},'SET',wire.payload.config,'review',true,wire.requestId)).toThrow()
 expect(()=>prepareModelPolicy(w,'SUSPEND',null,'review',true,wire.requestId)).toThrow()
 const p=prepared();p.payload.expected_revision='1';expect(()=>parsePreparedModelPolicy(p,actor)).toThrow()
})
it.each(['request','actor','revision','config','state','registry','reason','hash','applied']as const)('rejects a contradictory success: %s',kind=>{
 const r=structuredClone(wire.outcome)
 if(kind==='request')r.request_id='00000000-0000-4000-8000-000000000001'
 if(kind==='actor')r.actor_scope_id='00000000-0000-4000-8000-000000000001'
 if(kind==='revision')r.policy.revision='2'
 if(kind==='config')r.policy.config.minimum_training_days='30'
 if(kind==='state')r.policy.state='SUSPENDED'
 if(kind==='registry')r.policy.registry_id='cp7.native-model-policy.v1'
 if(kind==='reason')r.policy.reason='other'
 if(kind==='hash')r.template_hash='0'.repeat(64)
 if(kind==='applied')r.forecast_applied=true
 expect(()=>parseModelPolicyOutcome(r,prepared())).toThrow()
})
it('binds suspension to the prior immutable configuration and microsecond clock',()=>{
 const prior={policy:{...wire.outcome.policy,recorded_at:'2026-10-24T13:00:00.000002Z'},actor_scope_id:actor,request_id:wire.requestId,template_hash:wire.outcome.template_hash}
 const w=parseModelPolicyWorkspace({...wire.workspace,current:prior,revision:'1',state:'ACTIVE'},actor)
 const p=prepareModelPolicy(w,'SUSPEND',null,'Withdraw',true,crypto.randomUUID())
 const next='00000000-0000-4000-8000-000000000003'
 const reply={...wire.outcome,request_id:p.requestId,policy:{...prior.policy,id:next,registry_id:'cp7.owner-model-policy.'+next,revision:'2',state:'SUSPENDED',reason:'Withdraw',recorded_at:'2026-10-24T13:00:00.000003Z'}}
 expect(parseModelPolicyOutcome(reply,p).state).toBe('SUSPENDED')
 reply.policy.recorded_at='2026-10-24T13:00:00.000001Z';expect(()=>parseModelPolicyOutcome(reply,p)).toThrow()
})
it('keeps exact recovery across reread and refuses foreign actors, changed payload and corruption',()=>{
 const p=prepared();persistModelPolicyRequest(scope,p);expect(readModelPolicyRequest(scope,actor).pending).toEqual(p)
 expect(()=>persistModelPolicyRequest(scope,p)).toThrow();expect(()=>clearModelPolicyRequest(scope,{...p,payload:{...p.payload,reason:'different'}})).toThrow()
 expect(readModelPolicyRequest(scope,'00000000-0000-4000-8000-000000000001').error).not.toBe('')
 expect(readModelPolicyRequest(scope,actor).pending).toEqual(p);clearModelPolicyRequest(scope,p);expect(readModelPolicyRequest(scope,actor).pending).toBeNull()
 localStorage.setItem(modelPolicyRequestKey(scope),'broken');expect(readModelPolicyRequest(scope,actor).error).not.toBe('')
})
it('refuses unverified durable storage and transmits the unchanged payload and UUID',async()=>{
 const p=prepared();vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{});expect(()=>persistModelPolicyRequest(scope,p)).toThrow();vi.restoreAllMocks()
 const rpc=vi.fn().mockResolvedValueOnce({data:wire.workspace,error:null}).mockResolvedValueOnce({data:wire.outcome,error:null})
 expect(await readModelPolicy({rpc},actor)).toEqual(workspace());expect(await saveModelPolicy({rpc},p)).toEqual(wire.outcome.policy)
 expect(rpc.mock.calls[1]).toEqual(['erp_cp7_save_model_activation_policy_v1',{p_payload:p.payload,p_request:p.requestId}])
})
