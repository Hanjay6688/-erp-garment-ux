import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_f03_cash_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const money=n=>{const [a,b='']=n.split('.');return 'Rp'+(a.startsWith('-')?'-':'')+a.replace(/^-/,'').replace(/\B(?=(\d{3})+(?!\d))/g,'.')+(b.replace(/0+$/,'')?','+b.replace(/0+$/,''):'')}
const matches=(r,q)=>r.url().endsWith('/rpc/erp_cp7_get_sales_v1')&&Object.entries(q).every(([k,v])=>r.request().postDataJSON()?.p_query?.[k]===v)
async function capture(ui,page,name){await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:'cp6-proof/t3/'+name,fullPage:true})}
async function journey(ui,f,mobile){
 const user=await ui.login('OWNER',{label:'f03-receivables-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,ws=page.getByRole('main',{name:'Piutang pelanggan dari invoice',exact:true}),suffix=mobile?'MOBILE':'DESKTOP',screenshots=[]
 const q={q:f.invoice_query,status:null,offset:0,sale_id:null,limit:25},source=query=>{const r=fixture('sales-read',{query});delete r.report.read_at;return r}
 const noSource=async()=>{await ui.expect(ws.locator('[data-sale-id]')).toHaveCount(0);await ui.expect(ws.getByRole('region',{name:'Daftar sumber piutang'})).toHaveCount(0);assert.ok(!(await ws.innerText()).includes('Rp'))}
 let release=null
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
  const link=page.getByRole('button',{name:'• Piutang Pelanggan',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Keuangan'}).click();await link.click()
  await ui.expect(ws.getByRole('button',{name:'Cari piutang',exact:true})).toBeEnabled()
  const before=fixture('sales-state',{})
  await ws.getByRole('textbox',{name:'Cari sumber piutang',exact:true}).fill(q.q);await noSource()
  let response=page.waitForResponse(r=>matches(r,q));await ws.getByRole('button',{name:'Cari piutang',exact:true}).click();let result=await response;assert.equal(result.status(),200)
  assert.equal(fixture('sales-verify',{query:q,report:await result.json()}).status,'PASS')
  const expected=source(q);assert.equal(expected.report.page.total,'1');await ui.expect(ws.locator('[data-sale-id]')).toHaveCount(1)
  await ui.expect(ws.locator('[data-sale-id] strong').last()).toHaveText(money(expected.report.page.rows[0].financial.open_balance))
  const detailQuery={...q,sale_id:f.sale_id};response=page.waitForResponse(r=>matches(r,detailQuery));await ws.locator('[data-sale-id]').click();result=await response;assert.equal(result.status(),200)
  assert.equal(fixture('sales-verify',{query:detailQuery,report:await result.json()}).status,'PASS')
  const detail=source(detailQuery).report.detail,region=ws.getByRole('complementary',{name:'Rincian sumber piutang'})
  for(const [key,label]of [['gross_total','Nilai invoice'],['return_total','Retur tercatat'],['net_total','Nilai sesudah retur'],['paid_total','Pembayaran tercatat'],['open_balance','Sisa tagihan']])await ui.expect(region.locator('.cproc-total').filter({has:page.getByText(label,{exact:true})}).locator('strong')).toHaveText(money(detail.financial[key]))
  for(const item of detail.items)await ui.expect(region).toContainText(item.commercial_sku)
  await ui.expect(ws).toContainText('Kondisi dokumen sekarang');await ui.expect(ws).toContainText('Saldo awal dan penyesuaian buku')
  await capture(ui,page,`F03_RECEIVABLES_SOURCE_${suffix}.png`);screenshots.push(`F03_RECEIVABLES_SOURCE_${suffix}.png`)
  if(mobile){
   let held=null;const prepared=new Promise(resolve=>{held=resolve}),gate=new Promise(resolve=>{release=resolve})
   const handler=async route=>{const fetched=await route.fetch();assert.equal(fetched.status(),200);held();await gate;await route.fulfill({response:fetched})}
   await page.route('**/rest/v1/rpc/erp_cp7_get_sales_v1',handler)
   response=page.waitForResponse(r=>matches(r,detailQuery));await ws.getByRole('button',{name:'Muat ulang piutang',exact:true}).click()
   await Promise.race([prepared,new Promise((_,reject)=>setTimeout(()=>reject(Error('Native receivable response did not arrive')),30000))])
   await ws.getByRole('textbox',{name:'Cari sumber piutang',exact:true}).fill(q.q+'-absent');await noSource()
   release();result=await response;assert.equal(result.status(),200);assert.equal(fixture('sales-verify',{query:detailQuery,report:await result.json()}).status,'PASS')
   await page.unroute('**/rest/v1/rpc/erp_cp7_get_sales_v1',handler);await noSource()
   const next={...q,q:q.q+'-absent'};response=page.waitForResponse(r=>matches(r,next));await ws.getByRole('button',{name:'Muat ulang piutang',exact:true}).click();result=await response;assert.equal(result.status(),200);assert.equal(fixture('sales-verify',{query:next,report:await result.json()}).status,'PASS');await ui.expect(ws).toContainText('Tidak ada invoice sesuai pencarian.');assert.ok(!(await ws.innerText()).includes('Rp'))
  }else{
   await page.route('**/rest/v1/rpc/erp_cp7_get_sales_v1',route=>route.abort('failed'));await ws.getByRole('button',{name:'Muat ulang piutang',exact:true}).click();await ui.expect(ws.getByRole('alert')).toBeVisible();await noSource()
  }
  assert.deepEqual(fixture('sales-state',{}),before)
  await capture(ui,page,`F03_RECEIVABLES_RETIRED_${suffix}.png`);screenshots.push(`F03_RECEIVABLES_RETIRED_${suffix}.png`)
  return {status:'PASS',mobile,actual_owner_native_AR_route:true,complete_source_list_and_detail_match_native:true,all5_detail_money_metrics_exact:true,historical_commercial_SKU_source_kept:true,current_document_basis_and_book_opening_scope_labeled:true,search_edit_retires_source:true,failed_refresh_or_late_HTTP200_cannot_repaint:true,source_business_facts_unchanged:true,financial_writer_claim:false,screenshots}
 }catch(e){writeFileSync(`cp6-proof/t3/F03_RECEIVABLES_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await ws.innerText().catch(()=>''),source:source(q)},null,2));await page.screenshot({path:`cp6-proof/t3/F03_RECEIVABLES_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{release?.();await user.context.close()}
}
export function receivableCases(ui,f){return [['F03_RECEIVABLES_BROWSER_DESKTOP',()=>journey(ui,f,false)],['F03_RECEIVABLES_BROWSER_MOBILE',()=>journey(ui,f,true)]]}
