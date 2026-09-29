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
async function lifecycle(ui,today,mobile){
 const f=fixture('create_payment_source',{today}),user=await ui.login('OWNER',{label:'p11-cash-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),p=user.page,ws=p.locator('.csales'),detail=ws.getByRole('complementary',{name:'Rincian invoice'}),panel=ws.getByRole('region',{name:'Pembayaran invoice',exact:true}),form=panel.getByRole('form',{name:'Catat pembayaran pelanggan'})
 const money=(n)=>{const raw=String(n),negative=raw.startsWith('-'),[a,b='']=raw.replace(/^-/,'').split('.');assert.match(b.slice(2),/^0*$/);return (BigInt(a)*100n+BigInt(b.slice(0,2).padEnd(2,'0')))*(negative?-1n:1n)},delta=(a,b)=>Object.fromEntries([...new Set([...Object.keys(a),...Object.keys(b)])].map(k=>[k,money(b[k]??'0')-money(a[k]??'0')]).filter(([,v])=>v!==0n))
 try{
  await open(ui,p);await ws.getByLabel('Cari invoice',{exact:true}).fill(f.tag);await ws.getByRole('button',{name:'Cari invoice',exact:true}).click();await ui.expect(ws.locator('.cproc-receipt')).toHaveCount(1);await ws.locator('.cproc-receipt').click()
  await detail.getByLabel('Invoice sudah diperiksa',{exact:true}).check();await detail.getByRole('button',{name:'Sahkan invoice',exact:true}).click();await ui.expect(detail).toContainText('Sisa pembayaran Rp30,01');const before=fixture('read_payment',f)
  let lost=false,first=null,replay=null
  if(mobile)await p.route('**/rest/v1/rpc/erp_cp7_save_sale_v1',async route=>{const body=route.request().postDataJSON();if(body.p_action==='PAYMENT'&&!lost){first=body;const response=await route.fetch();assert.equal(response.status(),200);lost=true;await route.abort('failed')}else{if(body.p_action==='PAYMENT'&&replay===null)replay=body;await route.continue()}})
  for(const [n,amount,balance] of [[1,'10,01','20'],[2,'20','0']]){
   await detail.getByRole('button',{name:'Pembayaran invoice',exact:true}).click();await ui.expect(panel.getByRole('heading',{name:'Riwayat pembayaran',exact:true})).toBeVisible()
   await form.getByLabel('Nomor pembayaran pelanggan',{exact:true}).fill(f.tag+'-PAY-'+n);await form.getByLabel('Nominal pembayaran pelanggan',{exact:true}).fill(amount)
   await form.getByLabel('Cari rekening pembayaran pelanggan',{exact:true}).fill(f.bank_code);await form.getByRole('button',{name:'Cari rekening pelanggan',exact:true}).click();const banks=form.getByRole('region',{name:'Pilih rekening pembayaran pelanggan'}).locator('.cproc-receipt');await ui.expect(banks).toHaveCount(1);await banks.click()
   await form.getByLabel('Referensi pembayaran pelanggan',{exact:true}).fill('REF-'+n);await form.getByLabel('Catatan pembayaran pelanggan',{exact:true}).fill('Nominal dan rekening diperiksa')
   await ui.expect(form.getByRole('button',{name:'Catat pembayaran pelanggan',exact:true})).toBeDisabled();await form.getByLabel('Pembayaran pelanggan sudah diperiksa',{exact:true}).check();await form.getByRole('button',{name:'Catat pembayaran pelanggan',exact:true}).click()
   if(mobile&&n===1){await ui.expect(ws.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible();await p.reload();await open(ui,p);await ws.getByRole('button',{name:'Reconcile transaksi',exact:true}).click();await ui.expect(ws.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0);assert.ok(lost);assert.deepEqual(replay,first)}
   await ui.expect(panel).toHaveCount(0);await ui.expect(detail).toContainText('Sisa pembayaran Rp'+balance)
  }
  const paid=fixture('read_payment',f);assert.equal(paid.available,7);assert.equal(paid.document.status,'PAID');assert.equal(paid.cash.payments.total,'2');assert.deepEqual(delta(before.accounts,paid.accounts),{[f.cash_coa]:3001n,[f.ar_coa]:-3001n});assert.ok(paid.cash.payments.rows.every(x=>x.notes==='Nominal dan rekening diperiksa'&&x.reference.startsWith('REF-')))
  await detail.getByRole('button',{name:'Pembayaran invoice',exact:true}).click();await ui.expect(panel).toContainText('Total 2 pembayaran')
  await ui.expect.poll(()=>ws.evaluate(el=>{const r=el.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
  mkdirSync('cp6-proof/t3',{recursive:true});await p.evaluate(()=>window.scrollTo(0,0));await p.screenshot({path:`cp6-proof/t3/P11_PAYMENT_${mobile?'MOBILE':'DESKTOP'}.png`,fullPage:true})
  for(const [n,balance] of [[1,'10,01'],[2,'30,01']]){
   if(n===2)await detail.getByRole('button',{name:'Pembayaran invoice',exact:true}).click()
   await panel.getByRole('button',{name:'Koreksi pembayaran '+f.tag+'-PAY-'+n,exact:true}).click();await form.getByLabel('Alasan tindakan pembayaran',{exact:true}).fill('Pembayaran customer dibatalkan untuk koreksi');await form.getByLabel('Pembayaran pelanggan sudah diperiksa',{exact:true}).check();await form.getByRole('button',{name:'Batalkan pembayaran tercatat',exact:true}).click();await ui.expect(panel).toHaveCount(0);await ui.expect(detail).toContainText('Sisa pembayaran Rp'+balance)
  }
  const reversed=fixture('read_payment',f);assert.deepEqual(reversed.accounts,before.accounts);assert.equal(reversed.available,7);assert.equal(reversed.document.status,'POSTED');assert.equal(reversed.cash.payments.total,'2');assert.ok(reversed.cash.payments.rows.every(x=>x.status==='REVERSED'))
  return {status:'PASS',mobile,browser_post_pay_partial_pay_full_and_reverse_each:true,native_draft_and_bank_only_are_fixtures:true,invoice:'30.01',first_cash:'10.01',second_cash:'20.00',stock_stays7:true,cash_AR_only_delta:true,inverse_all_GL_accounts_neutral:true,payment_history_retained:2,lost_payment_reply_replay_identical:mobile?true:null,screenshot:`P11_PAYMENT_${mobile?'MOBILE':'DESKTOP'}.png`}
 }catch(e){let source;try{source=fixture('read_payment',f)}catch(x){source={error:String(x)}}mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync(`cp6-proof/t3/P11_PAYMENT_${mobile?'MOBILE':'DESKTOP'}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await ws.innerText().catch(()=>''),source},null,2));await p.screenshot({path:`cp6-proof/t3/P11_PAYMENT_${mobile?'MOBILE':'DESKTOP'}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{await user.context.close()}
}
export async function cases(ui,today){return [['P11_PAYMENT_BROWSER_DESKTOP',()=>lifecycle(ui,today,false)],['P11_PAYMENT_BROWSER_MOBILE_RECOVERY',()=>lifecycle(ui,today,true)]]}
