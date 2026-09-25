// Rev5: actual Auth/browser/HTTP, unchanged candidate parser; no response replacement.
// Fixture API identities and seed visibility isolation are disclosed in fixture receipts.
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { execFileSync } from 'node:child_process'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
const here=dirname(fileURLToPath(import.meta.url))
const auditRoot=resolve(process.cwd(),'../auditor')
const require=createRequire(resolve(auditRoot,'package.json'))
const parserSource=readFileSync(resolve(auditRoot,'src/laundryQcModel.ts'),'utf8')
const parserSha=createHash('sha256').update(parserSource).digest('hex')
const compiled=require('esbuild').transformSync(parserSource,{loader:'ts',format:'cjs',target:'node22'}).code
const parserModule={exports:{}}
new Function('module','exports',compiled)(parserModule,parserModule.exports)
const states={}
const rpc='erp_get_laundry_qc_workspace_v1'
const rpcUrl='**/rpc/'+rpc
const labels={LAUNDRY:'Laundry',QC:'QC & Final SKU'}
const placeholders={LAUNDRY:'Cari PO, Potongan, atau vendor…',QC:'Cari PO, Potongan, receipt, atau histori…'}
function parse(body){
  try{const w=parserModule.exports.parseLaundryQcWorkspace(body);return{ok:true,scope:w.scope,source_sha256:parserSha}}
  catch(e){return{ok:false,error:String(e.message),source_sha256:parserSha}}
}
function inspect(body,scope){
  return{parser:parse(body),qty:scope==='LAUNDRY'
    ?body?.deliveries?.reduce((s,r)=>s+Number(r.physical_outstanding_qty_pcs),0)
    :body?.qc_queue?.reduce((s,r)=>s+Number(r.available_for_qc_qty_pcs),0),
    seed_ids_absent:!JSON.stringify(body).includes('a1000000-0000-0000-0000-000000000001')
      &&!JSON.stringify(body).includes('a2000000-0000-0000-0000-000000000001'),
    row_counts:{products:body?.lookups?.products?.length,ready:body?.ready_batches?.length,
      deliveries:body?.deliveries?.length,qc:body?.qc_queue?.length}}
}
async function navigate(page,label){
 const target=page.locator('.sidebar .submenu button').filter({hasText:label})
 if(await target.isVisible()){await target.click();return}
 const buttons=page.locator('.sidebar .nav-main')
 for(let i=0;i<await buttons.count();i++){await buttons.nth(i).click();if(await target.isVisible()){await target.click();return}}
 throw Error('NAV_TARGET_MISSING:'+label)
}
function target(page,scope){return page.locator('.clq-kpis article').nth(scope==='LAUNDRY'?1:0).locator('strong')}
function fixture(scope,today){
 const raw=execFileSync('python',[resolve(here,'gpt_unknown_fixture_rev5.py'),scope,String(today)],
   {cwd:resolve(process.cwd(),'../writer'),encoding:'utf8',maxBuffer:4*1024*1024})
 return JSON.parse(raw.trim().split('\n').at(-1))
}
function responseFor(page,scope,query){
 return page.waitForResponse(r=>r.url().endsWith('/rpc/'+rpc)&&r.request().method()==='POST'
   &&r.request().postDataJSON().p_scope===scope&&r.request().postDataJSON().p_query===query)
}
async function healthy(ui,today,scope){
 const observed={scope,stage:'FIXTURE'}
 let u
 try{
   const f=fixture(scope,today);observed.fixture=f;states[scope]={fixture:f,healthy:false}
   observed.stage='REAL_AUTH_CONTROL'
   u=await ui.login('OWNER',{label:'unknown5-control-'+scope})
   const c=await u.rpc(rpc,{p_scope:scope,p_query:f.query})
   observed.auth_rpc={status:c.status,...inspect(c.body,scope)}
   if(c.status!==200||!observed.auth_rpc.parser.ok||!observed.auth_rpc.seed_ids_absent||observed.auth_rpc.qty!==f.expected_qty)
     return{status:'INCOMPLETE',...observed,workspace:c.body}
   observed.stage='REAL_BROWSER_RENDER'
   await navigate(u.page,labels[scope])
   const wait=responseFor(u.page,scope,f.query)
   await u.page.getByPlaceholder(placeholders[scope],{exact:true}).fill(f.query)
   const resp=await wait
   observed.browser_rpc={status:resp.status(),...inspect(await resp.json(),scope)}
   await ui.expect(target(u.page,scope)).toHaveText(String(f.expected_qty))
   await ui.expect(u.page.locator('.clq-alert.error')).toHaveCount(0)
   observed.rendered_qty=await target(u.page,scope).innerText()
   if(!observed.browser_rpc.parser.ok||!observed.browser_rpc.seed_ids_absent||observed.browser_rpc.qty!==f.expected_qty)
     return{status:'INCOMPLETE',...observed}
   states[scope].healthy=true
   states[scope].control=observed
   return{status:'PASS',...observed,oracle:'Fresh API UUIDv4 identities; actual filtered Auth RPC and real UI must both show Laundry20/QC10, with unchanged parser accepting all response IDs.'}
 }catch(e){return{status:'INCOMPLETE',...observed,error:String(e.stack||e).slice(0,3000)}}
 finally{if(u)await u.context.close()}
}
async function unknown(ui,today,scope){
 const state=states[scope]
 if(!state?.healthy)return{status:'INCOMPLETE',scope,stage:'HEALTHY_CONTROL_REQUIRED',healthy_control_pass:false}
 const observed={scope,healthy_control_pass:true,fixture:state.fixture}
 const f=state.fixture
 let u
 try{
   u=await ui.login('OWNER',{label:'unknown5-fault-'+scope})
   const {page}=u
   let dropped=0
   const handler=async route=>{
     if(route.request().method()==='POST'&&route.request().postDataJSON().p_scope===scope){
       dropped++;await route.abort('failed')
     }else await route.continue()
   }
   observed.stage='INITIAL_READ_FAILURE'
   await page.route(rpcUrl,handler)
   await navigate(page,labels[scope])
   await ui.expect(page.locator('.clq-alert.error')).toBeVisible()
   await ui.expect(page.getByRole('button',{name:'Muat ulang data',exact:true})).toBeEnabled()
   await page.getByPlaceholder(placeholders[scope],{exact:true}).fill(f.query)
   await ui.expect.poll(()=>dropped).toBeGreaterThanOrEqual(2)
   await ui.expect(page.locator('.clq-alert.error')).toBeVisible()
   await ui.expect(page.getByRole('button',{name:'Muat ulang data',exact:true})).toBeEnabled()
   observed.initial_kpis=await page.locator('.clq-kpis article').evaluateAll(es=>es.map(e=>({
     label:e.querySelector('span')?.textContent,value:e.querySelector('strong')?.textContent,text:e.textContent})))
   observed.initial_error=await page.locator('.clq-alert.error').innerText()
   observed.initial_writer_locked=(await page.locator('.connected-laundry-qc-page').innerText())
     .includes('Data belum tersedia; semua tombol transaksi tetap terkunci.')
   observed.dropped_reads=dropped
   observed.stage='HEALTHY_REFETCH_AFTER_FAULT_REMOVED'
   await page.unroute(rpcUrl,handler)
   const wait=responseFor(page,scope,f.query)
   await page.getByRole('button',{name:'Muat ulang data',exact:true}).click()
   const resp=await wait
   observed.refetch={status:resp.status(),...inspect(await resp.json(),scope)}
   await ui.expect(target(page,scope)).toHaveText(String(f.expected_qty))
   await ui.expect(page.locator('.clq-alert.error')).toHaveCount(0)
   observed.refetched_qty=await target(page,scope).innerText()
   if(resp.status()!==200||!observed.refetch.parser.ok||!observed.refetch.seed_ids_absent||observed.refetch.qty!==f.expected_qty)
     return{status:'INCOMPLETE',...observed}
   const primary=observed.initial_kpis[scope==='LAUNDRY'?1:0]
   return{status:primary?.value?.trim()==='0'?'COUNTEREXAMPLE':'PASS',...observed,
     positive_control_status:'PASS',refetch_control_status:'PASS',
     oracle:'M3825 unknown is not zero. Healthy Auth/UI and post-fault refetch must render true nonzero20/10; error/write-lock mitigation is recorded, not mistaken for a final financial result.',
     mutation_bypass_claimed:false,false_financial_finality_claimed:false,refetch_product_defect_claimed:false}
 }catch(e){return{status:'INCOMPLETE',...observed,error:String(e.stack||e).slice(0,3000)}}
 finally{if(u)await u.context.close()}
}
export async function cases(ui,today){
 return[
  ['G8UI:UNKNOWN:LAUNDRY_HEALTHY_CONTROL:rev5',()=>healthy(ui,today,'LAUNDRY')],
  ['G8UI:UNKNOWN:LAUNDRY_INITIAL_READ:rev5',()=>unknown(ui,today,'LAUNDRY')],
  ['G8UI:UNKNOWN:QC_HEALTHY_CONTROL:rev5',()=>healthy(ui,today,'QC')],
  ['G8UI:UNKNOWN:QC_INITIAL_READ:rev5',()=>unknown(ui,today,'QC')],
 ]
}
