/* Real-browser visual capture only. DEMO data, no ERP/SQL/Auth qualification. */
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import { spawn, execFileSync } from 'node:child_process'
import { chromium } from '@playwright/test'

const root=process.cwd(), before=path.resolve(root,'../before')
const out=path.resolve(root,'../ui-reference-proof')
const base='2c7a5a05516548667ec71faedcffb3591828100f'
const git=(cwd,...args)=>execFileSync('git',['-C',cwd,...args],{encoding:'utf8'}).trim()
const require=(ok,message)=>{if(!ok)throw Error(message)}
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms))
const surfaces=[
  {id:'dashboard',group:null,label:'Dashboard',ready:'.kpi-grid'},
  {id:'sales-invoice',group:'Penjualan',label:'Penjualan & Invoice',ready:'.biz-invoice-lifecycle'},
  {id:'finance-payroll',group:'Keuangan',label:'Payroll & Kasbon',ready:'.payroll-detail'},
]
fs.mkdirSync(out,{recursive:true})
const report={contract:'cp7.owner-UI.real-browser-capture.v1',status:'INCOMPLETE',
  before_head:git(before,'rev-parse','HEAD'),after_head:git(root,'rev-parse','HEAD'),
  variants:[],retained_originals:[],actual_financial_cases:0,actual_Auth_cases:0,actual_SQL_executed:0,
  actual_Mandor_popup_acceptance:false,actual_UI_final_acceptance:false,production_go:false,
  note:'Screenshots use existing DEMO_SIMULATION only. Findings are retained; capture is not final visual acceptance.'}
require(report.before_head===base,'UI_CAPTURE_EXACT_BEFORE_COMMIT_REQUIRED')
if(process.env.GITHUB_SHA)require(report.after_head===process.env.GITHUB_SHA,'UI_CAPTURE_CURRENT_CANDIDATE_REQUIRED')
const retainedDirectory=path.join(root,'scripts/ui-reference/retained-before320')
const retainedRaw=fs.readFileSync(path.join(retainedDirectory,'UI_REFERENCE_CAPTURE.json'))
require(crypto.createHash('sha256').update(retainedRaw).digest('hex')==='7d95bb1cd9efa30228a4753933607d5b3e8497ef42ba47d5fe614317383fab78',
  'UI_CAPTURE_EXACT_FIRST_ORIGINAL_REPORT_REQUIRED')
const retainedReport=JSON.parse(retainedRaw)
require(retainedReport.before_head===base&&retainedReport.variants.length===1,'UI_CAPTURE_RETAINED_IMMUTABLE_BASE_REQUIRED')
const retained=retainedReport.variants[0]
require(retained.variant==='before'&&retained.surface==='dashboard'&&retained.width===320
  &&retained.page_errors.length===0&&retained.http_failures.length===0,'UI_CAPTURE_ONLY_VALID_FIRST_BEFORE_VIEW_REUSED')
const retainedPNG=fs.readFileSync(path.join(retainedDirectory,retained.screenshot.name))
require(retainedPNG.length===322487&&crypto.createHash('sha256').update(retainedPNG).digest('hex')===
  '57a2f0a9642031e61d68d517e0d22df4b19312a86893f918ba144c8fbdf62ee2','UI_CAPTURE_EXACT_RETAINED_BEFORE_PNG_REQUIRED')
const immutableDashboardBaselines=[
  {width:320,name:'before-dashboard-320.png',bytes:322487,sha256:'57a2f0a9642031e61d68d517e0d22df4b19312a86893f918ba144c8fbdf62ee2',included_in_this_artifact:true},
  {width:390,name:'before-dashboard-390.png',bytes:357654,sha256:'d3330c3a0d8a9c1bb1db5d8ab54fed4a74e48667dd69bf00bcc57fe0a6b89cfe',included_in_this_artifact:false},
  {width:768,name:'before-dashboard-768.png',bytes:439198,sha256:'56e8d6997095479650560e6da327e23be464b59984632f702c859f7178617a7c',included_in_this_artifact:false},
  {width:1440,name:'before-dashboard-1440.png',bytes:426792,sha256:'11fb7cb78a120c0047af9a0916ec7cf90c30333ebf92d8bbf7447e7cdd79072e',included_in_this_artifact:false},
]
for(const baseline of immutableDashboardBaselines)report.retained_originals.push({variant:'before',surface:'dashboard',
  ...baseline,source_head:'a4f89315c5c1c5d4887a086e1455ffe9e94e3fd5',source_run_id:41512867605,
  source_job_id:125508871053,source_artifact_id:13174052118,
  source_zip_sha256:'c735e15a683291cd1ee131db75a7a62362907582d4a09bc18b734082812db3d1',
  original_PNG_preserved:true,case_rerun:false})
