// Read-only diagnosis around one actual existing UI command. No extra RPC,
// role, Native statement timeout, case assertion or execution credit.
import {spawn} from 'node:child_process'
import {createHash} from 'node:crypto'
import {mkdirSync,writeFileSync} from 'node:fs'
import {performance} from 'node:perf_hooks'

export function responseDiagnostic(status,body,elapsed,ready){
 const result={diagnostic_only:true,Native_exit_case_credit:0,status,UI_operation_response_elapsed_ms:Math.round(elapsed),instrument_ready:ready,query_claims_payload_headers_and_raw_error_emitted:false}
 if(status>=400){
  const bytes=Buffer.from(body,'utf8');let parsed;try{parsed=JSON.parse(body)}catch{}
  const code=parsed?.code
  result.error_utf8_bytes=bytes.length;result.opaque_error_sha256=createHash('sha256').update(bytes).digest('hex')
  result.server_code=typeof code==='string'&&/^(?:[A-Z0-9]{5}|PGRST[0-9]{3})$/.test(code)?code:null
  result.known_error_primary=parsed?.message==='canceling statement due to statement timeout'?'STATEMENT_TIMEOUT':null
 }
 return result
}

function wait(done,ms){return new Promise(resolve=>{const timer=setTimeout(()=>resolve(false),ms);done.then(()=>{clearTimeout(timer);resolve(true)})})}

export async function withActualHttpTrace(family,suffix,perform){
 if(!['F05_CAPTURE','F05_LOCAL_CLAIM'].includes(family)||!/^[A-Z_]+$/.test(suffix))throw Error('FIXED_DISPOSABLE_TRACE_TARGET_ONLY')
 let trace,closed=false,ready=false,done=Promise.resolve(),diagnostic
 try{
  trace=spawn('python',['../auditor/scripts/cp7_note_http_trace.py',suffix,family],{cwd:'../writer',stdio:['ignore','pipe','pipe']})
  done=new Promise(resolve=>{const finish=()=>{closed=true;resolve()};trace.once('exit',finish);trace.once('error',finish)})
  const available=new Promise(resolve=>{let output='';trace.stdout.on('data',bytes=>{output=(output+bytes.toString()).slice(-1024);if(output.includes('CP7_HTTP_TRACE_READY')){ready=true;resolve()}});trace.stderr.on('data',()=>{});done.then(resolve)})
  await wait(available,2000)
 }catch{closed=true}
 const started=performance.now()
 try{
  const response=await perform(),status=response.status();let body='',readable=true
  if(status>=400)try{body=await response.text()}catch{readable=false}
  diagnostic=responseDiagnostic(status,body,performance.now()-started,ready)
  if(!readable)diagnostic.error_body_readable=false
  return response
 }catch(error){
  diagnostic={diagnostic_only:true,Native_exit_case_credit:0,status:'NO_HTTP_RESPONSE',instrument_ready:ready,error_type:error?.constructor?.name??'Error',UI_operation_response_elapsed_ms:Math.round(performance.now()-started)}
  throw error
 }finally{
  try{if(trace&&!closed){trace.kill('SIGUSR1');if(!await wait(done,4000)){trace.kill('SIGTERM');if(!await wait(done,500)){trace.kill('SIGKILL');await wait(done,1000)}}}}catch{}
  try{if(diagnostic){mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync('cp6-proof/t3/'+family+'_'+suffix+'_HTTP_RESPONSE.json',JSON.stringify(diagnostic,null,2)+'\n')}}catch{}
 }
}
