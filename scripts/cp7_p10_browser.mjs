import {execFileSync} from 'node:child_process'
import {mkdirSync} from 'node:fs'
import {bookCases} from './cp7_p10_book_browser.mjs'
import {adjustmentCases} from './cp7_p10_adjustment_browser.mjs'
const fixture=(op,payload)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_p10_browser_fixture.py',op,JSON.stringify(payload)],{cwd:'../writer',encoding:'utf8'}).trim())
async function openPage(ui,p){
 const menu=p.getByRole('button',{name:'Buka menu',exact:true})
 await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:'Gudang'})).toBeAttached({timeout:20000})
 if(await menu.isVisible())await menu.click()
 const link=p.getByRole('button',{name:'• Ringkasan Barang Jadi',exact:true})
 if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click()
 await link.click();await ui.expect(p.getByRole('heading',{name:'Barang jadi',exact:true})).toBeVisible()
}
async function sourceReads(ui,today,mobile){
 const f=fixture('create',{today,ops:mobile}),user=await ui.login(mobile?'ADMIN':'OWNER',{label:'p10-fg-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
 try{
  const p=user.page;await openPage(ui,p)
  await p.getByLabel('Cari barang jadi',{exact:true}).fill(f.sku);await p.getByRole('button',{name:'Cari stok',exact:true}).click()
  await ui.expect(p.locator('.cfg-position')).toHaveCount(1)
  await ui.expect(p.locator('.cfg-totals article').nth(0)).toContainText('10 PCS')
  await ui.expect(p.locator('.cfg-totals article').nth(1)).toContainText('4 PCS')
  await ui.expect(p.locator('.cfg-totals article').nth(2)).toContainText('6 PCS')
  await p.locator('.cfg-position').getByRole('button').click()
  await ui.expect(p.locator('.cfg-ledger')).toContainText('Dicadangkan untuk penjualan')
  if(mobile){if((await p.locator('.cfg').innerText()).includes('Rp'))throw Error('Operations UI exposed an amount')}
  else await ui.expect(p.locator('.cfg-position')).toContainText('Nilai fisik Rp100')
  await ui.expect.poll(()=>p.locator('.cfg').evaluate(el=>{const b=el.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
  mkdirSync('cp6-proof/t3',{recursive:true});await p.evaluate(()=>window.scrollTo(0,0));await p.screenshot({path:`cp6-proof/t3/P10_FG_${mobile?'MOBILE':'DESKTOP'}.png`,fullPage:true})
  fixture('cancel',f);await p.getByRole('button',{name:'Muat ulang stok',exact:true}).click()
  await ui.expect(p.locator('.cfg-totals article').nth(1)).toContainText('0 PCS');await ui.expect(p.locator('.cfg-totals article').nth(2)).toContainText('10 PCS')
  fixture('post',f);await p.getByRole('button',{name:'Muat ulang stok',exact:true}).click()
  await ui.expect(p.locator('.cfg-totals article').nth(0)).toContainText('6 PCS');await ui.expect(p.locator('.cfg-totals article').nth(1)).toContainText('0 PCS')
  const actual=fixture('read',f);if(JSON.stringify(actual.qty)!=='[6,0,6]')throw Error('Native read-back differs from FG UI')
  if(mobile){
   await p.route('**/rest/v1/rpc/erp_cp7_get_fg_v1',r=>r.abort('failed'));await p.getByRole('button',{name:'Muat ulang stok',exact:true}).click()
   await ui.expect(p.locator('.cfg [role="alert"]')).toBeVisible();await ui.expect(p.locator('.cfg-position')).toHaveCount(0)
   await p.unroute('**/rest/v1/rpc/erp_cp7_get_fg_v1');await p.getByRole('button',{name:'Muat ulang stok',exact:true}).click()
   await ui.expect(p.locator('.cfg-totals article').nth(0)).toContainText('6 PCS')
  }
  return {status:'PASS',mobile,real_ui_auth_rpc_database_reads:true,ordinary_fixture_writes_not_P11_browser:true,initial:[10,4,6],cancelled:[10,0,10],posted:[6,0,6],ops_money_hidden:mobile?true:null,failed_read_clears_stale_stock:mobile?true:null,screenshot:`P10_FG_${mobile?'MOBILE':'DESKTOP'}.png`}
 }finally{await user.context.close()}
}
export async function cases(ui,today){return [['P10_FG_BROWSER_DESKTOP',()=>sourceReads(ui,today,false)],['P10_FG_BROWSER_OPERATIONS_MOBILE',()=>sourceReads(ui,today,true)],...adjustmentCases(ui,today),...bookCases(ui,today)]}
