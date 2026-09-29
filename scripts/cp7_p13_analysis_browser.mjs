import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
// The complete native catalogue/data boundary exceeds Node's default1MiB.
// Preserve the full comparison; refuse explicitly at16MiB rather than trim it.
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_p13_analysis_fixture.py',op,JSON.stringify(p)],{cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
async function analysis(ui,f,mobile){
 const user=await ui.login('OWNER',{label:'p13-analysis-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),p=user.page,suffix=mobile?'MOBILE':'DESKTOP'
 const panel=p.getByRole('region',{name:'Perbandingan periode dan arus kas',exact:true}),read=()=>{const r=fixture('read',f);delete r.report.captured_at;return r}
 try{
  await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:'Keuangan'})).toBeAttached();const menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
  const link=p.getByRole('button',{name:'• Laporan & Tutup Buku',exact:true});if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Keuangan'}).click();await link.click()
  await ui.expect(p.getByRole('button',{name:'Tampilkan laporan',exact:true})).toBeEnabled()
  for(const [name,key]of[['Periode laporan dari','from'],['Periode laporan sampai','to'],['Posisi laporan pada','as_of']])await p.getByLabel(name,{exact:true}).fill(f.query[key])
  await p.getByRole('button',{name:'Tampilkan laporan',exact:true}).click();await panel.getByRole('button',{name:'Buka perbandingan & arus kas',exact:true}).click()
  await panel.getByLabel('Periode pembanding dari',{exact:true}).fill(f.query.compare_from);await panel.getByLabel('Periode pembanding sampai',{exact:true}).fill(f.query.compare_to)
  const before=read();await panel.getByRole('button',{name:'Periksa perbandingan & kas',exact:true}).click()
  const metric=label=>panel.locator('.cproc-total').filter({has:p.getByText(label,{exact:true})}).locator('strong')
  await ui.expect(metric('Pertumbuhan penjualan')).toHaveText('20%');await ui.expect(metric('Perubahan margin kotor')).toHaveText('-3 poin persentase')
  await ui.expect(metric('Perubahan kas bersih')).toHaveText('Rp100');await ui.expect(metric('Debit rekening kas/bank')).toHaveText('Rp1.300');await ui.expect(metric('Kredit rekening kas/bank')).toHaveText('Rp1.200')
  await ui.expect(panel.getByRole('region',{name:'Kinerja periode ini',exact:true})).toContainText('Rp1.200');await ui.expect(panel.getByRole('region',{name:'Kinerja periode pembanding',exact:true})).toContainText('Rp1.000')
  await ui.expect(panel).toContainText('Saldo dan jurnal kas cocok.');await ui.expect(panel).toContainText('Penerimaan kas tidak otomatis menjadi penjualan');await ui.expect(panel).toContainText('pengetahuan masa lalu')
  const transfer=panel.locator('.cproc-item').filter({hasText:'P13_CASH_FIXTURE_TRANSFER'});await ui.expect(transfer).toContainText('bersih Rp0')
  assert.deepEqual(read(),before)
  await ui.expect.poll(()=>panel.evaluate(el=>{const r=el.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
  mkdirSync('cp6-proof/t3',{recursive:true});await p.evaluate(()=>scrollTo(0,0));await p.screenshot({path:`cp6-proof/t3/P13_ANALYSIS_${suffix}.png`,fullPage:true})
  await p.route('**/rest/v1/rpc/erp_cp7_get_finance_analysis_v1',route=>route.abort('failed'));await panel.getByRole('button',{name:'Periksa perbandingan & kas',exact:true}).click();await ui.expect(panel.getByRole('alert')).toBeVisible();await ui.expect(metric('Perubahan kas bersih')).toHaveCount(0);assert.ok(!(await panel.innerText()).includes('Rp'));await ui.expect(panel.getByLabel('Periode pembanding dari',{exact:true})).toHaveValue(f.query.compare_from);assert.deepEqual(read(),before)
  return {status:'PASS',mobile,real_auth_browser_native_reports_and_cash_sources:true,O13_revenue1000_to1200_growth20_margin27_to24_minus3pp:true,O14_internal_transfer1000_net0_receipt300_payment200_net100:true,gross_debits_and_credits_labeled_not_revenue:true,no_GL_stock_or_source_changes_by_browser_read:true,failed_refresh_retires_old_analysis_preserves_dates:true,screenshot:`P13_ANALYSIS_${suffix}.png`}
 }catch(e){mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync(`cp6-proof/t3/P13_ANALYSIS_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await panel.innerText().catch(()=>''),source:read()},null,2));throw e}
 finally{await user.context.close()}
}
export async function cases(ui,today){const f=fixture('prepare',{today});return [['P13_ANALYSIS_BROWSER_DESKTOP',()=>analysis(ui,f,false)],['P13_ANALYSIS_BROWSER_MOBILE',()=>analysis(ui,f,true)]]}
