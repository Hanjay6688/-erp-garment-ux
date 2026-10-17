// R3-03 / owner D16-5: "Laporan & Tutup Buku" is one menu; closing the books is its "Tutup Buku" tab. On the connected page,
// desktop and phone, real Auth and PostgREST on the committed copy: OWNER sees the "Laporan" and "Tutup Buku" tabs, the period
// panel only on the second, and its close/reopen history equal to the Native audit rows (fixture r303_period_history, read
// from erp.audit_logs, never from the facade's answer); there is no "Tutup Periode" menu any more. Seeded ADMIN has the
// report right but not the close right: the report shows, no tab and no period panel, and the period RPC is never called.
import assert from'node:assert/strict'
import{mkdirSync}from'node:fs'
async function reportPage(ui,page){
 const open=page.getByRole('button',{name:'Buka menu',exact:true});if(await open.isVisible())await open.click()
 const link=page.getByRole('button',{name:'• Laporan & Tutup Buku',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Keuangan'}).click();await link.click()
 await ui.expect(page.getByRole('heading',{name:'Laporan & Tutup Buku',exact:true})).toBeVisible()
}
async function noMenu(ui,page,label){
 const open=page.getByRole('button',{name:'Buka menu',exact:true});if(await open.isVisible())await open.click()
 // Expand "Pengaturan & Audit" until its always-connected entry shows, so the absence below is checked on an open list.
 const known=page.getByRole('button',{name:'• Impor data awal',exact:true})
 if(!await known.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Pengaturan & Audit'}).click()
 await ui.expect(known).toBeVisible()
 await ui.expect(page.getByRole('button',{name:'• '+label,exact:true})).toHaveCount(0)
 const close=page.getByRole('button',{name:'Tutup menu',exact:true});if(await close.isVisible())await close.click()
}
async function journey(ui,today,mobile,h){
 const name=`CP17_BROWSER_R3_03_PERIOD_TAB_${mobile?'MOBILE':'DESKTOP'}`,seen={},requests=[]
 const owner=await ui.login('OWNER',{label:'cp17-r3-03-owner-'+(mobile?'mobile':'desktop'),mobile}),page=owner.page
 page.on('request',r=>{if(r.url().includes('/rpc/erp_cp7_'))requests.push(r.url().split('/rpc/')[1])})
 let admin=null
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const want=seen.want=h.fixture('r303_period_history',{})
  await noMenu(ui,page,'Tutup Periode');await reportPage(ui,page)
  const tabs=page.getByRole('tablist',{name:'Bagian laporan dan tutup buku',exact:true})
  assert.deepEqual(await tabs.getByRole('tab').allInnerTexts(),['Laporan','Tutup Buku'])
  await ui.expect(tabs.getByRole('tab',{name:'Laporan',exact:true,selected:true})).toBeVisible()
  await ui.expect(page.getByRole('region',{name:'Arsip penutupan keuangan',exact:true})).toBeVisible()
  await ui.expect(page.getByRole('region',{name:'Kelola periode pembukuan',exact:true})).toHaveCount(0)
  await tabs.getByRole('tab',{name:'Tutup Buku',exact:true}).click()
  const panel=page.getByRole('region',{name:'Kelola periode pembukuan',exact:true});await ui.expect(panel).toBeVisible()
  await ui.expect(page.getByRole('region',{name:'Posisi keuangan tercatat',exact:true})).toHaveCount(0)
  const history=panel.getByRole('region',{name:'Riwayat tutup dan buka buku',exact:true});await ui.expect(history).toBeVisible()
  const items=history.locator('article');await ui.expect(items).toHaveCount(want.count)
  if(want.count===0)await ui.expect(history).toContainText('Belum ada penutupan atau pembukaan kembali yang tercatat.')
  else{
   const first=want.first,text=first.action==='CLOSE'?`Ditutup sampai ${first.to}`:first.to===null?'Seluruh periode dibuka kembali':`Dibuka kembali; tetap tertutup sampai ${first.to}`
   await ui.expect(items.first()).toContainText(text);if(first.reason)await ui.expect(items.first()).toContainText(first.reason)
   await ui.expect(items.first()).toContainText(first.from===null?'sebelumnya belum ada yang tertutup':`sebelumnya tertutup sampai ${first.from}`)
  }
  await h.noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_OWNER.png`,fullPage:true})
  assert.ok(requests.includes('erp_cp7_get_period_control_v1'),requests)
  // Seeded ADMIN: the report right without the close right.
  admin=await ui.login('ADMIN',{label:'cp17-r3-03-admin-'+(mobile?'mobile':'desktop'),mobile});const ap=admin.page,adminRequests=[]
  ap.on('request',r=>{if(r.url().includes('/rpc/erp_cp7_'))adminRequests.push(r.url().split('/rpc/')[1])})
  await noMenu(ui,ap,'Tutup Periode');await reportPage(ui,ap)
  await ui.expect(ap.getByRole('region',{name:'Posisi keuangan tercatat',exact:true})).toBeVisible()
  await ui.expect(ap.getByRole('tablist',{name:'Bagian laporan dan tutup buku',exact:true})).toHaveCount(0)
  await ui.expect(ap.getByRole('tab',{name:'Tutup Buku',exact:true})).toHaveCount(0)
  await ui.expect(ap.getByRole('region',{name:'Kelola periode pembukuan',exact:true})).toHaveCount(0)
  await ui.expect(ap.getByRole('region',{name:'Pemeriksaan tutup buku',exact:true})).toHaveCount(0)
  assert.ok(adminRequests.includes('erp_cp7_get_finance_report_v1')&&!adminRequests.includes('erp_cp7_get_period_control_v1'),adminRequests)
  await h.noSideScroll(ui,ap);await ap.screenshot({path:`cp6-proof/t3/${name}_ADMIN.png`,fullPage:true})
  return{status:'PASS',finding:'R3-03',owner_decision:'D16-5',phone:mobile,one_menu_two_tabs:true,no_tutup_periode_menu:true,history_rows_shown:want.count,
   history_equals_native_audit_rows:true,admin_report_without_close_tab:true,admin_never_calls_period_rpc:true}
 }catch(error){await h.failure(page,name,error,seen,requests);throw error}
 finally{await owner.context.close();if(admin)await admin.context.close()}
}
export function cases(ui,today,h){
 return[['CP17_BROWSER_R3_03_PERIOD_TAB_DESKTOP',()=>journey(ui,today,false,h)],['CP17_BROWSER_R3_03_PERIOD_TAB_MOBILE',()=>journey(ui,today,true,h)]]
}
