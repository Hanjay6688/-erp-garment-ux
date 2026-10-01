// Current UI + actual Auth/PostgREST. Responses and policy reads are Native.
import { mkdirSync } from 'node:fs'
import { resolve } from 'node:path'
async function open(p,ui,group,item) {
  await ui.expect(p.locator('.sidebar')).toBeAttached({timeout:20000})
  const menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
  const link=p.getByRole('button',{name:'• '+item,exact:true})
  if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:group}).click()
  await link.click()
}
async function readiness(ui,mobile) {
  const user=await ui.login('OWNER',{label:'cp6-readiness-'+mobile,mobile}),p=user.page
  const dir=resolve('cp6-proof/t3/readiness-ui');mkdirSync(dir,{recursive:true})
  const prefix=mobile?'mobile':'desktop',checks={}
  const screenshot=async name=>{
    await p.evaluate(()=>window.scrollTo(0,0))
    await p.screenshot({path:resolve(dir,prefix+'-'+name+'.png'),fullPage:true})
  }
  const version=(kind,key)=>ui.sql(`select version from erp.${kind}_policy_settings_v1 where policy_key='${key}'`)
  const apply=async(kind,key,value)=>{
    const r=await user.rpc(kind==='bd'?'erp_save_laundry_bd_action_v1':'erp_save_accessory_service_action_v1',{
      p_action:'SET_POLICY',p_payload:{policy_key:key,operation:value?'SET':'CLEAR',expected_version:version(kind,key),reason:'Disposable readiness browser prerequisite',...(value?{value}:{})},p_client_request_id:crypto.randomUUID()})
    if(r.status!==200)throw Error('Readiness prerequisite refused: '+kind+'/'+key+'/'+r.status)
  }
  try {
    for(const key of ['LAU_DEC01','LAU_DEC02','LAU_DEC03','LAU_DEC04','LAU_DEC05','LAU_DEC06'])await apply('bd',key,null)
    for(const key of ['ACC_DEC05','ACC_DEC07'])await apply('bc',key,null)
    await open(p,ui,'Produksi','Laundry');await p.getByRole('button',{name:'Harga & tagihan',exact:true}).click()
    const ready=()=>ui.expect(p.getByRole('button',{name:'Muat ulang harga',exact:true})).toBeEnabled({timeout:20000})
    await ready()
    await ui.expect(p.getByRole('row').filter({hasText:'LAU-DEC05'})).toContainText('Sengaja tidak diaktifkan')
    await ui.expect(p.getByRole('row').filter({hasText:'LAU-DEC06'})).toContainText('Keputusan owner belum diterapkan')
    await p.getByRole('button',{name:'Invoice vendor',exact:true}).click()
    await ui.expect(p.getByText(/^Posting invoice laundry belum siap/)).toBeVisible()
    await screenshot('laundry-pending')
    checks.pending_explained_before_post=true
    await p.getByRole('button',{name:'Kebijakan owner',exact:true}).click()
    await p.getByLabel('Kebijakan yang diubah',{exact:true}).selectOption('LAU-DEC06')
    const before=version('bd','LAU_DEC06')
    await p.getByRole('button',{name:'Isi sesuai keputusan owner',exact:true}).click()
    await ui.expect(p.getByLabel('Selisih invoice',{exact:true})).toHaveValue('PRODUCT_COST')
    await ui.expect(p.getByLabel('Koreksi sesudah bayar',{exact:true})).toHaveValue('CORRECTION_DOCUMENT')
    checks.prefill_does_not_write=version('bd','LAU_DEC06')===before
    await p.getByRole('button',{name:'Tetapkan LAU-DEC06',exact:true}).click();await ready()
    await ui.expect.poll(()=>version('bd','LAU_DEC06')).toBe(String(Number(before)+1))
    await ui.expect(p.getByRole('row').filter({hasText:'LAU-DEC06'})).toContainText('Ditetapkan di aplikasi')
    await p.getByRole('button',{name:'Invoice vendor',exact:true}).click()
    await ui.expect(p.getByText(/^Posting invoice laundry belum siap/)).toContainText('LAU-DEC02 di Kebijakan owner')
    checks.one_setting_does_not_make_invoice_ready=true
    await p.getByRole('button',{name:'Kebijakan owner',exact:true}).click()
    await p.getByLabel('Kebijakan yang diubah',{exact:true}).selectOption('LAU-DEC02')
    await p.getByLabel('Hasil baik',{exact:true}).check()
    await p.getByLabel('Alasan',{exact:true}).fill('Disposable browser GOOD-only invoice agreement')
    await p.getByRole('button',{name:'Tetapkan LAU-DEC02',exact:true}).click();await ready()
    await p.getByRole('button',{name:'Invoice vendor',exact:true}).click()
    await ui.expect(p.getByText(/^Posting invoice laundry belum siap/)).toHaveCount(0)
    checks.both_applied_remove_warning=true
    await screenshot('laundry-ready')
    await open(p,ui,'Gudang','Aksesori');await p.getByRole('button',{name:'Kebijakan & area',exact:true}).click()
    await ui.expect(p.getByRole('row').filter({hasText:'ACC-DEC07'})).toContainText('Keputusan owner belum diterapkan')
    await p.getByLabel('Kebijakan yang diubah',{exact:true}).selectOption('ACC-DEC07')
    const accessoryBefore=version('bc','ACC_DEC07')
    await p.getByRole('button',{name:'Isi sesuai keputusan owner',exact:true}).click()
    await ui.expect(p.getByLabel('Persetujuan owner biaya aksesori',{exact:true})).toHaveValue('NONE')
    checks.approval_none_is_not_zero=version('bc','ACC_DEC07')===accessoryBefore
    await screenshot('accessory-decision')
    await open(p,ui,'Keuangan','HPP & Rekalkulasi')
    await ui.expect(p.getByLabel('Catatan pembulatan biaya')).toContainText('tidak ada batas selisih sen per PO')
    await ui.expect(p.getByRole('button',{name:'Tampilkan',exact:true})).toBeEnabled({timeout:20000})
    await ui.expect(p.locator('p').filter({hasText:/^Posisi .*Biaya memakai versi/})).toBeVisible({timeout:20000})
    await ui.expect(p.getByRole('alert')).toHaveCount(0)
    checks.finance_native_report_loaded=true
    await screenshot('hpp-rounding')
    checks.finance_rounding_visible=true
    if(mobile)checks.mobile_width=await p.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)
    return {status:Object.values(checks).every(Boolean)?'PASS':'FAIL',checks,mobile,screenshots:4}
  } finally {
    for(const key of ['LAU_DEC02','LAU_DEC06'])await apply('bd',key,null)
    await user.context.close()
  }
}
export async function cases(ui,today) {
  return [['READINESS_BROWSER:DESKTOP_NATIVE_POLICY_STATES_FINANCE_NOTE',()=>readiness(ui,false)],
    ['READINESS_BROWSER:MOBILE_NATIVE_POLICY_STATES_FINANCE_NOTE',()=>readiness(ui,true)]]
}
