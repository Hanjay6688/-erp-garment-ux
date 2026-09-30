import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'

const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_f03_redye_browser_fixture.py',op,JSON.stringify(p)],{cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim().split('\n').at(-1))
const money=n=>{const [a,b='']=String(n).split('.');return 'Rp'+a.replace(/\B(?=(\d{3})+(?!\d))/g,'.')+(b.replace(/0+$/,'')?','+b.replace(/0+$/,''):'')}
async function open(ui,p,title,section){
  await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:section})).toBeAttached()
  const menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
  const link=p.getByRole('button',{name:'• '+title,exact:true})
  if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:section}).click()
  await link.click()
}
async function flow(ui,today,mobile){
  const f=fixture('prepare',{today}),suffix=mobile?'MOBILE':'DESKTOP'
  const owner=await ui.login('OWNER',{label:'x04-redye-'+suffix,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),p=owner.page
  const screenshots=[]
  try{
    assert.equal(f.before.qty,4);assert.equal(f.before.rate,null)
    assert.equal(f.before.row.valuation.state,'UNKNOWN')
    await open(ui,p,'Laundry','Produksi')
    await p.getByRole('button',{name:'Harga & tagihan',exact:true}).click()
    await ui.expect(p.getByRole('button',{name:'Muat ulang harga',exact:true})).toBeEnabled()
    await p.getByLabel('Vendor harga laundry',{exact:true}).selectOption(f.vendor)
    await ui.expect(p.getByRole('button',{name:'Muat ulang harga',exact:true})).toBeEnabled()
    await p.getByRole('button',{name:'Invoice vendor',exact:true}).click()
    const service=p.getByRole('region',{name:'Jasa celup ulang',exact:true}).getByRole('row').filter({hasText:f.number})
    await ui.expect(service).toContainText('Belum diketahui')
    await p.getByLabel('Tarif celup '+f.number,{exact:true}).fill('50.00')
    await p.getByLabel('Alasan pembatalan invoice',{exact:true}).fill('X04 tarif vendor diterima sesudah pindah grup')
    const posted=p.waitForResponse(r=>r.url().endsWith('/rpc/erp_save_product_conversion_action_v1')&&r.request().postDataJSON()?.p_action==='SET_REDYE_PRICE')
    await p.getByRole('button',{name:'Isi tarif celup '+f.number,exact:true}).click()
    const response=await posted;assert.equal(response.status(),200)
    await ui.expect.poll(()=>fixture('read',f).cost).toBe('200.00')
    const after=fixture('verify-price',f)
    await ui.expect(service).toContainText('Rp200')
    await open(ui,p,'Kartu Stok FG','Gudang')
    const ws=p.locator('.cfg')
    await ui.expect(ws.getByRole('heading',{name:'Kartu stok barang jadi',exact:true})).toBeVisible()
    await ui.expect(ws.getByRole('button',{name:'Cari stok',exact:true})).toBeEnabled()
    await ws.getByLabel('Cari barang jadi',{exact:true}).fill(f.target_sku)
    await ws.getByRole('button',{name:'Cari stok',exact:true}).click()
    const stock=ws.locator('.cfg-position').filter({hasText:f.successor_group.sku})
    await ui.expect(stock).toHaveCount(1)
    for(const label of ['Fisik','Tersedia'])await ui.expect(stock.locator('dl div').filter({has:p.getByText(label,{exact:true})}).locator('dd')).toHaveText('4')
    const cardResponse=p.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_get_fg_ledger_v1'))
    await stock.getByRole('button',{name:/^Lihat mutasi /}).click()
    const card=await cardResponse;assert.equal(card.status(),200)
    assert.equal(fixture('verify-card',{...f,card:await card.json()}).status,'PASS')
    await ui.expect(ws.locator('.cfg-ledger')).toContainText(f.initial_group.sku)
    await ui.expect(ws.locator('.cfg-ledger')).toContainText('Identitas SKU pada setiap mutasi mengikuti tanggal transaksinya.')
    mkdirSync('cp6-proof/t3',{recursive:true})
    await ui.expect.poll(()=>p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
    await p.evaluate(()=>window.scrollTo(0,0));await p.screenshot({path:`cp6-proof/t3/X04_REDYE_FG_${suffix}.png`,fullPage:true});screenshots.push(`X04_REDYE_FG_${suffix}.png`)
    await open(ui,p,'Laporan & Tutup Buku','Keuangan')
    const reportPage=p.locator('.cfinance-report')
    await ui.expect(reportPage.getByRole('button',{name:'Tampilkan laporan',exact:true})).toBeEnabled()
    await reportPage.getByLabel('Periode laporan dari',{exact:true}).fill(f.day)
    for(const name of ['Periode laporan sampai','Posisi laporan pada'])await reportPage.getByLabel(name,{exact:true}).fill(today)
    const reportResponse=p.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_get_finance_report_v1'))
    await reportPage.getByRole('button',{name:'Tampilkan laporan',exact:true}).click()
    const report=await reportResponse;assert.equal(report.status(),200)
    assert.equal(fixture('verify-report',{...f,report:await report.json()}).status,'PASS')
    const pos=reportPage.getByRole('region',{name:'Posisi keuangan tercatat',exact:true})
    const value=after.report.snapshot.financial_position.fg_inventory
    await ui.expect(pos.locator('.cproc-total').filter({has:p.getByText('Persediaan barang jadi',{exact:true})}).locator('strong')).toHaveText(money(value))
    assert.equal(fixture('read',f).cost,'200.00');assert.equal(fixture('read',f).qty,4)
    await ui.expect.poll(()=>p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
    await p.evaluate(()=>window.scrollTo(0,0));await p.screenshot({path:`cp6-proof/t3/X04_REDYE_REPORT_${suffix}.png`,fullPage:true});screenshots.push(`X04_REDYE_REPORT_${suffix}.png`)
    return {status:'PASS',mobile,actual_redye_price_write_in_browser:true,native_redye_creation_before_browser:true,
      first_price50_cost200_stock4:true,later_group_and_vendor99_do_not_reprice_source:true,
      current_group_display_preserves_original_movement_group:true,real_CP7_card_and_report_equal_native:true,
      fixture_ERP_schema_grant_absent_during_browser:true,whole_HPP_final_claim:false,
      full_X04_acceptance:false,full_family_acceptance:false,screenshots}
  }catch(e){
    mkdirSync('cp6-proof/t3',{recursive:true})
    writeFileSync(`cp6-proof/t3/X04_REDYE_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await p.locator('body').innerText().catch(()=> '')},null,2))
    await p.screenshot({path:`cp6-proof/t3/X04_REDYE_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{})
    throw e
  }finally{await owner.context.close()}
}
export async function cases(ui,today){return [['F03_X04_REDYE_BROWSER_DESKTOP',()=>flow(ui,today,false)],['F03_X04_REDYE_BROWSER_MOBILE',()=>flow(ui,today,true)]]}
