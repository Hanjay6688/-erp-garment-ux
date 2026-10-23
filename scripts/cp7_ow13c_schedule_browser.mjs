import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_ow13c_schedule_browser_fixture.py',op],
  {input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const SAVE='erp_cp7_save_staged_production_schedule_v1',GET='erp_cp7_get_staged_production_schedule_v1'
const wib=t=>new Date(Date.parse(t)+7*3600000).toISOString().slice(0,19)
async function open(ui,page,q){
 const parent=page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).first()
 await parent.waitFor({state:'attached'})
 const menu=page.getByRole('button',{name:'Buka menu',exact:true})
 if(await menu.isVisible()){await menu.click();await ui.expect(page.locator('.sidebar')).toHaveClass(/sidebar-open/)}
 const link=page.getByRole('button',{name:'• Ringkasan Barang Jadi',exact:true})
 if(!await link.isVisible())await parent.click()
 await link.click()
 const history=page.getByRole('region',{name:'Data permintaan ERP',exact:true})
 await history.getByRole('button',{name:'Data permintaan & stok',exact:true}).click()
 await history.getByLabel('Permintaan dari tanggal',{exact:true}).fill(q.from_date)
 await history.getByLabel('Permintaan sampai tanggal',{exact:true}).fill(q.through_date)
 await history.getByRole('button',{name:'Jadwal & kekurangan seluruh produk',exact:true}).click()
 return page.getByRole('region',{name:'Jadwal dan kekurangan produksi',exact:true})
}
async function fill(panel,c){
 await panel.getByLabel('Tempat kerja pilihan',{exact:true}).fill(c.work_centre_key)
 await panel.getByLabel('Batas jadwal WIB',{exact:true}).fill(wib(c.through_at))
 await panel.getByLabel('Waktu satu PCS baru',{exact:true}).fill(c.unit_minutes??'')
 for(let i=0;i<c.windows.length;i++){
  if(!await panel.getByLabel(`Mulai kerja ${i+1} WIB`,{exact:true}).count())await panel.getByRole('button',{name:'Tambah waktu kerja',exact:true}).click()
  const v=c.windows[i]
  await panel.getByLabel(`Mulai kerja ${i+1} WIB`,{exact:true}).fill(wib(v.starts_at))
  await panel.getByLabel(`Selesai kerja ${i+1} WIB`,{exact:true}).fill(wib(v.ends_at))
  await panel.getByLabel(`Beban lain ${i+1}`,{exact:true}).fill(v.other_load_minutes??'')
 }
 for(const p of c.positions){
  await panel.getByLabel('Jumlah '+p.position_key,{exact:true}).fill(p.eligible_input_pcs)
  const target=panel.getByLabel('Tujuan '+p.position_key,{exact:true})
  if(await target.count()){
   await target.selectOption(p.target_key??'')
   await panel.getByLabel('Bagus '+p.position_key,{exact:true}).fill(p.yield_numerator??'')
   await panel.getByLabel('Acuan '+p.position_key,{exact:true}).fill(p.yield_denominator??'')
  }
  for(const s of p.remaining_steps)await panel.getByLabel(s.stage+' menit '+p.position_key,{exact:true}).fill(s.remaining_minutes??'')
 }
 await panel.getByLabel('Alasan jadwal',{exact:true}).fill('Actual disposable browser work review, explicit fixture assumptions only')
}
async function journey(ui,today,mobile){
 const user=await ui.login('OWNER',{label:'ow13c-schedule-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
 const page=user.page,actor=user.user.id,requests=[],shots=[]
 let f,panel,lost=null,sourceReply,captureReply=null,workspaceReply=null
 const state=()=>fixture('state',{actor})
 const shot=async suffix=>{mkdirSync('cp6-proof/t3',{recursive:true});const path=`cp6-proof/t3/SCHEDULE_${mobile?'MOBILE':'DESKTOP'}_${suffix}.png`;await page.screenshot({path,fullPage:true});shots.push(path)}
 try{
  f=fixture('prepare',{today});const before=state()
  await page.setViewportSize(mobile?{width:390,height:844}:{width:1440,height:1000})
  await page.route('**/rest/v1/rpc/'+SAVE,async route=>{
   const args=route.request().postDataJSON(),reply=await route.fetch(),body=await reply.json()
   requests.push({args,status:reply.status(),body})
   if(mobile&&!lost){lost=requests.at(-1);await route.abort('failed')}else await route.fulfill({response:reply})
  })
  panel=await open(ui,page,f.query)
  const read=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/rpc/'+GET)).catch(error=>({error}))
  const captured=page.waitForResponse(r=>{
   if(r.request().method()!=='POST'||!r.url().endsWith('/rpc/erp_cp7_request_staged_analysis_v1'))return false
   const args=r.request().postDataJSON(),q=args?.p_query
   // The initial-auto panel uses this same endpoint concurrently. Bind the
   // observation to this work form's complete query and durable request.
   return typeof args.p_request==='string'&&q?.from_date===f.query.from_date&&q?.through_date===f.query.through_date&&q?.group_mode===f.query.group_mode
  })
  await panel.getByRole('button',{name:'Ambil stok proses terbaru',exact:true}).click()
  const capturedResponse=await captured;captureReply={args:capturedResponse.request().postDataJSON(),status:capturedResponse.status(),body:await capturedResponse.json()}
  assert.deepEqual(Object.keys(captureReply.args.p_query).sort(),['from_date','group_mode','through_date'])
  assert.equal(captureReply.status,200,JSON.stringify(captureReply))
  sourceReply=await read;if(sourceReply.error)throw sourceReply.error;assert.equal(sourceReply.status(),200);const workspace=await sourceReply.json();workspaceReply=workspace
  assert.equal(workspace.production_capture_state,'COMPLETE')
  await ui.expect(panel.getByLabel('Tempat kerja pilihan',{exact:true})).toBeVisible()
  await fill(panel,f.config)
  if(mobile){
   await panel.getByRole('button',{name:'Simpan jadwal yang diperiksa',exact:true}).click()
   await ui.expect(panel.getByRole('button',{name:'Ulangi simpan jadwal yang sama',exact:true})).toBeVisible()
   assert.equal(lost?.status,200)
   await page.reload();panel=await open(ui,page,f.query)
   await panel.getByRole('button',{name:'Ulangi simpan jadwal yang sama',exact:true}).click()
   await ui.expect(panel).toContainText('Jadwal tersimpan')
   assert.equal(requests.length,2);assert.deepEqual(requests[0].args,requests[1].args);assert.deepEqual(requests[0].body,requests[1].body)
   const after=state();assert.equal(after.plans,before.plans+1);assert.equal(after.commands,before.commands+1);assert.deepEqual(after.physical,before.physical)
  }else{
   await panel.getByLabel('Waktu satu PCS baru',{exact:true}).fill('3')
   fixture('stock',{root:f.root})
   await panel.getByRole('button',{name:'Simpan jadwal yang diperiksa',exact:true}).click()
   await ui.expect(panel).toContainText('Isianmu masih ada')
   await ui.expect(panel.getByLabel('Waktu satu PCS baru',{exact:true})).toHaveValue('3')
   await ui.expect(panel.getByRole('button',{name:'Simpan jadwal yang diperiksa',exact:true})).toBeDisabled()
   assert.equal(requests.length,1);assert.equal(requests[0].status,500);assert.equal(requests[0].body.code,'40001')
   await ui.expect(panel.getByRole('button',{name:'Ambil stok proses terbaru',exact:true})).toBeEnabled()
   await ui.expect(panel.getByRole('button',{name:'Ulangi simpan jadwal yang sama',exact:true})).toHaveCount(0)
   const after=state();assert.equal(after.plans,before.plans);assert.equal(after.commands,before.commands)
  }
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
  await shot('REVIEWED')
  fixture('deactivate',{actor})
  // The same access token must fail a fresh server read; no mock response.
  const denied=await user.context.request.post(sourceReply.url(),{data:{p_source_request:workspace.source_request_id},headers:sourceReply.request().headers()})
  assert.equal(denied.status(),403)
  return{status:'PASS',actual_Auth_PostgREST_browser:true,viewport:mobile?390:1440,no_horizontal_overflow:true,
   dirty_form_stale_refusal:!mobile,first_confirmed_refusal_releases_only_new_request:!mobile,lost_committed_response_same_UUID_reopen:mobile,current_token_denied:true,shots,
   production_quantity_claim:false}
 }catch(error){
  mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync(`cp6-proof/t3/SCHEDULE_${mobile?'MOBILE':'DESKTOP'}_FAILURE.json`,JSON.stringify({error:String(error),captureReply,workspaceReply,requests,lost,alerts:await page.getByRole('alert').allTextContents().catch(()=>[])},null,2));await shot('FAILURE').catch(()=>{});throw error
 }finally{fixture('restore',{actor});await user.context.close()}
}
export function cases(ui,today){return[
 ['OW13C_SCHEDULE_BROWSER_DESKTOP_STALE_DIRTY',()=>journey(ui,today,false)],
 ['OW13C_SCHEDULE_BROWSER_MOBILE_LOST_REPLY',()=>journey(ui,today,true)],
]}
