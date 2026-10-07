// Passive evidence collection on a separate, explicitly bounded CDP session.
// Playwright's default inspector cache can evict a real large Original. These
// are diagnostic buffers only: no product, RPC, page or client cap is raised.
// A body is read from the original browser request, never by replaying an RPC.
export const P19_INSPECTOR_CAPTURE = Object.freeze({
 maxTotalBufferSize:256000000,maxResourceBufferSize:128000000,maxPostDataSize:64000,
})

export async function attachP19NetworkCapture(page,rpcs,network,pending,record){
 const session=await page.context().newCDPSession(page),requests=new Map()
 const failed=(r,error)=>network.push({rpc:r.rpc,request:r.request,timing:r.timing,status:r.status,recorder_error:String(error?.message??error).slice(0,500)})
 session.on('Network.requestWillBeSent',e=>{
  const rpc=rpcs.find(name=>e.request.url.endsWith('/rpc/'+name));if(!rpc||e.request.method!=='POST')return
  let request,error
  try{request=JSON.parse(e.request.postData);if(!request||typeof request!=='object')throw Error('P19_CAPTURE_REQUEST_BODY_REQUIRED')}
  catch(e){error=e}
  requests.set(e.requestId,{rpc,request,error,start:e.timestamp,status:null,timing:{startTime:e.wallTime*1000}})
 })
 session.on('Network.responseReceived',e=>{
  const r=requests.get(e.requestId);if(!r)return
  r.status=e.response.status;r.timing.responseStart=(e.timestamp-r.start)*1000
 })
 session.on('Network.loadingFinished',e=>{
  const r=requests.get(e.requestId);if(!r)return;requests.delete(e.requestId)
  r.timing.responseEnd=(e.timestamp-r.start)*1000
  const task=(async()=>{
   if(r.error)throw r.error
   if(r.status===null)throw Error('P19_CAPTURE_RESPONSE_METADATA_REQUIRED')
   const result=await session.send('Network.getResponseBody',{requestId:e.requestId})
   const body=Buffer.from(result.body,result.base64Encoded?'base64':'utf8')
   network.push(record(r,body))
  })().catch(error=>failed(r,error))
  pending.push(task)
 })
 session.on('Network.loadingFailed',e=>{
  const r=requests.get(e.requestId);if(!r)return;requests.delete(e.requestId)
  network.push({rpc:r.rpc,request:r.request,timing:r.timing,failed:e.errorText??'NETWORK_FAILED'})
 })
 try{await session.send('Network.enable',P19_INSPECTOR_CAPTURE)}
 catch(error){await session.detach().catch(()=>{});throw error}
 return{
  async flush(){
   let count
   do{count=pending.length;await Promise.all(pending)}while(pending.length!==count)
   const errors=network.filter(r=>r.recorder_error)
   if(errors.length)throw Error('P19_RESPONSE_CAPTURE_FAILED '+JSON.stringify(errors.map(r=>({rpc:r.rpc,error:r.recorder_error}))))
   if(requests.size)throw Error('P19_RESPONSE_CAPTURE_INCOMPLETE')
  },
  async close(){await session.detach().catch(()=>{})},
 }
}
