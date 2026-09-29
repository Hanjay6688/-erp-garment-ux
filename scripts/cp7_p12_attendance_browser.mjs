import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_p12_browser_fixture.py',op,JSON.stringify(p)],{cwd:'../writer',encoding:'utf8'}).trim())
async function readSources(ui,today,mobile){
 const f=fixture('create_attendance_read',{today}),user=await ui.login('ADMIN',{label:'p12-attendance-read-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
 const p=user.page,suffix=mobile?'MOBILE':'DESKTOP'
 try{
  fixture('bind_settlement_actor',{role:f.role,actor:user.user.id});await p.reload()
  await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:'Keuangan'})).toBeAttached();const menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
  const link=p.getByRole('button',{name:'• Absensi & Rate Harian',exact:true});if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Keuangan'}).click();await link.click()
  const panel=p.locator('.catt'),detail=panel.getByRole('region',{name:'Rincian sumber absensi'})
  await ui.expect(panel.getByRole('heading',{name:'Absensi & Rate Harian',exact:true})).toBeVisible()
  await panel.getByLabel('Pencarian absensi',{exact:true}).fill(f.label);await panel.getByLabel('Absensi dari tanggal',{exact:true}).fill(f.workday);await panel.getByLabel('Absensi sampai tanggal',{exact:true}).fill(f.workday);await panel.getByRole('button',{name:'Tampilkan absensi',exact:true}).click()
  await ui.expect(panel.locator('.cproc-receipt')).toHaveCount(1);await panel.locator('.cproc-receipt').click();await ui.expect(panel.locator('.cproc-receipt')).toHaveCount(2)
  const historical=panel.locator('.cproc-receipt').filter({hasText:'Pekerja riwayat'});await ui.expect(historical).toContainText('Nonaktif sekarang');await ui.expect(historical).toContainText('Rp100,123456');await historical.click()
  await ui.expect(detail.locator('.catt-line')).toHaveCount(1);await ui.expect(detail.locator('.catt-line')).toContainText('Rp100,123456 / hari');assert.ok(!(await panel.innerText()).includes('Rp200,654321'),'Future rate must not replace the historical selection')
  await ui.expect.poll(()=>panel.evaluate(el=>{const b=el.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
  mkdirSync('cp6-proof/t3',{recursive:true});await p.evaluate(()=>window.scrollTo(0,0));await p.screenshot({path:`cp6-proof/t3/P12_ATTENDANCE_READ_${suffix}.png`,fullPage:true})
  await detail.getByRole('button',{name:'Riwayat masa kerja',exact:true}).click();await ui.expect(detail.locator('.catt-line')).toHaveCount(1);await ui.expect(detail.locator('.catt-line')).toContainText('P12 ordinary historical stop')
  await panel.getByRole('button',{name:'Periode absensi',exact:true}).click();await ui.expect(panel.locator('.cproc-receipt')).toHaveCount(1);await panel.locator('.cproc-receipt').click()
  await ui.expect(detail.locator('.catt-line')).toHaveCount(2);await ui.expect(detail).toContainText('Setengah hari');await ui.expect(detail).toContainText('0,5 hari dibayar');await ui.expect(detail).toContainText('Hari yang belum dicatat tidak dianggap tidak hadir atau libur.');await ui.expect(detail).toContainText('Belum dipakai oleh payroll aktif.')
  assert.deepEqual(fixture('read_attendance_facts',f),{facts:f.facts,source_facts:f.source_facts},'Reader cannot alter attendance, roster, rates, payroll, stock, HPP or GL')
  await panel.getByRole('button',{name:'Pekerja & riwayat tarif',exact:true}).click();await ui.expect(panel.locator('.cproc-receipt')).toHaveCount(2);await panel.locator('.cproc-receipt').filter({hasText:'Pekerja riwayat'}).click();await ui.expect(detail.locator('.catt-line')).toContainText('Rp100,123456')
  await p.route('**/rest/v1/rpc/erp_cp7_get_attendance_workspace_v1',route=>route.abort('failed'));await panel.getByRole('button',{name:'Muat ulang absensi',exact:true}).click();await ui.expect(panel.locator('[role="alert"]')).toBeVisible();await ui.expect(panel.locator('.cproc-receipt')).toHaveCount(0);await ui.expect(panel.locator('.catt-line')).toHaveCount(0);assert.ok(!(await panel.innerText()).includes('Rp'))
  return {status:'PASS',mobile,real_auth_attendance_view_only_custom_role:true,ordinary_native_prior_roster_rate_employment_attendance:true,inactive_worker_historical_visibility:true,historical_rate:'100.123456',future_rate_hidden:'200.654321',explicit_wib_calendar_dates:true,native_present_and_half_day_records:true,blank_not_invented_absence:true,failed_refresh_retires_money:true,no_source_payroll_stock_hpp_gl_write:true,no_source_editing_ui_claim:true,screenshot:`P12_ATTENDANCE_READ_${suffix}.png`}
 }catch(error){
  mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync(`cp6-proof/t3/P12_ATTENDANCE_READ_${suffix}_FAILURE.json`,JSON.stringify({error:String(error),panel:await p.locator('.catt').innerText().catch(()=>''),dto:await user.rpc('erp_cp7_get_attendance_workspace_v1',{p_section:'WORKERS',p_query:{contractor_id:f.contractor,date_from:f.workday,date_to:f.workday}})},null,2));await p.screenshot({path:`cp6-proof/t3/P12_ATTENDANCE_READ_${suffix}_FAILURE.png`,fullPage:true});throw error
 }finally{await user.context.close()}
}
export async function cases(ui,today){return [['P12_ATTENDANCE_READ_BROWSER_DESKTOP',()=>readSources(ui,today,false)],['P12_ATTENDANCE_READ_BROWSER_MOBILE',()=>readSources(ui,today,true)]]}
