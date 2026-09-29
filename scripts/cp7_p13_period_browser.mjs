import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_p13_period_fixture.py',op,JSON.stringify(p)],{cwd:'../writer',encoding:'utf8'}).trim())
async function open(ui,p){
 await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:'Keuangan'})).toBeAttached()
 const menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=p.getByRole('button',{name:'• Laporan & Tutup Buku',exact:true});if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Keuangan'}).click();await link.click()
 await ui.expect(p.getByRole('heading',{name:'Laporan & Tutup Buku',exact:true})).toBeVisible()
}
async function period(ui,f,mobile){
 const user=await ui.login('OWNER',{label:'p13-period-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),p=user.page,suffix=mobile?'MOBILE':'DESKTOP'
 try{
  await open(ui,p);const panel=p.getByRole('region',{name:'Kelola periode pembukuan',exact:true}),before=fixture('read',f),reason='Browser period '+suffix
  await panel.getByLabel('Tanggal pemeriksaan tutup buku',{exact:true}).fill(f.day)
  await ui.expect(panel).toContainText('Penghalang: 0.')
  await panel.getByLabel('Alasan perubahan periode',{exact:true}).fill(reason)
  const reviewed=panel.getByLabel('Saya sudah memeriksa tanggal, penghalang, dan alasan perubahan periode.',{exact:true});await reviewed.check()
  let lost=false,first=null,replay=null
  if(mobile)await p.route('**/rest/v1/rpc/erp_cp7_save_period_control_v1',async route=>{
   const body=route.request().postDataJSON()
   if(body.p_action==='CLOSE'&&!lost){first=body;const response=await route.fetch();if(response.status()!==200){await route.fulfill({response});return}lost=true;await route.abort('failed')}
   else{if(body.p_action==='CLOSE')replay=body;await route.continue()}
  })
  const close=panel.getByRole('button',{name:'Tutup buku dan simpan arsip',exact:true});await ui.expect(close).toBeEnabled();await close.click()
  await ui.expect.poll(()=>fixture('read',f).period.control.closed_through,{timeout:20000}).toBe(f.day)
  if(mobile){await ui.expect(panel.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible();await p.reload();await open(ui,p);await panel.getByRole('button',{name:'Reconcile transaksi',exact:true}).click();await ui.expect(panel.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0);assert.ok(lost);assert.deepEqual(replay,first)}
  await ui.expect(panel).toContainText('Periode tertutup sampai '+f.day)
  const after=fixture('read',f);assert.equal(after.filings.length,before.filings.length+1);assert.deepEqual(after.business,before.business);assert.deepEqual(after.filings.slice(0,-1),before.filings)
  const filed=after.filings.at(-1);assert.equal(filed.reason,reason);assert.equal(filed.closed_through,f.day);assert.equal(filed.readiness.status,'READY')
  const archives=p.getByRole('region',{name:'Arsip penutupan keuangan',exact:true});const original=archives.locator('.cproc-receipt').filter({hasText:reason});await ui.expect(original).toHaveCount(1);await original.click();await ui.expect(p.getByRole('region',{name:'Saldo asli saat penutupan',exact:true})).toContainText(reason)
  await ui.expect.poll(()=>panel.evaluate(el=>{const b=el.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
  mkdirSync('cp6-proof/t3',{recursive:true});await p.evaluate(()=>window.scrollTo(0,0));await p.screenshot({path:`cp6-proof/t3/P13_PERIOD_${suffix}.png`,fullPage:true})
  await panel.getByLabel('Tanggal pemeriksaan tutup buku',{exact:true}).fill(f.day);await ui.expect(panel.getByLabel('Tindakan periode',{exact:true})).toBeEnabled()
  await panel.getByLabel('Tindakan periode',{exact:true}).selectOption('REOPEN')
  if(f.previous_closed===null)await panel.getByLabel('Buka seluruh periode tertutup',{exact:true}).check()
  else await panel.getByLabel('Periode tetap tertutup sampai',{exact:true}).fill(f.previous_closed)
  await panel.getByLabel('Alasan perubahan periode',{exact:true}).fill('Koreksi setelah pemeriksaan '+suffix);await reviewed.check()
  await panel.getByRole('button',{name:'Buka kembali periode',exact:true}).click();await ui.expect.poll(()=>fixture('read',f).period.control.closed_through).toBe(f.previous_closed)
  await ui.expect(panel.getByLabel('Tindakan periode',{exact:true})).toBeEnabled()
  const opened=fixture('read',f);assert.deepEqual(opened.filings,after.filings);assert.deepEqual(opened.business,before.business)
  await p.route('**/rest/v1/rpc/erp_cp7_get_period_control_v1',route=>route.abort('failed'));await panel.getByRole('button',{name:'Periksa ulang periode',exact:true}).click();await ui.expect(panel.getByRole('alert')).toBeVisible();await ui.expect(panel.getByRole('button',{name:'Buka kembali periode',exact:true})).toHaveCount(0)
  assert.deepEqual(fixture('read',f).filings,after.filings)
  return {status:'PASS',mobile,real_browser_review_close_native_filing_view_and_reopen:true,only_source_preparation_is_native_fixture:true,one_new_archive_originals_immutable:true,GL_stock_unchanged_by_close_and_reopen:true,current_period_restored:true,failed_read_retires_actions:true,exact_lost_close_replay:mobile?true:null,screenshot:`P13_PERIOD_${suffix}.png`}
 }catch(e){mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync(`cp6-proof/t3/P13_PERIOD_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await p.locator('.cfinance-report').innerText().catch(()=>''),native:fixture('read',f)},null,2));throw e}
 finally{await user.context.close()}
}
export async function cases(ui,today){const f=fixture('prepare',{today});return [['P13_PERIOD_BROWSER_DESKTOP',()=>period(ui,f,false)],['P13_PERIOD_BROWSER_MOBILE_RECOVERY',()=>period(ui,f,true)]]}
