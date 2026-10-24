import assert from 'node:assert/strict'
import {openCuttingMenu} from '../cp7_ow13c_checked_browser.mjs'
const RPC='erp_cp7_read_product_analog_candidates_v1'
export async function quantity(ui,page,f){
 await openCuttingMenu(ui,page,'Produksi','Buat Potongan')
 const panel=page.getByRole('region',{name:'Saran potong',exact:true})
 await panel.getByLabel('Penjualan mulai untuk saran potong',{exact:true}).fill(f.query.from_date)
 await panel.getByLabel('Penjualan sampai untuk saran potong',{exact:true}).fill(f.query.through_date)
 await panel.getByRole('button',{name:'Buka saran potong',exact:true}).click()
 const q=page.getByRole('region',{name:'Kebutuhan seluruh produk',exact:true})
 await ui.expect(q.locator('tbody tr,[role="alert"]').first()).toBeVisible({timeout:180000})
 assert.deepEqual(await q.getByRole('alert').allTextContents(),[],'ANALOG_QUANTITY_ERROR')
 await ui.expect(q.locator('[data-quantity-target]').first()).toBeVisible()
 return q
}
export async function reply(page,action){
 // Observe both promises immediately: a slow/failed click must never leave the
 // response timeout unhandled and terminate the host before Auth cleanup.
 const[r]=await Promise.all([
  page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/rpc/'+RPC)),
  Promise.resolve().then(action),
 ])
 return{status:r.status(),args:r.request().postDataJSON(),body:await r.json()}
}
export async function open(ui,page,q,f){
 await q.locator('summary').filter({hasText:'Cari produk untuk melihat pembanding'}).click()
 await q.getByLabel('Cari SKU atau nama produk yang memerlukan pembanding',{exact:true}).fill(f.sku)
 const choice=q.locator(`[data-analog-choice="${f.target_key}"]`)
 await ui.expect(choice).toBeVisible()
 const read=await reply(page,()=>choice.getByRole('button',{name:'Lihat pembanding '+f.sku,exact:true}).click())
 assert.equal(read.status,200,JSON.stringify(read.body))
 const a=q.getByRole('region',{name:'Kandidat produk pembanding',exact:true})
 await ui.expect(a.locator('[data-analog-target]').first()).toBeVisible()
 assert.deepEqual(await a.getByRole('alert').allTextContents(),[])
 return{a,read}
}
