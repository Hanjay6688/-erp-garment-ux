// Retire answers to reads started before this explicit UI refresh.
// Real request/response identity is retained; no response or clock is replaced.
export async function freshRead(page,rpc,action){
 const notBefore=await page.evaluate(()=>Date.now())
 const pending=page.waitForResponse(response=>{
  const request=response.request()
  return request.method()==='POST'&&request.url().endsWith('/rpc/'+rpc)&&request.timing().startTime>=notBefore
 })
 void pending.catch(()=>{})
 await action()
 const response=await pending
 return{response,request_started_at:response.request().timing().startTime,refresh_registered_at:notBefore}
}
