import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_f03_cash_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const matches=(r,q)=>r.url().endsWith('/rpc/erp_cp7_get_journal_book_v1')&&Object.entries(q).every(([k,v])=>r.request().postDataJSON()?.p_query?.[k]===v)
const money=n=>{const [a,b='']=n.split('.');return 'Rp'+a.replace(/\B(?=(\d{3})+(?!\d))/g,'.')+(b.replace(/0+$/,'')?','+b.replace(/0+$/,''):'')}
async function capture(ui,page,name){await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:'cp6-proof/t3/'+name,fullPage:true})}
async function journey(ui,today,mobile){
 const f=fixture('journal-prepare',{today}),user=await ui.login(mobile?'ADMIN':'OWNER',{label:'f03-journal-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,ws=page.getByRole('main',{name:'Jurnal keuangan dari buku',exact:true}),suffix=mobile?'MOBILE':'DESKTOP',screenshots=[]
 const source=query=>{const r=fixture('journal-read',{query});delete r.report.captured_at;return r}
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
  const link=page.getByRole('button',{name:'• Jurnal & Transaksi Lain',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Keuangan'}).click();await link.click()
  await ui.expect(ws.getByRole('button',{name:'Tampilkan jurnal',exact:true})).toBeEnabled()
  await ws.getByLabel('Periode jurnal dari',{exact:true}).fill(f.query.from);await ws.getByLabel('Periode jurnal sampai',{exact:true}).fill(f.query.to);await ws.getByLabel('Cari sumber jurnal',{exact:true}).fill(f.query.q)
  const before=source(f.query)
  let response=page.waitForResponse(r=>matches(r,f.query));await ws.getByRole('button',{name:'Tampilkan jurnal',exact:true}).click();let result=await response;assert.equal(result.status(),200);assert.equal(fixture('journal-verify',{query:f.query,report:await result.json()}).status,'PASS')
  await ui.expect(ws.locator('[data-journal-id]')).toHaveCount(25);await ui.expect(ws.getByRole('region',{name:'Basis dan total jurnal'})).toContainText('Total 30 jurnal · 60 baris akun.');await ui.expect(ws.getByRole('region',{name:'Basis dan total jurnal'})).toContainText('Rp37,5')
  await capture(ui,page,`F03_JOURNAL_PAGE1_${suffix}.png`);screenshots.push(`F03_JOURNAL_PAGE1_${suffix}.png`)
  const next={...f.query,offset:25};response=page.waitForResponse(r=>matches(r,next));await ws.getByRole('button',{name:'Jurnal berikutnya',exact:true}).click();result=await response;assert.equal(result.status(),200);assert.equal(fixture('journal-verify',{query:next,report:await result.json()}).status,'PASS');await ui.expect(ws.locator('[data-journal-id]')).toHaveCount(5);await ui.expect(ws.getByRole('region',{name:'Basis dan total jurnal'})).toContainText('Rp37,5')
  const selected=source(next).report.page.rows[0],detailQuery={...next,journal_id:selected.id};response=page.waitForResponse(r=>matches(r,detailQuery));await ws.locator('[data-journal-id]').first().click();result=await response;assert.equal(result.status(),200);assert.equal(fixture('journal-verify',{query:detailQuery,report:await result.json()}).status,'PASS')
  const detail=source(detailQuery).report.detail;await ui.expect(ws.locator('[data-journal-line-id]')).toHaveCount(2)
  for(const line of detail.lines){const element=ws.locator(`[data-journal-line-id="${line.id}"]`);await ui.expect(element).toContainText(line.account_code+' · '+line.account_name);await ui.expect(element).toContainText('Debit '+money(line.debit)+' · kredit '+money(line.credit))}
  await capture(ui,page,`F03_JOURNAL_DETAIL_${suffix}.png`);screenshots.push(`F03_JOURNAL_DETAIL_${suffix}.png`)
  if(mobile){fixture('journal-revoke',{});response=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_get_journal_book_v1'));await ws.getByRole('button',{name:'Muat ulang jurnal',exact:true}).click();result=await response;assert.equal(result.status(),403)}
  else{await page.route('**/rest/v1/rpc/erp_cp7_get_journal_book_v1',route=>route.abort('failed'));await ws.getByRole('button',{name:'Muat ulang jurnal',exact:true}).click()}
  await ui.expect(ws.getByRole('alert')).toBeVisible();await ui.expect(ws.locator('[data-journal-id]')).toHaveCount(0);await ui.expect(ws.locator('[data-journal-line-id]')).toHaveCount(0);assert.ok(!(await ws.innerText()).includes('Rp'));assert.deepEqual(source(f.query),before)
  await capture(ui,page,`F03_JOURNAL_RETIRED_${suffix}.png`);screenshots.push(`F03_JOURNAL_RETIRED_${suffix}.png`)
  return {status:'PASS',mobile,actual_OWNER_or_ADMIN_native_journal_route:true,complete30_header_pages25_plus5_match_native:true,all_totals37_50_not_page_subtotals:true,all_selected_account_lines_exact:true,failed_network_or_current403_retires_all_money_source_and_lines:true,actual_current_ADMIN_permission_revocation:mobile,source_journals_unchanged:true,no_financial_writer_claim:true,screenshots}
 }catch(e){writeFileSync(`cp6-proof/t3/F03_JOURNAL_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await ws.innerText().catch(()=>''),source:source(f.query)},null,2));await page.screenshot({path:`cp6-proof/t3/F03_JOURNAL_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{await user.context.close()}
}
export function journalCases(ui,today){return [['F03_JOURNAL_BROWSER_DESKTOP',()=>journey(ui,today,false)],['F03_JOURNAL_BROWSER_MOBILE_CURRENT_AUTH',()=>journey(ui,today,true)]]}
