/* B continuation of A's isolated capture. Real browser; fixture/UI evidence only. */
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import { spawn, execFileSync } from 'node:child_process'
import { chromium } from '@playwright/test'
const root=process.cwd(),before=path.resolve(root,'../before'),out=path.resolve(root,process.env.UI_PROOF_DIR??'../ui-family-proof')
const git=(cwd,...args)=>execFileSync('git',['-C',cwd,...args],{encoding:'utf8'}).trim()
const require=(ok,message)=>{if(!ok)throw Error(message)}
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms))
const config=JSON.parse(fs.readFileSync('scripts/ui-reference/FAMILIES.json'))
fs.mkdirSync(out,{recursive:true})
const report={contract:'cp7.B.family-visual-browser.v1',status:'INCOMPLETE',before_head:git(before,'rev-parse','HEAD'),
 after_head:git(root,'rev-parse','HEAD'),variants:[],navigation:[],failures:[],actual_Auth_cases:0,actual_SQL_executed:0,
 actual_financial_cases:0,actual_connected_backend_acceptance:false,independent_acceptance:false,production_go:false,
 note:'DEMO routes and declared real-component fixtures only; no production/database services.'}
require(report.before_head===config.base_head,'EXACT_INHERITED_UI_BEFORE_REQUIRED')
if(process.env.GITHUB_SHA)require(report.after_head===process.env.GITHUB_SHA,'EXACT_B_UI_CANDIDATE_REQUIRED')
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
      '.primary-btn','.soft-btn','input','select','textarea','.field > span','.submenu .sub-active','.nav-main.active',
      '.mobile-primary-nav button','.mandor-shop-dialog p','.mandor-shop-dialog button','.mandor-shop-card dd','.mandor-shop-card dt',
      '.cp7-card','.cp7-notice','.cp7-muted','.role-title','.access-mode-banner','.cfg-totals strong']
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
      overflow_elements:[...document.querySelectorAll('.page-wrap *')].filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.right>innerWidth+1&&getComputedStyle(e).visibility!=='hidden'&&!e.closest('.responsive-table,.table-scroll,.cp7-table-scroll')}).slice(0,12).map(e=>({tag:e.tagName,cls:e.className,right:e.getBoundingClientRect().right})),
      samples,contrast_findings:samples.filter(s=>s.contrast!==null&&s.contrast<4.5)}
  })
}

