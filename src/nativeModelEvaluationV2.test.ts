// @vitest-environment jsdom
import {beforeEach,it,expect,vi} from 'vitest'
import wire from '../tests/fixtures/nativeModelEvaluationV2Sql.json'
import {parseModelQuery} from './nativeModelEvaluation'
import {parseModelV2Run,parseModelV2Request,modelV2Method,captureModelV2,readModelV2,persistModelV2Request,readModelV2Request,clearModelV2Request,modelV2RequestKey} from './nativeModelEvaluationV2'
const actor=wire.actor,scope='disposable:model-v2',query=parseModelQuery(wire.eligible.query)
const request=()=>({actor,requestId:wire.eligible.request_id,method:modelV2Method,query})
beforeEach(()=>{localStorage.clear();vi.restoreAllMocks()})
it.each(['baseline','eligible','withdrawn','noAllowedModel']as const)('reads actual SQL %s, without claiming actual Native/Auth evidence',name=>{
 expect(wire.actual_SQL).toBe(true);expect(wire.actual_Native_capture).toBe(false);expect(wire.actual_Auth_HTTP_credit).toBe(false)
 const raw=wire[name],r=parseModelV2Run(raw,parseModelQuery(raw.query),actor)
 expect(r.eligibleNow).toBe(name==='eligible');expect(r.admittedAtCapture).toBe(['eligible','withdrawn'].includes(name))
 expect(r.mean).toBe('50.5');expect(r.query).toEqual(raw.query)
 if(name==='noAllowedModel'){expect(r.scores).toEqual([]);expect(r.forecasts).toBeNull();expect(r.reason).toBe('NO_EXPLICITLY_ALLOWED_CHALLENGER')}
 if(name==='eligible')expect(r.forecasts).toEqual(Array(7).fill('100.000000000000'))
})
it('allows only the current guard to change on reread, retaining the exact archived assessment',()=>{
 const old=parseModelV2Run(wire.eligible,query,actor),next=parseModelV2Run(wire.withdrawn,query,actor,old)
 expect(next.immutableSignature).toBe(old.immutableSignature);expect(next.eligibleNow).toBe(false);expect(next.forecasts).toEqual(old.forecasts)
 const changed=structuredClone(wire.withdrawn);changed.assessment.evaluation!.product_name='changed';changed.assessment.source.product_name='changed'
 expect(()=>parseModelV2Run(changed,query,actor,old)).toThrow()
})
it.each(['actor','query','request','source','engine','clock','registry','policy','state','origin','guard','reason','method','params','vector','decimal','holdout','fold','extra','applied']as const)('rejects contradictory or malformed %s',kind=>{
 const r=structuredClone(wire.eligible),a=r.assessment,e=a.evaluation!,g=r.current_guard
 if(kind==='actor')r.actor_scope_id=crypto.randomUUID()
 if(kind==='query')r.query.horizon_days='8'
 if(kind==='request')r.request_id='invalid'
 if(kind==='source')a.activation.source_hash='0'.repeat(64)
 if(kind==='engine')a.activation.engine_hash='0'.repeat(32)
 if(kind==='clock')a.source.known_as_of='2026-10-24T23:59:59.999999Z'
 if(kind==='registry')a.source.registered_at='2026-06-02T00:00:00.123455Z'
 if(kind==='policy')a.policy_source!.policy.config.allowed_methods=[]
 if(kind==='state')g.state='BASELINE_REQUIRED'
 if(kind==='origin')a.activation.forecast_from_date='2026-10-23'
 if(kind==='guard')g.policy_unchanged=false
 if(kind==='reason')g.reason='ACTIVATION_POLICY_CHANGED'
 if(kind==='method')a.activation.selected_model!.method='SES'
 if(kind==='params')Object.assign(a.activation.forecast!.params,{alpha:'0.9'})
 if(kind==='vector')a.activation.forecast!.forecasts.pop()
 if(kind==='decimal')a.activation.forecast!.forecasts[0]='1e2'
 if(kind==='holdout')e.evaluation!.holdout.used_for_selection=true
 if(kind==='fold')e.evaluation!.challengers[0].summary.fold_count='2'
 if(kind==='extra')Object.assign(a,{unexpected:true})
 if(kind==='applied')r.forecast_applied=true
 expect(()=>parseModelV2Run(r,query,actor)).toThrow()
})
it('uses exact microseconds when retiring an evaluation after a clock anomaly',()=>{
 const r=structuredClone(wire.eligible);r.current_guard.checked_at=r.captured_at.slice(0,20)+(BigInt(r.captured_at.slice(20,26))-1n).toString().padStart(6,'0')+'Z';r.current_guard.reason='CURRENT_CLOCK_PRECEDES_EVALUATION';r.current_guard.state='BASELINE_REQUIRED'
 expect(parseModelV2Run(r,query,actor).eligibleNow).toBe(false)
})
it('binds storage to actor, method, UUID and exact payload, independently of v1',()=>{
 const r=request();persistModelV2Request(scope,r);expect(readModelV2Request(scope,actor).pending).toEqual(r)
 expect(()=>persistModelV2Request(scope,r)).toThrow();expect(readModelV2Request(scope,crypto.randomUUID()).error).not.toBe('')
 expect(()=>clearModelV2Request(scope,{...r,query:{...query,horizon_days:'8'}})).toThrow()
 expect(()=>parseModelV2Request({...r,method:'erp_cp7_capture_model_evaluation_v1'},actor)).toThrow()
 clearModelV2Request(scope,r);expect(readModelV2Request(scope,actor).pending).toBeNull()
 localStorage.setItem(modelV2RequestKey(scope),'broken');expect(readModelV2Request(scope,actor).error).not.toBe('')
})
it('verifies durable storage, sends exact capture and checks immutable reread',async()=>{
 vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{});expect(()=>persistModelV2Request(scope,request())).toThrow();vi.restoreAllMocks()
 const rpc=vi.fn().mockResolvedValueOnce({data:wire.eligible,error:null}).mockResolvedValueOnce({data:wire.withdrawn,error:null})
 const old=await captureModelV2({rpc},request());expect(rpc.mock.calls[0]).toEqual([modelV2Method,{p_query:query,p_request:request().requestId}]);expect((await readModelV2({rpc},old)).eligibleNow).toBe(false)
 expect(rpc.mock.calls[1]).toEqual(['erp_cp7_read_model_evaluation_v2',{p_run:wire.eligible.run_id}])
})
