import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'

const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_f03_cash_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const previous=day=>new Date(Date.parse(day+'T00:00:00Z')-86400000).toISOString().slice(0,10)
const money=n=>{const [a,b='']=n.split('.');return 'Rp'+(a.startsWith('-')?'-':'')+a.replace(/^-/,'').replace(/\B(?=(\d{3})+(?!\d))/g,'.')+(b.replace(/0+$/,'')?','+b.replace(/0+$/,''):'')}
const matches=(r,q)=>r.url().endsWith('/rpc/erp_cp7_get_finance_report_v1')&&Object.entries(q).every(([k,v])=>r.request().postDataJSON()?.p_query?.[k]===v)
async function capture(ui,page,name){await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:'cp6-proof/t3/'+name,fullPage:true})}
async function journey(ui,f,mobile){
 const user=await ui.login('OWNER',{label:'f03-finance-overview-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,ws=page.getByRole('main',{name:'Ringkasan keuangan dari buku',exact:true}),suffix=mobile?'MOBILE':'DESKTOP',screenshots=[]
 const q={from:f.query.from,to:f.query.to,as_of:f.query.as_of},source=dates=>{const r=fixture('report-read',{dates});delete r.report.captured_at;return r}
 const noMoney=async()=>{await ui.expect(ws.getByRole('region',{name:'Saldo ringkasan tercatat'})).toHaveCount(0);await ui.expect(ws.getByRole('region',{name:'Kinerja ringkasan tercatat'})).toHaveCount(0);assert.ok(!(await ws.innerText()).includes('Rp'))}
 let release=null
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
  const link=page.getByRole('button',{name:'• Ringkasan Keuangan',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Keuangan'}).click();await link.click()
  await ui.expect(ws.getByRole('button',{name:'Tampilkan ringkasan',exact:true})).toBeEnabled()
  for(const [label,key]of [['Periode ringkasan dari','from'],['Periode ringkasan sampai','to'],['Posisi ringkasan pada','as_of']])await ws.getByLabel(label,{exact:true}).fill(q[key])
  const before=source(q)
  let response=page.waitForResponse(r=>matches(r,q));await ws.getByRole('button',{name:'Tampilkan ringkasan',exact:true}).click()
  let result=await response;assert.equal(result.status(),200);assert.equal(fixture('report-verify',{dates:q,report:await result.json()}).status,'PASS')
  const s=before.report.snapshot,metric=label=>ws.locator('.cproc-total').filter({has:page.getByText(label,{exact:true})}).locator('strong')
  for(const [key,label]of [['cash','Kas dan bank'],['customer_ar','Piutang pelanggan menurut buku'],['supplier_final_ap','Utang supplier final menurut buku'],['grni_estimated_liability','Estimasi barang belum ditagih'],['assets','Total aset'],['liabilities','Total kewajiban']])await ui.expect(metric(label)).toHaveText(money(s.financial_position[key]))
  for(const [key,label]of [['sales_revenue_gl','Penjualan menurut jurnal'],['cogs_gl','Harga pokok penjualan'],['gross_profit','Laba kotor'],['operating_and_other_expense','Beban operasi dan lainnya'],['other_income','Penghasilan lain'],['net_profit','Laba/rugi bersih']])await ui.expect(metric(label)).toHaveText(money(s.performance[key]))
  const status={READY:'Lolos pemeriksaan tanggal ini',BLOCKED:'Ada penghalang',RECALC_PENDING:'Menunggu hitung ulang biaya'}
  await ui.expect(ws.getByRole('region',{name:'Basis dan kesiapan ringkasan'})).toContainText(status[s.data_confidence.status])
  for(const b of s.data_confidence.blockers)await ui.expect(ws).toContainText(b.reason)
  await ui.expect(ws).toContainText('Kondisi operasional sekarang');assert.ok(!(await ws.innerText()).includes('141 jt'))
  await capture(ui,page,`F03_FINANCE_OVERVIEW_SOURCE_${suffix}.png`);screenshots.push(`F03_FINANCE_OVERVIEW_SOURCE_${suffix}.png`)

  const selected={...q,from:previous(q.from)}
  await ws.getByLabel('Periode ringkasan dari',{exact:true}).fill(selected.from);await noMoney()
  response=page.waitForResponse(r=>matches(r,selected));await ws.getByRole('button',{name:'Tampilkan ringkasan',exact:true}).click();result=await response;assert.equal(result.status(),200);assert.equal(fixture('report-verify',{dates:selected,report:await result.json()}).status,'PASS')
  await ui.expect(ws.getByRole('region',{name:'Basis dan kesiapan ringkasan'})).toContainText(`Periode ${selected.from}–${selected.to}`)
  if(mobile){
   let held=null;const prepared=new Promise(resolve=>{held=resolve}),gate=new Promise(resolve=>{release=resolve})
   const handler=async route=>{const fetched=await route.fetch();assert.equal(fetched.status(),200);held();await gate;await route.fulfill({response:fetched})}
   await page.route('**/rest/v1/rpc/erp_cp7_get_finance_report_v1',handler)
   response=page.waitForResponse(r=>matches(r,selected));await ws.getByRole('button',{name:'Tampilkan ringkasan',exact:true}).click()
   await Promise.race([prepared,new Promise((_,reject)=>setTimeout(()=>reject(Error('Native report response did not arrive')),30000))])
   await ws.getByLabel('Posisi ringkasan pada',{exact:true}).fill(previous(selected.from));await noMoney();await ws.getByRole('button',{name:'Tampilkan ringkasan',exact:true}).click()
   await ui.expect(ws.getByRole('alert')).toContainText('Pilih tanggal mulai');release();result=await response;assert.equal(result.status(),200);assert.equal(fixture('report-verify',{dates:selected,report:await result.json()}).status,'PASS')
   await page.unroute('**/rest/v1/rpc/erp_cp7_get_finance_report_v1',handler);await noMoney()
  }else{
   await page.route('**/rest/v1/rpc/erp_cp7_get_finance_report_v1',route=>route.abort('failed'));await ws.getByRole('button',{name:'Tampilkan ringkasan',exact:true}).click();await ui.expect(ws.getByRole('alert')).toBeVisible();await noMoney()
  }
  assert.deepEqual(source(q),before)
  await capture(ui,page,`F03_FINANCE_OVERVIEW_RETIRED_${suffix}.png`);screenshots.push(`F03_FINANCE_OVERVIEW_RETIRED_${suffix}.png`)
  return {status:'PASS',mobile,actual_owner_native_overview_route:true,complete_report_matches_native:true,all12_money_metrics_exact:true,native_readiness_and_blockers:true,current_supplier_exposure_labeled:true,no_simulated_financial_amounts:true,date_edit_retires_immediately:true,failed_refresh_or_late_HTTP200_cannot_repaint:true,source_business_facts_unchanged:true,financial_writer_claim:false,screenshots}
 }catch(e){writeFileSync(`cp6-proof/t3/F03_FINANCE_OVERVIEW_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await ws.innerText().catch(()=>''),source:source(q)},null,2));await page.screenshot({path:`cp6-proof/t3/F03_FINANCE_OVERVIEW_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{release?.();await user.context.close()}
}
export function financeOverviewCases(ui,f){return [['F03_FINANCE_OVERVIEW_BROWSER_DESKTOP',()=>journey(ui,f,false)],['F03_FINANCE_OVERVIEW_BROWSER_MOBILE',()=>journey(ui,f,true)]]}
