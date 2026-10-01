import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_f03_supplier_credit_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:8*1024*1024}).trim().split('\n').at(-1))
async function open(ui,p){
 await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:'Keuangan'})).toBeAttached({timeout:20000})
 const menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=p.getByRole('button',{name:'• Hutang Supplier & Vendor',exact:true});if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Keuangan'}).click()
 await link.click();await ui.expect(p.getByRole('heading',{name:'Utang & kredit retur supplier',exact:true})).toBeVisible()
 await ui.expect(p.getByRole('button',{name:'Muat ulang kredit supplier',exact:true})).toBeEnabled()
}
async function flow(ui,today,mobile){
 const f=fixture('prepare',{today}),user=await ui.login('ADMIN',{label:'f03-paid-supplier-credit-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),p=user.page,suffix=mobile?'MOBILE':'DESKTOP',files=[]
 let revoked=null,sent=null,replay=null,committed=false,routeError=null
 const state=()=>fixture('read',f),ws=p.locator('.supplier-credit')
 const capture=async name=>{const file=`F03_SUPPLIER_CREDIT_${suffix}_${name}.png`;mkdirSync('cp6-proof/t3',{recursive:true});await p.screenshot({path:'cp6-proof/t3/'+file,fullPage:true});files.push(file)}
 const unchanged=now=>{assert.equal(now.stock,f.initial.stock);assert.deepEqual(now.values,f.initial.values);assert.equal(now.ledger,f.initial.ledger);assert.equal(now.bank_delta,'-80.00');assert.deepEqual(now.paid,['0.00','80.00','0.00'])}
 async function select(){await ws.getByLabel('Supplier kredit',{exact:true}).selectOption(f.supplier);await ui.expect(ws.getByRole('button',{name:`Atur alokasi ${f.return_number}`,exact:true})).toBeEnabled()}
 async function edit(){await ws.getByRole('button',{name:`Atur alokasi ${f.return_number}`,exact:true}).click()}
 const confirm=()=>ws.getByLabel('Saya sudah memeriksa pembelian asal, tujuan, dan nominal kredit.',{exact:true}).check()
 try{
  const start=state();assert.deepEqual(start.ap,['100.00','80.00','60.00']);assert.deepEqual(start.remaining,['100.00','0.00','60.00']);unchanged(start)
  await open(ui,p);await select();await edit()
  await ws.getByLabel(`Kredit untuk ${f.numbers[1]}`,{exact:true}).fill('')
  await ws.getByLabel(`Kredit untuk ${f.numbers[2]}`,{exact:true}).fill('20.00')
  await ws.getByLabel('Alasan pengalihan kredit',{exact:true}).fill('Pindah kredit; pembelian yang sudah dibayar tetap memakai kas asal')
  await confirm();await ui.expect(ws.getByRole('button',{name:'Simpan alokasi kredit',exact:true})).toBeEnabled();await capture('PAID_TARGET_REVIEW')
  await p.route('**/rest/v1/rpc/erp_save_supplier_credit_v1',async route=>{
   try{const args=route.request().postDataJSON();if(!committed){sent=args;const native=await route.fetch();assert.equal(native.status(),200);committed=true;await route.abort('failed')}else await route.continue()}
   catch(e){routeError=e;await route.abort('failed').catch(()=>{})}
  })
  await ws.getByRole('button',{name:'Simpan alokasi kredit',exact:true}).click()
  await ui.expect.poll(()=>committed||Boolean(routeError)).toBe(true);if(routeError)throw routeError
  await ui.expect(ws.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeEnabled()
  await ui.expect(ws.getByRole('heading',{name:'Utang pembelian',exact:true})).toBeHidden()
  const pending=await p.evaluate(()=>Object.entries(localStorage).filter(([k])=>k.startsWith('erp.production.SUPPLIER_CREDIT.pending-mutation.v1:')).map(([,v])=>JSON.parse(v)))
  assert.equal(pending.length,1);assert.equal(pending[0].id,sent.p_client_request_id);assert.deepEqual(pending[0].payload,sent.p_payload)
  const moved=state();unchanged(moved);assert.deepEqual(moved.ap,['100.00','100.00','40.00']);assert.deepEqual(moved.remaining,['100.00','20.00','40.00']);assert.equal(moved.move_event_count,3)
  await capture('UNCERTAIN_FINANCIAL_FACTS_RETIRED');await p.unroute('**/rest/v1/rpc/erp_save_supplier_credit_v1');await p.reload();await open(ui,p)
  await ui.expect(ws.getByRole('heading',{name:'Utang pembelian',exact:true})).toBeHidden()
  await p.route('**/rest/v1/rpc/erp_save_supplier_credit_v1',async route=>{replay=route.request().postDataJSON();await route.continue()})
  await ws.getByRole('button',{name:'Reconcile transaksi',exact:true}).click()
  await ui.expect(ws.getByRole('heading',{name:'Utang pembelian',exact:true})).toBeVisible();assert.deepEqual(replay,sent)
  const recovered=state();unchanged(recovered);assert.deepEqual(recovered.ap,moved.ap);assert.equal(recovered.move_event_count,3);await capture('EXACT_UUID_RECONCILED')
  await p.unroute('**/rest/v1/rpc/erp_save_supplier_credit_v1');await select();await edit()
  await ws.getByLabel(`Kredit untuk ${f.numbers[2]}`,{exact:true}).fill('')
  await ws.getByLabel('Alasan pengalihan kredit',{exact:true}).fill('Kembalikan seluruh kredit ke pembelian asal yang masih dapat menerima kredit')
  await confirm()
  const response=p.waitForResponse(r=>r.url().includes('/rpc/erp_save_supplier_credit_v1'))
  await ws.getByRole('button',{name:'Simpan alokasi kredit',exact:true}).click();assert.equal((await response).status(),200)
  await ui.expect(ws.getByRole('button',{name:`Atur alokasi ${f.return_number}`,exact:true})).toBeEnabled()
  const original=state();unchanged(original);assert.deepEqual(original.ap,['80.00','100.00','60.00']);assert.deepEqual(original.remaining,['80.00','20.00','60.00']);assert.equal(original.move_event_count,4);await capture('ORIGINAL_SOURCE_RESTORED')
  await edit();await ws.getByLabel('Alasan pengalihan kredit',{exact:true}).fill('Catatan operator disimpan ketika akses fakta ditolak')
  revoked=fixture('revoke',{actor:user.user.id})
  const own=p.waitForRequest(r=>r.url().includes('/rpc/erp_get_supplier_credit_v1'))
  await ws.getByRole('button',{name:'Muat ulang kredit supplier',exact:true}).click();const request=await own,current=await request.response()
  assert.equal(current.status(),403);const refusal=await current.json();assert.equal(refusal.code,'42501');assert.equal(refusal.message,'PERMISSION_DENIED: finance.ap.view')
  await ui.expect(ws.getByRole('heading',{name:'Utang pembelian',exact:true})).toBeHidden();await ui.expect(ws.getByRole('heading',{name:'Kredit retur',exact:true})).toBeHidden();assert.deepEqual(state(),original)
  await capture('CURRENT_AUTHORITY_REFUSAL_FACTS_RETIRED')
  fixture('restore',revoked);revoked=null;await ws.getByRole('button',{name:'Muat ulang kredit supplier',exact:true}).click()
  await ui.expect(ws.getByLabel('Alasan pengalihan kredit',{exact:true})).toHaveValue('Catatan operator disimpan ketika akses fakta ditolak')
  await ui.expect.poll(()=>p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
  return{status:'PASS',mobile,actual_Native_paid80_target_credit20_moves_to_other_purchase:true,paid_target_remaining0_to20:true,bank_stock_HPP_values_net_AP_unchanged_by_credit_move:true,lost_committed_reply_exact_UUID_payload_reconciled_once:true,original_source_credit_restored:true,current_authority_refusal_retires_all_credit_and_AP_facts:true,operator_reason_preserved_after_authorized_read:true,screenshots:files,independent_acceptance:false,full_family_acceptance:false,production_go:false}
 }catch(e){mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync(`cp6-proof/t3/F03_SUPPLIER_CREDIT_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,body:(await p.locator('body').innerText().catch(()=>'' )).slice(0,16000),native:state()},null,2));await p.screenshot({path:`cp6-proof/t3/F03_SUPPLIER_CREDIT_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{try{if(revoked)fixture('restore',revoked)}finally{await user.context.close()}}
}
export function cases(ui,today){return[['F03_P09_PAID_SUPPLIER_CREDIT_DESKTOP',()=>flow(ui,today,false)],['F03_P09_PAID_SUPPLIER_CREDIT_MOBILE',()=>flow(ui,today,true)]]}
