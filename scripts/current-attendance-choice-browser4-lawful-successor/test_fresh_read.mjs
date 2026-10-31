// Request selection controls only, no real ERP or browser case credit.
import assert from 'node:assert/strict'
import test from 'node:test'
import {freshRead} from './fresh_read.mjs'
function answer(start,url='http://127.0.0.1:3000/rest/v1/rpc/read',method='POST'){
 const request={method:()=>method,url:()=>url,timing:()=>({startTime:start})}
 return{request:()=>request,status:()=>200,json:async()=>({closed_through:start<1000?null:'2026-10-24'}),text:async()=>''}
}
test('queued old answer reproduces false closure while current helper selects the actual fresh request',async()=>{
 const older=answer(500),current=answer(1500);let click=false
 const page={evaluate:async operation=>{assert.equal(typeof operation,'function');return 1000},
  waitForResponse:predicate=>Promise.resolve([older,answer(1300,'http://127.0.0.1:3000/rest/v1/rpc/other'),answer(1400,undefined,'OPTIONS'),current].find(predicate))}
 assert.equal((await older.json()).closed_through,null)
 const chosen=await freshRead(page,'read',async()=>{click=true})
 assert.equal(click,true);assert.equal(chosen.response,current);assert.equal(chosen.request_started_at,1500)
 assert.equal(chosen.refresh_registered_at,1000);assert.equal((await chosen.response.json()).closed_through,'2026-10-24')
})
test('failed click and failed response remain the original errors',async()=>{
 const click=new Error('actual click failed'),network=new Error('actual response failed')
 const page={evaluate:async()=>1000,waitForResponse:()=>Promise.reject(network)}
 await assert.rejects(()=>freshRead(page,'read',async()=>{throw click}),e=>e===click)
 await assert.rejects(()=>freshRead(page,'read',async()=>{}),e=>e===network)
})
