import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_p12_browser_fixture.py',op,JSON.stringify(p)],{cwd:'../writer',encoding:'utf8'}).trim())
async function payrollReview(ui,today,mobile){
 // Prior business state is created through the qualified native Nota commands.
 // This case claims the finance reader/UI, not creation, approval or payment UI.
 const f=fixture('create_payroll_review',{today}),user=await ui.login('ADMIN',{label:'p12-payroll-read-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
 try{
  const p=user.page,menu=p.getByRole('button',{name:'Buka menu',exact:true});await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:'Keuangan'})).toBeAttached()
  if(await menu.isVisible())await menu.click()
  const link=p.getByRole('button',{name:'• Payroll & Kasbon',exact:true});if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Keuangan'}).click();await link.click()
  const panel=p.locator('.cpay'),detail=panel.getByRole('region',{name:'Rincian payroll'})
  await ui.expect(panel.getByRole('heading',{name:'Payroll & Kasbon',exact:true})).toBeVisible()
  await panel.getByLabel('Cari payroll',{exact:true}).fill(f.label);await panel.getByRole('button',{name:'Cari payroll',exact:true}).click()
  await ui.expect(panel.locator('.cproc-receipt')).toHaveCount(1);await panel.locator('.cproc-receipt').click()
  await ui.expect(detail.locator('.cpay-net')).toHaveText('Bersih payrollRp6.000');await ui.expect(detail.locator('.cpay-line')).toHaveCount(2)
  await ui.expect(detail.locator('.cpay-lines')).toContainText('1 PCS × Rp2.000');await ui.expect(detail.locator('.cpay-lines')).toContainText('2 PCS × Rp2.000')
  for(const tab of ['Absensi','Tambahan & reimbursement','Potongan & kasbon']){await detail.getByRole('button',{name:new RegExp('^'+tab.replaceAll('&','\\&'))}).click();await ui.expect(detail).toContainText('Belum ada rincian dalam bagian ini.');await ui.expect(detail.locator('.cpay-net')).toHaveText('Bersih payrollRp6.000')}
  await detail.getByRole('button',{name:/^Nota asal/}).click();await ui.expect(detail.locator('.cpay-line')).toHaveCount(1);await ui.expect(detail.locator('.cpay-line')).toContainText('Rp6.000');await ui.expect(detail.locator('.cpay-lines')).toContainText('1 PCS × Rp2.000 = Rp2.000');await ui.expect(detail.locator('.cpay-lines')).toContainText('2 PCS × Rp2.000 = Rp4.000')
  await ui.expect.poll(()=>panel.evaluate(el=>{const b=el.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
  const direct=await user.rpc('erp_cp7_get_payroll_workspace_v1',{p_section:'PAYROLLS',p_query:{id:f.payroll}})
  if(direct.status!==200||direct.body.capabilities.approve||direct.body.capabilities.pay||direct.body.page.rows[0].net_payable!=='6000.00')throw Error('Finance view-only capability/oracle mismatch')
  let actual=fixture('read',f);if(actual.allocated[0]!==2||actual.allocated[1]!==3||Number(actual.allocated[2])!==6000||JSON.stringify(actual.facts)!==JSON.stringify(f.facts))throw Error('Reading payroll changed business facts')
  mkdirSync('cp6-proof/t3',{recursive:true});await p.evaluate(()=>window.scrollTo(0,0));await p.screenshot({path:`cp6-proof/t3/P12_PAYROLL_REVIEW_${mobile?'MOBILE':'DESKTOP'}.png`,fullPage:true})
  fixture('cancel',f);await panel.getByRole('button',{name:'Muat ulang payroll',exact:true}).click();await ui.expect(detail).toContainText('Rincian berikut adalah riwayat payroll tersebut.');await ui.expect(detail.locator('.cpay-net')).toHaveText('Jumlah pada dokumen batalRp6.000');await ui.expect(detail.locator('.cpay-line')).toHaveCount(1)
  actual=fixture('read',f);if(JSON.stringify(actual.facts)!==JSON.stringify(f.facts))throw Error('Cancelled payroll reader changed money/stock facts')
  await p.route('**/rest/v1/rpc/erp_cp7_get_payroll_workspace_v1',r=>r.abort('failed'));await panel.getByRole('button',{name:'Muat ulang payroll',exact:true}).click();await ui.expect(panel.locator('[role="alert"]').first()).toBeVisible();await ui.expect(panel.locator('.cpay-totals')).toHaveCount(0);await ui.expect(panel.locator('.cproc-receipt')).toHaveCount(0);if((await panel.innerText()).includes('Rp'))throw Error('Failed refresh retained financial facts')
  return {status:'PASS',mobile,finance_view_only:true,actual_browser_native_payroll_review:true,work_qty:3,labor:'6000',tabs_and_native_note_trace:true,full_totals_not_page_subtotal:true,prior_note_created_by_qualified_native_control:true,native_cancel_control_not_connected_reversal:true,reversed_history_explicit:true,failed_refresh_clears_money:true,no_financial_or_stock_read_effect:true,screenshot:`P12_PAYROLL_REVIEW_${mobile?'MOBILE':'DESKTOP'}.png`}
 }catch(error){mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync(`cp6-proof/t3/P12_PAYROLL_REVIEW_${mobile?'MOBILE':'DESKTOP'}_FAILURE.json`,JSON.stringify({error:String(error),panel:await user.page.locator('.cpay').innerText().catch(()=>''),dto:await user.rpc('erp_cp7_get_payroll_workspace_v1',{p_section:'PAYROLLS',p_query:{id:f.payroll}})},null,2));await user.page.screenshot({path:`cp6-proof/t3/P12_PAYROLL_REVIEW_${mobile?'MOBILE':'DESKTOP'}_FAILURE.png`,fullPage:true});throw error
 }finally{await user.context.close()}
}
export async function cases(ui,today){return [['P12_PAYROLL_REVIEW_BROWSER_DESKTOP',()=>payrollReview(ui,today,false)],['P12_PAYROLL_REVIEW_BROWSER_MOBILE',()=>payrollReview(ui,today,true)]]}