async function take(page,variant,surface,width,contract='DEMO_SIMULATION'){
  await page.evaluate(()=>document.fonts.ready)
  const name=`${variant}-${surface}-${width}.png`
  const observations=await inspect(page)
  await page.screenshot({path:path.join(out,name),fullPage:true,animations:'disabled'})
  const raw=fs.readFileSync(path.join(out,name))
  const headings=await page.locator('h1,h2').allTextContents()
  report.variants.push({variant,surface,width,contract,headings,
    screenshot:{name,bytes:raw.length,sha256:crypto.createHash('sha256').update(raw).digest('hex')},observations})
  console.log(JSON.stringify({captured:report.variants.length,variant,surface,width,overflow:observations.page_overflow,contrast_findings:observations.contrast_findings.length}))
}
async function navigate(page,surface,width){
  if(surface.id==='dashboard'){
    if(width<=860)await page.getByRole('button',{name:'Buka menu',exact:true}).click()
    await page.locator('.sidebar .nav-main').filter({hasText:/^Dashboard$/}).click()
  }else{
    if(width<=860)await page.getByRole('button',{name:'Buka menu',exact:true}).click()
    const item=page.locator('.submenu button').filter({hasText:surface.label})
    // Use the real group and submenu. A previously open group remains usable.
    if(!await item.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:surface.group}).click()
    require(await item.count()===1,'EXACT_UNIQUE_REAL_NAV_ITEM:'+surface.label)
    await item.click()
    await page.locator('.submenu .sub-active').filter({hasText:surface.label}).waitFor({state:'attached'})
  }
  await page.waitForFunction(()=>{
    const panel=document.querySelector('.page-wrap')
    return panel&&panel.textContent.trim().length>20&&![...panel.querySelectorAll('h2')].some(e=>/^Menyiapkan .+…$/.test(e.textContent.trim()))
  },undefined,{timeout:30000})
}
async function guarded(page,key,operation){
  try{await operation()}catch(error){
    const failure={key,error:error.stack};report.failures.push(failure)
    try{await page.screenshot({path:path.join(out,'FAILED-'+key+'.png'),fullPage:true})}catch{}
    console.error(JSON.stringify({failed:key,error:error.message}))
    try{await page.goto(new URL(page.url()).origin,{waitUntil:'networkidle'})}catch{}
  }
}
async function isolatedContext(url,width){
  const context=await browser.newContext({viewport:{width,height:980},locale:'id-ID',timezoneId:'Asia/Jakarta',reducedMotion:'reduce'})
  await context.route('**/*',route=>{
    const u=new URL(route.request().url())
    if(['data:','blob:'].includes(u.protocol)||u.origin===url)return route.continue()
    report.failures.push({external_network_refused:u.host+u.pathname});return route.abort('blockedbyclient')
  })
  return context
}
try{
  report.baseline_harness_overlay=[]
  for(const name of ['families-fixture.html','families-fixture.tsx']){
    const raw=fs.readFileSync(path.join(root,'scripts/ui-reference',name)),target=path.join(before,'scripts/ui-reference',name)
    require(!fs.existsSync(target),'BEFORE_HARNESS_OVERLAY_MUST_BE_NEW')
    fs.writeFileSync(target,raw,{flag:'wx'});report.baseline_harness_overlay.push({name,sha256:crypto.createHash('sha256').update(raw).digest('hex'),tracked_product_changed:false})
  }
  require(git(before,'diff','--name-only')==='','BEFORE_TRACKED_SOURCE_IMMUTABLE')
  const endpoints=[{name:'before',url:await server(before,4177,'before')},{name:'after',url:await server(root,4178,'after')}]
  browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH?{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH}:{})})
  for(const variant of endpoints)for(const width of config.widths){
    const context=await isolatedContext(variant.url,width),page=await context.newPage()
    page.on('pageerror',e=>report.failures.push({variant:variant.name,width,page_error:e.message}))
    page.on('response',r=>{if(r.status()>=400)report.failures.push({variant:variant.name,width,status:r.status(),path:new URL(r.url()).pathname})})
    try{
      await page.goto(variant.url,{waitUntil:'networkidle'});await page.locator('.app-shell').waitFor()
      for(const surface of config.surfaces){
        if(variant.name==='before'&&!config.before_surfaces.includes(surface.id))continue
        await guarded(page,`${variant.name}-${surface.id}-${width}`,async()=>{
          await navigate(page,surface,width)
          await take(page,variant.name,surface.id,width,
            ['pocket-fabric','admin-import'].includes(surface.id)?'DEMO_HONEST_CONNECTED_SIGN_IN_BOUNDARY':'DEMO_SIMULATION')
        })
      }
      if(variant.name==='after'&&width<=860)await guarded(page,`navigation-${width}`,async()=>{
        await page.goto(variant.url,{waitUntil:'networkidle'})
        const more=page.getByRole('button',{name:'Lainnya, buka menu lengkap',exact:true})
        await more.click();await page.getByRole('button',{name:'Tutup menu',exact:true}).waitFor({state:'visible'})
        require(await page.locator('.sidebar').evaluate(e=>e.contains(document.activeElement)),'DRAWER_FOCUS_ENTERED')
        await page.keyboard.press('Shift+Tab')
        require(await page.locator('.sidebar').evaluate(e=>e.contains(document.activeElement)),'DRAWER_FOCUS_TRAPPED')
        await page.keyboard.press('Escape');await page.locator('.sidebar-open').waitFor({state:'hidden'})
        require(await more.evaluate(e=>e===document.activeElement),'DRAWER_FOCUS_RESTORED')
        const input=page.getByRole('button',{name:'Dashboard',exact:true}).filter({has:page.locator('span')})
        const identity=await page.locator('.kpi-grid').evaluate(e=>{e.dataset.uiIdentity='preserved';return e.dataset.uiIdentity})
        await page.locator('.mobile-primary-nav button[aria-current=page]').click()
        require(await page.locator('.kpi-grid').getAttribute('data-ui-identity')===identity,'CURRENT_WORKSPACE_NOT_REMOUNTED')
        report.navigation.push({width,focus_entered:true,focus_trapped:true,Escape_and_focus_return:true,current_workspace_preserved:true})
        await take(page,'after','mobile-navigation',width)
      })
      {
        const states=variant.name==='after'?['ready','long','empty','loading','error','stale','approved','review','pending']:['ready','review']
        for(const state of states)await guarded(page,`mandor-${state}-${width}`,async()=>{
          await page.goto(variant.url+'/scripts/ui-reference/families-fixture.html?state='+state,{waitUntil:'networkidle'})
          const dialog=page.getByRole('dialog');await dialog.waitFor({state:'visible'})
          if(['review','pending'].includes(state)){
            await page.getByRole('button',{name:'Pilih nota INV-EPI-01',exact:true}).click()
            await page.getByLabel('Nominal potongan belanja',{exact:true}).fill('100000,19')
            require(await page.getByText('Rp1.899.999,81',{exact:true}).count()===1,'EXACT_CENTS_PREVIEW_RETAINED')
            await page.getByRole('checkbox').check()
            if(state==='pending'){
              const submit=page.getByRole('button',{name:'Pasang tagihan ke payroll',exact:true})
              await submit.evaluate(e=>{e.click();e.click()})
              await page.getByRole('status').filter({hasText:'Memproses pilihan…'}).waitFor()
              require(await page.getByRole('button',{name:'Tutup kartu tagihan',exact:true}).isDisabled(),'PENDING_CLOSE_REMAINS_BLOCKED')
              await page.keyboard.press('Escape');require(await dialog.isVisible(),'PENDING_ESCAPE_REMAINS_BLOCKED')
              require(await page.getByLabel('Jumlah panggilan fixture',{exact:true}).textContent()==='1','PENDING_DOUBLE_CLICK_ONE_CALLBACK')
            }
          }
          if(['loading','error','stale'].includes(state))require(!await dialog.textContent().then(x=>/Rp[\d\s]/.test(x)),'STALE_OR_LOADING_FIGURES_WITHHELD')
          await take(page,variant.name,'mandor-'+state,width,'REAL_MANDOR_CARDS_DECLARED_ISOLATED_FIXTURE_NO_BACKEND')
          if(state==='ready'){
            await page.keyboard.press('Escape');require(!await dialog.isVisible(),'IDLE_DIALOG_ESCAPE_CLOSES')
            await page.getByRole('button',{name:'Buka kartu tagihan',exact:true}).click();await dialog.waitFor()
          }
        })
        if(variant.name==='after')await guarded(page,`cp7-${width}`,async()=>{
          await page.goto(variant.url+'/cp7-preview',{waitUntil:'networkidle'});await page.locator('.cp7-controls').waitFor()
          await page.getByLabel('Isi pratinjau',{exact:true}).selectOption('FRAMEWORK')
          await page.locator('.cp7-notice[data-state=READY]').waitFor()
          for(const button of await page.locator('.cp7-sidebar nav button').all()){
            const label=await button.innerText();await button.click()
            await take(page,'after','cp7-'+label.toLowerCase().replace(/[^a-z0-9]+/g,'-'),width,'EXISTING_CP7_PREVIEW_FIXTURE_NOT_CONNECTED_ANALYSIS')
          }
          await page.locator('.cp7-sidebar nav button').first().click()
          for(const state of ['EMPTY','PARTIAL','STALE','ERROR']){
            await page.getByLabel('Isi pratinjau',{exact:true}).selectOption(state)
            await page.locator('.cp7-notice[data-state='+state+']').waitFor()
            await take(page,'after','cp7-state-'+state.toLowerCase(),width,'EXISTING_CP7_PREVIEW_STATE')
          }
          await page.getByLabel('Isi pratinjau',{exact:true}).selectOption('FRAMEWORK');await page.locator('.cp7-notice[data-state=READY]').waitFor()
          for(const access of ['OPERATIONS','DENIED']){
            await page.getByLabel('Hak akses contoh',{exact:true}).selectOption(access)
            await take(page,'after','cp7-access-'+access.toLowerCase(),width,'EXISTING_CP7_PREVIEW_ROLE_NOT_AUTH')
          }
        })
      }
    }finally{await context.close()}
  }
  report.expected_after_route_views=47*4
  report.actual_after_route_views=report.variants.filter(x=>x.variant==='after'&&config.surfaces.some(s=>s.id===x.surface)).length
  require(report.actual_after_route_views===report.expected_after_route_views,'EVERY_ACTUAL_NAVIGATION_ROUTE_AT_ALL_FOUR_WIDTHS_REQUIRED')
  require(report.variants.filter(x=>x.variant==='after'&&x.surface.startsWith('mandor-')).length===36,'EXACT36_MANDOR_DIALOG_VIEWS_REQUIRED')
  require(report.variants.filter(x=>x.variant==='after'&&x.surface.startsWith('cp7-')).length===56,'EXACT56_CP7_VIEW_STATE_ROLE_VIEWS_REQUIRED')
  require(report.navigation.length===3,'THREE_MOBILE_WIDTHS_REAL_FOCUS_RECOVERY_REQUIRED')
  report.status=report.failures.length?'CAPTURED_WITH_FAILURES_NOT_ACCEPTED':'CAPTURED_FOR_VISUAL_REVIEW_NOT_BACKEND_ACCEPTANCE'
}catch(error){report.first_error=error.stack;process.exitCode=1}
finally{
  report.cleanup_errors=[]
  if(browser)try{await browser.close()}catch(error){report.cleanup_errors.push(error.stack);process.exitCode=1}
  for(const child of children)try{await stop(child)}catch(error){report.cleanup_errors.push(error.stack);process.exitCode=1}
  report.preview_children_reaped=children.every(child=>exited(child)&&!groupExists(child))
  if(report.failures.length||report.cleanup_errors.length)process.exitCode=1
  fs.writeFileSync(path.join(out,'UI_FAMILY_CAPTURE.json'),JSON.stringify(report,null,2)+'\n')
  console.log(JSON.stringify({status:report.status,screenshots:report.variants.length,failures:report.failures.length,
    after_contrast_findings:report.variants.filter(x=>x.variant==='after').reduce((n,x)=>n+x.observations.contrast_findings.length,0),
    after_overflow_views:report.variants.filter(x=>x.variant==='after'&&x.observations.page_overflow).length,
    preview_children_reaped:report.preview_children_reaped,first_error:report.first_error}))
}