const loadedReferences=[
  {variant:'before',surface:'sales-invoice',width:320,name:'before-sales-invoice-320.png',bytes:378786,sha256:'0e450e7efc478153050d9c273ed2dced2bd1fec902fb9f86accb01107e271f2d'},
  {variant:'before',surface:'finance-payroll',width:320,name:'before-finance-payroll-320.png',bytes:446562,sha256:'0f7db466e51e6c6a07386d78263210adf978f46742884bf244ba8f464f128413'},
  {variant:'before',surface:'sales-invoice',width:390,name:'before-sales-invoice-390.png',bytes:417863,sha256:'c7a230f051547da372edf965fe0226926813a23c30e3f7ebc1ae4755ca6749ef'},
  {variant:'before',surface:'finance-payroll',width:390,name:'before-finance-payroll-390.png',bytes:491853,sha256:'961deb7f83abffb8ffa640bf2770a1947404509cecabc09c06d439a2b3453b31'},
  {variant:'before',surface:'sales-invoice',width:768,name:'before-sales-invoice-768.png',bytes:544686,sha256:'cf5699f3e68058a2b096176a1e1ef3fb4cb567827e621613ac73330153e69f77'},
  {variant:'before',surface:'finance-payroll',width:768,name:'before-finance-payroll-768.png',bytes:540152,sha256:'4236fb5a3f7e68d901c910bd4935b2d2dcfb87428ae15bd58cbf526833ba50f6'},
  {variant:'before',surface:'sales-invoice',width:1440,name:'before-sales-invoice-1440.png',bytes:551902,sha256:'a5c699e0dd7e101a246d31dbf767424a73429fd02ce2be4297ff53a16e328502'},
  {variant:'before',surface:'finance-payroll',width:1440,name:'before-finance-payroll-1440.png',bytes:674439,sha256:'8877e9bd1a90febe2d3424925a2e97792661148bb0d98892301f65c283269e11'},
  {variant:'after',surface:'dashboard',width:320,name:'after-dashboard-320.png',bytes:138396,sha256:'426c709f7203642124df0202e18079477ece1dffab505056ef8250e84b6a171d'},
  {variant:'after',surface:'dashboard',width:390,name:'after-dashboard-390.png',bytes:141252,sha256:'8602dee86fd84eac1692024f1daece0437c6a43c7d97e37d36cd53826ed10534'},
  {variant:'after',surface:'dashboard',width:768,name:'after-dashboard-768.png',bytes:144734,sha256:'d9545e1c3eacc3b385c27c03d72cc948571b94eb480abbac221c648a78b20e3b'},
  {variant:'after',surface:'dashboard',width:1440,name:'after-dashboard-1440.png',bytes:174276,sha256:'58300f9734330c01cc4ed9079d74db6465c202ed9d7a691eb0088539e684a1c9'},
]
for(const reference of loadedReferences)report.retained_originals.push({...reference,included_in_this_artifact:false,
  source_head:'8bee8130e992a10da6a334d6de54a4b89e98a0c0',source_run_id:41517224634,
  source_job_id:125523748264,source_artifact_id:13176370866,
  source_zip_sha256:'1d972386a73f4c0b7687c58ea948ad4aee8c2e8575b03755239fa228653a18c7',
  actual_loaded_selector:reference.surface==='sales-invoice'?'.biz-invoice-lifecycle':reference.surface==='finance-payroll'?'.payroll-detail':'.kpi-grid',
  workspace_fallback_absent:true,original_PNG_preserved:true,case_rerun:false})
const children=[]
let browser
const exited=child=>child.exitCode!==null||child.signalCode!==null
const groupExists=child=>{try{process.kill(-child.pid,0);return true}catch(error){if(error.code==='ESRCH')return false;throw error}}

