import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_p12_browser_fixture.py',op,JSON.stringify(p)],{cwd:'../writer',encoding:'utf8'}).trim())
const changed=(before,after)=>Object.fromEntries([...new Set([...Object.keys(before),...Object.keys(after)])].sort().flatMap(k=>{const v=Number(after[k]??0)-Number(before[k]??0);return v?[[k,v]]:[]}))
async function openPage(ui,p){
 const menu=p.getByRole('button',{name:'Buka menu',exact:true})
 await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:'Keuangan'})).toBeAttached()
 if(await menu.isVisible())await menu.click()
 const link=p.getByRole('button',{name:'• Payroll & Kasbon',exact:true})
 if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Keuangan'}).click()
 await link.click();await ui.expect(p.locator('.cpay').getByRole('heading',{name:'Payroll & Kasbon',exact:true})).toBeVisible()
}
async function lifecycle(ui,today,mobile,unpaid=false){
 // Only prior Nota, roster, rate and attendance use ordinary native fixture
 // writers. Every settlement action below must go through the actual UI.
 const f=fixture('create_payroll_settlement',{today}),user=await ui.login('ADMIN',{label:'p12-payroll-'+mobile+'-'+unpaid,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
 const suffix=unpaid?'UNPAID_CANCEL':mobile?'MOBILE':'DESKTOP',p=user.page
 try{
  const binding=fixture('bind_settlement_actor',{role:f.role,actor:user.user.id});assert.ok(binding.role_code.startsWith('P02_'))
  await p.reload();await openPage(ui,p)
  const panel=p.locator('.cpay'),detail=panel.getByRole('region',{name:'Rincian payroll'})
  async function select(){
   await panel.getByLabel('Cari payroll',{exact:true}).fill(f.label);await panel.getByRole('button',{name:'Cari payroll',exact:true}).click()
   await ui.expect(panel.locator('.cproc-receipt')).toHaveCount(1);await panel.locator('.cproc-receipt').click()
  }
  async function confirm(label,setup){
   await detail.getByRole('button',{name:label,exact:true}).click()
   const form=detail.getByRole('region',{name:'Periksa tindakan payroll'}),commit=form.getByRole('button',{name:label==='Koreksi payroll lunas'?'Batalkan payroll dan pembayaran sekarang':label+' sekarang',exact:true})
   await ui.expect(commit).toBeDisabled();if(setup)await setup(form)
   await form.getByLabel('Alasan tindakan payroll',{exact:true}).fill('P12 pemeriksaan sumber dan jumlah melalui browser')
   await form.getByLabel('Rincian payroll sudah diperiksa',{exact:true}).check();await ui.expect(commit).toBeEnabled();await commit.click()
  }
  await select();await ui.expect(detail.locator('.cpay-net')).toHaveText('Bersih payrollRp6.000')
  await detail.getByRole('button',{name:'Hitung sumber',exact:true}).click()
  await ui.expect(detail.locator('.cpay-net')).toHaveText('Bersih payrollRp6.100')
  await detail.getByRole('button',{name:/^Absensi /}).click();await ui.expect(detail.locator('.cpay-line')).toHaveCount(1);await ui.expect(detail.locator('.cpay-line')).toContainText('P12 attendance worker');await ui.expect(detail.locator('.cpay-line')).toContainText('1 hari × Rp100')
  let native=fixture('read_settlement',f);assert.equal(native.document.labor_total,'6000.00');assert.equal(native.document.attendance_total,'100.00');assert.deepEqual(changed(f.base_gl,native.gl),{});assert.deepEqual(native.physical,f.physical)
  await confirm('Setujui payroll');await ui.expect(detail.getByRole('button',{name:'Lunasi payroll',exact:true})).toBeEnabled()
  native=fixture('read_settlement',f);assert.equal(native.document.status,'APPROVED');assert.deepEqual(changed(f.base_gl,native.gl),{[f.wip]:100,[f.payable]:-100});assert.deepEqual(native.accrual.map(Number),[2,100,100]);assert.deepEqual(native.physical,f.physical)
  let first=null,replay=null,lost=false
  if(unpaid){
   await confirm('Batalkan payroll');await ui.expect(detail).toContainText('Rincian berikut adalah riwayat payroll tersebut.')
  }else{
   if(mobile)await p.route('**/rest/v1/rpc/erp_cp7_save_payroll_v1',async route=>{
    const body=route.request().postDataJSON()
    if(body.p_action==='PAY'&&!lost){first=body;const response=await route.fetch();assert.equal(response.status(),200,'PAY must commit before the simulated lost reply');lost=true;await route.abort('failed')}
    else{if(body.p_action==='PAY'&&replay===null)replay=body;await route.continue()}
   })
   await confirm('Lunasi payroll',async form=>{
    await ui.expect(form.getByLabel('Tanggal pembayaran payroll',{exact:true})).toHaveValue(today)
    await form.getByLabel('Cari akun pembayaran payroll',{exact:true}).fill(f.bank_code);await form.getByRole('button',{name:'Cari akun pembayaran',exact:true}).click()
    await ui.expect(form.locator('.cpay-cash-row')).toHaveCount(1);await form.locator('.cpay-cash-row').click()
   })
   await ui.expect.poll(()=>fixture('read_settlement',f).document.status).toBe('PAID')
   if(mobile){
    await ui.expect(panel.getByRole('button',{name:'Periksa status payroll',exact:true})).toBeVisible();await p.reload();await openPage(ui,p)
    await panel.getByRole('button',{name:'Periksa status payroll',exact:true}).click();await ui.expect(panel.getByRole('button',{name:'Periksa status payroll',exact:true})).toHaveCount(0)
    assert.ok(lost);assert.deepEqual(replay,first,'Recovery must retain request UUID, date, cash, token and exact version');await select()
   }
   await ui.expect(detail.locator('.cpay-net')).toHaveText('Jumlah dilunasiRp6.100')
   native=fixture('read_settlement',f);assert.equal(native.document.status,'PAID');assert.deepEqual(native.payment.map(Number),[2,6100,6100]);assert.deepEqual(native.accrual.map(Number),[2,100,100]);assert.deepEqual(changed(f.base_gl,native.gl),{[f.wip]:100,[f.payable]:6000,[f.bank_coa]:-6100});assert.deepEqual(native.physical,f.physical)
   await ui.expect.poll(()=>panel.evaluate(el=>{const b=el.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
   mkdirSync('cp6-proof/t3',{recursive:true});await p.evaluate(()=>window.scrollTo(0,0));await p.screenshot({path:`cp6-proof/t3/P12_PAYROLL_SETTLEMENT_${suffix}.png`,fullPage:true})
   await confirm('Koreksi payroll lunas');await ui.expect(detail).toContainText('Rincian berikut adalah riwayat payroll tersebut.')
  }
  await ui.expect(detail.locator('.cpay-net')).toHaveText('Jumlah pada dokumen batalRp6.100')
  native=fixture('read_settlement',f);assert.equal(native.document.status,'REVERSED');assert.equal(native.note.status,'POSTED');assert.equal(native.note.payroll_status,'REVERSED');assert.equal(native.sources,'2');assert.deepEqual(changed(f.base_gl,native.gl),{});assert.deepEqual(native.physical,f.physical)
  if(unpaid)assert.deepEqual(native.payment.map(Number),[0,0,0])
  return {status:'PASS',mobile,real_auth_custom_role:true,prior_nota_roster_rate_attendance_by_ordinary_native_fixture:true,actual_browser_prepare_approve:true,labor:'6000',attendance:'100',net:'6100',approval_accrual_once:true,actual_browser_full_payment:!unpaid,actual_browser_unpaid_cancel:unpaid,actual_browser_paid_reversal:!unpaid,exact_lost_reply_replay:mobile?true:null,payment_once:!unpaid,inverse_gl_neutral:true,stock_hpp_unchanged:true,source_released_note_retained:true,screenshot:unpaid?null:`P12_PAYROLL_SETTLEMENT_${suffix}.png`}
 }catch(error){
  mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync(`cp6-proof/t3/P12_PAYROLL_SETTLEMENT_${suffix}_FAILURE.json`,JSON.stringify({error:String(error),panel:await p.locator('.cpay').innerText().catch(()=>''),dto:await user.rpc('erp_cp7_get_payroll_workspace_v1',{p_section:'PAYROLLS',p_query:{id:f.payroll}})},null,2))
  await p.screenshot({path:`cp6-proof/t3/P12_PAYROLL_SETTLEMENT_${suffix}_FAILURE.png`,fullPage:true});throw error
 }finally{await user.context.close()}
}
export async function cases(ui,today){return [['P12_SETTLEMENT_BROWSER_DESKTOP',()=>lifecycle(ui,today,false)],['P12_SETTLEMENT_BROWSER_MOBILE_RECOVERY',()=>lifecycle(ui,today,true)],['P12_SETTLEMENT_BROWSER_UNPAID_CANCEL',()=>lifecycle(ui,today,false,true)]]}
