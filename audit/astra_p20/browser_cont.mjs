import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {fileURLToPath} from 'node:url'
import {mkdirSync,writeFileSync} from 'node:fs'
const output='cp6-proof/t3/'
const fixture=(op,p)=>JSON.parse(execFileSync('python',[fileURLToPath(new URL('./browser_cont_fixture.py',import.meta.url)),op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8'}).trim())
const write=(name,x)=>{mkdirSync(output,{recursive:true});writeFileSync(output+'ASTRA_'+name+'.json',JSON.stringify(x,null,2)+'\n')}
const cents=n=>{const s=String(n),neg=s.startsWith('-'),[a,b='']=s.replace(/^-/,'').split('.');assert.match(b.slice(2),/^0*$/);return(BigInt(a)*100n+BigInt(b.slice(0,2).padEnd(2,'0')))*(neg?-1n:1n)}
const delta=(a,z)=>Object.fromEntries([...new Set([...Object.keys(a),...Object.keys(z)])].map(k=>[k,cents(z[k]??0)-cents(a[k]??0)]).filter(([,v])=>v!==0n))
async function navigate(ui,page){
 await ui.expect(page.locator('.sidebar .nav-main').filter({hasText:'Penjualan'})).toBeAttached()
 const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=page.getByRole('button',{name:'• Penjualan & Invoice',exact:true})
 if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Penjualan'}).click()
 await link.click();await ui.expect(page.locator('.csales').getByRole('heading',{name:'Penjualan & Invoice',exact:true})).toBeVisible()
}
async function journey(ui,today,mobile){
 const id='AS20C-47-WRITE-'+(mobile?'MOBILE':'DESKTOP'),f=fixture('prepare',{today}),state=()=>fixture('state',{fixture:f}),before=state()
 const user=await ui.login('OWNER',{label:id,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,ws=page.locator('.csales'),detail=ws.getByRole('complementary',{name:'Rincian invoice'})
 const receipts=[],observations={before},errors=[];page.on('pageerror',e=>errors.push(e.message))
 page.on('response',async r=>{if(r.url().includes('/rpc/erp_cp7_save_sale_v1')){let body;try{body=await r.json()}catch{}receipts.push({action:r.request().postDataJSON()?.p_action,status:r.status(),body})}})
 const pick=async(form,label,button,region,text)=>{await form.getByLabel(label,{exact:true}).fill(text);await form.getByRole('button',{name:button,exact:true}).click();const rows=form.getByRole('region',{name:region,exact:true}).locator('.cproc-receipt');await ui.expect(rows).toHaveCount(1);await rows.click()}
 const balance=async expected=>{await ui.expect.poll(()=>state().document?.financial?.open_balance,{timeout:30000}).toBe(expected)}
 try{
  assert.equal(Number(before.available),41);assert.deepEqual(before.unbalanced_journals,[])
  await navigate(ui,page);await ws.getByRole('button',{name:'Buat invoice',exact:true}).click();const draft=ws.getByRole('form',{name:'Draft invoice'})
  await draft.getByLabel('Nomor draft invoice',{exact:true}).fill(f.tag)
  await draft.getByLabel('Waktu draft invoice WIB',{exact:true}).fill(new Date(new Date(f.sale_at).getTime()+7*3600000).toISOString().slice(0,16))
  await pick(draft,'Cari pelanggan draft','Cari pelanggan draft','Pilih pelanggan invoice',f.tag)
  await pick(draft,'Cari barang draft','Cari barang draft','Pilih barang invoice',f.sku)
  await draft.getByLabel('Jumlah invoice 1',{exact:true}).fill('13');await draft.getByLabel('Harga invoice 1',{exact:true}).fill('29,91')
  await draft.getByLabel('Alasan simpan invoice',{exact:true}).fill('Astra thirteen pieces own exact worksheet')
  await draft.getByLabel('Draft invoice sudah diperiksa',{exact:true}).check();await draft.getByRole('button',{name:'Simpan draft invoice',exact:true}).click()
  await ui.expect(draft).toHaveCount(0);await ui.expect(detail).toContainText('13 PCS masih dipesan')
  observations.draft=state();assert.equal(Number(observations.draft.available),28);assert.deepEqual(observations.draft.accounts,before.accounts)
  await detail.getByLabel('Invoice sudah diperiksa',{exact:true}).check();await detail.getByRole('button',{name:'Sahkan invoice',exact:true}).click();await balance('388.83')
  observations.post=state();assert.equal(Number(observations.post.available),28)
  assert.deepEqual(delta(before.accounts,observations.post.accounts),{[f.mapping.AR_CUSTOMER]:38883n,[f.mapping.SALES_REVENUE]:-38883n,[f.mapping.FG_INVENTORY]:-21398n,[f.mapping.COGS]:21398n})
  const pay=ws.getByRole('region',{name:'Pembayaran invoice',exact:true}),pf=pay.getByRole('form',{name:'Catat pembayaran pelanggan'})
  await detail.getByRole('button',{name:'Pembayaran invoice',exact:true}).click()
  await pf.getByLabel('Nomor pembayaran pelanggan',{exact:true}).fill(f.tag+'-PAY');await pf.getByLabel('Nominal pembayaran pelanggan',{exact:true}).fill('137,03')
  await pick(pf,'Cari rekening pembayaran pelanggan','Cari rekening pelanggan','Pilih rekening pembayaran pelanggan',f.bank_code)
  await pf.getByLabel('Pembayaran pelanggan sudah diperiksa',{exact:true}).check();await pf.getByRole('button',{name:'Catat pembayaran pelanggan',exact:true}).click();await ui.expect(pay).toHaveCount(0);await balance('251.80')
  observations.paid=state();assert.deepEqual(delta(observations.post.accounts,observations.paid.accounts),{[f.mapping.AR_CUSTOMER]:-13703n,[f.cash_coa]:13703n})
  const ret=ws.getByRole('region',{name:'Retur fisik invoice',exact:true}),rf=ret.getByRole('form',{name:'Catat retur pelanggan'})
  await detail.getByRole('button',{name:'Retur fisik invoice',exact:true}).click();await rf.getByLabel('Nomor retur pelanggan',{exact:true}).fill(f.tag+'-RET')
  await pick(rf,'Cari gudang retur','Cari gudang retur','Pilih gudang retur',f.destination_name)
  const allocations=rf.getByRole('region',{name:'Pilih alokasi retur',exact:true}).locator('.cproc-receipt');await ui.expect(allocations).toHaveCount(1);await allocations.click()
  await rf.getByLabel('Jumlah retur 1',{exact:true}).fill('4');await rf.getByLabel('Nilai retur 1',{exact:true}).fill('119,64')
  await rf.getByLabel('Grade retur 1',{exact:true}).selectOption(mobile?'GRADE_B':'GRADE_A');await rf.getByLabel('Catatan barang retur 1',{exact:true}).fill('Astra four real returned pieces')
  await rf.getByLabel('Retur pelanggan sudah diperiksa',{exact:true}).check()
  let lost=false,first=null,replay=null,serverReceipt=null
  if(mobile)await page.route('**/rest/v1/rpc/erp_cp7_save_sale_v1',async route=>{const body=route.request().postDataJSON();if(body.p_action==='RETURN'&&!lost){const response=await route.fetch();if(response.status()!==200){await route.fulfill({response});return}first=body;serverReceipt=await response.json();lost=true;await route.abort('failed')}else{if(body.p_action==='RETURN')replay=body;await route.continue()}})
  await rf.getByRole('button',{name:'Catat retur pelanggan',exact:true}).click()
  if(mobile){await ui.expect(ws.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible();observations.committed_without_response=state();assert.equal(observations.committed_without_response.returns.length,1);await page.reload();await navigate(ui,page);await ws.getByRole('button',{name:'Reconcile transaksi',exact:true}).click();await ui.expect(ws.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0);assert.ok(lost);assert.deepEqual(replay,first)}
  await ui.expect(ret).toHaveCount(0);await balance('132.16');observations.returned=state()
  assert.equal(Number(observations.returned.available),32);assert.equal(observations.returned.returns.length,1);assert.equal(observations.returned.payments.length,1)
  const positions=observations.returned.positions.map(([l,g,q])=>[l,g,Number(q)])
  assert.deepEqual(positions,mobile?[[f.location,'GRADE_A',28],[f.location,'GRADE_B',4]]:[[f.location,'GRADE_A',32]])
  assert.deepEqual(delta(before.accounts,observations.returned.accounts),{[f.mapping.AR_CUSTOMER]:13216n,[f.mapping.SALES_REVENUE]:-26919n,[f.mapping.FG_INVENTORY]:-14814n,[f.mapping.COGS]:14814n,[f.cash_coa]:13703n})
  if(mobile)assert.deepEqual(observations.returned.accounts,observations.committed_without_response.accounts)
  await detail.getByRole('button',{name:'Retur fisik invoice',exact:true}).click();await ui.expect(ret).toContainText(mobile?'Grade B':'Grade A')
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
  mkdirSync(output,{recursive:true});await page.screenshot({path:output+'ASTRA_'+id+'_RETURN.png',fullPage:true})
  await ret.getByRole('button',{name:'Tutup retur invoice',exact:true}).click()
  await detail.getByRole('button',{name:'Pembayaran invoice',exact:true}).click();await pay.getByRole('button',{name:'Koreksi pembayaran '+f.tag+'-PAY',exact:true}).click()
  await pf.getByLabel('Alasan tindakan pembayaran',{exact:true}).fill('Astra inverse explicit payment first');await pf.getByLabel('Pembayaran pelanggan sudah diperiksa',{exact:true}).check();await pf.getByRole('button',{name:'Batalkan pembayaran tercatat',exact:true}).click();await ui.expect(pay).toHaveCount(0);await balance('269.19')
  await detail.getByRole('button',{name:'Retur fisik invoice',exact:true}).click();await ret.getByRole('button',{name:'Koreksi retur '+f.tag+'-RET',exact:true}).click()
  await rf.getByLabel('Alasan tindakan retur',{exact:true}).fill('Astra inverse explicit return second');await rf.getByLabel('Retur pelanggan sudah diperiksa',{exact:true}).check();await rf.getByRole('button',{name:'Batalkan retur tercatat',exact:true}).click();await ui.expect(ret).toHaveCount(0);await balance('388.83')
  await detail.getByLabel('Alasan pembatalan penjualan',{exact:true}).fill('Astra inverse explicit sale last');await detail.getByLabel('Pembatalan penjualan sudah diperiksa',{exact:true}).check();await detail.getByRole('button',{name:'Batalkan penjualan tercatat',exact:true}).click();await ui.expect(detail).toContainText('Penjualan dibatalkan')
  observations.final=state();assert.equal(observations.final.document.status,'REVERSED');assert.equal(Number(observations.final.available),41);assert.deepEqual(observations.final.accounts,before.accounts);assert.deepEqual(observations.final.positions,before.positions);assert.deepEqual(observations.final.raw,before.raw);assert.deepEqual(observations.final.unbalanced_journals,[])
  assert.equal(observations.final.returns.length,1);assert.equal(observations.final.returns[0][1],'REVERSED');assert.equal(observations.final.payments.length,1);assert.equal(observations.final.payments[0][1],'REVERSED');assert.deepEqual(errors,[])
  const result={status:'PASS',audit_case_id:id,evidence_origin:'INDEPENDENT_BROWSER_CASE',oracle_origin:'ASTRA_73_41_13_4_13703_EXACT_MATH',fixture_origin:'ASTRA_REAL_PRODUCTION_WITH_WRITER_TRANSPORT',mobile,grade:mobile?'GRADE_B':'GRADE_A',actual_UI_commands:['CREATE','POST','PAYMENT','RETURN','PAYMENT_REVERSE','RETURN_REVERSE','SALE_REVERSE'],response_lost_after_server_commit:mobile,replay_identical:mobile?JSON.stringify(first)===JSON.stringify(replay):null,net_AR:'132.16',net_revenue:'269.19',net_COGS:'148.14',FG_after_return:32,inverse_FG:41,inverse_all_GL_exact:true,production_go:false}
  write(id,{...result,fixture:f,observations,receipts,lostResponse:{first,replay,serverReceipt}});return result
 }catch(e){const result={status:'INCOMPLETE',audit_case_id:id,error:String(e),stack:e.stack,observations,receipts,errors,body:await ws.innerText().catch(()=>''),state:state()};write(id,result);await page.screenshot({path:output+'ASTRA_'+id+'_FAILURE.png',fullPage:true}).catch(()=>{});return result}
 finally{await user.context.close()}
}
export async function cases(ui,today){return [['AS20C-47-WRITE-DESKTOP',()=>journey(ui,today,false)],['AS20C-47-WRITE-MOBILE',()=>journey(ui,today,true)]]}
