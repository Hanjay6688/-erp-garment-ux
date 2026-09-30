import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'

const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_f03_cash_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const previous=(day,n=1)=>new Date(Date.parse(day+'T00:00:00Z')-n*86400000).toISOString().slice(0,10)
const money=n=>{const [a,b='']=n.split('.'),negative=a.startsWith('-');return 'Rp'+(negative?'-':'')+a.replace(/^-/,'').replace(/\B(?=(\d{3})+(?!\d))/g,'.')+(b.replace(/0+$/,'')?','+b.replace(/0+$/,''):'')}
const rpc='/rpc/erp_cp7_get_finance_report_v1'
const isQuery=(r,dates)=>r.url().endsWith(rpc)&&Object.entries(dates).every(([k,v])=>r.request().postDataJSON()?.p_query?.[k]===v)
async function capture(ui,page,name){
 await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
 await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:'cp6-proof/t3/'+name,fullPage:true})
}
async function journey(ui,f,mobile){
 const user=await ui.login('OWNER',{label:'f03-report-dates-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,ws=page.locator('.cfinance-report'),suffix=mobile?'MOBILE':'DESKTOP',screenshots=[]
 const dates={from:f.query.from,to:f.query.to,as_of:f.query.as_of}
 const source=q=>{const r=fixture('report-read',{dates:q});delete r.report.captured_at;return r}
 const noAmounts=async()=>{await ui.expect(ws.getByRole('region',{name:'Kinerja keuangan tercatat'})).toHaveCount(0);await ui.expect(ws.getByRole('region',{name:'Posisi keuangan tercatat'})).toHaveCount(0);assert.ok(!(await ws.innerText()).includes('Rp'))}
 let release=null
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  await ui.expect(page.locator('.sidebar .nav-main').filter({hasText:'Keuangan'})).toBeAttached()
  const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
  const link=page.getByRole('button',{name:'• Laporan & Tutup Buku',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Keuangan'}).click();await link.click()
  await ui.expect(ws.getByRole('button',{name:'Tampilkan laporan',exact:true})).toBeEnabled()
  for(const [label,key]of [['Periode laporan dari','from'],['Periode laporan sampai','to'],['Posisi laporan pada','as_of']])await ws.getByLabel(label,{exact:true}).fill(dates[key])
  let response=page.waitForResponse(r=>isQuery(r,dates))
  await ws.getByRole('button',{name:'Tampilkan laporan',exact:true}).click()
  let result=await response;assert.equal(result.status(),200)
  assert.equal(fixture('report-verify',{dates,report:await result.json()}).status,'PASS')
  const before=source(dates),position=ws.getByRole('region',{name:'Posisi keuangan tercatat'})
  await ui.expect(position.locator('.cproc-total').filter({has:page.getByText('Kas dan bank',{exact:true})}).locator('strong')).toHaveText(money(before.report.snapshot.financial_position.cash))
  await capture(ui,page,`F03_REPORT_DATE_SOURCE_${suffix}.png`);screenshots.push(`F03_REPORT_DATE_SOURCE_${suffix}.png`)

  // No automatic read may put the old source period under edited date controls.
  const selected={...dates,from:previous(dates.from)}
  await ws.getByLabel('Periode laporan dari',{exact:true}).fill(selected.from);await noAmounts()
  response=page.waitForResponse(r=>isQuery(r,selected))
  await ws.getByRole('button',{name:'Muat ulang laporan',exact:true}).click()
  result=await response;assert.equal(result.status(),200)
  assert.equal(fixture('report-verify',{dates:selected,report:await result.json()}).status,'PASS')
  await ui.expect(ws.getByRole('region',{name:'Basis dan kesiapan laporan'})).toContainText(`Periode ${selected.from}–${selected.to}`)

  // Hold an actual successful native HTTP response, edit to an invalid range,
  // then deliver it. The result must remain retired despite HTTP200.
  let held=null;const prepared=new Promise(resolve=>{held=resolve}),gate=new Promise(resolve=>{release=resolve})
  const handler=async route=>{const fetched=await route.fetch();assert.equal(fetched.status(),200);held();await gate;await route.fulfill({response:fetched})}
  await page.route('**/rest/v1/rpc/erp_cp7_get_finance_report_v1',handler)
  response=page.waitForResponse(r=>isQuery(r,selected))
  await ws.getByRole('button',{name:'Muat ulang laporan',exact:true}).click();await prepared
  await ws.getByLabel('Posisi laporan pada',{exact:true}).fill(previous(selected.from));await noAmounts()
  await ws.getByRole('button',{name:'Tampilkan laporan',exact:true}).click()
  await ui.expect(ws.getByRole('alert')).toContainText('Pilih tanggal mulai')
  release();result=await response;assert.equal(result.status(),200)
  assert.equal(fixture('report-verify',{dates:selected,report:await result.json()}).status,'PASS')
  await page.unroute('**/rest/v1/rpc/erp_cp7_get_finance_report_v1',handler)
  await noAmounts();await ui.expect(ws.getByRole('alert')).toContainText('Pilih tanggal mulai')
  await capture(ui,page,`F03_REPORT_DATE_RETIRED_${suffix}.png`);screenshots.push(`F03_REPORT_DATE_RETIRED_${suffix}.png`)

  await ws.getByLabel('Posisi laporan pada',{exact:true}).fill(selected.as_of)
  response=page.waitForResponse(r=>isQuery(r,selected));await ws.getByRole('button',{name:'Muat ulang laporan',exact:true}).click()
  result=await response;assert.equal(result.status(),200);assert.equal(fixture('report-verify',{dates:selected,report:await result.json()}).status,'PASS')
  await ui.expect(ws.getByRole('region',{name:'Posisi keuangan tercatat'})).toBeVisible()
  assert.deepEqual(source(dates),before)
  return {status:'PASS',mobile,actual_owner_auth_native_report:true,complete_report_rows_amounts_readiness_match_native:true,date_edit_retires_old_money:true,refresh_uses_entered_dates:true,held_actual_HTTP200_cannot_repaint_after_invalid_dates:true,explicit_valid_refresh_recovers:true,source_business_facts_unchanged:true,financial_writer_claim:false,screenshots}
 }catch(e){
  mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync(`cp6-proof/t3/F03_REPORT_DATES_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await ws.innerText().catch(()=>''),source:source(dates)},null,2))
  await page.screenshot({path:`cp6-proof/t3/F03_REPORT_DATES_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e
 }finally{release?.();await user.context.close()}
}
export function reportDateCases(ui,f){return [['F03_REPORT_DATES_BROWSER_DESKTOP',()=>journey(ui,f,false)],['F03_REPORT_DATES_BROWSER_MOBILE',()=>journey(ui,f,true)]]}
