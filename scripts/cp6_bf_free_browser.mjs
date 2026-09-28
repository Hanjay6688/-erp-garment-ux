import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
const { cases: regression } = await import(pathToFileURL(resolve('scripts/cp6_be_revision_browser.mjs')).href)
const fixture=(script,args=[])=>JSON.parse(execFileSync('python',['../auditor/scripts/'+script,...args],{cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const read=f=>fixture('cp6_bf_browser_fixture.py',['read',JSON.stringify(f)])
async function open(user){
 const p=user.page,menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=p.getByRole('button',{name:'• Produk & SKU',exact:true});if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Master'}).click();await link.click();return p
}
async function freeMaster(ui,mobile){
 const f=fixture('cp6_bf_free_browser_fixture.py'),user=await ui.login('OWNER',{label:'sku-free-'+mobile,mobile})
 try{
  const p=await open(user)
  await p.getByLabel('Cari SKU atau merek',{exact:true}).fill(f.tag);await p.getByRole('button',{name:'Cari / muat ulang',exact:true}).click()
  await p.getByRole('button',{name:'Buat SKU dari ukuran '+f.sizes[0],exact:true}).click();await p.getByLabel('Kode SKU',{exact:true}).fill(f.sku)
  for(const size of f.sizes.slice(1))await p.getByRole('button',{name:'Tambah ukuran '+size,exact:true}).click()
  await p.getByLabel('Harga jual per PCS untuk seluruh ukuran',{exact:true}).fill('185000');await p.getByLabel('Status resep',{exact:true}).selectOption('SET')
  for(const [i,rate] of f.rates.entries()){
   await p.getByRole('button',{name:'Tambah tarif laundry',exact:true}).click()
   const fields=p.getByRole('group',{name:'Jasa laundry '+(i+1),exact:true})
   await ui.expect(fields).toBeVisible()
   await fields.getByLabel(/^Vendor/).selectOption(rate.vendor_id);await fields.getByLabel(/^Jenis/).selectOption('COMPONENT')
   await fields.getByLabel(/^Jasa/).selectOption(rate.ref_id);await fields.getByLabel(/^Status harga/).selectOption(rate.rate_status)
   await fields.getByLabel('Alasan harga',{exact:true}).fill(rate.reason)
  }
  await p.getByLabel('Alasan perubahan',{exact:true}).fill('Browser agreed FREE and WAIVED with valid reasons')
  await p.getByRole('button',{name:'Periksa seluruh dampak perubahan',exact:true}).click()
  await p.getByLabel('Saya sudah memeriksa anggota dan pengaturan seluruh kelompok yang berubah.',{exact:true}).check()
  await p.getByRole('button',{name:'Simpan seluruh perubahan SKU',exact:true}).click()
  await ui.expect.poll(()=>read(f).groups.length,{timeout:20000}).toBe(1)
  const saved=read(f),rates=saved.groups[0][2].laundry_rates
  const checks={three_physical_members:saved.groups[0][3]===3,once:Number(saved.groups[0][1])===1,no_stock:saved.stock===0,
   free_waived_saved:rates.length===2&&rates.every((r,i)=>r.rate==='0.00'&&r.rate_status===f.rates[i].rate_status&&r.reason===f.rates[i].reason)}
  await p.reload();await open(user);await p.getByLabel('Cari SKU atau merek',{exact:true}).fill(f.sku);await p.getByRole('button',{name:'Cari / muat ulang',exact:true}).click()
  await p.getByRole('button',{name:'Ubah SKU '+f.sku,exact:true}).click()
  for(const [i,rate] of f.rates.entries()){
   const fields=p.getByRole('group',{name:'Jasa laundry '+(i+1),exact:true})
   await ui.expect(fields.getByLabel(/^Status harga/)).toHaveValue(rate.rate_status)
   await ui.expect(fields.getByLabel('Alasan harga',{exact:true})).toHaveValue(rate.reason)
  }
  checks.reload_preserves_status_and_reason=true
  return {status:Object.values(checks).every(Boolean)?'PASS':'FAIL',checks,mobile}
 }finally{await user.context.close()}
}
export async function cases(ui,today){return [...await regression(ui,today),['SKU01_BROWSER:FREE_WAIVED_DESKTOP_SAVE_RELOAD',()=>freeMaster(ui,false)],['SKU01_BROWSER:FREE_WAIVED_MOBILE_SAVE_RELOAD',()=>freeMaster(ui,true)]]}