async function server(directory,port,name){
  const log=fs.openSync(path.join(out,name+'-server.log'),'wx')
  const env={PATH:process.env.PATH,HOME:process.env.HOME,LANG:'C.UTF-8',
    VITE_ERP_RUNTIME_MODE:'DEMO_SIMULATION',NODE_ENV:'development'}
  const child=spawn(process.execPath,[path.join(root,'node_modules/vite/bin/vite.js'),
    '--host','127.0.0.1','--port',String(port),'--strictPort','--mode','ui-reference-preview'],
    {cwd:directory,env,stdio:['ignore',log,log],detached:true})
  fs.closeSync(log);children.push(child)
  const url=`http://127.0.0.1:${port}`
  for(let attempt=0;attempt<300;attempt++){
    if(exited(child))throw Error(name+' preview server exited before readiness')
    try{const response=await fetch(url);if(response.ok)return url}catch{}
    await sleep(200)
  }
  throw Error(name+' preview server did not become ready')
}

async function stop(child){
  if(exited(child)&&!groupExists(child))return
  try{process.kill(-child.pid,'SIGTERM')}catch(error){if(error.code!=='ESRCH')throw error}
  for(let i=0;i<50&&(!exited(child)||groupExists(child));i++)await sleep(100)
  if(!exited(child)||groupExists(child)){try{process.kill(-child.pid,'SIGKILL')}catch(error){if(error.code!=='ESRCH')throw error}}
  for(let i=0;i<20&&(!exited(child)||groupExists(child));i++)await sleep(100)
  require(exited(child)&&!groupExists(child),'UI_CAPTURE_PREVIEW_CHILD_MUST_BE_REAPED')
}

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
      '.primary-btn','.soft-btn','input','select','textarea','.field > span','.submenu .sub-active','.nav-main.active']
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
      sidebar:getComputedStyle(document.querySelector('.sidebar')).backgroundColor,
      page_overflow:Math.max(document.body.scrollWidth,document.documentElement.scrollWidth)>innerWidth+1,
      samples,contrast_findings:samples.filter(s=>s.contrast!==null&&s.contrast<4.5)}
  })
}

