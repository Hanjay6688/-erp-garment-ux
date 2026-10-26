// Preparation only. No production UI imports or default RPC registration.
import {parseAnalogCandidates,type AnalogReadContext,type AnalogCandidates} from '../../../src/nativeProductAnalog'

type Client={rpc(name:'erp_cp7_read_product_analog_candidates_v2',args:{p_request:string;p_target:string;p_offset:number;p_limit:50;p_access:string}):PromiseLike<{data:unknown;error:unknown}>}

export async function readFrozenAnalogCandidates(client:Client,context:AnalogReadContext,offset=0,previous?:AnalogCandidates){
 if(context.sourceMethod!=='FROZEN_V2'||!Number.isSafeInteger(offset)||offset<0||offset>5000)throw Error('Acuan pembanding beku belum lengkap.')
 const reply=await client.rpc('erp_cp7_read_product_analog_candidates_v2',{p_request:context.requestId,p_target:context.targetKey,p_offset:offset,p_limit:50,p_access:context.accessEpoch})
 if(reply.error)throw reply.error
 return parseAnalogCandidates(reply.data,context,offset,previous)
}
