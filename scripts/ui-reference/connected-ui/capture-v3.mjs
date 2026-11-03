/* Continuation of B's existing browser/capture helpers; real components, fake transport only. */
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import {execFileSync} from 'node:child_process'
import {chromium} from '@playwright/test'
import {server,stopAll,children} from './server.mjs'
const out=path.resolve(process.env.UI_PROOF_DIR??'../ui-connected-proof')
const retained=JSON.parse(fs.readFileSync(path.join(out,'RETAINED_V2_VIEWS.json')))
const retainedKeys=new Set(retained.variants.map(v=>`${v.form}/${v.state}/${v.width}`))
const needed=(form,state,width)=>!retainedKeys.has(`${form}/${state}/${width}`)
const require=(ok,message)=>{if(!ok)throw Error(message)}
const sha=b=>crypto.createHash('sha256').update(b).digest('hex')
const config={forms:['pocket','import'],states:['ready','long','empty','loading','error','pending','denied','revoked'],widths:[320,390,768,1440]}
const report={contract:'cp7.B.actual-connected-component-visual-fixture.v1',source:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),variants:[...retained.variants],retained_evidence:retained.original,retained_views:52,fresh_views:0,failures:[],console_errors:[],requests:[],recoveries:[...retained.recoveries],actual_Auth_cases:0,actual_SQL_executed:0,actual_financial_backend_cases:0,production_go:false,independent_acceptance:false,status:'INCOMPLETE'}
if(process.env.GITHUB_SHA)require(report.source===process.env.GITHUB_SHA,'EXACT_SOURCE_REQUIRED')
const ID='11111111-1111-4111-8111-111111111111'
let browser,child
const flush=()=>fs.writeFileSync(path.join(out,'CONNECTED_UI_CAPTURE.json'),JSON.stringify(report,null,2)+'\n')
async function inspect(page){
  return page.evaluate(()=>{
    const rgb=value=>{const m=value.match(/^rgba?\(([^)]+)\)$/);return m?m[1].split(',').map(Number):null}
    const luminance=c=>c.slice(0,3).map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((n,x,i)=>n+x*[.2126,.7152,.0722][i],0)
    const background=element=>{
      let color=[255,255,255]
      const parents=[];for(let e=element;e;e=e.parentElement)parents.push(e)
      let uniform=true
      for(const e of parents.reverse()){
        const s=getComputedStyle(e);if(s.backgroundImage!=='none')uniform=false
        const c=rgb(s.backgroundColor)
        if(c){const a=c[3]??1;color=c.slice(0,3).map((v,i)=>v*a+color[i]*(1-a))}
      }
      return {color,uniform}
    }
    const selectors=['h1','.hero-copy p','.top-title strong','.top-title span','.panel h2','.panel p',
      '.initial-import h2','.initial-import p','.initial-import button','.initial-import label','.primary-btn','.soft-btn','input','select','textarea','.field > span','.submenu .sub-active','.nav-main.active',
      '.mobile-primary-nav button','.mandor-shop-dialog p','.mandor-shop-dialog button','.mandor-shop-card dd','.mandor-shop-card dt',
      '.cp7-card','.cp7-button','.cp7-sidebar nav button','.cp7-back','.cp7-brand span','.cp7-notice','.cp7-muted','.role-title','.access-mode-banner','.cfg-totals strong']
    const samples=[]
    for(const selector of selectors){
      const elements=[...document.querySelectorAll(selector)].filter(e=>{
        const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&r.right>0&&r.left<innerWidth&&getComputedStyle(e).visibility!=='hidden'
      }).slice(0,5)
      for(const e of elements){
        const s=getComputedStyle(e),fg=rgb(s.color),bg=background(e),box=e.getBoundingClientRect()
        const contrast=fg&&bg.uniform?(Math.max(luminance(fg),luminance(bg.color))+.05)/(Math.min(luminance(fg),luminance(bg.color))+.05):null
        samples.push({selector,text:(e.textContent||e.getAttribute('aria-label')||'').trim().slice(0,100),
          color:s.color,background:bg.color,uniform_background:bg.uniform,contrast,font_size:s.fontSize,
          width:box.width,height:box.height,disabled:e.matches(':disabled')})
      }
    }
    return {viewport:{width:innerWidth,height:innerHeight},body_width:document.body.scrollWidth,
      document_width:document.documentElement.scrollWidth,canvas:getComputedStyle(document.body).backgroundColor,
      sidebar:document.querySelector('.sidebar')?getComputedStyle(document.querySelector('.sidebar')).backgroundColor:null,
      page_overflow:Math.max(document.body.scrollWidth,document.documentElement.scrollWidth)>innerWidth+1,
      overflow_elements:[...document.querySelectorAll('.fixture-workspace *')].filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.right>innerWidth+1&&getComputedStyle(e).visibility!=='hidden'&&!e.closest('.responsive-table,.table-scroll,.cp7-table-scroll,.initial-import-table')}).slice(0,12).map(e=>({tag:e.tagName,cls:e.className,right:e.getBoundingClientRect().right})),
      samples,contrast_findings:samples.filter(s=>s.contrast!==null&&s.contrast<4.5)}
  })
}

