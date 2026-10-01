import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'

const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_f03_e03_browser_fixture.py',op,JSON.stringify(p)],{cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim().split('\n').at(-1))
// Chromium normalizes exact zero seconds to minute form. Preserve nonzero
// Native seconds while using the canonical DOM value for an exact minute.
const wib=iso=>new Date(new Date(iso).getTime()+7*60*60*1000).toISOString().slice(0,19).replace(/:00$/,'')
async function open(ui,p) {
  await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:'Gudang'})).toBeAttached()
  const menu=p.getByRole('button',{name:'Buka menu',exact:true})
  if(await menu.isVisible())await menu.click()
  const link=p.getByRole('button',{name:'• Aksesori',exact:true})
  if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click()
  await link.click()
  await ui.expect(p.getByRole('heading',{name:'Pemakaian & Pengembalian Aksesori',exact:true})).toBeVisible()
  await ui.expect(p.getByRole('button',{name:'Muat ulang',exact:true})).toBeEnabled()
}

async function flow(ui,today,mobile) {
  const f=fixture('prepare',{today}),suffix=mobile?'MOBILE':'DESKTOP'
  const owner=await ui.login('OWNER',{label:'e03-'+suffix,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
  const p=owner.page
  const form=p.getByRole('region',{name:'Catat transaksi aksesori',exact:true})
  async function choose(action) {
    await p.getByRole('button',{name:'Catat transaksi',exact:true}).click()
    await form.getByLabel('Jenis transaksi aksesori',{exact:true}).selectOption(action)
  }
  async function submit(label) {
    await form.getByLabel('Alasan transaksi',{exact:true}).fill('E03 kepemilikan pelanggan tetap; sumber invoice '+f.tag)
    await form.getByLabel('Referensi (opsional)',{exact:true}).fill(f.service_reference)
    await form.getByRole('button',{name:'Periksa transaksi',exact:true}).click()
    await form.getByRole('button',{name:'Sahkan '+label,exact:true}).click()
  }
  try {
    assert.equal(f.before.fg,45);assert.equal(f.before.invoice.open_balance,'175.00')
    await open(ui,p)
    await choose('CUSTOMER_GARMENT_IN')
    await form.getByLabel('Cari pelanggan titipan',{exact:true}).fill(f.tag)
    await form.getByRole('button',{name:'Cari pelanggan',exact:true}).click()
    await form.getByLabel('Pelanggan',{exact:true}).selectOption(f.customer)
    await form.getByLabel('Keterangan barang',{exact:true}).fill(f.custody_description)
    await form.getByLabel('Jumlah PCS',{exact:true}).fill('1')
    await form.getByLabel('Waktu terima (WIB)',{exact:true}).fill(wib(f.service_in_at))
    await submit('terima titipan pelanggan')
    await ui.expect.poll(()=>fixture('read',f).custody.length).toBe(1)
    const entered=fixture('read',f),custody=entered.custody[0].id
    assert.deepEqual(entered.protected,f.before.protected);assert.deepEqual(entered.accounts,f.before.accounts)
    await choose('INTERNAL_USE')
    await form.getByLabel('Lokasi pemakaian',{exact:true}).selectOption(f.service_accessory.main)
    await form.getByLabel('Cari aksesori transaksi',{exact:true}).fill(f.service_accessory.code)
    await form.getByLabel('Cari aksesori transaksi',{exact:true}).press('Enter')
    await form.getByLabel('Aksesori baris 1',{exact:true}).selectOption(f.service_accessory.material)
    await form.getByLabel('Jumlah baris 1',{exact:true}).fill('2')
    await form.getByLabel('Waktu pakai baris 1',{exact:true}).fill(wib(f.service_use_at))
    await form.getByLabel('Tujuan baris 1',{exact:true}).selectOption('CUSTOMER_SERVICE')
    await form.getByLabel('Titipan baris 1',{exact:true}).selectOption(custody)
    let lost=false,first=null,replay=null
    if(mobile)await p.route('**/rest/v1/rpc/erp_save_accessory_service_action_v1',async route=>{
      const body=route.request().postDataJSON()
      if(body.p_action==='INTERNAL_USE'&&!lost) {
        first=body;const response=await route.fetch()
        if(response.status()!==200){await route.fulfill({response});return}
        lost=true;await route.abort('failed')
      }else{if(body.p_action==='INTERNAL_USE'&&replay===null)replay=body;await route.continue()}
    })
    await submit('pemakaian perusahaan')
    if(mobile) {
      await ui.expect(p.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible()
      await p.reload();await open(ui,p)
      await p.getByRole('button',{name:'Reconcile transaksi',exact:true}).click()
      await ui.expect(p.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0)
      assert.ok(lost);assert.deepEqual(replay,first)
    }
    await ui.expect.poll(()=>Number(fixture('read',f).accessory_qty)).toBe(8)
    fixture('verify',{...f,expected_returned:false})
    await choose('CUSTOMER_GARMENT_OUT')
    await form.getByLabel('Titipan pelanggan',{exact:true}).selectOption(custody)
    await form.getByLabel('Waktu kembali (WIB)',{exact:true}).fill(wib(f.service_out_at))
    await submit('kembalikan titipan pelanggan')
    await ui.expect.poll(()=>fixture('read',f).custody[0].returned).toBe(true)
    const result=fixture('verify',{...f,expected_returned:true})
    await p.getByRole('button',{name:'Barang kembali',exact:true}).click()
    const returned=p.getByRole('region',{name:'Barang kembali dan titipan',exact:true})
    const row=returned.getByRole('row').filter({hasText:f.custody_description})
    await ui.expect(row).toContainText('Sudah dikembalikan')
    await ui.expect.poll(()=>p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
    mkdirSync('cp6-proof/t3',{recursive:true})
    await p.screenshot({path:`cp6-proof/t3/E03_CUSTOMER_CUSTODY_${suffix}.png`,fullPage:true})
    return {status:'PASS',journey:'E03_SELECTED_CUSTOMER_CUSTODY_SERVICE',mobile,source_production_sale_return_native:true,browser_custody_in_consume_two_return_to_owner:true,accessory10_to8_cost4:true,company_FG45_AR175_cash200_HPP_unchanged:true,no_customer_refund_or_payroll_entitlement:true,report_confidence:result.report.snapshot.data_confidence,lost_service_response_exact_UUID_replay:mobile?true:null,cash_refund_execution_claim:false,full_E03_acceptance:false,full_family_acceptance:false,screenshots:[`E03_CUSTOMER_CUSTODY_${suffix}.png`]}
  }catch(e) {
    mkdirSync('cp6-proof/t3',{recursive:true})
    writeFileSync(`cp6-proof/t3/E03_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await p.locator('body').innerText().catch(()=> '')},null,2))
    await p.screenshot({path:`cp6-proof/t3/E03_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{})
    throw e
  }finally{await owner.context.close()}
}
export async function cases(ui,today){return [['F03_E03_BROWSER_DESKTOP',()=>flow(ui,today,false)],['F03_E03_BROWSER_MOBILE_LOST_SERVICE',()=>flow(ui,today,true)]]}
