// Extend B's existing actual-component fixture runner; no actual Auth, SDK or DB.
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import {execFileSync} from 'node:child_process'
import {chromium} from '@playwright/test'
import {server,stopAll,children} from '../ui-reference/connected-ui/server.mjs'
import {readable} from '../current-ui-sku-reader-integration-preparation/contrast.mjs'
const out=path.resolve(process.env.UI_PROOF_DIR??'../ui-refusal-browser-proof');fs.mkdirSync(out,{recursive:false})
const require=(ok,message)=>{if(!ok)throw Error(message)},sha=b=>crypto.createHash('sha256').update(b).digest('hex')
const ID='11111111-1111-4111-8111-111111111111'
const readers={workspace:'erp_get_pocket_fabric_workspace_v1','period-page':'erp_get_pocket_periods_v1','period-preview':'erp_preview_pocket_fabric_period_v1'}
const cases=[]
for(const width of [320,390,768,1440])for(const status of [401,403])for(const target of Object.keys(readers))cases.push({kind:'read',target,status,width})
for(const width of [390,1440])for(const status of [401,403])cases.push({kind:'recovery',target:'workspace',status,width})
const key=c=>`${c.kind}/${c.target}/${c.status}/${c.width}`
const report={contract:'cp7.B.real-component-source-refusal-browser.v1',source:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),cases:[],screenshots:[],failures:[],console_errors:[],external_network:[],actual_Auth:0,actual_SQL:0,actual_financial_backend:0,backend_idempotence_claim:false,production_go:false,independent_acceptance:false,status:'INCOMPLETE'}
if(process.env.GITHUB_SHA)require(report.source===process.env.GITHUB_SHA,'EXACT_SOURCE_REQUIRED')
const flush=()=>fs.writeFileSync(path.join(out,'SOURCE_REFUSAL_BROWSER.json'),JSON.stringify(report,null,2)+'\n')
const envelope=page=>page.evaluate(()=>window.__writerBUI.recovery().pending.POCKET_FABRIC??null)
const saves=page=>page.evaluate(()=>window.__writerBUI.calls.filter(c=>c.name.startsWith('erp_save_')))
let browser
async function take(page,c,stage){
 await page.evaluate(()=>document.fonts.ready)
 const name=`${c.kind}-${c.target}-${c.status}-${c.width}-${stage}.png`
 await page.screenshot({path:path.join(out,name),fullPage:true,animations:'disabled'})
 const b=fs.readFileSync(path.join(out,name)),shot={case:key(c),stage,name,bytes:b.length,sha256:sha(b)};report.screenshots.push(shot)
 const observed=await page.evaluate(()=>({width:innerWidth,document:document.documentElement.scrollWidth,identity:window.__writerBUI.identityStatus(),violations:window.__writerBUI.violations,probe:window.__writerBUI.probeMeta(),caption_boxes:[...document.querySelectorAll('.initial-import-table')].flatMap(panel=>{const b=panel.getBoundingClientRect();return [...panel.children].filter(e=>e.matches('h2,p')).map(e=>{const r=e.getBoundingClientRect();return {tag:e.tagName,text:e.textContent.slice(0,80),left:r.left,right:r.right,panel_left:b.left,panel_right:b.right}})})}))
 Object.assign(shot,{observed});require(observed.width===c.width&&observed.document<=c.width,'DOCUMENT_OVERFLOW:'+name)
 require(observed.identity==='AUTHORIZED'&&observed.violations.length===0,'PROVIDER_OR_TRANSPORT_CHANGED:'+name)
 require(observed.caption_boxes.length===4&&observed.caption_boxes.every(c=>c.left>=c.panel_left-1&&c.right<=c.panel_right+1),'HISTORY_CAPTIONS_MUST_STAY_VISIBLE_DURING_TABLE_SCROLL:'+name)
 const contrast=await readable(page.locator('.fixture-workspace'))
 Object.assign(shot,{minimum_contrast:Math.min(...contrast.rows.map(r=>r.ratio)),text_nodes:contrast.rows.length,inactive_control_exemptions:contrast.exempt.length})
 flush()
}
async function prepare(page){
 await page.waitForFunction(()=>{const s=document.querySelector('[aria-label="Roll kain kantong"]');return s&&!s.disabled&&s.options.length>1})
 await page.getByLabel('Roll kain kantong',{exact:true}).selectOption(ID+':'+ID)
 await page.getByLabel('Jumlah kain kantong',{exact:true}).fill('15')
 await page.getByLabel('Tanggal pengurangan',{exact:true}).fill('2026-09-21')
 require((await page.locator('.fixture-workspace').textContent()).includes('11,25'),'REAL_WORKSPACE_HPP_MUST_BE_PRESENT_BEFORE_REFUSAL')
}
async function arm(page){await page.evaluate(()=>{window.__writerBUI.refuseRead();const u=new URL(location.href);u.searchParams.set('start_refused','1');history.replaceState({},'',u)})}
async function retired(page,c){
 await page.getByRole('alert').filter({hasText:c.status===401?/Sesi berakhir/:/Akun tidak memiliki izin/}).first().waitFor()
 const text=await page.locator('.fixture-workspace').textContent()
 require(!text.includes('KKT-FIXTURE')&&!text.includes('11,25')&&!text.includes('Stok tercatat:'),'PROTECTED_SOURCE_FACTS_MUST_RETIRE')
 require(!text.includes('0 dari 0 alokasi'),'UNAVAILABLE_ALLOCATION_COUNT_IS_NOT_ZERO')
 require(await page.getByRole('button',{name:'Sahkan pembatalan alokasi',exact:true}).count()===0,'CACHED_CANCELLATION_MUST_RETIRE')
 require(await page.getByRole('button',{name:'Sahkan pengurangan stok',exact:true}).isDisabled(),'POST_MUST_REMAIN_LOCKED')
 require(await page.evaluate(()=>window.__writerBUI.identityStatus())==='AUTHORIZED','PROVIDER_MUST_REMAIN_AUTHORIZED')
}
try{
 const running=await server(process.cwd(),4188,'source-refusal',out)
 browser=await chromium.launch({headless:true})
 for(const c of cases){
  const started=performance.now(),context=await browser.newContext({viewport:{width:c.width,height:980},locale:'id-ID',timezoneId:'Asia/Jakarta',reducedMotion:'reduce'}),page=await context.newPage();page.setDefaultTimeout(10000)
  page.on('pageerror',e=>report.failures.push({case:key(c),page_error:e.message}))
  page.on('console',m=>{if(m.type()==='error')report.console_errors.push({case:key(c),text:m.text()})})
  page.on('response',r=>{if(r.status()>=400)report.failures.push({case:key(c),http:r.status(),path:new URL(r.url()).pathname})})
  await context.route('**/*',route=>{const u=new URL(route.request().url());if(['data:','blob:'].includes(u.protocol)||u.origin===running.url)return route.continue();report.external_network.push({case:key(c),host:u.host,path:u.pathname});return route.abort('blockedbyclient')})
  try{
   const failBefore=report.failures.length,consoleBefore=report.console_errors.length
   const params=new URLSearchParams({form:'pocket',state:'ready',refusal_probe:'1',probe_case:c.kind,probe_target:c.target,probe_status:String(c.status)})
   await page.goto(running.url+'/scripts/ui-reference/connected-ui/fixture.html?'+params,{waitUntil:'networkidle'})
   require(report.failures.length===failBefore&&report.console_errors.length===consoleBefore,'FIXTURE_BOOTSTRAP_FAILED')
   await prepare(page)
   let pending
   if(c.kind==='recovery'){
    const b=page.getByRole('button',{name:'Sahkan pengurangan stok',exact:true});require(await b.isEnabled(),'REVIEWED_POST_MUST_BE_VALID')
    await b.evaluate(e=>{e.click();e.click()})
    await page.waitForFunction(()=>Boolean(window.__writerBUI.recovery().pending.POCKET_FABRIC)&&window.__writerBUI.calls.filter(c=>c.name.startsWith('erp_save_')).length===1)
    await page.getByRole('button',{name:'Muat ulang',exact:true}).waitFor();await page.waitForFunction(()=>[...document.querySelectorAll('button')].some(b=>b.textContent.trim()==='Muat ulang'&&!b.disabled))
    pending=await envelope(page);const writes=await saves(page)
    require(writes.length===1&&writes[0].args.p_client_request_id===pending.id,'ONE_WRITE_AND_MATCHING_REAL_ENVELOPE_UUID')
    await page.getByRole('button',{name:'Reconcile transaksi',exact:true}).waitFor({state:'visible'})
   }else if(c.target==='workspace'){
    await page.getByRole('button',{name:'Batalkan alokasi 2026-09-01',exact:true}).click()
    await page.getByRole('button',{name:'Sahkan pembatalan alokasi',exact:true}).waitFor({state:'visible'})
   }else if(c.target==='period-preview'){
    await page.getByLabel('Awal periode kain kantong',{exact:true}).fill('2026-09-01');await page.getByLabel('Akhir periode kain kantong',{exact:true}).fill('2026-09-20')
   }
   await take(page,c,'before')
   const callsBefore=await page.evaluate(name=>window.__writerBUI.calls.filter(c=>c.name===name).length,readers[c.target])
   await arm(page)
   await page.getByRole('button',{name:c.target==='workspace'?'Muat ulang':c.target==='period-page'?'Muat periode berikutnya':'Lihat pembagian',exact:true}).click()
   await page.getByRole('alert').filter({hasText:c.status===401?/Sesi berakhir/:/Akun tidak memiliki izin/}).first().waitFor()
   await take(page,c,'after');await retired(page,c)
   require(await page.evaluate(name=>window.__writerBUI.calls.filter(c=>c.name===name).length,readers[c.target])===callsBefore+1,'EXACTLY_ONE_REFUSED_READ')
   if(c.kind==='recovery'){
    require(JSON.stringify(await envelope(page))===JSON.stringify(pending),'SOURCE_REFUSAL_MUST_NOT_CLEAR_OR_REWRITE_PENDING_ENVELOPE')
    require((await saves(page)).length===1,'SOURCE_REFUSAL_MUST_NOT_REPLAY_WRITE')
    await page.reload({waitUntil:'networkidle'})
    await page.getByRole('button',{name:'Reconcile transaksi',exact:true}).waitFor({state:'visible'})
    await page.getByRole('alert').filter({hasText:c.status===401?/Sesi berakhir/:/Akun tidak memiliki izin/}).first().waitFor()
    await take(page,c,'reopened');await retired(page,c)
    require(JSON.stringify(await envelope(page))===JSON.stringify(pending),'REOPEN_SAME_UUID_FINGERPRINT_AND_PAYLOAD')
    require((await saves(page)).length===0,'REOPEN_NO_AUTOMATIC_DUPLICATE_WRITE')
   }else require((await saves(page)).length===0,'READ_CASE_MUST_NOT_WRITE')
   require(report.failures.length===failBefore&&report.console_errors.length===consoleBefore,'BROWSER_ERROR_DURING_CASE')
   report.cases.push({...c,key:key(c),source_status:c.status,status:'PASS',seconds:Number(((performance.now()-started)/1000).toFixed(3)),pending_uuid:pending?.id??null,pending_payload_preserved:Boolean(pending),automatic_replay:0})
   console.log(JSON.stringify({completed:report.cases.length,total:28,case:key(c)}));flush()
  }catch(error){report.failures.push({case:key(c),error:error.stack});try{await page.screenshot({path:path.join(out,'FAILED-'+key(c).replaceAll('/','-')+'.png'),fullPage:true})}catch{}flush();if(report.failures.length>=3)throw Error('THREE_FAILURES_STOP_FOR_DIAGNOSIS')}
  finally{await context.close()}
 }
 require(report.cases.length===28&&new Set(report.cases.map(c=>c.key)).size===28&&cases.every(c=>report.cases.some(r=>r.key===key(c))),'EXACT_28_CASE_IDENTITIES')
 require(report.screenshots.length===60&&new Set(report.screenshots.map(s=>s.name)).size===60,'EXACT_60_SCREENSHOTS')
 require(report.failures.length===0&&report.console_errors.length===0&&report.external_network.length===0,'NO_BROWSER_ERRORS_OR_EXTERNAL_NETWORK')
 report.status='PASS_REAL_COMPONENT_BROWSER_WITH_DECLARED_DOUBLES_NOT_ACTUAL_AUTH_OR_BACKEND'
}catch(error){report.first_error=error.stack;process.exitCode=1}
finally{
 report.cleanup_errors=[]
 if(browser)try{await browser.close()}catch(e){report.cleanup_errors.push(String(e));process.exitCode=1}
 try{await stopAll();report.server_started=children.length>0;report.server_reaped=children.length>0}catch(e){report.cleanup_errors.push(String(e));process.exitCode=1}
 flush();console.log(JSON.stringify({status:report.status,completed:report.cases.length,screenshots:report.screenshots.length,failures:report.failures.length,server_reaped:report.server_reaped}))
}
