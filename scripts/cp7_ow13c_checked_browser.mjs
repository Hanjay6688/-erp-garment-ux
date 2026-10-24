import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
import {cases as retainedCases} from './cp7_ow10_reorder_browser.mjs'

const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_ow13c_checked_browser_fixture.py',op],
  {input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const SAVE='erp_cp7_save_cutting_suggestion_v1',STAGED='Analisis bertahap (hingga 5.000 target)'
const wib=t=>new Date(Date.parse(t)+7*3600000).toISOString().slice(0,16)
async function navigate(ui,page,parentName,childName){
  const parent=page.locator('.sidebar .nav-main').filter({hasText:parentName}).first()
  await parent.waitFor({state:'attached'})
  const menu=page.getByRole('button',{name:'Buka menu',exact:true})
  if(await menu.isVisible()){await menu.click();await ui.expect(page.locator('.sidebar')).toHaveClass(/sidebar-open/)}
  const link=page.getByRole('button',{name:'• '+childName,exact:true})
  if(!await link.isVisible())await parent.click()
  await link.click()
}
async function ordinaryPanel(ui,page){
  await navigate(ui,page,'Gudang','Ringkasan Barang Jadi')
  const history=page.getByRole('region',{name:'Data permintaan ERP',exact:true})
  await history.getByRole('button',{name:'Data permintaan & stok',exact:true}).click()
  await history.getByRole('button',{name:'Analisis, laporan & pengingat seluruh produk',exact:true}).click()
  return page.getByRole('region',{name:'Analisis ERP bersama',exact:true})
}
async function response(page,name,action){
  const result=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/rpc/'+name))
  await action()
  return result
}
async function openTarget(ui,page,target){
  const region=page.getByRole('region',{name:'Hasil analisis bertahap',exact:true})
  await ui.expect(region).toBeVisible({timeout:180000})
  const row=region.locator(`[data-analysis-target="${target}"]`),select=region.getByLabel('Pilih rentang target',{exact:true})
  const pages=await select.locator('option').count()
  for(let i=0;i<pages&&!await row.count();i++){
    await select.selectOption(String(i))
    await ui.expect(region.locator('[data-page-index]')).toHaveAttribute('data-page-index',String(i),{timeout:60000})
  }
  await ui.expect(row).toHaveCount(1)
  await row.getByRole('button',{name:/^Rencanakan Potongan /}).click()
  return page.getByRole('region',{name:'Rencana Potongan ERP',exact:true})
}
async function journey(ui,today,mobile){
  const f=fixture('prepare',{today}),user=await ui.login('OWNER',{label:'ow13c-checked-'+mobile,mobile,
    timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,actor=user.user.id,requests=[],calls=[],shots=[]
  const state=()=>fixture('state',{actor})
  let panel,plan,lost=null
  const shot=async suffix=>{
    await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
    const path=`cp6-proof/t3/OW13C_${mobile?'MOBILE':'DESKTOP'}_${suffix}.png`
    await page.screenshot({path,fullPage:true});shots.push(path)
  }
  page.on('request',r=>{if(r.method()==='POST'&&r.url().includes('/rpc/'))calls.push(r.url().split('/rpc/')[1])})
  try{
    mkdirSync('cp6-proof/t3',{recursive:true})
    await page.setViewportSize(mobile?{width:390,height:844}:{width:1440,height:1000})
    await page.route('**/rest/v1/rpc/'+SAVE,async route=>{
      // Actual server execution and response first; only delivery is interrupted.
      const args=route.request().postDataJSON(),reply=await route.fetch(),body=await reply.json()
      requests.push({args,status:reply.status(),body})
      if(mobile&&!lost){lost=requests.at(-1);await route.abort('failed')}
      else await route.fulfill({response:reply})
    })
    await navigate(ui,page,'Produksi','Buat Potongan')
    const suggestions=page.getByRole('region',{name:'Saran potong',exact:true})
    await suggestions.getByLabel('Penjualan mulai untuk saran potong',{exact:true}).fill(f.query.from_date)
    await suggestions.getByLabel('Penjualan sampai untuk saran potong',{exact:true}).fill(f.query.through_date)
    await suggestions.getByRole('button',{name:'Buka analisis & arsip saran potong',exact:true}).click()
    panel=page.getByRole('region',{name:'Analisis ERP bersama',exact:true})
    await panel.getByRole('button',{name:STAGED,exact:true}).click()
    plan=await openTarget(ui,page,f.target_key)
    await ui.expect(plan).toContainText('Saran ini memakai mesin rencana yang sama.')
    let reply=await response(page,'erp_cp7_get_plan_options_v2',()=>plan.getByRole('button',{name:'Muat pilihan Potongan dari ERP',exact:true}).click())
    assert.equal(reply.status(),200)
    await plan.getByLabel('Gudang bahan rencana',{exact:true}).selectOption(f.location_id)
    reply=await response(page,'erp_cp7_get_plan_options_v2',()=>plan.getByRole('button',{name:'Muat pilihan Potongan dari ERP',exact:true}).click())
    assert.equal(reply.status(),200)
    const options=await reply.json(),roll=options.rolls.find(x=>x.material_id===f.material_id)
    assert.ok(roll,'OW13C_FIXTURE_ROLL_MISSING')
    await ui.expect(plan).toContainText(options.product_sku+' · '+options.product_name)
    await ui.expect(plan).toContainText('Rencana dari analisis bertahap: data per ')
    await plan.getByLabel('PO rencana',{exact:true}).selectOption(f.po_id)
    await plan.getByLabel('Pola rencana',{exact:true}).selectOption(options.patterns[0].id)
    await plan.getByLabel('Waktu pencatatan draf WIB',{exact:true}).fill(wib(new Date(Date.now()-3600000).toISOString()))
    await plan.getByRole('button',{name:'Pilih roll '+roll.number,exact:true}).click()
    for(const[name,value]of[['Keluar roll rencana 1','1'],['Terpakai roll rencana 1','0.5'],['Sisa roll rencana 1','0.5'],['Hasil roll rencana 1','2']])
      await plan.getByLabel(name,{exact:true}).fill(value)
    // An explicit operator edit, with the same server plan engine and Native data.
    await plan.getByLabel('Hasil roll rencana 1',{exact:true}).fill('1')
    await plan.getByLabel('Alasan rencana Potongan',{exact:true}).fill('OW13C explicit browser fixture, edited one PCS, no owner default')
    await plan.getByLabel('Asumsi dan komposisi rencana sudah diperiksa',{exact:true}).check()
    const before=state()
    await plan.getByRole('button',{name:'Simpan rencana Potongan',exact:true}).click()
    if(mobile){
      await ui.expect.poll(()=>lost?.status,{timeout:30000}).toBe(200)
      await ui.expect(plan.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeEnabled()
      assert.equal(lost.status,200)
      const committed=state();assert.deepEqual([committed.drafts,committed.receipts,committed.intents],[1,1,0])
      await page.reload()
      panel=await ordinaryPanel(ui,page)
      plan=await openTarget(ui,page,f.target_key)
      await ui.expect(plan).not.toContainText('Saran ini memakai mesin rencana yang sama.')
      await plan.getByRole('button',{name:'Reconcile transaksi',exact:true}).click()
      await ui.expect(plan).toContainText('Rencana tersimpan.')
      assert.equal(requests.length,2);assert.deepEqual(requests[0].args,requests[1].args)
      assert.deepEqual(requests[0].body,requests[1].body)
    }else await ui.expect(plan).toContainText('Rencana tersimpan.')
    const saved=requests[0]
    assert.equal(saved.status,200);assert.equal(saved.body.cutting_save_guard.feasible,true)
    assert.equal(saved.args.p_payload.cutting_save_contract,'cp7.cutting-checked-save.v1')
    assert.equal(saved.args.p_payload.cutting.rolls[0].yields[0].qty_pcs,'1')
    let after=state();assert.deepEqual([after.drafts,after.receipts,after.intents],[1,1,0])
    assert.deepEqual(after.monetary,before.monetary)
    assert.equal(calls.filter(n=>n==='erp_cp7_save_plan_draft_v2'||n==='erp_cp7_save_plan_draft_v1').length,0)
    await shot('SAVED')
    if(!mobile){
      reply=await response(page,'erp_cp7_get_plan_options_v2',()=>plan.getByRole('button',{name:'Muat pilihan Potongan dari ERP',exact:true}).click())
      assert.equal(reply.status(),200)
      fixture('stock',{root:f.root})
      await plan.getByLabel('Alasan rencana Potongan',{exact:true}).fill('OW13C changed stock after options read must refuse this save')
      reply=await response(page,SAVE,()=>plan.getByRole('button',{name:'Simpan rencana Potongan',exact:true}).click())
      const refusal=await reply.json()
      assert.equal(reply.status(),500);assert.equal(refusal.code,'40001');assert.equal(refusal.message,'CP7_CUTTING_SUGGESTION_SOURCE_CHANGED')
      await ui.expect(plan).toContainText('Data untuk saran potong sudah berubah. Ambil analisis terbaru sebelum menyimpan.')
      after=state();assert.deepEqual([after.drafts,after.receipts,after.intents],[1,1,0])
      await shot('STALE_REFUSED')
    }
    return{status:'PASS',actual_Auth_PostgREST_Native:true,same_staged_plan_engine:true,explicit_edited_one_PCS:true,
      checked_SAVE_proof_validated:true,lost_actual_committed_reply_reopened_in_ordinary_plan:mobile,
      exact_UUID_payload_route_and_response_replayed:mobile,one_draft_one_receipt_no_physical_posting:true,
      actual_Native_stock_change_refused:!mobile,viewport:mobile?390:1440,no_horizontal_overflow:true,shots}
  }catch(error){
    writeFileSync(`cp6-proof/t3/OW13C_${mobile?'MOBILE':'DESKTOP'}_FAILURE.json`,JSON.stringify({error:String(error),requests,calls,
      alerts:await page.getByRole('alert').allTextContents().catch(()=>[])},null,2))
    await page.screenshot({path:`cp6-proof/t3/OW13C_${mobile?'MOBILE':'DESKTOP'}_FAILURE.png`,fullPage:true}).catch(()=>{})
    throw error
  }finally{await page.unrouteAll({behavior:'wait'});fixture('restore',{actor});await user.context.close()}
}
export {navigate as openCuttingMenu}
export function cases(ui,today){return[...retainedCases(ui,today),
  ['OW13C_BROWSER_DESKTOP_EDIT_AND_STALE_REFUSAL',()=>journey(ui,today,false)],
  ['OW13C_BROWSER_MOBILE_LOST_REPLY_ORDINARY_PLAN_REOPEN',()=>journey(ui,today,true)],
]}
