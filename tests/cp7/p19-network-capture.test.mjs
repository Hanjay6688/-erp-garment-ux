// @vitest-environment node
import {test,expect} from 'vitest'
import {EventEmitter} from 'node:events'
import {createHash} from 'node:crypto'
import {attachP19NetworkCapture,P19_INSPECTOR_CAPTURE} from '../../scripts/cp7_p19_network_capture.mjs'

const RPC='erp_cp7_read_staged_analysis_page_v1'
const sha=body=>createHash('sha256').update(body).digest('hex')
function setup({body='{"label":"Kain biru Rp16.000 — ukuran besar"}',base64=false,error=null,enableError=null}={}){
 const session=new EventEmitter(),calls=[],network=[],pending=[]
 session.send=async(method,args)=>{
  calls.push({method,args})
  if(method==='Network.enable'){if(enableError)throw enableError;return{}}
  if(method==='Network.getResponseBody'){if(error)throw error;return{body:base64?Buffer.from(body).toString('base64'):body,base64Encoded:base64}}
  throw Error('UNEXPECTED_RPC_REPLAY_OR_CDP_COMMAND '+method)
 }
 session.detach=async()=>{calls.push({method:'detach'})}
 const page={context:()=>({newCDPSession:async()=>session})}
 const record=(meta,body)=>({...meta,bytes:body.length,sha256:sha(body)})
 const request=(id='original',method='POST',rpc=RPC,postData='{"p_run":"same-run","p_index":3}')=>session.emit('Network.requestWillBeSent',{
  requestId:id,timestamp:10,wallTime:100,request:{method,url:'http://disposable.test/rpc/'+rpc,postData}})
 const finish=(id='original')=>{
  session.emit('Network.responseReceived',{requestId:id,timestamp:10.05,response:{status:200}})
  session.emit('Network.loadingFinished',{requestId:id,timestamp:10.1})
 }
 return{session,calls,network,pending,page,record,request,finish,body}
}

test.each([false,true])('records the exact original UTF-8 response through its own bounded CDP session (base64=%s)',async base64=>{
 const h=setup({base64}),capture=await attachP19NetworkCapture(h.page,[RPC],h.network,h.pending,h.record)
 h.request();h.finish();await capture.flush();await capture.close()
 expect(h.calls).toEqual([
  {method:'Network.enable',args:P19_INSPECTOR_CAPTURE},
  {method:'Network.getResponseBody',args:{requestId:'original'}},{method:'detach'},
 ])
 expect(h.network).toHaveLength(1)
 expect(h.network[0]).toMatchObject({rpc:RPC,request:{p_run:'same-run',p_index:3},status:200,bytes:Buffer.byteLength(h.body),sha256:sha(Buffer.from(h.body))})
 expect(h.network[0].timing.responseEnd).toBeCloseTo(100)
})

test('ignores CORS preflights and unrelated requests; does not demand their bodies or replay a public RPC',async()=>{
 const h=setup(),capture=await attachP19NetworkCapture(h.page,[RPC],h.network,h.pending,h.record)
 h.request('preflight','OPTIONS',RPC,undefined);h.finish('preflight')
 h.request('unrelated','POST','other_rpc');h.finish('unrelated')
 await capture.flush();await capture.close()
 expect(h.network).toEqual([])
 expect(h.calls.map(c=>c.method)).toEqual(['Network.enable','detach'])
})

test('evicted-body errors are retained and thrown by flush, allowing the caller to clean up; no missing-body credit',async()=>{
 const h=setup({error:Error('Request content was evicted from inspector cache')}),capture=await attachP19NetworkCapture(h.page,[RPC],h.network,h.pending,h.record)
 h.request();h.finish()
 try{await expect(capture.flush()).rejects.toThrow('P19_RESPONSE_CAPTURE_FAILED')}
 finally{await capture.close()}
 expect(h.network).toHaveLength(1)
 expect(h.network[0]).toMatchObject({rpc:RPC,recorder_error:'Request content was evicted from inspector cache'})
 expect(h.network[0].sha256).toBeUndefined()
 expect(h.calls.at(-1)).toEqual({method:'detach'})
})

test('in-flight evidence cannot pass and a genuine failed request is kept as a network refusal',async()=>{
 const h=setup(),capture=await attachP19NetworkCapture(h.page,[RPC],h.network,h.pending,h.record)
 h.request();await expect(capture.flush()).rejects.toThrow('P19_RESPONSE_CAPTURE_INCOMPLETE')
 h.session.emit('Network.loadingFailed',{requestId:'original',errorText:'net::ERR_CONNECTION_RESET'})
 await capture.flush();await capture.close()
 expect(h.network[0]).toMatchObject({rpc:RPC,failed:'net::ERR_CONNECTION_RESET'})
 expect(h.network[0].sha256).toBeUndefined()
})

test('detaches the evidence session when enabling its diagnostic buffers fails',async()=>{
 const h=setup({enableError:Error('CDP closed')})
 await expect(attachP19NetworkCapture(h.page,[RPC],h.network,h.pending,h.record)).rejects.toThrow('CDP closed')
 expect(h.calls.at(-1)).toEqual({method:'detach'})
})
