import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'

const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_f03_capacity_browser_fixture.py',op,JSON.stringify(p)],{cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim().split('\n').at(-1))
async function open(ui,p,title,section){
  await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:section})).toBeAttached()
  const menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
  const link=p.getByRole('button',{name:'• '+title,exact:true})
  if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:section}).click()
  await link.click()
}
async function screen(ui,p,name){
  mkdirSync('cp6-proof/t3',{recursive:true})
  await ui.expect.poll(()=>p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
  await p.evaluate(()=>window.scrollTo(0,0));await p.screenshot({path:'cp6-proof/t3/'+name,fullPage:true})
}
async function journey(ui,today,mobile){
  const f=fixture('prepare',{today,ops:mobile}),suffix=mobile?'OPERATIONS_MOBILE':'OWNER_DESKTOP'
  const user=await ui.login(mobile?'ADMIN':'OWNER',{label:'capacity-'+suffix,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
  const p=user.page,screenshots=[],pages=[]
  try{
    assert.deepEqual(f.before.qty,[30,0,30]);assert.equal(Number(f.before.available_value),300)
    await open(ui,p,'Ringkasan Barang Jadi','Gudang')
    const ws=p.locator('.cfg')
    await ui.expect(ws.getByRole('button',{name:'Cari stok',exact:true})).toBeEnabled()
    await ws.getByLabel('Cari barang jadi',{exact:true}).fill(f.sku)
    let response=p.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_get_fg_v1')&&r.request().postDataJSON()?.p_query?.q===f.sku)
    await ws.getByRole('button',{name:'Cari stok',exact:true}).click()
    let read=await response;assert.equal(read.status(),200);pages.push(await read.json())
    await ui.expect(ws.locator('.cfg-position')).toHaveCount(25)
    for(const [i,n] of [[0,30],[1,0],[2,30]])await ui.expect(ws.locator('.cfg-totals article').nth(i)).toContainText(n+' PCS')
    response=p.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_get_fg_v1')&&r.request().postDataJSON()?.p_query?.offset===25)
    await ws.getByRole('button',{name:'Stok berikutnya',exact:true}).click()
    read=await response;assert.equal(read.status(),200);pages.push(await read.json())
    await ui.expect(ws.locator('.cfg-position')).toHaveCount(5)
    for(const [i,n] of [[0,30],[1,0],[2,30]])await ui.expect(ws.locator('.cfg-totals article').nth(i)).toContainText(n+' PCS')
    assert.equal(fixture('verify-pages',{...f,pages,ops:mobile}).status,'PASS')
    if(mobile){
      assert.ok(!(await ws.innerText()).includes('Rp'))
      response=p.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_get_fg_ledger_v1'))
      await ws.locator('.cfg-position').last().getByRole('button',{name:/^Lihat mutasi /}).click()
      read=await response;assert.equal(read.status(),200)
      assert.equal(fixture('verify-card',{...f,card:await read.json()}).status,'PASS')
      await ui.expect(ws.locator('.cfg-ledger')).toContainText('Saldo fisik')
      assert.ok(!(await ws.innerText()).includes('Rp'))
      await screen(ui,p,`E20_E14_SOURCE_${suffix}.png`);screenshots.push(`E20_E14_SOURCE_${suffix}.png`)
      const before=fixture('read',f);fixture('revoke-ops',f)
      response=p.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_get_fg_v1'))
      await ws.getByRole('button',{name:'Muat ulang stok',exact:true}).click()
      read=await response;assert.equal(read.status(),403)
      await ui.expect(ws.getByRole('alert')).toBeVisible()
      await ui.expect(ws.locator('.cfg-position')).toHaveCount(0)
      await ui.expect(ws.locator('.cfg-movement')).toHaveCount(0)
      const after=fixture('read',f);assert.deepEqual(after.qty,before.qty);assert.deepEqual(after.accounts,before.accounts)
      await screen(ui,p,`E20_E14_REVOKED_${suffix}.png`);screenshots.push(`E20_E14_REVOKED_${suffix}.png`)
      return {status:'PASS',mobile,pages:[25,5],physical_source_lots:30,both_pages_and_actual_card_no_money:true,
        actual_403_reload_clears_old_positions_and_card:true,stock_and_accounts_unchanged:true,
        invoice_write_claim:false,full_family_acceptance:false,screenshots}
    }
    await screen(ui,p,`E20_SOURCE_${suffix}.png`);screenshots.push(`E20_SOURCE_${suffix}.png`)
    await open(ui,p,'Penjualan & Invoice','Penjualan')
    const sales=p.locator('.csales'),detail=sales.getByRole('complementary',{name:'Rincian invoice'})
    await sales.getByRole('button',{name:'Buat invoice',exact:true}).click()
    const draft=sales.getByRole('form',{name:'Draft invoice'})
    await draft.getByLabel('Nomor draft invoice',{exact:true}).fill(f.tag)
    await draft.getByLabel('Waktu draft invoice WIB',{exact:true}).fill(new Date(new Date(f.sale_at).getTime()+7*60*60*1000).toISOString().slice(0,16))
    await draft.getByLabel('Cari pelanggan draft',{exact:true}).fill(f.tag)
    await draft.getByRole('button',{name:'Cari pelanggan draft',exact:true}).click()
    const customer=draft.getByRole('region',{name:'Pilih pelanggan invoice'}).locator('.cproc-receipt')
    await ui.expect(customer).toHaveCount(1);await customer.click()
    await draft.getByLabel('Cari barang draft',{exact:true}).fill(f.sku)
    response=p.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_get_sales_form_v1')&&r.request().postDataJSON()?.p_query?.kind==='STOCK')
    await draft.getByRole('button',{name:'Cari barang draft',exact:true}).click()
    read=await response;assert.equal(read.status(),200)
    const selector=await read.json();assert.equal(selector.rows.length,1);assert.equal(selector.rows[0].available_qty,'30')
    const stock=draft.getByRole('region',{name:'Pilih barang invoice'}).locator('.cproc-receipt')
    await ui.expect(stock).toHaveCount(1);await stock.click()
    await draft.getByLabel('Jumlah invoice 1',{exact:true}).fill('27')
    await draft.getByLabel('Harga invoice 1',{exact:true}).fill('20')
    await draft.getByLabel('Alasan simpan invoice',{exact:true}).fill('E20 ambil27 dari seluruh30 lot bukan halaman25')
    await draft.getByLabel('Draft invoice sudah diperiksa',{exact:true}).check()
    response=p.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_save_sale_v1')&&r.request().postDataJSON()?.p_action==='CREATE')
    await draft.getByRole('button',{name:'Simpan draft invoice',exact:true}).click()
    read=await response;assert.equal(read.status(),200)
    await ui.expect(draft).toHaveCount(0);await ui.expect(detail).toContainText('27 PCS masih dipesan')
    const reserved=fixture('read',f);assert.deepEqual(reserved.qty,[30,27,3]);assert.deepEqual(reserved.accounts,f.before.accounts)
    await detail.getByLabel('Invoice sudah diperiksa',{exact:true}).check()
    response=p.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_save_sale_v1')&&r.request().postDataJSON()?.p_action==='POST')
    await detail.getByRole('button',{name:'Sahkan invoice',exact:true}).click()
    read=await response;assert.equal(read.status(),200)
    await ui.expect(detail).toContainText('Sisa pembayaran Rp540')
    const posted=fixture('verify-posted',f);assert.equal(posted.status,'PASS');assert.deepEqual(posted.qty,[3,0,3])
    await screen(ui,p,`E20_INVOICE_${suffix}.png`);screenshots.push(`E20_INVOICE_${suffix}.png`)
    await open(ui,p,'Ringkasan Barang Jadi','Gudang')
    await ws.getByLabel('Cari barang jadi',{exact:true}).fill(f.sku)
    await ws.getByRole('button',{name:'Cari stok',exact:true}).click()
    await ui.expect(ws.locator('.cfg-position')).toHaveCount(3)
    for(const [i,n] of [[0,3],[1,0],[2,3]])await ui.expect(ws.locator('.cfg-totals article').nth(i)).toContainText(n+' PCS')
    await screen(ui,p,`E20_POSTED_STOCK_${suffix}.png`);screenshots.push(`E20_POSTED_STOCK_${suffix}.png`)
    return {status:'PASS',mobile,pages:[25,5],physical_source_lots:30,actual_browser_create27_and_post:true,
      draft:[30,27,3],posted:[3,0,3],COGS:'270.00',AR:'540.00',FG_value:'30.00',
      allocation_lots:27,no_second_stock_deduction:true,not_a_planner_gap_engine_claim:true,
      full_family_acceptance:false,screenshots}
  }catch(e){
    mkdirSync('cp6-proof/t3',{recursive:true})
    writeFileSync(`cp6-proof/t3/E20_E14_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await p.locator('body').innerText().catch(()=> '')},null,2))
    await p.screenshot({path:`cp6-proof/t3/E20_E14_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{})
    throw e
  }finally{await user.context.close()}
}
export async function cases(ui,today){return [['F03_E20_BROWSER_OWNER_PAGES_TO_INVOICE',()=>journey(ui,today,false)],['F03_E14_BROWSER_OPERATIONS_PAGES_REVOKED',()=>journey(ui,today,true)]]}
