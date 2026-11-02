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
const escape=value=>value.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')
const surfaces=[
  {id:'dashboard',group:null,label:'Dashboard'},
  {id:'sales-invoice',group:'Penjualan',label:'Penjualan & Invoice'},
  {id:'finance-payroll',group:'Keuangan',label:'Payroll & Kasbon'},
]
fs.mkdirSync(out,{recursive:true})
const report={contract:'cp7.owner-UI.real-browser-capture.v1',status:'INCOMPLETE',
  before_head:git(before,'rev-parse','HEAD'),after_head:git(root,'rev-parse','HEAD'),
  variants:[],actual_financial_cases:0,actual_Auth_cases:0,actual_SQL_executed:0,
  actual_Mandor_popup_acceptance:false,actual_UI_final_acceptance:false,production_go:false,
  note:'Screenshots use existing DEMO_SIMULATION only. Findings are retained; capture is not final visual acceptance.'}
require(report.before_head===base,'UI_CAPTURE_EXACT_BEFORE_COMMIT_REQUIRED')
if(process.env.GITHUB_SHA)require(report.after_head===process.env.GITHUB_SHA,'UI_CAPTURE_CURRENT_CANDIDATE_REQUIRED')
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
        const page=await context.newPage(),errors=[],failures=[]
        page.on('pageerror',e=>errors.push(e.message))
        page.on('response',r=>{if(r.status()>=400)failures.push({status:r.status(),path:new URL(r.url()).pathname})})
        try{
          await page.goto(variant.url,{waitUntil:'networkidle'})
          await page.locator('.app-shell').waitFor({state:'visible'})
          if(surface.group){
            if(width<=860)await page.getByRole('button',{name:'Buka menu',exact:true}).click()
            await page.locator('.nav-main').filter({hasText:new RegExp('^'+escape(surface.group)+'(?:\\s|$)')}).click()
            const button=page.locator('.submenu button').filter({hasText:surface.label})
            require(await button.count()===1,'UI_CAPTURE_UNIQUE_ACTUAL_MENU_REQUIRED:'+surface.label)
            await button.click()
            await page.locator('.submenu .sub-active').filter({hasText:surface.label}).waitFor({state:'attached'})
          }
          await page.locator('.page-wrap').waitFor({state:'visible'})
          await page.evaluate(()=>document.fonts.ready)
          const name=`${variant.name}-${surface.id}-${width}.png`
          await page.screenshot({path:path.join(out,name),fullPage:true,animations:'disabled'})
          const observations=await inspect(page),raw=fs.readFileSync(path.join(out,name))
          report.variants.push({variant:variant.name,surface:surface.id,width,screenshot:{name,bytes:raw.length,
            sha256:crypto.createHash('sha256').update(raw).digest('hex')},observations,page_errors:errors,http_failures:failures})
          require(errors.length===0&&failures.length===0,'UI_CAPTURE_APPLICATION_RENDER_ERROR:'+name)
          if(variant.name==='after')require(observations.canvas==='rgb(244, 246, 250)'&&observations.sidebar==='rgb(24, 34, 57)',
            'UI_CAPTURE_ACTUAL_LIGHT_CANVAS_AND_NAVY_SIDEBAR_REQUIRED:'+name)
        }finally{await page.close()}
      }
      require(blocked.length===0,'UI_CAPTURE_EXTERNAL_NETWORK_ATTEMPT_REFUSED')
    }finally{await context.close()}
  }
  require(report.variants.length===24,'UI_CAPTURE_EXACT_TWENTYFOUR_VIEWS_REQUIRED')
  report.status='BEFORE_AFTER24_CAPTURED_FINDINGS_RETAINED_NOT_FINAL_UI_ACCEPTANCE'
}catch(error){report.first_error=error.stack;process.exitCode=1}
finally{
  report.cleanup_errors=[]
  if(browser)try{await browser.close()}catch(error){report.cleanup_errors.push(error.stack);process.exitCode=1}
  for(const child of children)try{await stop(child)}catch(error){report.cleanup_errors.push(error.stack);process.exitCode=1}
  report.preview_children_reaped=children.every(child=>exited(child)&&!groupExists(child))
  fs.writeFileSync(path.join(out,'UI_REFERENCE_CAPTURE.json'),JSON.stringify(report,null,2)+'\n')
  console.log(JSON.stringify({status:report.status,screenshots:report.variants.length,
    after_contrast_findings:report.variants.filter(x=>x.variant==='after').reduce((n,x)=>n+x.observations.contrast_findings.length,0),
    after_overflow_views:report.variants.filter(x=>x.variant==='after'&&x.observations.page_overflow).length,
    preview_children_reaped:report.preview_children_reaped,first_error:report.first_error,
    actual_financial_or_Auth_cases:0,actual_UI_final_acceptance:false}))
}
