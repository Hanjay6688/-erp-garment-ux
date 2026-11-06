import assert from 'node:assert/strict'
import {createRequire} from 'node:module'
import {readFileSync,writeFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
import {performance} from 'node:perf_hooks'
import {createFixture,mandor,sku,slice} from './smoke-fixtures.mjs'

const [kind,out]=process.argv.slice(2)
assert(['mandor','sku'].includes(kind)&&out)
const root=new URL(`./${kind}/`,import.meta.url)
const require=createRequire(new URL('package.json',root))
const {chromium,expect:baseExpect}=require('@playwright/test')
const expect=baseExpect.configure({timeout:6000})
const browserPath=kind==='mandor'?'scripts/current-mandor-shop-native-qualification/browser.mjs':'scripts/current-sku-automatic-composite-preparation/browser.mjs'
const entry=new URL(browserPath,root)
const source=readFileSync(entry,'utf8')
const original=await import(entry.href)
assert.equal(typeof original.cases,'function')
assert.equal(original.IDS.length,2)
const origin='http://127.0.0.1:4176',api='http://127.0.0.1:54099'
const sha=text=>createHash('sha256').update(text).digest('hex')

function bind(page){
 if(kind==='mandor'){
  const helper=slice(source,'const READ=','const observed=')+slice(source,'async function menu','async function journey')
  return {helper_sha256:sha(helper),...new Function('assert',helper+'\nreturn {choosePayroll,selectAmount,fresh,dialog,amount,reviewed,reserve}') (assert)}
 }
 const helper=slice(source,'const RPC=','const fixture=')+slice(source,'const args=','function pinnedSource')
  +slice(source,'async function success','async function journey')
  +slice(source,' const pairWorkspace=',' const groupSource=')
  +slice(source,' async function searchGroup','\n try{\n  await menu')
 return {helper_sha256:sha(helper),...new Function('assert','page','expect','f',helper+'\nreturn {menu,searchGroup,editPair,choosePair,openConversion,selectSource,searchTarget,selectTarget,destination,success,rpc,args,RPC}')(assert,page,expect,sku)}
}

const start=performance.now()
const result={status:'INCOMPLETE',kind,source_sha256:sha(source),runner_case_ids:original.IDS,source_path:browserPath,playwright:require('@playwright/test/package.json').version,transport:'LOOPBACK_INTERCEPTED_AUTH_AND_RPC_FIXTURES',actual_SQL:0,actual_Auth:0,actual_financial_cases:0,observations:[]}
let browser
try{
 browser=await chromium.launch({headless:true,timeout:15000})
 result.chromium=browser.version()
 for(const width of[1440,390]){
  const began=performance.now(),mobile=width===390,role=kind==='sku'&&mobile?'ADMIN':'OWNER'
  const f=createFixture(kind,role),external=[],errors=[],phases=[]
  const context=await browser.newContext({viewport:{width,height:900},timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta',isMobile:mobile,hasTouch:mobile,serviceWorkers:'block'})
  context.setDefaultTimeout(6000)
  const page=await context.newPage()
  page.on('pageerror',e=>errors.push(e.message))
  page.on('console',m=>{if(m.type()==='error')errors.push(m.text())})
  const row={width,role,status:'INCOMPLETE',phases,external,errors,requests:f.state.requests,unknown:f.state.unknown,simulatedWrites:f.state.simulatedWrites}
  result.observations.push(row)
  await context.route('**/*',async route=>{
   const r=route.request(),u=new URL(r.url())
   if(u.origin===origin&&['GET','HEAD'].includes(r.method()))return route.continue()
   if(u.origin!==api){external.push(u.origin+u.pathname);return route.abort('blockedbyclient')}
   const headers={'access-control-allow-origin':origin,'access-control-allow-methods':'GET,POST,OPTIONS','access-control-allow-headers':r.headers()['access-control-request-headers']??'*'}
   if(r.method()==='OPTIONS')return route.fulfill({status:204,headers})
   try{
    let body
    if(u.pathname==='/auth/v1/token'&&r.method()==='POST'&&u.searchParams.get('grant_type')==='password')body=f.session
    else if(u.pathname==='/auth/v1/user'&&r.method()==='GET')body=f.user
    else if(u.pathname.startsWith('/rest/v1/rpc/')&&r.method()==='POST')body=f.rpc(u.pathname.split('/').at(-1),r.postDataJSON()??{})
    else throw Error('UNDECLARED_FIXTURE_ENDPOINT '+u.pathname)
    return route.fulfill({status:200,headers,json:body})
   }catch(e){errors.push(e.message);return route.fulfill({status:400,headers,json:{code:'FIXTURE_REQUEST_REJECTED',message:e.message}})}
  })
  async function phase(name,fn){
   const time=performance.now();row.active_phase=name
   const value=await fn();phases.push({name,seconds:(performance.now()-time)/1000});return value
  }
  try{
   const h=bind(page);row.exact_runner_helper_sha256=h.helper_sha256
   await phase('normal_app_login_form',async()=>{
    await page.goto(origin)
    await page.getByLabel('Email akun ERP').fill('browser-fixture@example.invalid')
    await page.getByLabel('Kata sandi').fill('Browser-fixture-only')
    await page.getByRole('button',{name:'Masuk',exact:true}).click()
    await expect(page.locator('.sidebar')).toBeAttached()
    await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
   })
   if(kind==='mandor'){
    const ui={expect}
    await phase('existing_runner_payroll_search_and_invoice_card',()=>h.choosePayroll(ui,page,mandor))
    await phase('existing_runner_amount_review_gate_and_cancel',async()=>{
     await h.selectAmount(ui,page,mandor,'100000.00')
     await h.dialog(page).getByRole('button',{name:'Batal memilih tagihan',exact:true}).click()
     await expect(h.amount(page)).toHaveCount(0)
    })
    await phase('existing_runner_fresh_read_and_release_review_gate',async()=>{
     f.state.reserved=true
     await h.fresh(ui,page,mandor)
     await h.dialog(page).getByRole('button',{name:'Lepas nota '+mandor.sale_number,exact:true}).click()
     const release=h.dialog(page).getByRole('button',{name:'Lepas tagihan dari payroll',exact:true})
     await expect(release).toBeDisabled();await h.reviewed(page).check();await expect(release).toBeEnabled()
    })
   }else{
    await phase('existing_runner_group_search_edit_and_pair_request',async()=>{
     await h.menu(page,'Master Data','Produk & SKU')
     await h.editPair(sku.groups[0].id)
     const reply=await h.choosePair(sku.groups[1].id)
     assert.equal(reply.source_group_id,sku.groups[0].id);assert.equal(reply.target_group_id,sku.groups[1].id)
     await expect(await h.searchGroup(sku.groups[1].id)).toContainText('Vivo · 1002')
    })
    await phase('existing_runner_source_and_target_controls',async()=>{
     await h.openConversion();await h.selectSource()
     await h.searchTarget(sku.products.other.sku);await h.selectTarget(sku.other)
     await h.searchTarget(sku.products.target.sku)
     await expect(h.destination().getByRole('combobox',{name:'SKU tujuan',exact:true})).toHaveValue('')
     await expect(h.destination().getByRole('button',{name:'Lihat pratinjau',exact:true})).toBeDisabled()
     const selected=await h.selectTarget(sku.target)
     assert.deepEqual(selected.selection.source_stock,{physical:10,reserved:1,available:9})
     assert.deepEqual(selected.selection.target_stock,{physical:4,reserved:0,available:4})
    })
    await phase('existing_runner_wib_quantity_and_preview_controls',async()=>{
     const dst=h.destination()
     await dst.getByLabel('Jumlah PCS',{exact:true}).fill('4')
     await dst.getByLabel('Waktu fisik · WIB',{exact:true}).fill(sku.physical_local)
     await dst.getByLabel('Alasan',{exact:true}).fill('Koreksi fisik campuran merek dan ukuran lewat layar owner29')
     const pending=page.waitForResponse(r=>h.rpc(h.RPC.read)(r)&&h.args(r).p_filters?.preview?.target_product_id===sku.target)
     await dst.getByRole('button',{name:'Lihat pratinjau',exact:true}).click()
     const reviewed=await h.success(pending)
     assert.equal(reviewed.preview.qty_pcs,4);assert.equal(reviewed.preview.physical_at,'2026-10-20T00:00:00.000Z')
     await expect(dst.getByRole('button',{name:'Catat konversi fisik',exact:true})).toBeEnabled()
    })
   }
   await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
   assert.deepEqual(f.state.unknown,[]);assert.deepEqual(external,[]);assert.deepEqual(errors,[])
   assert.equal(f.state.simulatedWrites.length,kind==='sku'?1:0)
   row.status='PASS';row.seconds=(performance.now()-began)/1000
  }catch(error){
   row.error=String(error.stack??error);row.visible_text=(await page.locator('body').innerText().catch(()=>'' )).slice(-3500);throw error
  }finally{await context.close()}
 }
 result.status='PASS_LOCAL_REAL_CHROMIUM_DECLARED_FIXTURES'
}catch(error){result.error=String(error.stack??error);process.exitCode=1}
finally{if(browser)await browser.close();result.seconds=(performance.now()-start)/1000;writeFileSync(out,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({kind,status:result.status,seconds:result.seconds,observations:result.observations.map(x=>({width:x.width,status:x.status,phase:x.active_phase,errors:x.errors.slice(0,5),unknown:x.unknown})),error:result.error?.slice(0,1800)}))}
