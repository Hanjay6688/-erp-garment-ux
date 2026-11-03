/* Closed transport double; no SDK, credentials, HTTP or database connection. */
import {state,calls,violations} from './state'
import {ID,pocketData,importData,cutoverData,periodPreview} from './data'
const reads=new Set(['erp_get_pocket_fabric_workspace_v1','erp_preview_pocket_fabric_period_v1','erp_get_initial_import_workspace_v1','erp_cp7_get_cutover_v1'])
const writes=new Set(['erp_save_pocket_fabric_action_v1','erp_save_initial_import_action_v1'])
const held=()=>new Promise<never>(()=>{})
const client={rpc:async(name:string,args:Record<string,unknown>={})=>{
  calls.push({name,args:structuredClone(args)})
  if(!reads.has(name)&&!writes.has(name)){violations.push('UNDECLARED_RPC:'+name);throw Error('UNDECLARED_RPC:'+name)}
  if(writes.has(name)){
    if(state!=='pending'){violations.push('UNEXPECTED_WRITE:'+name);throw Error('UNEXPECTED_WRITE:'+name)}
    return held()
  }
  if(state==='loading')return held()
  if(state==='error')return {data:null,error:{code:'UI_FIXTURE_ERROR',message:'Pemuatan fixture sengaja gagal untuk pemeriksaan tampilan.',status:503}}
  if(name==='erp_get_pocket_fabric_workspace_v1')return {data:pocketData(state),error:null}
  if(name==='erp_preview_pocket_fabric_period_v1')return {data:periodPreview,error:null}
  if(name==='erp_cp7_get_cutover_v1')return {data:cutoverData,error:null}
  if(args.p_batch_id!==null&&args.p_batch_id!==undefined&&args.p_batch_id!==ID){violations.push('UNDECLARED_BATCH');throw Error('UNDECLARED_BATCH')}
  return {data:importData(state,args.p_batch_id===ID),error:null}
}}
export const getUatSupabaseClient=()=>client
