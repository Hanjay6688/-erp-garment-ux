import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_p11_browser_fixture.py',op,JSON.stringify(p)],{cwd:'../writer',encoding:'utf8'}).trim())
async function open(ui,p){
 await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:'Penjualan'})).toBeAttached()
 const menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=p.getByRole('button',{name:'• Penjualan & Invoice',exact:true});if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Penjualan'}).click();await link.click()
 await ui.expect(p.locator('.csales').getByRole('heading',{name:'Penjualan & Invoice',exact:true})).toBeVisible()
}
async function transitions(ui,today,mobile){
 const first=fixture('create',{today}),second=fixture('create',{today}),user=await ui.login('OWNER',{label:'p11-command-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),p=user.page,ws=p.locator('.csales'),detail=ws.getByRole('complementary',{name:'Rincian invoice'})
 const select=async f=>{await ws.getByLabel('Cari invoice',{exact:true}).fill(f.tag);await ws.getByRole('button',{name:'Cari invoice',exact:true}).click();await ui.expect(ws.locator('.cproc-receipt')).toHaveCount(1);await ws.locator('.cproc-receipt').click();await ui.expect(detail).toContainText('4 PCS masih dipesan')}
 const review=async()=>{await detail.getByLabel('Catatan tindakan invoice',{exact:true}).fill('P11 pelanggan harga barang dan tanggal diperiksa');await detail.getByLabel('Invoice sudah diperiksa',{exact:true}).check()}
 try{
  await open(ui,p);await select(first);const before=fixture('read',first);await ui.expect(detail.getByRole('button',{name:'Batalkan draft invoice',exact:true})).toBeDisabled();await review()
  await detail.getByRole('button',{name:'Batalkan draft invoice',exact:true}).click();await ui.expect(detail).toContainText('Draft dibatalkan');await ui.expect(detail).toContainText('0 PCS masih dipesan')
  const cancelled=fixture('read',first);assert.equal(cancelled.available,10);assert.deepEqual(cancelled.gl,before.gl);assert.equal(cancelled.document.status,'CANCELLED')
  await select(second);let lost=false,sent=null,replayed=null
  if(mobile)await p.route('**/rest/v1/rpc/erp_cp7_save_sale_v1',async route=>{
   const body=route.request().postDataJSON()
   if(body.p_action==='POST'&&!lost){sent=body;const response=await route.fetch();assert.equal(response.status(),200);lost=true;await route.abort('failed')}
   else {if(body.p_action==='POST'&&replayed===null)replayed=body;await route.continue()}
  })
  await review();await detail.getByRole('button',{name:'Sahkan invoice',exact:true}).click()
  if(mobile){await ui.expect(ws.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible();await p.reload();await open(ui,p);await ws.getByRole('button',{name:'Reconcile transaksi',exact:true}).click();await ui.expect(ws.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0);assert.ok(lost);assert.deepEqual(replayed,sent)}
  await ui.expect(detail).toContainText('Belum lunas');await ui.expect(detail).toContainText('Sisa pembayaran Rp80');await ui.expect(detail).toContainText('0 PCS masih dipesan')
  const posted=fixture('read',second);assert.equal(posted.document.status,'POSTED');assert.equal(posted.available,6);assert.equal(posted.document.financial.open_balance,'80.00');assert.equal(Number(posted.movements[0]),2)
  await ui.expect.poll(()=>ws.evaluate(el=>{const r=el.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
  mkdirSync('cp6-proof/t3',{recursive:true});await p.evaluate(()=>window.scrollTo(0,0));await p.screenshot({path:`cp6-proof/t3/P11_COMMAND_${mobile?'MOBILE':'DESKTOP'}.png`,fullPage:true})
  return {status:'PASS',mobile,browser_cancel_releases4_to10:true,browser_post_retains_reserved_available6:true,posted_receivable:'80',cancel_gl_unchanged:true,only_one_original_receipt_and_one_sale_movement:true,lost_commit_replay_identical:mobile?true:null,source_draft_creation_is_native_fixture:true,remaining_r10_create_return_payment:true,screenshot:`P11_COMMAND_${mobile?'MOBILE':'DESKTOP'}.png`}
 }catch(e){let source;try{source=fixture('read',second)}catch(x){source={error:String(x)}}mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync(`cp6-proof/t3/P11_COMMAND_${mobile?'MOBILE':'DESKTOP'}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await ws.innerText().catch(()=>''),source},null,2));await p.screenshot({path:`cp6-proof/t3/P11_COMMAND_${mobile?'MOBILE':'DESKTOP'}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{await user.context.close()}
}
export async function cases(ui,today){return [['P11_COMMAND_BROWSER_DESKTOP',()=>transitions(ui,today,false)],['P11_COMMAND_BROWSER_MOBILE_RECOVERY',()=>transitions(ui,today,true)]]}
