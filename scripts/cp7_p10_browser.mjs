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
  const stockIds=await p.locator('.cfg-position').evaluateAll(rows=>rows.map(row=>row.innerText)),beforeTools=fixture('read',f)
  await p.getByLabel('Urutkan halaman barang jadi',{exact:true}).selectOption('LABEL_DESC')
  if(JSON.stringify(await p.locator('.cfg-position').evaluateAll(rows=>rows.map(row=>row.innerText)))!==JSON.stringify(stockIds))throw Error('One-position display sort changed Native amounts')
  if(JSON.stringify(fixture('read',f))!==JSON.stringify(beforeTools))throw Error('Display sorting changed Native stock')
  await p.getByRole('button',{name:'Browse semua',exact:true}).click();await ui.expect(p.getByLabel('Cari barang jadi',{exact:true})).toHaveValue('')
  await p.getByLabel('Cari barang jadi',{exact:true}).fill(f.sku);await p.getByRole('button',{name:'Cari stok',exact:true}).click();await ui.expect(p.locator('.cfg-position')).toHaveCount(1)
  await p.locator('.cfg-position').getByRole('button').click()
  await ui.expect(p.locator('.cfg-ledger')).toContainText('Dicadangkan untuk penjualan')
  // Owner D17-16 (OW-09): movement type and order go to the card reader, which applies them to every movement of the
  // position before paging; each change restarts at page 1 and the running balances stay attached to their rows.
  const card=check=>p.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_get_fg_ledger_v2')&&r.status()===200&&check(r.request().postDataJSON()?.p_query??{})),beforeCard=fixture('read',f)
  let read=card(q=>q.movement_type==='SALE_RESERVE'&&q.offset===0&&q.order==='SOURCE');await p.getByLabel('Jenis mutasi FG',{exact:true}).selectOption('SALE_RESERVE');let body=await (await read).json()
  if(body.page.list?.movement_type!=='SALE_RESERVE'||!body.page.rows.every(m=>m.movement_type==='SALE_RESERVE'))throw Error('Card reader did not apply the movement type');await ui.expect(p.locator('.cfg-movement')).toHaveCount(body.page.rows.length);await ui.expect(p.locator('.cfg-movement')).toHaveCount(1)
  read=card(q=>q.order==='LABEL_ASC'&&q.movement_type==='SALE_RESERVE'&&q.offset===0);await p.getByLabel('Urutkan mutasi posisi FG',{exact:true}).selectOption('LABEL_ASC');body=await (await read).json();await ui.expect(p.locator('.cfg-movement')).toContainText(/Saldo fisik\s*10/)
  read=card(q=>q.movement_type===null&&q.order==='LABEL_ASC'&&q.offset===0);await p.getByLabel('Jenis mutasi FG',{exact:true}).selectOption('');await read
  if(JSON.stringify(fixture('read',f))!==JSON.stringify(beforeCard))throw Error('Card search, type or order changed Native stock')
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
