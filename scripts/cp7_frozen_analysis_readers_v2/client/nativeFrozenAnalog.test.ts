import {expect,it,vi} from 'vitest'
import preparedSQL from '../reader.prepared.sql?raw'
import {parseAnalogCandidates,readProductAnalogCandidates,type AnalogReadContext} from '../../../src/nativeProductAnalog'
import {analogContext,analogReply} from '../../../tests/fixtures/nativeProductAnalog'
import demand from '../../../tests/fixtures/nativeTargetDemandSql.json'
import {readFrozenAnalogCandidates} from './nativeFrozenAnalog'

function fixture(){
 const c:AnalogReadContext={...analogContext(),sourceMethod:'FROZEN_V2',targetKey:demand.analog.target_key,query:{...demand.analog.query,group_mode:'AS_SOLD'},reference:{...analogContext().reference,capturedAt:demand.analog.captured_at}}
 const reply={...analogReply(c),contract_version:'cp7.product-analog-candidates-read.v3',bounded_request_contract:'cp7.bounded-analysis-request.v2',bounded_reference_contract:'cp7.bounded-analysis-reference.v2',consumer_capability:'REVIEWED_ANALOG_FOR_FRESH_CAPTURES',target_demand:structuredClone(demand.analog)}
 return{c,reply}
}
it('calls only the explicit frozen reader with exact SQL named arguments and retains demand provenance',async()=>{
 const{c,reply}=fixture(),rpc=vi.fn(async(_name:string,_args:object)=>({data:reply,error:null}))
 const expected=preparedSQL.match(/create function public\.erp_cp7_read_product_analog_candidates_v2\(([^)]+)\)/)![1].split(',').map(v=>v.trim().split(/\s+/)[0]).sort()
 const parsed=await readFrozenAnalogCandidates({rpc},c)
 expect(rpc).toHaveBeenCalledWith('erp_cp7_read_product_analog_candidates_v2',{p_request:c.requestId,p_target:c.targetKey,p_offset:0,p_limit:50,p_access:c.accessEpoch})
 expect(Object.keys(rpc.mock.calls[0]![1] as object).sort()).toEqual(expected)
 expect(parsed.sourceMethod).toBe('FROZEN_V2');expect(parsed.targetDemand?.targetPcs).toBe('1');expect(parsed.rows[0].mean).toBe('0.000000000000')
})
it.each(['oldContext','missingRequest','oldRequest','missingReference','oldReference','oldResponse','missingDemand','producer','epoch','clock','ownHistory','foreignTarget']as const)('refuses frozen %s mismatch without promoting old inputs',key=>{
 const{c,reply}=fixture(),r:Record<string,any>=reply
 if(key==='oldContext')delete c.sourceMethod
 if(key==='missingRequest')delete r.bounded_request_contract
 if(key==='oldRequest')r.bounded_request_contract='cp7.bounded-analysis-request.v1'
 if(key==='missingReference')delete r.bounded_reference_contract
 if(key==='oldReference')r.bounded_reference_contract='cp7.bounded-analysis-reference.v1'
 if(key==='oldResponse')r.contract_version='cp7.product-analog-candidates-read.v2'
 if(key==='missingDemand')delete r.target_demand
 if(key==='producer')r.producer_hash='invalid'
 if(key==='epoch')r.access_epoch='9'.repeat(64)
 if(key==='clock')r.result.source_captured_at=r.result.source_captured_at.replace('123456','123457')
 if(key==='ownHistory')r.target_demand.own_total_pcs='1'
 if(key==='foreignTarget')r.target_demand.target_key=r.target_demand.analog.source_key
 expect(()=>parseAnalogCandidates(r,c,0)).toThrow()
})
it('rejects pagination across explicit methods even when all other bindings match',()=>{
 const{c,reply}=fixture(),oldContext={...c};delete oldContext.sourceMethod
 const oldReply:Record<string,unknown>={...reply,contract_version:'cp7.product-analog-candidates-read.v2'}
 delete oldReply.bounded_request_contract;delete oldReply.bounded_reference_contract
 const frozen=parseAnalogCandidates(reply,c,0),old=parseAnalogCandidates(oldReply,oldContext,0)
 expect(()=>parseAnalogCandidates(reply,c,0,old)).toThrow()
 expect(()=>parseAnalogCandidates(oldReply,oldContext,0,frozen)).toThrow()
 expect(()=>parseAnalogCandidates(reply,c,0,frozen)).not.toThrow()
})
it('refuses a frozen context on the old RPC and an old context on the new RPC before network work',async()=>{
 const{c}=fixture(),rpc=vi.fn(async()=>({data:null,error:null}))
 await expect(readProductAnalogCandidates({rpc},c)).rejects.toThrow()
 delete c.sourceMethod
 await expect(readFrozenAnalogCandidates({rpc},c)).rejects.toThrow()
 expect(rpc).not.toHaveBeenCalled()
})
it('propagates current server access errors instead of parsing or falling back to the old reader',async()=>{
 const{c}=fixture(),error={code:'42501'},rpc=vi.fn(async()=>({data:null,error}))
 await expect(readFrozenAnalogCandidates({rpc},c)).rejects.toBe(error)
 expect(rpc).toHaveBeenCalledTimes(1)
})
