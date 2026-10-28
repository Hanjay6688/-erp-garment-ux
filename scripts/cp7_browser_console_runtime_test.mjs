// Actual Chromium instrumentation checks only: no ERP, Auth or database credit.
import assert from 'node:assert/strict'
import {before,after,test} from 'node:test'
import {createServer} from 'node:http'
import {once} from 'node:events'
import {readFile,mkdir,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import {join} from 'node:path'
import {chromium} from '@playwright/test'
import {observeConsole,requireConsoleEvidence} from './current-finance-combined-browser-qualification/console_evidence.mjs'

const directory=process.env.B_BROWSER_EVIDENCE_DIRECTORY??'test-results/b-browser-console-runtime'
const report={classification:'ACTUAL_CHROMIUM_TOOLING_ONLY_NO_ERP_AUTH_OR_DATABASE',status:'INCOMPLETE',
 candidate_commit:process.env.GITHUB_SHA??null,cases:[],failures:[],ERP_cases:0,Auth_cases:0,database_connections:0,
 production_go:false,independent_acceptance:false}
let browser,server,origin
before(async()=>{
 try{
  await mkdir(directory,{recursive:true})
  const config=JSON.parse(await readFile('scripts/current-finance-combined-browser-qualification/CONFIG.json','utf8'))
  assert.equal(config.allow_database_execution,false);assert.equal(config.accepted_combined,null)
  report.backend_gate_closed=true
  const paths=['package-lock.json','scripts/cp7_browser_console_runtime_test.mjs','scripts/current-finance-combined-browser-qualification/console_evidence.mjs']
  report.sources=Object.fromEntries(await Promise.all(paths.map(async path=>[path,createHash('sha256').update(await readFile(path)).digest('hex')])))
  server=createServer((request,response)=>{
   if(request.url==='/denied'){response.writeHead(403,{'Content-Type':'application/json'});response.end('{"tool_fixture":"denied"}');return}
   if(request.url==='/missing'){response.writeHead(404);response.end('tool fixture missing');return}
   response.writeHead(200,{'Content-Type':'text/html'});response.end('<!doctype html><link rel="icon" href="data:,"><title>Console instrumentation fixture</title>Browser tooling only')
  })
  server.listen(0,'127.0.0.1');await once(server,'listening');origin='http://127.0.0.1:'+server.address().port
  browser=await chromium.launch();report.chromium_version=browser.version()
 }catch(error){report.failures.push({stage:'SETUP',error:String(error.stack)});throw error}
},{timeout:60000})

for(const mobile of[false,true])test(mobile?'real Chromium mobile console evidence':'real Chromium desktop console evidence',{timeout:30000},async()=>{
 const observed={viewport:mobile?{width:390,height:844}:{width:1440,height:1000},status:'INCOMPLETE',observations:[]}
 let context,capture
 try{
  context=await browser.newContext({viewport:observed.viewport,isMobile:mobile,hasTouch:mobile})
  const page=await context.newPage();page.setDefaultTimeout(5000)
  capture=observeConsole(page);await page.goto(origin)
  const since=()=>capture.errors.length
  const trigger=async(action,url)=>{
   const event=page.waitForEvent('console',{predicate:m=>m.type()==='error'&&m.location().url===url})
   await action();await event
  }
  let start=since()
  const appEvent=page.waitForEvent('console',{predicate:m=>m.type()==='error'&&m.text()==='B_CONSOLE_TOOL_APPLICATION_ERROR'})
  await page.evaluate(()=>console.error('B_CONSOLE_TOOL_APPLICATION_ERROR'));await appEvent
  const application=capture.errors.slice(start)
  assert.equal(application.length,1);assert.throws(()=>requireConsoleEvidence(application,[]),/UNEXPECTED_BROWSER_CONSOLE_ERROR/)
  observed.observations.push({case:'REAL_APPLICATION_CONSOLE_ERROR_REJECTED',errors:application})

  const lost=origin+'/lost',lostExpected={url:lost,text:'Failed to load resource: net::ERR_FAILED',reason:'deliberately aborted tooling response'}
  await page.route(lost,route=>route.abort('failed'))
  start=since();await trigger(()=>page.evaluate(url=>fetch(url).catch(()=>null),lost),lost)
  const aborted=capture.errors.slice(start);assert.equal(aborted.length,1)
  observed.observations.push({case:'REAL_ABORT_MESSAGE_AND_URL_MATCH',proof:requireConsoleEvidence(aborted,[lostExpected])})
  assert.throws(()=>requireConsoleEvidence(aborted,[{...lostExpected,url:origin+'/different'}]),/UNEXPECTED_BROWSER_CONSOLE_ERROR/)
  observed.observations.push({case:'WRONG_EXPECTED_URL_REFUSED'})

  start=since();const denied=origin+'/denied'
  await trigger(()=>page.evaluate(async url=>(await fetch(url)).status,denied),denied)
  const deniedErrors=capture.errors.slice(start);assert.equal(deniedErrors.length,1)
  observed.observations.push({case:'REAL_HTTP403_MESSAGE_AND_URL_MATCH',proof:requireConsoleEvidence(deniedErrors,[{url:denied,text:'Failed to load resource: the server responded with a status of 403 (Forbidden)',reason:'tooling server returns actual403'}])})

  start=since();const missing=origin+'/missing'
  await trigger(()=>page.evaluate(async url=>(await fetch(url)).status,missing),missing)
  const missingErrors=capture.errors.slice(start);assert.equal(missingErrors.length,1)
  assert.throws(()=>requireConsoleEvidence(missingErrors,[]),/UNEXPECTED_BROWSER_CONSOLE_ERROR/)
  observed.observations.push({case:'REAL_UNEXPECTED_HTTP404_REJECTED',errors:missingErrors})

  start=since()
  for(let i=0;i<2;i++)await trigger(()=>page.evaluate(url=>fetch(url).catch(()=>null),lost),lost)
  const duplicate=capture.errors.slice(start);assert.equal(duplicate.length,2)
  assert.throws(()=>requireConsoleEvidence(duplicate,[lostExpected]),/UNEXPECTED_BROWSER_CONSOLE_ERROR/)
  observed.observations.push({case:'ONE_ALLOWANCE_CANNOT_HIDE_TWO_REAL_ERRORS',errors:duplicate})
  assert.equal(observed.observations.length,6)
  capture.stop();assert.equal(page.listenerCount('console'),0)
  observed.listener_removed=true;observed.status='PASS'
 }catch(error){observed.error=String(error.stack);report.failures.push({stage:mobile?'MOBILE':'DESKTOP',error:observed.error});throw error}
 finally{observed.all_console_errors=capture?.errors??[];capture?.stop();await context?.close();report.cases.push(observed)}
})

after(async()=>{
 try{await browser?.close();if(server)await new Promise((resolve,reject)=>server.close(error=>error?reject(error):resolve()))}
 catch(error){report.failures.push({stage:'CLEANUP',error:String(error.stack)});throw error}
 finally{
  report.status=report.failures.length===0&&report.cases.length===2&&report.cases.every(c=>c.status==='PASS')?'PASS':'INCOMPLETE'
  await writeFile(join(directory,'BROWSER_CONSOLE_RUNTIME.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'})
 }
},{timeout:15000})
