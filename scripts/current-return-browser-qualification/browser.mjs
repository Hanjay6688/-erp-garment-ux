// Explicit UI successors for the qualified malformed sibling DRAFT correction.
import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'

const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/current-return-browser-qualification/fixture.py',op,JSON.stringify(p)],{cwd:'../writer',encoding:'utf8',maxBuffer:8*1024*1024}).trim())
const cents=value=>{const raw=String(value),negative=raw.startsWith('-'),[a,b='']=raw.replace(/^-/,'').split('.');assert.match(b.slice(2),/^0*$/);return(BigInt(a)*100n+BigInt(b.slice(0,2).padEnd(2,'0')))*(negative?-1n:1n)}
const delta=(a,b)=>Object.fromEntries([...new Set([...Object.keys(a),...Object.keys(b)])].map(k=>[k,cents(b[k]??0)-cents(a[k]??0)]).filter(([,v])=>v!==0n))
const positions=(f,grade,returned)=>[{location:f.location,grade:'GRADE_A',qty:6},...(returned?[{location:f.destination,grade,qty:1}]:[])].sort((a,b)=>a.location.localeCompare(b.location)||a.grade.localeCompare(b.grade))
function unchangedDraft(f,read){assert.deepEqual(read.bad_raw,f.bad_raw);assert.equal(read.bad_raw.header.status,'DRAFT');assert.equal(read.bad_journals,0)}

async function open(ui,p){
 await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:'Penjualan'})).toBeAttached()
 const menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=p.getByRole('button',{name:'• Retur Penjualan',exact:true});if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Penjualan'}).click()
 await link.click();await ui.expect(p.locator('.csales').getByRole('heading',{name:'Retur Penjualan',exact:true})).toBeVisible()
}

