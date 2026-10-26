// Server-shaped manifest/segment/job bodies built from an exact Original, with
// the same 2,000,000-code-point cut and SHA256 values the SQL layer stores.
const bytes=(text:string)=>new TextEncoder().encode(text)
export const sha=async(text:string)=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes(text))),b=>b.toString(16).padStart(2,'0')).join('')
export async function transport(original:Record<string,unknown>,sourceState:'UNCHANGED'|'ARCHIVED_STALE'='UNCHANGED'){
 const body=JSON.stringify(original),chars=Array.from(body),n=2000000,count=Math.ceil(chars.length/n)
 const parts=Array.from({length:count},(_,i)=>chars.slice(i*n,(i+1)*n).join(''))
 const hashes=await Promise.all(parts.map(sha)),whole=await sha(body)
 const manifest={contract_version:'cp7.native-analysis-manifest.v1',run_id:original.run_id,request_id:original.request_id,source_state:sourceState,access_epoch:'a'.repeat(64),
  document:{utf8_bytes:bytes(body).byteLength,characters:chars.length,sha256:whole,segment_count:count,segment_characters:n},apply_enabled:false,production_go:false}
 const segment=(i:number)=>({contract_version:'cp7.native-analysis-segment.v1',run_id:original.run_id,index:i,segment_count:count,document_sha256:whole,
  document_utf8_bytes:manifest.document.utf8_bytes,utf8_bytes:bytes(parts[i]).byteLength,sha256:hashes[i],body:parts[i]})
 return{manifest,segment,parts,body}
}
export function job(requestId:string,query:unknown,state:'WAITING'|'RUNNING'|'DONE'|'FAILED',runId:string|null=null,extra:Record<string,unknown>={}){
 const finished=state==='DONE'||state==='FAILED'
 return{contract_version:'cp7.native-analysis-job.v1',request_id:requestId,query,state,requested_at:'2026-10-06T12:00:00.000000Z',started_at:'2026-10-06T12:00:00.000000Z',
  finished_at:finished?'2026-10-06T12:00:05.000000Z':null,attempts:1,run_id:state==='DONE'?runId:null,
  failure:state==='FAILED'?{sqlstate:'57014',code:'CP7_ANALYSIS_JOB_STOPPED'}:null,apply_enabled:false,production_go:false,...extra}
}
