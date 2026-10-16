// Genuine UAT bundle, real disposable Auth + Native public RPC, transport redirected by the isolated host.
import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {writeFileSync} from 'node:fs'
import * as master from '../../../auditor/scripts/cp7_master_browser.mjs'
import * as autoPo from '../../../auditor/scripts/cp7_auto_po_browser.mjs'
const hidden=['Ringkasan Gudang','Penjualan & Invoice','Semua Invoice','Retur Penjualan','Pembayaran Pelanggan','Riwayat Pelanggan',
 'Ringkasan Keuangan','Kas & Bank','Piutang Pelanggan','Payroll & Kasbon','Absensi & Rate Harian','Jurnal & Transaksi Lain',
 'Laporan & Tutup Buku','Reminder','Pengaturan ERP','Tutup Periode','Audit Trail']
const fixture=(operation,payload={})=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_cp17_fix_browser_fixture.py',operation],
 {input:JSON.stringify(payload),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const noSideScroll=async(ui,page)=>{assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true)}
async function failure(page,name,error,state,requests){
 writeFileSync(`cp6-proof/t3/SOL_UAT_${name}_FAILURE.json`,JSON.stringify({error:String(error),state,requests,screen:await page.locator('main').innerText().catch(()=>'' )},null,2))
}
async function hiddenPhone(ui){
 const u=await ui.login('OWNER',{label:'sol-r2-uat-hidden',mobile:true}),p=u.page
 try{
  assert.match(await p.locator('.topbar').innerText(),/UAT/)
  await p.getByRole('button',{name:'Buka menu',exact:true}).click()
  const seen=new Set()
  for(const section of ['Produksi','Gudang','Penjualan','Keuangan','Master Data','Pengaturan & Audit']){
   const branch=p.locator('.sidebar .nav-main').filter({hasText:section})
   if(await branch.count()){
    if(!(await branch.getAttribute('class'))?.split(' ').includes('active'))await branch.click()
    for(const text of await p.locator('.sidebar .submenu button').allInnerTexts())seen.add(text.replace(/^•\s*/,''))
    for(const label of hidden)assert.equal(await p.getByRole('button',{name:'• '+label,exact:true}).count(),0,label)
   }
  }
  assert.equal(seen.size,30)
  const dashboard=await p.locator('.page-wrap').innerText()
  assert.ok(!/284[.,]6|Rp\s*284/.test(dashboard),'No sample book balance on UAT dashboard')
  await noSideScroll(ui,p)
  return{status:'PASS',real_auth:true,actual_build_mode:'UAT_AUTH_SIMULATION',hidden_labels:17,visible_non_dashboard_menus:30,global_mode_shown:true,sample_balance_absent:true,hosted_contact:false}
 }finally{await u.context.close()}
}
export function cases(ui,today){
 const h={fixture,noSideScroll,failure}
 const customer=master.cases(ui,today,h).find(([id])=>id==='CP17_BROWSER_R2_MASTER_CUSTOMERS_DESKTOP')
 const po=autoPo.cases(ui,today,h).find(([id])=>id==='CP17_BROWSER_R2_D15_6_AUTO_PO_MOBILE')
 assert.ok(customer&&po)
 return[
  ['SOL_R2_UAT_REAL_AUTH_HIDDEN_MENUS_PHONE',()=>hiddenPhone(ui)],
  ['SOL_R2_UAT_CUSTOMER_LIFECYCLE_DESKTOP',async()=>({...await customer[1](),provider_case:customer[0],actual_build_mode:'UAT_AUTH_SIMULATION'})],
  ['SOL_R2_UAT_AUTO_PO_NATIVE_PHONE',async()=>({...await po[1](),provider_case:po[0],actual_build_mode:'UAT_AUTH_SIMULATION'})],
 ]
}
