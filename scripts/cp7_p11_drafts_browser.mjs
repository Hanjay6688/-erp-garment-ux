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
 const f=fixture('create_draft_source',{today}),user=await ui.login('OWNER',{label:'p11-draft-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),p=user.page,ws=p.locator('.csales'),form=ws.getByRole('form',{name:'Draft invoice'}),detail=ws.getByRole('complementary',{name:'Rincian invoice'}),before=fixture('read_draft',f)
 try{
  await open(ui,p);await ws.getByRole('button',{name:'Buat invoice',exact:true}).click()
  await form.getByLabel('Nomor draft invoice',{exact:true}).fill(f.tag);await form.getByLabel('Waktu draft invoice WIB',{exact:true}).fill(new Date(new Date(f.sale_at).getTime()+7*60*60*1000).toISOString().slice(0,16))
  await form.getByLabel('Jatuh tempo draft invoice',{exact:true}).fill(today);await form.getByLabel('Syarat pembayaran draft',{exact:true}).fill('Transfer setelah barang diperiksa')
  await form.getByLabel('Cari pelanggan draft',{exact:true}).fill(f.tag);await form.getByRole('button',{name:'Cari pelanggan draft',exact:true}).click();await ui.expect(form.getByRole('region',{name:'Pilih pelanggan invoice'}).locator('.cproc-receipt')).toHaveCount(1);await form.getByRole('region',{name:'Pilih pelanggan invoice'}).locator('.cproc-receipt').click()
  for(const sku of [f.sku,f.second.sku]){await form.getByLabel('Cari barang draft',{exact:true}).fill(sku);await form.getByRole('button',{name:'Cari barang draft',exact:true}).click();const rows=form.getByRole('region',{name:'Pilih barang invoice'}).locator('.cproc-receipt');await ui.expect(rows).toHaveCount(1);await rows.click()}
  for(const [n,qty,price,discount] of [[1,'13','20','0'],[2,'2','10,01','0,02']]){await form.getByLabel(`Jumlah invoice ${n}`,{exact:true}).fill(qty);await form.getByLabel(`Harga invoice ${n}`,{exact:true}).fill(price);await form.getByLabel(`Potongan invoice ${n}`,{exact:true}).fill(discount);await form.getByLabel(`Catatan barang invoice ${n}`,{exact:true}).fill('Barang '+n+' tetap utuh')}
  await form.getByLabel('Catatan draft invoice',{exact:true}).fill('Dua barang dan semua catatan');await form.getByLabel('Alasan simpan invoice',{exact:true}).fill('P11 seluruh sumber dan angka diperiksa')
  await ui.expect(form.locator('.cproc-total')).toContainText('Rp280');await ui.expect(form.getByRole('button',{name:'Simpan draft invoice',exact:true})).toBeDisabled();await form.getByLabel('Draft invoice sudah diperiksa',{exact:true}).check()
  let lost=false,first=null,replay=null
  if(mobile)await p.route('**/rest/v1/rpc/erp_cp7_save_sale_v1',async route=>{const body=route.request().postDataJSON();if(body.p_action==='CREATE'&&!lost){first=body;const response=await route.fetch();assert.equal(response.status(),200);lost=true;await route.abort('failed')}else{if(body.p_action==='CREATE'&&replay===null)replay=body;await route.continue()}})
  await form.getByRole('button',{name:'Simpan draft invoice',exact:true}).click()
  if(mobile){await ui.expect(ws.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible();await p.reload();await open(ui,p);await ws.getByRole('button',{name:'Reconcile transaksi',exact:true}).click();await ui.expect(ws.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0);assert.ok(lost);assert.deepEqual(replay,first)}
  await ui.expect(form).toHaveCount(0);await ui.expect(detail).toContainText('15 PCS masih dipesan');let actual=fixture('read_draft',f);assert.deepEqual(actual.available,[17,28]);assert.deepEqual(actual.gl,before.gl);assert.equal(actual.document.financial.gross_total,'280.00');const original=actual.document
  await detail.getByRole('button',{name:'Edit draft invoice',exact:true}).click();await ui.expect(form).toBeVisible()
  // Native child rows are UUID ordered. Select the exact physical product,
  // never assume the original client order survives full native replacement.
  const line=form.locator('article').filter({hasText:f.sku});await ui.expect(line).toHaveCount(1);await line.locator('input[aria-label^="Jumlah invoice"]').fill('5')
  await form.getByLabel('Alasan simpan invoice',{exact:true}).fill('Jumlah barang pertama menjadi5 PCS');await form.getByLabel('Draft invoice sudah diperiksa',{exact:true}).check();await ui.expect(form.locator('.cproc-total')).toContainText('Rp120')
  await ui.expect.poll(()=>ws.evaluate(el=>{const r=el.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
  mkdirSync('cp6-proof/t3',{recursive:true});await p.evaluate(()=>window.scrollTo(0,0));await p.screenshot({path:`cp6-proof/t3/P11_DRAFT_${mobile?'MOBILE':'DESKTOP'}.png`,fullPage:true})
  await form.getByRole('button',{name:'Simpan draft invoice',exact:true}).click();await ui.expect(form).toHaveCount(0);await ui.expect(detail).toContainText('7 PCS masih dipesan');actual=fixture('read_draft',f)
  assert.deepEqual(actual.available,[25,28]);assert.deepEqual(actual.gl,before.gl);assert.equal(actual.document.id,original.id);assert.notEqual(actual.document.row_version,original.row_version);assert.equal(actual.document.physical_at,original.physical_at);assert.equal(actual.document.due_date,original.due_date);assert.equal(actual.document.payment_terms,original.payment_terms);assert.equal(actual.document.notes,original.notes)
  assert.deepEqual(actual.document.items.map(i=>i.notes).sort(),original.items.map(i=>i.notes).sort());assert.equal(actual.document.financial.gross_total,'120.00')
  await detail.getByLabel('Invoice sudah diperiksa',{exact:true}).check();await detail.getByRole('button',{name:'Sahkan invoice',exact:true}).click();await ui.expect(detail).toContainText('Sisa pembayaran Rp120');actual=fixture('read_draft',f);assert.deepEqual(actual.available,[25,28]);assert.equal(actual.document.status,'POSTED')
  return {status:'PASS',mobile,source_customer_and_two_products_only_are_fixtures:true,browser_create_edit_post:true,manual13_preserved:true,initial_total:'280',edited_total:'120',initial_available:[17,28],edited_and_post_available:[25,28],all_other_lines_notes_terms_due_full_timestamp_retained:true,create_edit_no_gl_effect:true,lost_create_replay_identical:mobile?true:null,screenshot:`P11_DRAFT_${mobile?'MOBILE':'DESKTOP'}.png`}
 }catch(e){let source;try{source=fixture('read_draft',f)}catch(x){source={error:String(x)}}mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync(`cp6-proof/t3/P11_DRAFT_${mobile?'MOBILE':'DESKTOP'}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await ws.innerText().catch(()=>''),source},null,2));await p.screenshot({path:`cp6-proof/t3/P11_DRAFT_${mobile?'MOBILE':'DESKTOP'}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{await user.context.close()}
}
export async function cases(ui,today){return [['P11_DRAFT_BROWSER_DESKTOP',()=>lifecycle(ui,today,false)],['P11_DRAFT_BROWSER_MOBILE_RECOVERY',()=>lifecycle(ui,today,true)]]}
