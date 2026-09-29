import assert from 'node:assert/strict'
import {cases as commandCases} from './cp7_p11_commands_browser.mjs'
import {cases as draftCases} from './cp7_p11_drafts_browser.mjs'
import {cases as paymentCases} from './cp7_p11_payments_browser.mjs'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_p11_browser_fixture.py',op,JSON.stringify(p)],{cwd:'../writer',encoding:'utf8'}).trim())
async function invoice(ui,today,mobile){
 const f={...fixture('create',{today,ops:mobile}),today},user=await ui.login(mobile?'ADMIN':'OWNER',{label:'p11-reader-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),p=user.page,ws=p.locator('.csales'),detail=ws.getByRole('complementary',{name:'Rincian invoice'})
 try{
  await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:'Penjualan'})).toBeAttached()
  const menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
  const link=p.getByRole('button',{name:'• Penjualan & Invoice',exact:true});if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Penjualan'}).click();await link.click()
  await ui.expect(ws.getByRole('heading',{name:'Penjualan & Invoice',exact:true})).toBeVisible()
  await ws.getByLabel('Cari invoice',{exact:true}).fill(f.tag);await ws.getByRole('button',{name:'Cari invoice',exact:true}).click();await ui.expect(ws.locator('.cproc-receipt')).toHaveCount(1)
  const before=fixture('read',f);await ws.locator('.cproc-receipt').click();await ui.expect(detail).toContainText('4 PCS masih dipesan')
  if(mobile){assert.ok(!(await ws.innerText()).includes('Rp'));await ui.expect(detail.getByRole('region',{name:'Nilai invoice'})).toHaveCount(0)}
  else await ui.expect(detail).toContainText('Nilai draft belum menjadi piutang.')
  assert.deepEqual(fixture('read',f),before)
  // These are explicit native controls. The browser qualifies reload/readback,
  // not sale/payment/return writes, so R10 remains open.
  fixture('progress',f);const posted=fixture('read',f);await ws.getByRole('button',{name:'Muat ulang invoice',exact:true}).click()
  await ui.expect(detail).toContainText('Dibayar sebagian');await ui.expect(detail).toContainText('0 PCS masih dipesan · 1 PCS sudah diretur')
  if(mobile)assert.ok(!(await ws.innerText()).includes('Rp'))
  else{await ui.expect(detail.getByLabel('Nilai invoice')).toContainText('Sisa pembayaran Rp30');await ui.expect(detail.getByLabel('Nilai invoice')).toContainText('bersih Rp60')}
  assert.deepEqual(fixture('read',f),posted)
  await ui.expect.poll(()=>ws.evaluate(el=>{const r=el.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
  mkdirSync('cp6-proof/t3',{recursive:true});await p.evaluate(()=>window.scrollTo(0,0));await p.screenshot({path:`cp6-proof/t3/P11_READ_${mobile?'MOBILE':'DESKTOP'}.png`,fullPage:true})
  await p.route('**/rest/v1/rpc/erp_cp7_get_sales_v1',route=>route.abort('failed'));await ws.getByRole('button',{name:'Muat ulang invoice',exact:true}).click()
  await ui.expect(ws.getByRole('alert').first()).toBeVisible();await ui.expect(ws.locator('.cproc-receipt')).toHaveCount(0);await ui.expect(detail.getByRole('heading',{name:f.tag,exact:true})).toHaveCount(0)
  assert.ok(!(await ws.innerText()).includes('Rp'));assert.deepEqual(fixture('read',f),posted)
  return {status:'PASS',mobile,read_only_browser:true,native_fixture_transitions_not_r10_writes:true,source_bound_draft_reservation:true,native_net:'60',native_paid:'30',native_remaining:'30',operational_money_redacted:mobile?true:null,failed_refresh_retires_old_document_and_money:true,reader_leaves_stock_and_gl_unchanged:true,screenshot:`P11_READ_${mobile?'MOBILE':'DESKTOP'}.png`}
 }catch(e){mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync(`cp6-proof/t3/P11_READ_${mobile?'MOBILE':'DESKTOP'}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await ws.innerText().catch(()=>''),source:fixture('read',f)},null,2));await p.screenshot({path:`cp6-proof/t3/P11_READ_${mobile?'MOBILE':'DESKTOP'}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{await user.context.close()}
}
export async function cases(ui,today){return [['P11_READ_BROWSER_DESKTOP',()=>invoice(ui,today,false)],['P11_READ_BROWSER_MOBILE_OPERATIONS',()=>invoice(ui,today,true)],...await commandCases(ui,today),...await draftCases(ui,today),...await paymentCases(ui,today)]}