async function flow(ui,today,mobile){
 const f=fixture('create',{today}),grade=mobile?'GRADE_B':'GRADE_A',number=f.tag+'-UI-GOOD',label=mobile?'MOBILE_B':'DESKTOP_A'
 const user=await ui.login('OWNER',{label:'current-return-'+label.toLowerCase(),mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),p=user.page
 const ws=p.locator('.csales'),detail=ws.getByRole('complementary',{name:'Rincian invoice'}),ret=ws.getByRole('region',{name:'Retur fisik invoice'}),form=ret.getByRole('form',{name:'Catat retur pelanggan'})
 let quote,first=null,replay=null,lost=false
 try{
  await open(ui,p)
  await ws.getByLabel('Cari invoice',{exact:true}).fill(f.tag);await ws.getByRole('button',{name:'Cari invoice',exact:true}).click()
  const rows=ws.getByRole('region',{name:'Daftar invoice'}).locator('.cproc-receipt');await ui.expect(rows).toHaveCount(1);await rows.click()
  await ui.expect(detail.getByRole('heading',{name:f.tag,exact:true})).toBeVisible();await ui.expect(detail).toContainText('Sisa pembayaran Rp80')
  await detail.getByRole('button',{name:'Retur fisik invoice',exact:true}).click();await ui.expect(form).toBeVisible()
  const at=new Date(new Date(f.sale_at).getTime()+(2*60+7*60*60)*1000).toISOString().slice(0,16),iso=new Date(at+'+07:00').toISOString()
  await form.getByLabel('Nomor retur pelanggan',{exact:true}).fill(number)
  await form.getByLabel('Waktu retur pelanggan WIB',{exact:true}).fill(at)
  await form.getByLabel('Cari gudang retur',{exact:true}).fill(f.destination_name);await form.getByRole('button',{name:'Cari gudang retur',exact:true}).click()
  const locations=form.getByRole('region',{name:'Pilih gudang retur'}).locator('.cproc-receipt');await ui.expect(locations).toHaveCount(1);await locations.click()
  const allocations=form.getByRole('region',{name:'Pilih alokasi retur'}).locator('.cproc-receipt');await ui.expect(allocations).toHaveCount(1);await allocations.click()
  await form.getByLabel('Jumlah retur 1',{exact:true}).fill('1');await form.getByLabel('Nilai retur 1',{exact:true}).fill('20');await form.getByLabel('Grade retur 1',{exact:true}).selectOption(grade)
  await form.getByLabel('Catatan barang retur 1',{exact:true}).fill('Retur sah di samping draft yang belum sah')
  await ui.expect(form.getByLabel('Retur pelanggan sudah diperiksa',{exact:true})).toBeDisabled();await ui.expect(form.getByRole('button',{name:'Catat retur dan penyelesaian',exact:true})).toBeDisabled()
  const beforeQuote=fixture('fingerprint',f)
  const [response]=await Promise.all([p.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_get_sales_return_settlement_quote_v1')&&r.request().postDataJSON()?.p_query?.kind!=='ACCOUNT_OPTIONS',{timeout:30000}),form.getByRole('button',{name:'Periksa penyelesaian retur',exact:true}).click()])
  assert.equal(response.status(),200);quote=await response.json();assert.equal(quote.kind,'QUOTE');assert.deepEqual(quote.readiness,{state:'READY',issues:[]})
  assert.equal(quote.current_credit_amount,'0.00');assert.equal(quote.has_recognition_effect,false);assert.equal(quote.totals.after.receivable_remaining,'60.00')
  assert.deepEqual(fixture('fingerprint',f),beforeQuote,'UI quote changed rows, sequences or full22 catalog')
  await ui.expect(form.getByRole('region',{name:'Hasil pemeriksaan penyelesaian retur',exact:true})).toBeVisible();await form.getByLabel('Retur pelanggan sudah diperiksa',{exact:true}).check()
  if(mobile)await p.route('**/rest/v1/rpc/erp_cp7_settle_sales_return_v1',async route=>{
   const body=route.request().postDataJSON()
   if(!lost){first=body;const result=await route.fetch();if(result.status()!==200){await route.fulfill({response:result});return}lost=true;await route.abort('failed')}
   else{if(replay===null)replay=body;await route.continue()}
  })
  await form.getByRole('button',{name:'Catat retur dan penyelesaian',exact:true}).click()
  if(mobile){await ui.expect(ws.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible();await p.reload();await open(ui,p);await ws.getByRole('button',{name:'Reconcile transaksi',exact:true}).click();await ui.expect(ws.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0);assert.ok(lost);assert.deepEqual(replay,first)}
  await ui.expect(ret).toHaveCount(0);await ui.expect(detail).toContainText('Sisa pembayaran Rp60')
  const returned=fixture('read',f);unchangedDraft(f,returned);assert.equal(returned.good_returns.length,1);assert.equal(returned.good_returns[0].number,number);assert.equal(returned.good_returns[0].status,'POSTED');assert.equal(new Date(returned.good_returns[0].physical_at).toISOString(),iso)
  assert.deepEqual(returned.positions,positions(f,grade,true));assert.deepEqual(delta(f.before_return,returned.accounts),{[f.mapping.AR_CUSTOMER]:-2000n,[f.mapping.SALES_REVENUE]:2000n,[f.mapping.FG_INVENTORY]:1000n,[f.mapping.COGS]:-1000n})
  await detail.getByRole('button',{name:'Retur fisik invoice',exact:true}).click();await ui.expect(ret).toContainText(f.destination_name);await ui.expect(ret).toContainText(mobile?'Grade B':'Grade A')
  await ui.expect.poll(()=>ws.evaluate(el=>{const r=el.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
  mkdirSync('cp6-proof/t3',{recursive:true});await p.screenshot({path:`cp6-proof/t3/CURRENT_RETURN_${label}.png`,fullPage:true})
  await ret.getByRole('button',{name:'Koreksi retur '+number,exact:true}).click();await form.getByLabel('Alasan tindakan retur',{exact:true}).fill('Pembatalan eksplisit retur yang sah');await form.getByLabel('Retur pelanggan sudah diperiksa',{exact:true}).check();await form.getByRole('button',{name:'Batalkan retur tercatat',exact:true}).click()
  await ui.expect(ret).toHaveCount(0);await ui.expect(detail).toContainText('Sisa pembayaran Rp80')
  const reversed=fixture('read',f);unchangedDraft(f,reversed);assert.deepEqual(delta(f.before_return,reversed.accounts),{});assert.deepEqual(reversed.positions,positions(f,grade,false));assert.equal(reversed.good_returns[0].status,'REVERSED')
  await detail.getByLabel('Alasan pembatalan penjualan',{exact:true}).fill('Pembatalan sumber setelah inverse retur');await detail.getByLabel('Pembatalan penjualan sudah diperiksa',{exact:true}).check();await detail.getByRole('button',{name:'Batalkan penjualan tercatat',exact:true}).click();await ui.expect(detail).toContainText('Penjualan dibatalkan')
  const final=fixture('read',f);unchangedDraft(f,final);assert.equal(final.sale_status,'REVERSED');assert.equal(final.good_returns.length,1);assert.equal(final.good_returns[0].status,'REVERSED');assert.deepEqual(delta(f.before_sale,final.accounts),{});assert.deepEqual(final.positions,[{location:f.location,grade:'GRADE_A',qty:10}])
  return{status:'PASS',grade,mobile,real_browser_login_quote_commit_and_named_inverse:true,Native_posted_sale_and_malformed_DRAFT_fixture_only:true,malformed_DRAFT_header_items_unchanged_no_journal:true,exact_AR_revenue_FG_COGS_and_stock:true,quote_all_rows_sequences_full22_unchanged:true,explicit_WIB_date_preserved_in_device_zone:true,lost_response_identical_replay_one_return:mobile?true:null,final_GL_neutral_stock10:true,screenshot:`CURRENT_RETURN_${label}.png`}
 }catch(error){
  mkdirSync('cp6-proof/t3',{recursive:true});let source;try{source=fixture('read',f)}catch(e){source={error:String(e)}}
  writeFileSync(`cp6-proof/t3/CURRENT_RETURN_${label}_FAILURE.json`,JSON.stringify({error:String(error),stack:error.stack,text:await ws.innerText().catch(()=>''),source,quote},null,2)+'\n')
  await p.screenshot({path:`cp6-proof/t3/CURRENT_RETURN_${label}_FAILURE.png`,fullPage:true}).catch(()=>{});throw error
 }finally{await user.context.close()}
}

export async function cases(ui,today){return[['CURRENT_RETURN_BROWSER_BAD_DRAFT_DESKTOP_A',()=>flow(ui,today,false)],['CURRENT_RETURN_BROWSER_BAD_DRAFT_MOBILE_B_RECOVERY',()=>flow(ui,today,true)]]}