try{
  const endpoints=[{name:'before',url:await server(before,4177,'before')},{name:'after',url:await server(root,4178,'after')}]
  browser=await chromium.launch({headless:true})
  for(const variant of endpoints)for(const width of[320,390,768,1440]){
    const context=await browser.newContext({viewport:{width,height:980},locale:'id-ID',timezoneId:'Asia/Jakarta',reducedMotion:'reduce'})
    const blocked=[]
    await context.route('**/*',route=>{
      const u=new URL(route.request().url())
      if(u.protocol==='data:'||u.protocol==='blob:'||u.origin===variant.url)return route.continue()
      blocked.push({host:u.host,path:u.pathname});return route.abort('blockedbyclient')
    })
    try{
      for(const surface of surfaces){
        if(variant.name==='before'||variant.name==='after'&&surface.id==='dashboard'){
          if(variant.name==='before'&&surface.id==='dashboard'&&width===320)
            fs.writeFileSync(path.join(out,retained.screenshot.name),retainedPNG,{flag:'wx'})
          continue
        }
        const page=await context.newPage(),errors=[],failures=[]
        page.on('pageerror',e=>errors.push(e.message))
        page.on('response',r=>{if(r.status()>=400)failures.push({status:r.status(),path:new URL(r.url()).pathname})})
        try{
          await page.goto(variant.url,{waitUntil:'networkidle'})
          await page.locator('.app-shell').waitFor({state:'visible'})
          if(surface.group){
            if(width<=860)await page.getByRole('button',{name:'Buka menu',exact:true}).click()
            const group=page.locator('.nav-main').filter({hasText:surface.group})
            require(await group.count()===1,'UI_CAPTURE_UNIQUE_ACTUAL_GROUP_LABEL_REQUIRED:'+surface.group)
            await group.click()
            const button=page.locator('.submenu button').filter({hasText:surface.label})
            require(await button.count()===1,'UI_CAPTURE_UNIQUE_ACTUAL_MENU_REQUIRED:'+surface.label)
            await button.click()
            await page.locator('.submenu .sub-active').filter({hasText:surface.label}).waitFor({state:'attached'})
          }
          await page.locator('.page-wrap').waitFor({state:'visible'})
          await page.locator(surface.ready).first().waitFor({state:'visible',timeout:30000})
          require(await page.getByText(/^Menyiapkan (Penjualan|Keuangan)…$/).count()===0,
            'UI_CAPTURE_WORKSPACE_FALLBACK_MUST_BE_GONE:'+surface.id)
          await page.evaluate(()=>document.fonts.ready)
          const name=`${variant.name}-${surface.id}-${width}.png`
          await page.screenshot({path:path.join(out,name),fullPage:true,animations:'disabled'})
          const observations=await inspect(page),raw=fs.readFileSync(path.join(out,name))
          report.variants.push({variant:variant.name,surface:surface.id,width,actual_loaded_selector:surface.ready,
            workspace_fallback_absent:true,screenshot:{name,bytes:raw.length,
            sha256:crypto.createHash('sha256').update(raw).digest('hex')},observations,page_errors:errors,http_failures:failures})
          require(errors.length===0&&failures.length===0,'UI_CAPTURE_APPLICATION_RENDER_ERROR:'+name)
          if(variant.name==='after')require(observations.canvas==='rgb(244, 246, 250)'&&observations.sidebar==='rgb(24, 34, 57)',
            'UI_CAPTURE_ACTUAL_LIGHT_CANVAS_AND_NAVY_SIDEBAR_REQUIRED:'+name)
        }catch(error){
          report.failed_view={variant:variant.name,surface:surface.id,width,
            actual_menu_text:await page.locator('.nav-main').allTextContents(),
            actual_submenu_text:await page.locator('.submenu button').allTextContents()}
          try{
            const name=`FAILED-${variant.name}-${surface.id}-${width}.png`
            await page.screenshot({path:path.join(out,name),fullPage:true,animations:'disabled'})
            report.failed_view.screenshot=name
          }catch(captureError){report.failed_view.screenshot_error=captureError.message}
          throw error
        }finally{await page.close()}
      }
      require(blocked.length===0,'UI_CAPTURE_EXTERNAL_NETWORK_ATTEMPT_REFUSED')
    }finally{await context.close()}
  }
  require(report.variants.length===8,'UI_CAPTURE_EXACT_EIGHT_NEW_BUSINESS_VIEWS_REQUIRED')
  require(report.retained_originals.length===16,'UI_CAPTURE_EXACT_SIXTEEN_VALID_REFERENCES_REQUIRED')
  const evidenceKeys=[...report.variants.map(x=>`${x.variant}:${x.surface}:${x.width}`),
    ...report.retained_originals.map(x=>`${x.variant}:${x.surface}:${x.width}`)]
  require(new Set(evidenceKeys).size===24,'UI_CAPTURE_EACH_REQUIRED_EVIDENCE_VIEW_ONCE')
  report.status='BEFORE_AFTER24_RETAINED16_NEW8_BUSINESS_THEME_CAPTURED_FINDINGS_PENDING_NOT_FINAL_UI_ACCEPTANCE'
}catch(error){report.first_error=error.stack;process.exitCode=1}
finally{
  report.cleanup_errors=[]
  if(browser)try{await browser.close()}catch(error){report.cleanup_errors.push(error.stack);process.exitCode=1}
  for(const child of children)try{await stop(child)}catch(error){report.cleanup_errors.push(error.stack);process.exitCode=1}
  report.preview_children_reaped=children.every(child=>exited(child)&&!groupExists(child))
  fs.writeFileSync(path.join(out,'UI_REFERENCE_CAPTURE.json'),JSON.stringify(report,null,2)+'\n')
  console.log(JSON.stringify({status:report.status,screenshots:report.variants.length,
    retained_valid_views:report.retained_originals.length,new_captured_views:report.variants.length,
    after_contrast_findings:report.variants.filter(x=>x.variant==='after').reduce((n,x)=>n+x.observations.contrast_findings.length,0),
    after_overflow_views:report.variants.filter(x=>x.variant==='after'&&x.observations.page_overflow).length,
    preview_children_reaped:report.preview_children_reaped,first_error:report.first_error,
    actual_financial_or_Auth_cases:0,actual_UI_final_acceptance:false}))
}
