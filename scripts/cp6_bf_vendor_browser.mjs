import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
const { cases: supplier } = await import(pathToFileURL(resolve('scripts/cp6_bf_supplier_browser.mjs')).href)
const { cases: regression } = await import(pathToFileURL(resolve('scripts/cp6_bf_browser.mjs')).href)
const { cases: readiness } = await import(pathToFileURL(resolve('scripts/cp6_readiness_browser.mjs')).href)
const { freeMaster } = await import(pathToFileURL(resolve('scripts/cp6_bf_free_browser.mjs')).href)
const fixture = (op, payload) => JSON.parse(execFileSync('python', ['../auditor/scripts/cp6_bd_revision_fixture.py', op, JSON.stringify(payload)], { cwd: '../writer', encoding: 'utf8' }).trim())
async function deferred(ui, today, mobile) {
 const f=fixture('create',{kind:'components',today}),user=await ui.login('OWNER',{label:'vendor-deferred-'+mobile,mobile})
 try {
  const p=user.page,menu=p.getByRole('button',{name:'Buka menu',exact:true})
  await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:'Produksi'})).toBeAttached({timeout:20000})
  if(await menu.isVisible())await menu.click()
  const link=p.getByRole('button',{name:'• Laundry',exact:true})
  if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Produksi'}).click()
  await link.click();await p.getByRole('button',{name:'Harga & tagihan',exact:true}).click()
  const ready=()=>ui.expect(p.getByRole('button',{name:'Muat ulang harga',exact:true})).toBeEnabled({timeout:20000})
  await ready();await p.getByLabel('Vendor harga laundry',{exact:true}).selectOption(f.vendor);await ready()
  await p.getByRole('button',{name:'Kirim & rincian biaya',exact:true}).click()
  await ui.expect(p.getByLabel('Pilihan rincian biaya',{exact:true})).toHaveValue('PENDING')
  await p.getByLabel('Batch kirim berharga',{exact:true}).selectOption(f.batch)
  await p.getByLabel('Proses kirim berharga',{exact:true}).selectOption(f.process)
  await p.getByLabel('Warna kirim berharga',{exact:true}).fill('Pending navy')
  await p.getByLabel('Waktu kirim berharga',{exact:true}).fill(f.day+'T11:00')
  await p.getByLabel('Bukti serah terima',{exact:true}).fill('Details will be entered from kontra bon')
  for(const s of f.sizes)await p.getByLabel('Qty kirim berharga '+s.code,{exact:true}).fill(String(s.qty))
  await p.getByLabel(/Vendor, batch, ukuran, jumlah, warna, waktu, dan pilihan rincian biaya sudah/).check()
  await p.getByRole('button',{name:'Catat kiriman berharga',exact:true}).click()
  await ui.expect.poll(()=>fixture('read',f).deliveries.length,{timeout:20000}).toBe(1)
  const d=fixture('read',f).deliveries[0]
  await ready();await p.getByRole('button',{name:'Harga belum diketahui',exact:true}).click()
  await ui.expect(p.getByText(/Catat nilai aktual pada Invoice vendor setelah barang diterima/)).toBeVisible()
  const checks={no_fake_charge:d.charges.length===0,unknown:!d.total_complete&&d.mode==='PENDING',physical_qty:d.qty_sent===13}
  return {status:Object.values(checks).every(Boolean)?'PASS':'FAIL',checks,mobile}
 }finally{await user.context.close()}
}
export async function cases(ui,today){return [
 ...await readiness(ui,today),
 ['VENDOR_FREE_BROWSER:DESKTOP_SAVE_RELOAD',()=>freeMaster(ui,false)],
 ['VENDOR_FREE_BROWSER:MOBILE_SAVE_RELOAD',()=>freeMaster(ui,true)],
 ['VENDOR_BROWSER:EMPTY_DETAILS_DESKTOP',()=>deferred(ui,today,false)],
 ['VENDOR_BROWSER:EMPTY_DETAILS_MOBILE',()=>deferred(ui,today,true)],...await supplier(ui,today),...await regression(ui,today)]}