async function take(page,form,state,width){
 if(!needed(form,state,width))return
 await page.evaluate(()=>document.fonts.ready)
 const name=`${form}-${state}-${width}.png`;await page.screenshot({path:path.join(out,name),fullPage:true,animations:'disabled'})
 const observations=await inspect(page),raw=fs.readFileSync(path.join(out,name))
 const calls=await page.evaluate(()=>window.__writerBUI.calls),violations=await page.evaluate(()=>window.__writerBUI.violations)
 require(violations.length===0,'CLOSED_FIXTURE_TRANSPORT:'+violations.join(','))
 report.fresh_views++
 report.variants.push({form,state,width,screenshot:{name,bytes:raw.length,sha256:sha(raw)},observations,calls,contract:'ACTUAL_CONNECTED_COMPONENT_WITH_DECLARED_AUTH_RPC_DOUBLES_NOT_BACKEND_ACCEPTANCE'})
 require(!observations.page_overflow,'NO_DOCUMENT_OVERFLOW:'+name)
 console.log(JSON.stringify({captured:report.variants.length,total:80,form,state,width,contrast:observations.contrast_findings.length}))
}
async function prepare(page,form){
 if(form==='pocket'){
  await page.waitForFunction(()=>{const s=document.querySelector('[aria-label="Roll kain kantong"]');return s&&!s.disabled&&s.options.length>1},undefined,{timeout:10000})
  await page.getByLabel('Roll kain kantong',{exact:true}).selectOption(ID+':'+ID)
  await page.getByLabel('Jumlah kain kantong',{exact:true}).fill('15')
  await page.getByLabel('Tanggal pengurangan',{exact:true}).fill('2026-09-21')
 }else{
  await page.waitForFunction(()=>{const s=document.querySelector('[aria-label="Batch impor"]');return s&&!s.disabled&&s.options.length>1},undefined,{timeout:10000})
  await page.getByLabel('Batch impor',{exact:true}).selectOption(ID)
  await page.getByLabel('Kode bahan, baris 2',{exact:true}).waitFor({state:'visible'})
 }
}
try{
 const running=await server(process.cwd(),4188,'connected',out);child=running.child
 browser=await chromium.launch({headless:true})
 for(const width of config.widths)for(const form of config.forms)for(const state of config.states){
  if(!needed(form,state,width)&&!(state==='ready'&&needed(form,form==='pocket'?'period-preview':'CSV-preview',width))&&!(state==='pending'&&needed(form,'pending-reopened',width)))continue
  const context=await browser.newContext({viewport:{width,height:980},locale:'id-ID',timezoneId:'Asia/Jakarta',reducedMotion:'reduce'}),page=await context.newPage();page.setDefaultTimeout(10000)
  page.on('pageerror',error=>report.failures.push({form,state,width,page_error:error.message}))
  page.on('console',message=>{if(message.type()==='error')report.console_errors.push({form,state,width,text:message.text()})})
  page.on('response',response=>{if(response.status()>=400)report.failures.push({form,state,width,http:response.status(),path:new URL(response.url()).pathname})})
  await context.route('**/*',route=>{const u=new URL(route.request().url());if(['data:','blob:'].includes(u.protocol)||u.origin===running.url)return route.continue();report.failures.push({external_network_refused:u.host+u.pathname});return route.abort('blockedbyclient')})
  try{
   const failuresBefore=report.failures.length,consoleBefore=report.console_errors.length
   await page.goto(running.url+'/scripts/ui-reference/connected-ui/fixture.html?form='+form+'&state='+state,{waitUntil:'networkidle'})
   require(report.failures.length===failuresBefore&&report.console_errors.length===consoleBefore,'FIXTURE_BOOTSTRAP_RESOURCE_ERROR')
   await page.locator('.fixture-workspace h1').waitFor({state:'visible'})
   if(['ready','long','pending','revoked'].includes(state))await prepare(page,form)
   if(state==='empty')await page.waitForFunction(()=>{const s=document.querySelector('select');return s&&!s.disabled},undefined,{timeout:10000})
   if(state==='loading'){
    await page.getByRole('status').filter({hasText:/Menyiapkan data/}).waitFor()
    if(form==='pocket')require(!await page.locator('.fixture-workspace').textContent().then(x=>x.includes('0 dari 0 alokasi')||x.includes('Belum ada stok kain kantong')),'UNKNOWN_IS_NOT_ZERO_OR_EMPTY')
   }
   if(['error','denied'].includes(state))await page.getByRole('alert').first().waitFor({state:'visible'})
   if(state==='denied')require(await page.evaluate(()=>window.__writerBUI.calls.length)===0,'DENIED_NO_RPC')
   if(state==='revoked'){
    const count=await page.evaluate(()=>window.__writerBUI.calls.length);await page.evaluate(()=>window.__writerBUI.revoke())
    await page.getByRole('alert').first().waitFor({state:'visible'})
    require(await page.locator('.fixture-workspace table,.fixture-workspace input,.fixture-workspace select').count()===0,'REVOKED_DATA_WITHHELD')
    require(await page.evaluate(()=>window.__writerBUI.calls.length)===count,'REVOKED_NO_NEW_RPC')
   }
   let envelope
   const domain=form==='pocket'?'POCKET_FABRIC':'INITIAL_IMPORT'
   if(state==='pending'){
    if(form==='import')await page.getByLabel('Kode bahan, baris 2',{exact:true}).fill('KAIN-PENDING')
    const button=page.getByRole('button',{name:form==='pocket'?'Sahkan pengurangan stok':'Simpan perubahan draft',exact:true})
    require(await button.isEnabled(),'PENDING_ACTION_MUST_BE_VALID_BEFORE_CLICK')
    await button.evaluate(e=>{e.click();e.click()})
    await page.waitForFunction(domain=>window.__writerBUI.recovery().pending[domain]&&window.__writerBUI.calls.filter(c=>c.name.startsWith('erp_save_')).length===1,domain,{timeout:10000})
    if(form==='pocket')require(await button.isDisabled(),'PENDING_NATIVE_DISABLED')
    else{
     // The existing recovery observer retires the import workspace during SAVE_FILE.
     // An absent editor is the intentional lock; requiring its former button timed out.
     await button.waitFor({state:'detached'})
     require(await page.getByLabel('Kode bahan, baris 2',{exact:true}).count()===0,'PENDING_IMPORT_EDITOR_RETIRED')
     require(await page.getByLabel('Batch impor',{exact:true}).isDisabled(),'PENDING_IMPORT_BATCH_LOCKED')
     await page.getByRole('button',{name:'Reconcile transaksi',exact:true}).waitFor({state:'visible'})
    }
    envelope=await page.evaluate(domain=>window.__writerBUI.recovery().pending[domain],domain)
    const calls=await page.evaluate(()=>window.__writerBUI.calls.filter(c=>c.name.startsWith('erp_save_')))
    require(calls.length===1&&calls[0].args.p_client_request_id===envelope.id,'ONE_UI_WRITE_AND_SAME_ENVELOPE_UUID')
   }
   await take(page,form,state,width)
   if(state==='ready'){
    if(form==='pocket'){
     await page.getByLabel('Awal periode kain kantong',{exact:true}).fill('2026-09-01');await page.getByLabel('Akhir periode kain kantong',{exact:true}).fill('2026-09-20')
     await page.getByRole('button',{name:'Lihat pembagian',exact:true}).click();await page.getByText(/1,125 per pcs/).waitFor()
     await take(page,form,'period-preview',width)
    }else{
     const csv='material_sku,material_name,material_type,unit_code,accessory_category_code,is_active\nKAIN-CSV,Kain dari file asli,FABRIC,YD,,true\n'
     await page.getByLabel('Pilih file CSV',{exact:true}).setInputFiles({name:'UI_FIXTURE.csv',mimeType:'text/csv',buffer:Buffer.from(csv)})
     await page.waitForFunction(()=>document.querySelector('[aria-label="Kode bahan, baris 2"]')?.value==='KAIN-CSV')
     require(await page.evaluate(()=>window.__writerBUI.calls.filter(c=>c.name.startsWith('erp_save_')).length)===0,'CSV_PREVIEW_IS_NOT_A_WRITE')
     await take(page,form,'CSV-preview',width)
    }
   }
   if(state==='pending'){
    await page.reload({waitUntil:'networkidle'});await page.getByRole('button',{name:'Reconcile transaksi',exact:true}).waitFor({state:'visible'})
    const current=await page.evaluate(domain=>window.__writerBUI.recovery().pending[domain],domain)
    require(JSON.stringify(current)===JSON.stringify(envelope),'REOPEN_PRESERVES_SAME_UUID_AND_PAYLOAD')
    require(await page.evaluate(()=>window.__writerBUI.calls.filter(c=>c.name.startsWith('erp_save_')).length)===0,'REOPEN_NO_AUTOMATIC_DUPLICATE_WRITE')
    report.recoveries.push({form,width,uuid:current.id,same_payload:true,automatic_replay_count:0,backend_idempotence_claim:false})
    await take(page,form,'pending-reopened',width)
   }
  }catch(error){report.failures.push({form,state,width,error:error.stack});try{await page.screenshot({path:path.join(out,`FAILED-${form}-${state}-${width}.png`),fullPage:true})}catch{}flush();if(report.failures.length>=3)throw Error('THREE_FAILURES_STOP_FOR_DIAGNOSIS')}
  finally{await context.close()}
 }
 const keys=report.variants.map(v=>`${v.form}/${v.state}/${v.width}`),expected=[]
 for(const width of config.widths)for(const form of config.forms)for(const state of [...config.states,form==='pocket'?'period-preview':'CSV-preview','pending-reopened'])expected.push(`${form}/${state}/${width}`)
 require(keys.length===80&&new Set(keys).size===80&&JSON.stringify(keys.sort())===JSON.stringify(expected.sort()),'EXACT80_CURRENT_UI_IDENTITIES')
 require(report.recoveries.length===8,'EIGHT_REOPENED_PENDING_FIXTURE_VIEWS')
 require(report.fresh_views===28&&report.retained_views===52,'EXACT_28_NEW_52_RETAINED')
 require(report.failures.length===0&&report.console_errors.length===0,'NO_BROWSER_ERRORS')
 report.status='CAPTURED_FOR_VISUAL_REVIEW_NOT_ACTUAL_AUTH_OR_BACKEND_ACCEPTANCE'
}catch(error){report.first_error=error.stack;process.exitCode=1}
finally{
 report.cleanup_errors=[]
 if(browser)try{await browser.close()}catch(error){report.cleanup_errors.push(String(error));process.exitCode=1}
 try{await stopAll();report.server_started=children.length>0;report.server_reaped=children.length>0}catch(error){report.cleanup_errors.push(String(error));process.exitCode=1}
 flush();console.log(JSON.stringify({status:report.status,views:report.variants.length,failures:report.failures.length,console_errors:report.console_errors.length,server_reaped:report.server_reaped,first_error:report.first_error}))
}
