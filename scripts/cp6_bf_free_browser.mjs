// The legacy filename now tests CURRENT vendor prices and an empty SKU tariff
// list. No obsolete SKU-price UI or historical receipt is relabelled as passing.
import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
const { cases: regression } = await import(pathToFileURL(resolve('scripts/cp6_be_revision_browser.mjs')).href)
const fixture=(script,args=[])=>JSON.parse(execFileSync('python',['../auditor/scripts/'+script,...args],{cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const read=f=>fixture('cp6_bf_browser_fixture.py',['read',JSON.stringify(f)])
const vendorRead=f=>fixture('cp6_bf_free_browser_fixture.py',['read',JSON.stringify(f)])
async function open(user,group,item){
 const p=user.page
 await p.locator('.sidebar').waitFor({state:'attached'})
 const menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=p.getByRole('button',{name:'• '+item,exact:true});if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:group}).click();await link.click();return p
}
export async function freeMaster(ui,mobile){
 const f=fixture('cp6_bf_free_browser_fixture.py'),user=await ui.login('OWNER',{label:'vendor-free-'+mobile,mobile})
 try{
  const p=await open(user,'Master','Produk & SKU')
  await p.getByLabel('Cari SKU atau merek',{exact:true}).fill(f.tag);await p.getByRole('button',{name:'Cari / muat ulang',exact:true}).click()
  await p.getByRole('button',{name:'Buat SKU dari ukuran '+f.sizes[0],exact:true}).click();await p.getByLabel('Kode SKU',{exact:true}).fill(f.sku)
  for(const size of f.sizes.slice(1))await p.getByRole('button',{name:'Tambah ukuran '+size,exact:true}).click()
  await p.getByLabel('Harga jual per PCS untuk seluruh ukuran',{exact:true}).fill('185000');await p.getByLabel('Status resep',{exact:true}).selectOption('SET')
  await ui.expect(p.getByRole('button',{name:'Tambah tarif laundry',exact:true})).toHaveCount(0)
  await p.getByLabel('Alasan perubahan',{exact:true}).fill('Current SKU identity; laundry prices belong to the vendor')
  await p.getByRole('button',{name:'Periksa seluruh dampak perubahan',exact:true}).click()
  await p.getByLabel('Saya sudah memeriksa anggota dan pengaturan seluruh kelompok yang berubah.',{exact:true}).check()
  await p.getByRole('button',{name:'Simpan seluruh perubahan SKU',exact:true}).click()
  await ui.expect.poll(()=>read(f).groups.length,{timeout:20000}).toBe(1)
  const saved=read(f),checks={three_physical_members:saved.groups[0][3]===3,once:Number(saved.groups[0][1])===1,no_stock:saved.stock===0,sku_laundry_empty:saved.groups[0][2].laundry_rates.length===0}
  await open(user,'Produksi','Laundry');await p.getByRole('button',{name:'Harga & tagihan',exact:true}).click()
  const ready=()=>ui.expect(p.getByRole('button',{name:'Muat ulang harga',exact:true})).toBeEnabled({timeout:20000})
  await ready();await p.getByLabel('Vendor harga laundry',{exact:true}).selectOption(f.vendor);await ready()
  await p.getByRole('button',{name:'Harga vendor',exact:true}).click()
  for(const rate of f.rates){
   const reason='Browser vendor '+rate.rate_status+' explicit zero'
   await p.getByLabel('Komponen harga',{exact:true}).selectOption(rate.ref_id)
   await p.getByLabel('Status harga komponen',{exact:true}).selectOption(rate.rate_status)
   await p.getByLabel('Berlaku sejak (WIB)',{exact:true}).fill(f.effective_local)
   await p.getByLabel('Alasan',{exact:true}).fill(reason)
   await p.getByRole('button',{name:'Simpan versi harga komponen',exact:true}).click()
   await ui.expect.poll(()=>vendorRead(f).rates.find(r=>r[0]===rate.ref_id)?.[3],{timeout:20000}).toBe(reason)
   await ready()
  }
  await p.reload();await open(user,'Produksi','Laundry');await p.getByRole('button',{name:'Harga & tagihan',exact:true}).click();await ready()
  await p.getByLabel('Vendor harga laundry',{exact:true}).selectOption(f.vendor);await ready();await p.getByRole('button',{name:'Harga vendor',exact:true}).click()
  for(const rate of f.rates)await ui.expect(p.getByText('Browser vendor '+rate.rate_status+' explicit zero',{exact:false})).toBeVisible()
  const current=vendorRead(f).rates
  checks.vendor_free_waived=current.length===2&&f.rates.every(rate=>current.some(r=>r[0]===rate.ref_id&&r[1]===rate.rate_status&&r[2]==='0.00'))
  checks.reload_preserves_vendor_reason=true
  if(mobile)checks.mobile_width=await p.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)
  return {status:Object.values(checks).every(Boolean)?'PASS':'FAIL',checks,mobile}
 }finally{await user.context.close()}
}
export async function cases(ui,today){return [...await regression(ui,today),['VENDOR_FREE_BROWSER:DESKTOP_SAVE_RELOAD',()=>freeMaster(ui,false)],['VENDOR_FREE_BROWSER:MOBILE_SAVE_RELOAD',()=>freeMaster(ui,true)]]}
