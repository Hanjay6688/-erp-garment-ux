import assert from 'node:assert/strict'
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs'
import {fileURLToPath} from 'node:url'
const inventory=JSON.parse(readFileSync(new URL('./UI_INVENTORY.json',import.meta.url),'utf8'))
const output='cp6-proof/t3/'
const write=(name,value)=>{mkdirSync(output,{recursive:true});writeFileSync(output+name,JSON.stringify(value,null,2)+'\n')}
const stockHash=ui=>ui.sql(`set timezone='UTC'; select jsonb_build_object('stock',(select md5(coalesce(jsonb_agg(to_jsonb(x)order by id),'[]'::jsonb)::text)from erp.fg_stock_movements x),'raw',(select md5(coalesce(jsonb_agg(to_jsonb(x)order by id),'[]'::jsonb)::text)from erp.material_stock_movements x),'journals',(select md5(coalesce(jsonb_agg(to_jsonb(x)order by id),'[]'::jsonb)::text)from erp.journal_lines x));`)
async function openMenu(page){const b=page.getByRole('button',{name:'Buka menu',exact:true});if(await b.isVisible())await b.click()}
async function choose(page,section,label){
 await openMenu(page)
 const sub=page.getByRole('button',{name:'• '+label,exact:true})
 if(!await sub.isVisible())await page.locator('.sidebar .nav-main').filter({has:page.locator('span').filter({hasText:new RegExp('^'+section.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'$')})}).click()
 await sub.click()
}
async function routes(ui,mobile){
 const owner=await ui.login('OWNER',{label:'astra-all-routes-'+(mobile?'mobile':'desktop'),mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
 const page=owner.page;const events=[],errors=[],rows=[];let pending=0
 page.on('pageerror',e=>errors.push(e.message))
 page.on('request',r=>{if(r.url().includes('/rpc/'))pending++})
 page.on('requestfailed',r=>{if(r.url().includes('/rpc/')){pending--;events.push({name:r.url().split('/').at(-1),failure:r.failure()?.errorText})}})
 page.on('response',async r=>{if(r.url().includes('/rpc/')){let b;try{b=await r.json()}catch{}events.push({name:r.url().split('/').at(-1),status:r.status(),args:r.request().postDataJSON(),code:b?.code,message:b?.message});pending--}})
 const before=stockHash(ui)
 try{
  const all=[['Dashboard','Dashboard'],...Object.entries(inventory.sections).flatMap(([s,labels])=>labels.map(l=>[s,l]))]
  assert.equal(all.length,48)
  for(const [section,label] of all){
   const start=events.length;const priorErrors=errors.length;let failure=null
   try{
    if(label==='Dashboard'){await openMenu(page);await page.locator('.sidebar .nav-main').filter({hasText:'Dashboard'}).click()}
    else await choose(page,section,label)
    await ui.expect(page.locator('.top-title strong')).toBeVisible()
    await ui.expect(page.getByText('Memuat workspace dan guardrail transaksi.',{exact:true})).not.toBeVisible({timeout:30000})
    await ui.expect.poll(async()=>await page.locator('.page-wrap').innerText(),{timeout:30000}).not.toMatch(/Menyiapkan[^\n]*…|Memuat workspace dan guardrail transaksi\./)
    await ui.expect.poll(()=>pending,{timeout:30000}).toBe(0)
    await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))))
    assert.ok((await page.locator('.page-wrap').innerText()).trim().length>5,'Empty work area')
    assert.equal(errors.length,priorErrors,'Unhandled browser exception')
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Whole document overflows viewport')
   }catch(e){failure=String(e.stack||e)}
   const body=await page.locator('.page-wrap').innerText().catch(()=>''),calls=events.slice(start)
   const title=await page.locator('.top-title strong').innerText().catch(()=>'')
   rows.push({section,label,title,status:failure?'INCOMPLETE':'PASS',failure,real_rpc_calls:calls,body,view_only_notice:/simulasi|belum terhubung|pratinjau|contoh data/i.test(body),visible_buttons:await page.locator('.page-wrap button:visible').allTextContents()})
   write('ASTRA_UI_'+(mobile?'MOBILE':'DESKTOP')+'_ROUTES.json',{inventory,rows,errors})
   if(['Ringkasan Barang Jadi','Laporan & Tutup Buku','Penjualan & Invoice'].includes(label))await page.screenshot({path:output+'ASTRA_UI_'+(mobile?'MOBILE':'DESKTOP')+'_'+label.replace(/[^a-zA-Z]/g,'_')+'.png',fullPage:true})
  }
  const after=stockHash(ui);assert.equal(after,before,'Navigation must not change money or stock')
  const bad=rows.filter(r=>r.status!=='PASS'),httpFailures=rows.flatMap(r=>r.real_rpc_calls.filter(x=>x.status>=500).map(c=>({label:r.label,...c})))
  return{status:bad.length||httpFailures.length?'COUNTEREXAMPLE':'PASS',oracle_origin:'ASTRA_ROUTE_INVENTORY_AND_RUNTIME',fixture_origin:'FROZEN_RUNTIME_BASELINE_UNCHANGED',routes:rows.length,failed_routes:bad.map(r=>({label:r.label,error:r.failure})),server_errors:httpFailures,stock_money_unchanged:true,viewport:mobile?'390x844':'1440x1000',scope:'ROUTE_RENDER_READ_PERMISSION_SMOKE_NOT_EVERY_COMMAND_BUSINESS_ACCEPTANCE',connected_rpc_routes:rows.filter(r=>r.real_rpc_calls.length).length,view_only_notices:rows.filter(r=>r.view_only_notice).map(r=>r.label),production_go:false}
 }finally{await owner.context.close()}
}
async function denied(ui){
 const owner=await ui.login('OWNER',{label:'astra-finance-owner-control'}),worker=await ui.login('GUDANG',{label:'astra-finance-denied',mobile:true})
 const observed=[]
 owner.page.on('response',async r=>{if(r.url().includes('/rpc/')){let body;try{body=await r.json()}catch{}observed.push({name:r.url().split('/').at(-1),status:r.status(),args:r.request().postDataJSON(),body})}})
 try{
  await choose(owner.page,'Keuangan','Laporan & Tutup Buku')
  await ui.expect.poll(()=>observed.filter(x=>x.status===200&&/finance|report/i.test(x.name)).length,{timeout:30000}).toBeGreaterThan(0)
  const read=observed.filter(x=>x.status===200&&/finance|report/i.test(x.name));const results=[]
  for(const x of read){const a=await owner.rpc(x.name,x.args),b=await worker.rpc(x.name,x.args),c=await ui.anonRpc(x.name,x.args);assert.equal(a.status,200);results.push({name:x.name,owner:a.status,worker:b,anon:c})}
  await openMenu(worker.page)
  assert.equal(await worker.page.getByRole('button',{name:'• Laporan & Tutup Buku',exact:true}).count(),0)
  const safe=results.every(r=>r.worker.status>=400&&r.anon.status>=400)
  return{status:safe?'PASS':'COUNTEREXAMPLE',results,real_auth:true,oracle_origin:'ASTRA_OWNER_FINANCE_EXCLUSION',production_go:false}
 }finally{await owner.context.close();await worker.context.close()}
}
export async function cases(ui,today){return [['AS20-47_DESKTOP_ALL48',()=>routes(ui,false)],['AS20-47_MOBILE_ALL48',()=>routes(ui,true)],['AS20-01_47_FINANCE_ROLE_BOUNDARY',()=>denied(ui)]]}
