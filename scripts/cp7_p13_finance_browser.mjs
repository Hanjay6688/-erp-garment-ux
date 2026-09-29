import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_p13_browser_fixture.py',op,JSON.stringify(p)],{cwd:'../writer',encoding:'utf8'}).trim())
const money=n=>{const [a,b='']=n.split('.'),negative=a.startsWith('-');return 'Rp'+(negative?'-':'')+a.replace(/^-/,'').replace(/\B(?=(\d{3})+(?!\d))/g,'.')+(b.replace(/0+$/,'')?','+b.replace(/0+$/,''):'')}
async function report(ui,f,mobile){
 const user=await ui.login('OWNER',{label:'p13-report-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),p=user.page,ws=p.locator('.cfinance-report'),suffix=mobile?'MOBILE':'DESKTOP'
 const read=()=>{const r=fixture('read',f);delete r.report.captured_at;return r}
 try{
  await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:'Keuangan'})).toBeAttached()
  const menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
  const link=p.getByRole('button',{name:'• Laporan & Tutup Buku',exact:true});if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Keuangan'}).click();await link.click()
  await ui.expect(ws.getByRole('heading',{name:'Laporan & Tutup Buku',exact:true})).toBeVisible()
  await ui.expect(ws.getByRole('button',{name:'Tampilkan laporan',exact:true})).toBeEnabled()
  for(const name of ['Periode laporan dari','Periode laporan sampai','Posisi laporan pada'])await ws.getByLabel(name,{exact:true}).fill(f.today)
  await ws.getByRole('button',{name:'Tampilkan laporan',exact:true}).click()
  const performance=ws.getByRole('region',{name:'Kinerja keuangan tercatat'}),position=ws.getByRole('region',{name:'Posisi keuangan tercatat'}),basis=ws.getByRole('region',{name:'Basis dan kesiapan laporan'})
  for(const [label,key]of [['Penjualan menurut jurnal','sales_revenue_gl'],['Harga pokok penjualan','cogs_gl'],['Laba kotor','gross_profit'],['Laba/rugi bersih','net_profit']])await ui.expect(performance.locator('.cproc-total').filter({has:p.getByText(label,{exact:true})}).locator('strong')).toHaveText(money(f.current.snapshot.performance[key]))
  for(const [label,key]of [['Kas dan bank','cash'],['Piutang pelanggan','customer_ar'],['Persediaan barang jadi','fg_inventory']])await ui.expect(position.locator('.cproc-total').filter({has:p.getByText(label,{exact:true})}).locator('strong')).toHaveText(money(f.current.snapshot.financial_position[key]))
  await ui.expect(basis).toContainText('Ini bukan rekonstruksi informasi yang diketahui pada masa lalu.')
  await ui.expect(ws.getByRole('region',{name:'Kondisi supplier saat ini'})).toContainText('kondisi operasional sekarang')
  const before=read(),archive=ws.getByRole('region',{name:'Arsip penutupan keuangan'});await ui.expect(archive.locator('.cproc-receipt')).toHaveCount(1);await archive.locator('.cproc-receipt').click()
  const original=ws.getByRole('region',{name:'Saldo asli saat penutupan'});await ui.expect(original).toBeVisible();await ui.expect(basis).toContainText('Ada perubahan setelah arsip penutupan; arsip asli tetap.');await ui.expect(basis).toContainText('Lolos pemeriksaan tanggal ini')
  await ui.expect(ws.getByLabel('Posisi laporan pada',{exact:true})).toHaveValue(f.day)
  for(const [code,value]of Object.entries(f.corrected.filing.gl_balances))await ui.expect(original.locator('.cproc-total').filter({has:p.getByText('Akun '+code,{exact:true})}).locator('strong')).toHaveText(money(value))
  assert.deepEqual(read(),before)
  await ui.expect.poll(()=>ws.evaluate(el=>{const r=el.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
  mkdirSync('cp6-proof/t3',{recursive:true});await p.evaluate(()=>window.scrollTo(0,0));await p.screenshot({path:`cp6-proof/t3/P13_REPORT_${suffix}.png`,fullPage:true})
  await p.route('**/rest/v1/rpc/erp_cp7_get_finance_report_v1',route=>route.abort('failed'));await ws.getByRole('button',{name:'Muat ulang laporan',exact:true}).click();await ui.expect(ws.getByRole('alert')).toBeVisible();await ui.expect(performance).toHaveCount(0);await ui.expect(original).toHaveCount(0);assert.ok(!(await ws.innerText()).includes('Rp'));await ui.expect(ws.getByLabel('Posisi laporan pada',{exact:true})).toHaveValue(f.day);assert.deepEqual(read(),before)
  return {status:'PASS',mobile,real_auth_native_financial_report_and_original_filing:true,fixtures_native_not_browser_financial_writes:true,source_sale80_return20_cash30_AR30_revenue60_COGS30:true,signed_GL_archive_values_match_native_source:true,READY_current_corrected_keeps_changed_since_filing_marker:true,current_operational_supplier_basis_explicit:true,historical_knowledge_not_invented:true,failed_refresh_retires_old_money_preserves_dates:true,GL_stock_and_filing_unchanged_by_reader:true,screenshot:`P13_REPORT_${suffix}.png`}
 }catch(e){mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync(`cp6-proof/t3/P13_REPORT_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await ws.innerText().catch(()=>''),source:read()},null,2));await p.screenshot({path:`cp6-proof/t3/P13_REPORT_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{await user.context.close()}
}
export async function cases(ui,today){const f=fixture('prepare',{today});return [['P13_REPORT_BROWSER_DESKTOP',()=>report(ui,f,false)],['P13_REPORT_BROWSER_MOBILE',()=>report(ui,f,true)]]}
