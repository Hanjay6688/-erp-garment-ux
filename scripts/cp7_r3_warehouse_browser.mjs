// R3-03 (owner D16-1): Ringkasan Gudang from real stock, desktop and phone, real Auth and PostgREST on the committed copy,
// opened as OWNER and as the limited role GUDANG (warehouse.dashboard.view without finance.hpp.view or
// warehouse.stock.adjust, per src/auth/accessCatalog.ts and the seeded role). The fixture is the native case's one: a roll of
// 10 received at its own warehouse and 4 cut through Buat Potongan (fixture r303_warehouse). The figures on screen are
// compared with the Native rows of that warehouse (fixture r303_warehouse_state), never with the read's own answer; the
// state is the same before and after (the screen only reads).
import assert from'node:assert/strict'
import{mkdirSync}from'node:fs'
async function openSummary(ui,page){
 const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=page.getByRole('button',{name:'• Ringkasan Gudang',exact:true})
 if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click()
 await link.click();await ui.expect(page.getByRole('heading',{name:'Ringkasan Gudang',exact:true})).toBeVisible()
}
async function search(ui,page,f){
 await page.getByLabel('Cari gudang',{exact:true}).fill(f.code);await page.getByRole('button',{name:'Cari gudang',exact:true}).click()
 const card=page.locator(`[data-location-id="${f.location}"]`);await ui.expect(card).toHaveCount(1);return card
}
async function journey(ui,today,mobile,h){
 const name=`CP17_BROWSER_R3_03_WAREHOUSE_SUMMARY_${mobile?'MOBILE':'DESKTOP'}`,f=h.fixture('r303_warehouse',{today}),seen={},requests=[]
 const state=()=>h.fixture('r303_warehouse_state',f)
 const owner=await ui.login('OWNER',{label:'cp17-r3-03-owner-'+(mobile?'mobile':'desktop'),mobile})
 let gudang=null,page=owner.page
 const watch=p=>p.on('request',r=>{const m=r.url().match(/\/rpc\/([a-z0-9_]+)$/);if(m)requests.push(m[1])})
 watch(page)
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const before=seen.before=state()
  assert.equal(before.rolls,1)
  // OWNER: quantity, rolls and value of the warehouse equal its Native rows; the totals of this search too.
  await openSummary(ui,page);let card=await search(ui,page,f)
  await ui.expect(card).toContainText(before.qty_text);await ui.expect(card).toContainText('1 roll berisi');await ui.expect(card).toContainText(`Nilai bahan ${before.value_text}`)
  const totals=page.getByRole('article',{name:'Total bahan dan roll',exact:true})
  await ui.expect(totals).toContainText('Bahan & Roll sesuai pencarian');await ui.expect(totals).toContainText(before.qty_text)
  await ui.expect(page.getByRole('region',{name:'Perlu diperhatikan',exact:true})).toBeVisible()
  await h.noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_OWNER.png`,fullPage:true})
  assert.ok(requests.includes('erp_cp7_get_warehouse_summary_v1'));assert.deepEqual(requests.filter(n=>/save|post|reverse|set_/.test(n)),[])
  // The link opens the detail screen it names.
  await totals.getByRole('button',{name:'Buka Bahan & Roll',exact:true}).click()
  await ui.expect(page.getByRole('heading',{name:'Bahan & roll',exact:true})).toBeVisible()
  await owner.context.close()
  // GUDANG: the same quantity, no value, no check or link of Stock Adjustment.
  gudang=await ui.login('GUDANG',{label:'cp17-r3-03-gudang-'+(mobile?'mobile':'desktop'),mobile});page=gudang.page;watch(page)
  await openSummary(ui,page);card=await search(ui,page,f)
  await ui.expect(card).toContainText(before.qty_text);await ui.expect(card).toContainText('1 roll berisi')
  await ui.expect(page.getByText('Nilai stok tidak ditampilkan karena hak melihat HPP belum diberikan.',{exact:true})).toBeVisible()
  // The whole page area (the app's main panel holds the summary's own named main landmark): no amount anywhere.
  assert.ok(!(await page.locator('main.main-panel').innerText()).includes('Rp'))
  await ui.expect(page.getByRole('button',{name:'Buka Stock Adjustment',exact:true})).toHaveCount(0)
  await ui.expect(page.locator('[data-attention="MATERIAL_COUNT_DRAFT"],[data-attention="FG_ADJUSTMENT_DRAFT"],[data-attention="FABRIC_BELOW_MINIMUM"]')).toHaveCount(0)
  await h.noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_GUDANG.png`,fullPage:true})
  const after=seen.after=state();assert.deepEqual(after,before)
  assert.deepEqual(requests.filter(n=>/save|post|reverse|set_/.test(n)),[])
  return{status:'PASS',finding:'R3-03',owner_decision:'D16-1',phone:mobile,warehouse:f.code,qty:before.qty_text,rolls:before.rolls,owner_value:before.value_text,
   gudang_no_value:true,gudang_no_stock_adjustment:true,link_opens_bahan_roll:true,native_rows_unchanged:true,reads:requests.filter(n=>n==='erp_cp7_get_warehouse_summary_v1').length}
 }catch(error){try{seen.actual=state()}catch(e){seen.observation_error=String(e)};await h.failure(page,name,error,seen,requests);throw error}
 finally{await owner.context.close().catch(()=>{});if(gudang)await gudang.context.close().catch(()=>{})}
}
export function cases(ui,today,h){
 return[['CP17_BROWSER_R3_03_WAREHOUSE_SUMMARY_DESKTOP',()=>journey(ui,today,false,h)],['CP17_BROWSER_R3_03_WAREHOUSE_SUMMARY_MOBILE',()=>journey(ui,today,true,h)]]
}
