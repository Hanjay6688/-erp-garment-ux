import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'

export const IDS=['OW05_DESKTOP_NATIVE_UNDO_CORRECT_REPOST_NEW24','OW05_MOBILE390_NATIVE_UNDO_CORRECT_REPOST_NEW24']
const fixed=(op,args)=>JSON.parse(execFileSync('python',['../auditor/scripts/ow05-browser-qualification/fixture.py',op],
 {cwd:'../writer',input:JSON.stringify(args),encoding:'utf8',maxBuffer:8*1024*1024}).trim())
const rpc=name=>r=>r.url().endsWith('/rpc/'+name)
async function response(promise){const r=await promise;assert.equal(r.status(),200,await r.text());return r.json()}

async function journey(ui,today,mobile){
 const f=fixed('prepare',{today}),user=await ui.login('OWNER',{label:'ow05-'+(mobile?'phone':'desktop'),mobile,timezoneId:'America/Los_Angeles'})
 const page=user.page,expect=ui.expect,requests=[],progress={}
 const correctionRpc='erp_cp7_correct_mandor_v1',sewingRpc='erp_cp7_save_sewing_completion_v1'
 page.on('request',r=>{if(rpc(correctionRpc)(r)||rpc(sewingRpc)(r))requests.push({rpc:r.url().split('/').at(-1),args:r.postDataJSON()})})
 const sidebar=page.locator('.sidebar')
 if(mobile){const toggle=page.getByRole('button',{name:'Buka menu',exact:true});await toggle.waitFor({state:'visible'});if(!await sidebar.evaluate(e=>e.classList.contains('sidebar-open')))await toggle.click()}
 else await sidebar.waitFor({state:'visible'})
 const link=page.getByRole('button',{name:'• WIP & Sewing',exact:true})
 if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Produksi'}).click()
 await link.click()
 await page.getByLabel('Cari WIP',{exact:true}).fill(f.number)
 await page.getByLabel('Cari WIP',{exact:true}).press('Enter')
 const card=()=>page.locator('.cwip-list>article').filter({hasText:f.number})
 const correction=()=>card().getByRole('region',{name:'Koreksi mandor sesudah jahit',exact:true})
 const sewing=()=>card().getByRole('region',{name:'Selesai jahit '+f.number,exact:true})
 await expect(card()).toHaveCount(1)
 let waiting=page.waitForResponse(rpc('erp_cp7_get_mandor_correction_v1'))
 await correction().getByRole('button',{name:'Koreksi mandor sesudah jahit',exact:true}).click()
 const blocked=await response(waiting)
 assert.equal(blocked.eligible,false);assert.ok(blocked.blockers.some(b=>b.kind==='SEWING'))
 await expect(correction().getByRole('button',{name:'Ganti pembagian ke mandor yang benar',exact:true})).toBeDisabled()
 progress.active_wage_refused=true
 await sewing().getByRole('button',{name:'Catat selesai jahit',exact:true}).click()
 await sewing().getByRole('button',{name:'Batalkan 4 pcs',exact:true}).click()
 await sewing().getByLabel('Alasan batal selesai jahit '+f.number,{exact:true}).fill('Mandor salah; batalkan upah asal sebelum koreksi')
 waiting=page.waitForResponse(rpc(sewingRpc))
 await sewing().getByRole('button',{name:'Batalkan catatan selesai jahit',exact:true}).click()
 await response(waiting)
 await expect(correction().getByRole('button',{name:'Koreksi mandor sesudah jahit',exact:true})).toBeVisible()
 const undone=fixed('observe',{fixture:f})
 assert.equal(undone.old_work_status,'REVERSED');assert.equal(Number(undone.old_payable),0);assert.equal(Number(undone.wip_increment),0)
 waiting=page.waitForResponse(rpc('erp_cp7_get_mandor_correction_v1'))
 await correction().getByRole('button',{name:'Koreksi mandor sesudah jahit',exact:true}).click()
 const eligible=await response(waiting);assert.equal(eligible.eligible,true)
 await correction().getByLabel('Mandor yang benar',{exact:true}).selectOption(f.target)
 await correction().getByLabel('Alasan koreksi mandor',{exact:true}).fill('Ganti seluruh PO ke mandor yang mengerjakan jahitan')
 await correction().getByLabel('Koreksi seluruh PO sudah diperiksa',{exact:true}).check()
 waiting=page.waitForResponse(rpc(correctionRpc))
 await correction().getByRole('button',{name:'Ganti pembagian ke mandor yang benar',exact:true}).click()
 const changed=await response(waiting);assert.equal(changed.status,'PICKUPS_REPLACED');assert.equal(changed.sewing_repost_required,true)
 await expect(page.locator('.cwip-sewing-done')).toContainText('Catat ulang hasil jahit')
 const assigned=fixed('observe',{fixture:f})
 assert.deepEqual(assigned.preserved,undone.preserved)
 assert.equal(assigned.current_mandor,f.target);assert.equal(assigned.old_pickup_status,'REVERSED')
 assert.equal(assigned.current_pickups.length,1);assert.equal(assigned.current_pickups[0][1],f.target)
 assert.equal(assigned.current_pickups[0][2],assigned.original_pickup_at)
 assert.equal(assigned.history_count,1);assert.equal(assigned.context_count,0)
 progress.assignment_preserves_old_history_stock_HPP_and_physical_time=true
 await sewing().getByRole('button',{name:'Catat selesai jahit',exact:true}).click()
 await sewing().getByLabel('Jumlah selesai dijahit '+f.number,{exact:true}).fill('4')
 await sewing().getByLabel('Waktu selesai jahit '+f.number,{exact:true}).fill(f.physical_local)
 await sewing().getByLabel('Tarif baru (berlaku pada waktu jahit) '+f.number,{exact:true}).check()
 await sewing().getByLabel('Catatan selesai jahit '+f.number,{exact:true}).fill('Catat ulang empat pcs pada waktu fisik aslinya')
 await sewing().getByLabel('Selesai jahit '+f.number+' sudah diperiksa',{exact:true}).check()
 waiting=page.waitForResponse(rpc(sewingRpc))
 await sewing().getByRole('button',{name:'Simpan selesai jahit',exact:true}).click()
 const posted=await response(waiting);assert.equal(Number(posted.result.wage_amount),24)
 const final=fixed('observe',{fixture:f})
 assert.equal(final.old_work_status,'REVERSED');assert.equal(final.posted_work_count,1)
 assert.equal(Number(final.old_payable),0);assert.equal(Number(final.new_payable),24);assert.equal(Number(final.wip_increment),24)
 assert.equal(final.history_count,1);assert.equal(final.context_count,0)
 const corrections=requests.filter(r=>r.rpc===correctionRpc),sewings=requests.filter(r=>r.rpc===sewingRpc)
 assert.equal(corrections.length,1);assert.equal(corrections[0].args.p_payload.contractor_id,f.target)
 assert.deepEqual(sewings.map(r=>r.args.p_payload.action),['REVERSE','RECORD'])
 const record=sewings[1].args.p_payload
 assert.equal(record.rate_choice,'NEW');assert.equal(record.qty_pcs,'4')
 assert.equal(Date.parse(record.physical_at),Date.parse(f.physical_iso))
 const viewport=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}))
 assert.ok(viewport.scroll<=viewport.width,JSON.stringify(viewport))
 if(mobile)assert.equal(viewport.width,390)
 return {status:'PASS',real_login:true,fixture_created_by_Native_SQL:true,all_journey_writes_from_actual_UI:true,
  timezone:'America/Los_Angeles',physical_time_WIB_preserved:true,mobile,viewport,progress,
  old_mandor_payable:'0.00',new_mandor_payable:'24.00',WIP_increment:'24.00',posted_work_count:1,
  one_correction_one_history:true,private_contexts:0,nota_UI_not_claimed:true,production_go:false}
}
export async function cases(ui,today){return IDS.map((id,i)=>[id,()=>journey(ui,today,Boolean(i))])}
