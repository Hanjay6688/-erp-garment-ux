// @vitest-environment jsdom
import {beforeEach,it,expect,vi} from 'vitest'
import wire from '../tests/fixtures/nativeScopedModelSql.json'
import {parseNativeDemandHistory} from './nativeDemandHistory'
import {parseModelQuery} from './nativeModelEvaluation'
import {parseModelV2Run} from './nativeModelEvaluationV2'
import {parseScopedHistoryQuery,parseScopedHistoryRun,parseScopedModelRun,scopedHistoryMethod,scopedModelMethod,scopedHistoryRecovery,scopedModelRecovery,captureScopedHistory,captureScopedModel,readScopedModel,readScopedHistory} from './nativeScopedModel'
const scope='disposable:scoped',actor=wire.actor,q=parseScopedHistoryQuery(wire.history.query),mq=parseModelQuery(wire.model.query)
const historyRequest=()=>({requestId:wire.history.request_id,actor,method:scopedHistoryMethod,query:q})
const modelRequest=()=>({requestId:wire.model.request_id,actor,method:scopedModelMethod,query:mq})
beforeEach(()=>{localStorage.clear();vi.restoreAllMocks()})
it('reads actual scoped SQL history and retained evaluation without a global history capture',()=>{
 expect(wire.actual_SQL).toBe(true);expect(wire.actual_Native_capture).toBe(false)
 const h=parseScopedHistoryRun(wire.history,q,actor),m=parseScopedModelRun(wire.model,mq,actor)
 expect(h.history.rows).toHaveLength(1);expect(h.history.rows[0].targetKey).toBe(q.target_key)
 expect(m.knownAt).toBe(h.history.capturedAt);expect(m.eligibleNow).toBe(false)
 expect(m.runtime).toBe('SCOPED_V3');expect(m.admittedAtCapture).toBe(false)
 expect(()=>parseNativeDemandHistory({...wire.history.history,run_id:h.runId,request_id:h.requestId,source_state:'UNCHANGED'})).toThrow()
 expect(()=>parseModelV2Run(wire.model,mq,actor)).toThrow()
})
it('preserves the original assessment when actual controlled source changes',()=>{
 const query=parseModelQuery(wire.beforeSourceChange.query),old=parseScopedModelRun(wire.beforeSourceChange,query,actor)
 const next=parseScopedModelRun(wire.afterSourceChange,query,actor,old)
 expect(next.immutableSignature).toBe(old.immutableSignature);expect(next.reason).toBe('NATIVE_HISTORY_SOURCE_CHANGED')
 const changed=structuredClone(wire.afterSourceChange);changed.assessment.source.product_name='changed'
 expect(()=>parseScopedModelRun(changed,query,actor,old)).toThrow()
})
it.each(['actor','target','scope','producer','clock','hash','state','guard','empty','multiple','extra','applied']as const)('rejects contradictory scoped history %s',kind=>{
 const r=structuredClone(wire.history)
 if(kind==='actor')r.actor_scope_id=crypto.randomUUID()
 if(kind==='target')r.query.target_key=crypto.randomUUID()+':'+crypto.randomUUID()
 if(kind==='scope')r.history.scope='GLOBAL_CURRENT_PHYSICAL_ROOTS'
 if(kind==='producer')r.history.versions.producer='native-demand-1'
 if(kind==='clock')r.history.training_known_at='2026-01-01T00:00:00.000000Z'
 if(kind==='hash')r.history.source_hash='0'.repeat(64)
 if(kind==='state')r.current_guard.source_state='ARCHIVED_STALE'
 if(kind==='guard')r.current_guard.live_source_hash='0'.repeat(64)
 if(kind==='empty')r.history.current_stock=[]
 if(kind==='multiple')r.history.current_stock.push(r.history.current_stock[0])
 if(kind==='extra')Object.assign(r,{unexpected:true})
 if(kind==='applied')r.production_go=true
 expect(()=>parseScopedHistoryRun(r,q,actor)).toThrow()
})
it.each(['contract','scope','actor','extra','assessment']as const)('rejects a misbound v3 envelope %s',kind=>{
 const r=structuredClone(wire.model)
 if(kind==='contract')r.contract_version='cp7.native-model-run.v2'
 if(kind==='scope')r.history_scope='GLOBAL_CURRENT_PHYSICAL_ROOTS'
 if(kind==='actor')r.actor_scope_id=crypto.randomUUID()
 if(kind==='extra')Object.assign(r,{unexpected:true})
 if(kind==='assessment')r.assessment.activation.source_hash='0'.repeat(64)
 expect(()=>parseScopedModelRun(r,mq,actor)).toThrow()
})
it('keeps exact actor, method, UUID and payload separately for history and model recovery',()=>{
 const h=historyRequest(),m={...modelRequest(),requestId:h.requestId}
 scopedHistoryRecovery.persist(scope,h);scopedModelRecovery.persist(scope,m)
 expect(scopedHistoryRecovery.read(scope,actor).pending).toEqual(h)
 expect(scopedModelRecovery.read(scope,actor).pending).toEqual(m)
 expect(scopedHistoryRecovery.read(scope,crypto.randomUUID()).error).not.toBe('')
 expect(()=>scopedModelRecovery.clear(scope,{...m,query:{...m.query,horizon_days:'8'}})).toThrow()
 expect(()=>scopedHistoryRecovery.persist(scope,h)).toThrow()
 scopedHistoryRecovery.clear(scope,h);expect(scopedModelRecovery.read(scope,actor).pending).toEqual(m)
 scopedModelRecovery.clear(scope,m)
 localStorage.setItem(scopedModelRecovery.key(scope),JSON.stringify({...m,method:'erp_cp7_capture_model_evaluation_v2'}))
 expect(scopedModelRecovery.read(scope,actor).error).not.toBe('')
})
it('refuses invalid period, unknown keys, unavailable storage and failed removal',()=>{
 expect(()=>parseScopedHistoryQuery({...q,through_date:'2027-10-01'})).toThrow()
 expect(()=>parseScopedHistoryQuery({...q,source_hash:'forged'})).toThrow()
 vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{});expect(()=>scopedHistoryRecovery.persist(scope,historyRequest())).toThrow()
 vi.restoreAllMocks();scopedHistoryRecovery.persist(scope,historyRequest())
 vi.spyOn(Storage.prototype,'removeItem').mockImplementation(()=>{});expect(()=>scopedHistoryRecovery.clear(scope,historyRequest())).toThrow()
})
it('sends exact RPC methods and preserves immutable reread binding',async()=>{
 const rpc=vi.fn().mockResolvedValueOnce({data:wire.history,error:null}).mockResolvedValueOnce({data:wire.history,error:null}).mockResolvedValueOnce({data:wire.model,error:null}).mockResolvedValueOnce({data:wire.model,error:null})
 const h=await captureScopedHistory({rpc},historyRequest());await readScopedHistory({rpc},h)
 const m=await captureScopedModel({rpc},modelRequest());await readScopedModel({rpc},m)
 expect(rpc.mock.calls.map(c=>c[0])).toEqual([scopedHistoryMethod,'erp_cp7_read_model_history_v1',scopedModelMethod,'erp_cp7_read_model_evaluation_v3'])
 expect(rpc.mock.calls[0][1]).toEqual({p_query:q,p_request:historyRequest().requestId})
 expect(rpc.mock.calls[2][1]).toEqual({p_query:mq,p_request:modelRequest().requestId})
 const wrong=structuredClone(wire.model);wrong.request_id=crypto.randomUUID()
 await expect(captureScopedModel({rpc:vi.fn().mockResolvedValue({data:wrong,error:null})},modelRequest())).rejects.toThrow()
})
