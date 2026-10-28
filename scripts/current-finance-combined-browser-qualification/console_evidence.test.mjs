import assert from 'node:assert/strict'
import {EventEmitter} from 'node:events'
import {test} from 'node:test'
import {observeConsole,requireConsoleEvidence} from './console_evidence.mjs'

const url='http://127.0.0.1:54321/rest/v1/rpc/example'
const message=(text,at=url)=>({text,location:{url:at,lineNumber:0,columnNumber:0}})
const text='Failed to load resource: net::ERR_FAILED'
const expected=[{url,text,reason:'deliberately lost committed reply'}]
test('listener retains every console error and detaches at cleanup',()=>{
 const page=new EventEmitter(),capture=observeConsole(page)
 page.emit('console',{type:()=> 'log',text:()=> 'ordinary log',location:()=>({url})})
 page.emit('console',{type:()=> 'error',text:()=> text,location:()=>({url})})
 assert.deepEqual(capture.errors,[{text,location:{url}}])
 capture.stop();assert.equal(page.listenerCount('console'),0)
})
test('only a recorded exact network failure is accepted and retained',()=>{
 const error=message(text),proof=requireConsoleEvidence([error],expected)
 assert.deepEqual(proof.observed,[error]);assert.equal(proof.expected_network_errors.length,1)
 assert.equal(proof.expected_network_errors[0].reason,expected[0].reason)
 assert.deepEqual(proof.unexpected_errors,[])
})
test('application errors and a different failed URL cannot hide behind expected loss',()=>{
 for(const error of [message('application bug'),message(text,url+'/other')])
  assert.throws(()=>requireConsoleEvidence([error],expected),/UNEXPECTED_BROWSER_CONSOLE_ERROR/)
})
test('one expected network event cannot excuse repeated console errors',()=>{
 assert.throws(()=>requireConsoleEvidence([message(text),message(text)],expected),/UNEXPECTED_BROWSER_CONSOLE_ERROR/)
 assert.throws(()=>requireConsoleEvidence([message(text)],[]),/UNEXPECTED_BROWSER_CONSOLE_ERROR/)
})
