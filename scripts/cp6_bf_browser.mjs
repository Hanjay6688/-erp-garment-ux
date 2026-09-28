import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
const { cases: regression } = await import(pathToFileURL(resolve('scripts/cp6_bd_revision_browser.mjs')).href)
const fixture = (op, payload) => JSON.parse(execFileSync('python', ['../auditor/scripts/cp6_bf_browser_fixture.py', op, JSON.stringify(payload)], { cwd:'../writer', encoding:'utf8', maxBuffer:16*1024*1024 }).trim())
async function open(user, group, item) {
 const p=user.page, menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=p.getByRole('button',{name:'• '+item,exact:true});if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:group}).click();await link.click();return p
}
async function master(ui,singleton,mobile) {
 const f=fixture('create',{singleton}),user=await ui.login('OWNER',{label:'bf-master-'+singleton+'-'+mobile,mobile})
 try {
  const p=await open(user,'Master','Produk & SKU')
  await ui.expect(p.getByRole('heading',{name:'Produk & SKU',exact:true})).toBeVisible()
  await p.getByLabel('Cari SKU atau merek',{exact:true}).fill(f.tag)
  await p.getByRole('button',{name:'Cari / muat ulang',exact:true}).click()
  await p.getByRole('button',{name:'Buat SKU dari ukuran '+f.sizes[0],exact:true}).click()
  await p.getByLabel('Kode SKU',{exact:true}).fill(f.sku)
  for(const size of f.sizes.slice(1))await p.getByRole('button',{name:'Tambah ukuran '+size,exact:true}).click()
  if(!singleton){await p.getByLabel('Harga jual per PCS untuk seluruh ukuran',{exact:true}).fill('185000.00');await p.getByLabel('Status resep',{exact:true}).selectOption('SET')}
  await p.getByLabel('Alasan perubahan',{exact:true}).fill('Browser owner confirms one SKU for actual member sizes')
  await p.getByRole('button',{name:'Periksa seluruh dampak perubahan',exact:true}).click()
  await ui.expect(p.getByRole('heading',{name:'Periksa sebelum menyimpan',exact:true})).toBeVisible()
  await p.getByLabel('Saya sudah memeriksa anggota dan pengaturan seluruh kelompok yang berubah.',{exact:true}).check()
  await p.getByRole('button',{name:'Simpan seluruh perubahan SKU',exact:true}).click()
  await ui.expect.poll(()=>fixture('read',f).groups.length,{timeout:20000}).toBe(1)
  const r=fixture('read',f),checks={members:r.groups[0][3]===f.sizes.length,revision:Number(r.groups[0][1])===1,no_stock_mutation:r.stock===0,price:singleton?r.groups[0][2].price===null:r.prices.length===4&&r.prices.every(x=>x[0]==='185000.00'),bom:singleton?r.groups[0][2].bom===null:r.groups[0][2].bom.length===0}
  if(mobile)checks.mobile_width=await p.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)
  await open(user,'Keuangan','HPP & Rekalkulasi')
  await p.getByLabel('Cari SKU atau merek',{exact:true}).fill(f.sku)
  await p.getByRole('button',{name:'Tampilkan',exact:true}).click()
  await ui.expect(p.getByText('Tidak ada stok SKU yang cocok.',{exact:true})).toBeVisible()
  checks.hpp_no_invented_stock=true
  return {status:Object.values(checks).every(Boolean)?'PASS':'FAIL',checks,singleton,mobile}
 }finally{await user.context.close()}
}
export async function cases(ui,today){return [...await regression(ui,today),['BF_BROWSER:FOUR_SIZE_MASTER_DESKTOP',()=>master(ui,false,false)],['BF_BROWSER:SINGLETON_UNCONFIGURED_MOBILE',()=>master(ui,true,true)]]}
