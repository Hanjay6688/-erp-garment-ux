import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_f03_refund_browser_fixture.py',op],{cwd:'../writer',input:JSON.stringify(p),encoding:'utf8',maxBuffer:8*1024*1024}).trim().split('\n').at(-1))
async function open(ui,p,batch){
 const menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=p.getByRole('button',{name:'• Impor data awal',exact:true})
 if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Pengaturan & Audit'}).click()
 await link.click();await ui.expect(p.getByRole('heading',{name:'Impor data awal',exact:true})).toBeVisible()
 await ui.expect(p.getByRole('button',{name:'Muat ulang',exact:true})).toBeEnabled()
 await p.getByLabel('Batch impor',{exact:true}).selectOption(batch)
 await ui.expect(p.getByText('Sudah disahkan',{exact:false})).toBeVisible()
}
async function flow(ui,today,mobile){
 const user=await ui.login('OWNER',{label:'f03-source-refund-'+(mobile?'mobile':'desktop'),mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
 const p=user.page,f=fixture('prepare',{today}),suffix=mobile?'MOBILE':'DESKTOP',files=[]
 const screenshot=async name=>{const file=`F03_E03_REFUND_${suffix}_${name}.png`;mkdirSync('cp6-proof/t3',{recursive:true});await p.screenshot({path:'cp6-proof/t3/'+file,fullPage:true});files.push(file)}
 try{
  await open(ui,p,f.batch)
  const returns=p.getByRole('region',{name:'Retur penjualan lama',exact:true})
  await returns.getByLabel('Hak retur',{exact:true}).selectOption(f.right_id)
  await returns.getByLabel('Jumlah retur diterima',{exact:true}).fill('3')
  await returns.getByLabel('Gudang retur',{exact:true}).selectOption(f.location_id)
  await returns.getByLabel('Tanggal retur diterima',{exact:true}).fill(today)
  await returns.getByLabel('Catatan retur',{exact:true}).fill('Terima tiga PCS dari invoice lama yang sudah lunas')
  await returns.getByRole('button',{name:'Terima retur',exact:true}).click()
  await ui.expect.poll(()=>fixture('read',f).company_returned_pcs).toBe(3)
  const before=fixture('read',f),credit=before.credits[0];assert.equal(credit.remaining_amount,'30.00');assert.equal(before.bank,'100.00')
  const panel=p.getByRole('region',{name:'Kredit pelanggan saldo awal',exact:true})
  await ui.expect(panel).toBeVisible();await panel.getByLabel('Kredit pelanggan',{exact:true}).selectOption(credit.credit_id)
  await panel.getByLabel('Tindakan kredit pelanggan',{exact:true}).selectOption('REFUND')
  await panel.getByLabel('Nominal kredit',{exact:true}).fill('10,00')
  await panel.getByLabel('Tanggal kredit',{exact:true}).fill(today)
  await panel.getByLabel('Alasan kredit',{exact:true}).fill('Pengembalian sepuluh dari kredit tiga puluh yang sah')
  await ui.expect(panel.getByRole('button',{name:'Kembalikan uang',exact:true})).toBeDisabled()
  await panel.getByLabel('Rekening pengembalian kredit',{exact:true}).selectOption(f.cash)
  await screenshot('REVIEWED_SOURCE')
  let sent=null,done=false,routeError=null
  await p.route('**/rest/v1/rpc/erp_save_initial_import_action_v1',async route=>{
   try{
    const args=route.request().postDataJSON()
    if(args.p_action==='CUSTOMER_CREDIT'&&args.p_payload.operation==='REFUND'&&!done){sent=args;const response=await route.fetch();assert.equal(response.status(),200);done=true;await route.abort('failed')}
    else await route.continue()
   }catch(e){routeError=e;await route.abort('failed').catch(()=>{})}
  })
  await panel.getByRole('button',{name:'Kembalikan uang',exact:true}).click()
  await ui.expect.poll(()=>done||Boolean(routeError)).toBe(true);if(routeError)throw routeError
  await ui.expect(p.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeEnabled()
  const pending=await p.evaluate(()=>Object.entries(localStorage).filter(([k])=>k.startsWith('erp.production.INITIAL_IMPORT.pending-mutation.v1:')).map(([,v])=>JSON.parse(v)))
  assert.equal(pending.length,1);assert.equal(pending[0].id,sent.p_client_request_id);assert.deepEqual(pending[0].payload,sent.p_payload)
  const committed=fixture('read',f);assert.equal(committed.refund_events,1);assert.equal(committed.bank,'90.00');assert.equal(committed.company_returned_pcs,3);assert.equal(committed.credits[0].remaining_amount,'20.00')
  await ui.expect(panel).toBeHidden();await screenshot('UNCERTAIN_REPLY_FACTS_RETIRED')
  await p.unroute('**/rest/v1/rpc/erp_save_initial_import_action_v1');await p.reload()
  await ui.expect(p.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeEnabled()
  let replay=null
  await p.route('**/rest/v1/rpc/erp_save_initial_import_action_v1',async route=>{replay=route.request().postDataJSON();await route.continue()})
  await p.getByRole('button',{name:'Reconcile transaksi',exact:true}).click()
  await ui.expect(panel).toBeVisible();assert.deepEqual(replay,sent)
  const recovered=fixture('read',f);assert.equal(recovered.refund_events,1);assert.equal(recovered.bank,'90.00');assert.equal(recovered.credits[0].remaining_amount,'20.00');assert.equal(recovered.company_returned_pcs,3)
  await screenshot('EXACT_UUID_RECONCILED')
  await panel.getByLabel('Alasan kredit',{exact:true}).fill('Catatan operator sendiri tetap disimpan')
  fixture('deactivate',{actor:user.user.id})
  const request=p.waitForRequest(r=>r.url().includes('/rest/v1/rpc/erp_get_initial_import_workspace_v1'))
  await p.getByRole('button',{name:'Muat ulang',exact:true}).click();const ownRequest=await request;const response=await ownRequest.response();assert.equal(response.status(),403)
  await ui.expect(panel).toBeHidden();await ui.expect(returns).toBeHidden();await ui.expect(p.getByText(f.code,{exact:true})).toBeHidden()
  assert.equal(fixture('read',f).refund_events,1);await screenshot('CURRENT403_FACTS_RETIRED')
  fixture('restore',{actor:user.user.id});await p.getByRole('button',{name:'Muat ulang',exact:true}).click();await ui.expect(panel).toBeVisible()
  await ui.expect(panel.getByLabel('Alasan kredit',{exact:true})).toHaveValue('Catatan operator sendiri tetap disimpan')
  await ui.expect.poll(()=>p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
  return{status:'PASS',mobile,lawful_paid_old_sale_provenance:true,physical_return3_credit30:true,actual_cash_refund10_remaining20_bank90:true,current_paid_native_sale_policy_unchanged:true,exact_lost_committed_UUID_payload_replay_once:true,current403_source_facts_retired_operator_reason_preserved:true,screenshots:files,full_family_acceptance:false,independent_acceptance:false,production_go:false}
 }catch(e){mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync(`cp6-proof/t3/F03_E03_REFUND_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:(await p.locator('body').innerText().catch(()=>'' )).slice(0,16000)},null,2));await p.screenshot({path:`cp6-proof/t3/F03_E03_REFUND_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{fixture('restore',{actor:user.user.id});await user.context.close()}
}
export async function cases(ui,today){return[['F03_E03_REFUND_BROWSER_DESKTOP',()=>flow(ui,today,false)],['F03_E03_REFUND_BROWSER_MOBILE',()=>flow(ui,today,true)]]}
