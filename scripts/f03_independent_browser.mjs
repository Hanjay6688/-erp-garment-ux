import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync, writeFileSync} from 'node:fs'

const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/f03_independent_browser_fixture.py',op,JSON.stringify(p)],{cwd:'../writer',encoding:'utf8'}).trim())
const cents=s=>{const negative=String(s).startsWith('-'),[a,b='']=String(s).replace(/^-/,'').split('.');assert.match(b.slice(2),/^0*$/);return (BigInt(a)*100n+BigInt(b.slice(0,2).padEnd(2,'0')))*(negative?-1n:1n)}
const delta=(a,b)=>Object.fromEntries([...new Set([...Object.keys(a),...Object.keys(b)])].map(k=>[k,cents(b[k]??'0')-cents(a[k]??'0')]).filter(([,v])=>v!==0n))

async function open(ui,p){
 await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:'Penjualan'})).toBeAttached()
 const menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=p.getByRole('button',{name:'• Penjualan & Invoice',exact:true})
 if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Penjualan'}).click()
 await link.click()
 await ui.expect(p.locator('.csales').getByRole('heading',{name:'Penjualan & Invoice',exact:true})).toBeVisible()
}

async function journey(ui,today,mobile){
 const f=fixture('create',{today}),u=await ui.login('OWNER',{label:'if03-'+mobile,mobile,timezoneId:mobile?'Pacific/Honolulu':'Asia/Jakarta'})
 const p=u.page,ws=p.locator('.csales'),detail=ws.getByRole('complementary',{name:'Rincian invoice'}),panel=ws.getByRole('region',{name:'Pembayaran invoice',exact:true}),form=panel.getByRole('form',{name:'Catat pembayaran pelanggan'})
 const proof=`cp6-proof/t3/IF03_BROWSER_${mobile?'MOBILE':'DESKTOP'}`
 mkdirSync('cp6-proof/t3',{recursive:true})
 try{
  await open(ui,p)
  await ws.getByLabel('Cari invoice',{exact:true}).fill(f.tag)
  await ws.getByRole('button',{name:'Cari invoice',exact:true}).click()
  await ui.expect(ws.locator('.cproc-receipt')).toHaveCount(1)
  await ws.locator('.cproc-receipt').click()
  await ui.expect(detail).toContainText('7 PCS masih dipesan')
  await detail.getByLabel('Invoice sudah diperiksa',{exact:true}).check()
  await detail.getByRole('button',{name:'Sahkan invoice',exact:true}).click()
  await ui.expect(detail).toContainText('Sisa pembayaran Rp259,85')
  const posted=fixture('read',f);assert.equal(posted.available,3)
  let captured=null,replayed=null,lost=false
  await p.route('**/rest/v1/rpc/erp_cp7_save_sale_v1',async route=>{
   const body=route.request().postDataJSON()
   if(body.p_action==='PAYMENT'&&!lost){
    captured=body
    const response=await route.fetch();assert.equal(response.status(),200)
    await route.abort('failed');lost=true
   }else{if(body.p_action==='PAYMENT'&&replayed===null)replayed=body;await route.continue()}
  })
  await detail.getByRole('button',{name:'Pembayaran invoice',exact:true}).click()
  await ui.expect(panel.getByRole('heading',{name:'Riwayat pembayaran',exact:true})).toBeVisible()
  await form.getByLabel('Nomor pembayaran pelanggan',{exact:true}).fill(f.tag+'-INDEPENDENT')
  await form.getByLabel('Nominal pembayaran pelanggan',{exact:true}).fill('123,45')
  await form.getByLabel('Cari rekening pembayaran pelanggan',{exact:true}).fill(f.bank_code)
  await form.getByRole('button',{name:'Cari rekening pelanggan',exact:true}).click()
  const bank=form.getByRole('region',{name:'Pilih rekening pembayaran pelanggan'}).locator('.cproc-receipt')
  await ui.expect(bank).toHaveCount(1);await bank.click()
  await form.getByLabel('Catatan pembayaran pelanggan',{exact:true}).fill('Independent exact cash worksheet reviewed')
  await form.getByLabel('Pembayaran pelanggan sudah diperiksa',{exact:true}).check()
  await form.getByRole('button',{name:'Catat pembayaran pelanggan',exact:true}).click()
  await ui.expect(ws.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible()
  // Pending UI is visible while the request is still in flight. Synchronize
  // on our completed real-response loss before inspecting committed facts.
  await ui.expect.poll(()=>lost,{timeout:20000}).toBe(true)
  assert.ok(lost)
  const committed=fixture('read',f)
  assert.equal(committed.document.financial.open_balance,'136.40')
  assert.equal(committed.payments.total,'1')
  assert.deepEqual(delta(posted.accounts,committed.accounts),{[f.cash_coa]:12345n,[f.ar_coa]:-12345n})
  await p.reload();await open(ui,p)
  await ws.getByRole('button',{name:'Reconcile transaksi',exact:true}).click()
  await ui.expect(ws.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0)
  await ui.expect(detail).toContainText('Sisa pembayaran Rp136,4')
  assert.deepEqual(replayed,captured)
  const final=fixture('read',f)
  assert.equal(final.available,3);assert.equal(final.payments.total,'1');assert.deepEqual(final.accounts,committed.accounts)
  await p.screenshot({path:proof+'.png',fullPage:true})
  // A failed current read must remove the old financial document. No fake RPC
  // result is supplied: this is an actual network-failure injection only.
  await p.route('**/rest/v1/rpc/erp_cp7_get_sales_v1',route=>route.abort('failed'))
  await ws.getByRole('button',{name:'Muat ulang invoice',exact:true}).click()
  await ui.expect(ws.getByRole('alert').first()).toBeVisible()
  await ui.expect(ws.locator('.cproc-receipt')).toHaveCount(0)
  assert.ok(!(await ws.innerText()).includes('Rp136,4'))
  assert.deepEqual(fixture('read',f).accounts,committed.accounts)
  return {status:'PASS',mobile,invoice:'259.85',cash:'123.45',remaining:'136.40',available:3,
   actual_auth_and_database:true,fixture_only_draft_and_bank:true,one_committed_payment_after_lost_response:true,
   exact_original_envelope:true,only_cash_AR_changed:true,failed_refresh_retires_old_money:true,screenshot:proof+'.png'}
 }catch(e){
  writeFileSync(proof+'_FAILURE.json',JSON.stringify({error:String(e),stack:e.stack,body:await ws.innerText().catch(()=>''),source:fixture('read',f)},null,2))
  await p.screenshot({path:proof+'_FAILURE.png',fullPage:true}).catch(()=>{})
  throw e
 }finally{await u.context.close()}
}
export async function cases(ui,today){return [['IF03_B01_DESKTOP_RECOVERY',()=>journey(ui,today,false)],['IF03_B02_MOBILE_RECOVERY',()=>journey(ui,today,true)]]}
