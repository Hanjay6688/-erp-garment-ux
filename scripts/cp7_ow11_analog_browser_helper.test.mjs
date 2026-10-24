import assert from 'node:assert/strict'
import test from 'node:test'
import {setTimeout as delay} from 'node:timers/promises'
import {reply} from './cp7_ow11_analog_browser.mjs'

test('response timeout is caught while the browser click is still waiting',async()=>{
 const timeout=new Error('response timeout'),page={waitForResponse:async()=>{await delay(1);throw timeout}}
 let cleanup=false
 try{await assert.rejects(reply(page,()=>delay(20)),error=>error===timeout)}finally{cleanup=true}
 await delay(25)
 assert.equal(cleanup,true)
})
test('failed click does not leave the pending response rejection unobserved',async()=>{
 const click=new Error('target unavailable'),page={waitForResponse:async()=>{await delay(10);throw Error('late response timeout')}}
 await assert.rejects(reply(page,async()=>{throw click}),error=>error===click)
 await delay(20)
})
test('captures the exact response after action without altering status or body',async()=>{
 const args={p_request:'same-request'},body={selected:false,forecast_applied:false}
 const page={waitForResponse:async()=>({status:()=>200,request:()=>({postDataJSON:()=>args}),json:async()=>body})}
 assert.deepEqual(await reply(page,async()=>{}),{status:200,args,body})
})
