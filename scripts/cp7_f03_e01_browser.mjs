import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync, writeFileSync} from 'node:fs'

const fixture = (op, p) => JSON.parse(execFileSync('python', ['../auditor/scripts/cp7_f03_e01_browser_fixture.py', op, JSON.stringify(p)], {cwd:'../writer', encoding:'utf8', maxBuffer:16*1024*1024}).trim().split('\n').at(-1))
const cents = n => {
  const raw=String(n), negative=raw.startsWith('-'), [a,b='']=raw.replace(/^-/,'').split('.')
  assert.match(b.slice(2), /^0*$/)
  return (BigInt(a)*100n+BigInt(b.slice(0,2).padEnd(2,'0')))*(negative?-1n:1n)
}
const delta = (a,b) => Object.fromEntries([...new Set([...Object.keys(a),...Object.keys(b)])].map(k=>[k,cents(b[k]??'0')-cents(a[k]??'0')]).filter(([,v])=>v!==0n))
const money = n => {
  const [a,b='']=String(n).split('.')
  return 'Rp'+a.replace(/\B(?=(\d{3})+(?!\d))/g,'.')+(b.replace(/0+$/,'')?','+b.replace(/0+$/,''):'')
}
async function open(ui,p,title='Penjualan & Invoice',section='Penjualan') {
  await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:section})).toBeAttached()
  const menu=p.getByRole('button',{name:'Buka menu',exact:true})
  if(await menu.isVisible()) await menu.click()
  const link=p.getByRole('button',{name:'• '+title,exact:true})
  if(!await link.isVisible()) await p.locator('.sidebar .nav-main').filter({hasText:section}).click()
  await link.click()
}
function ledger(f,before,after,{ar,revenue,fg,cogs,cash=0}) {
  const expected={[f.mapping.AR_CUSTOMER]:BigInt(ar)*100n,[f.mapping.SALES_REVENUE]:BigInt(-revenue)*100n,[f.mapping.FG_INVENTORY]:BigInt(fg)*100n,[f.mapping.COGS]:BigInt(cogs)*100n,[f.cash_coa]:BigInt(cash)*100n}
  assert.deepEqual(delta(before.accounts,after.accounts),Object.fromEntries(Object.entries(expected).filter(([,v])=>v!==0n)))
}
async function journey(ui,today,mobile) {
  const f=fixture('prepare',{today}), before=fixture('read',f), suffix=mobile?'MOBILE':'DESKTOP'
  const user=await ui.login('OWNER',{label:'e01-'+suffix,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
  const p=user.page, ws=p.locator('.csales'), detail=ws.getByRole('complementary',{name:'Rincian invoice'})
  const cash=ws.getByRole('region',{name:'Pembayaran invoice',exact:true}), cashForm=cash.getByRole('form',{name:'Catat pembayaran pelanggan'})
  const ret=ws.getByRole('region',{name:'Retur fisik invoice'}), retForm=ret.getByRole('form',{name:'Catat retur pelanggan'})
  const select=async()=>{
    await ws.getByLabel('Cari invoice',{exact:true}).fill(f.tag)
    await ws.getByRole('button',{name:'Cari invoice',exact:true}).click()
    const row=ws.getByRole('region',{name:'Daftar invoice'}).locator('.cproc-receipt')
    await ui.expect(row).toHaveCount(1); await row.click()
    await ui.expect(detail.getByRole('heading',{name:f.tag,exact:true})).toBeVisible()
  }
  let peer=null,peerWrites=0
  const peerErrors=[]
  try {
    assert.equal(before.available,60); assert.equal(cents(before.fg_value),90000n)
    assert.equal(before.report.snapshot.data_confidence.status,'READY')
    await open(ui,p)
    await ws.getByRole('button',{name:'Buat invoice',exact:true}).click()
    const draft=ws.getByRole('form',{name:'Draft invoice'})
    await draft.getByLabel('Nomor draft invoice',{exact:true}).fill(f.tag)
    await draft.getByLabel('Waktu draft invoice WIB',{exact:true}).fill(new Date(new Date(f.sale_at).getTime()+7*60*60*1000).toISOString().slice(0,16))
    await draft.getByLabel('Cari pelanggan draft',{exact:true}).fill(f.tag)
    await draft.getByRole('button',{name:'Cari pelanggan draft',exact:true}).click()
    const customer=draft.getByRole('region',{name:'Pilih pelanggan invoice'}).locator('.cproc-receipt')
    await ui.expect(customer).toHaveCount(1); await customer.click()
    await draft.getByLabel('Cari barang draft',{exact:true}).fill(f.sku)
    await draft.getByRole('button',{name:'Cari barang draft',exact:true}).click()
    const stock=draft.getByRole('region',{name:'Pilih barang invoice'}).locator('.cproc-receipt')
    await ui.expect(stock).toHaveCount(1); await stock.click()
    await draft.getByLabel('Jumlah invoice 1',{exact:true}).fill('20')
    await draft.getByLabel('Harga invoice 1',{exact:true}).fill('25')
    await draft.getByLabel('Alasan simpan invoice',{exact:true}).fill('E01 dua puluh dari produksi enam puluh')
    await draft.getByLabel('Draft invoice sudah diperiksa',{exact:true}).check()
    await draft.getByRole('button',{name:'Simpan draft invoice',exact:true}).click()
    await ui.expect(draft).toHaveCount(0); await ui.expect(detail).toContainText('20 PCS masih dipesan')
    const reserved=fixture('read',f); assert.equal(reserved.available,40); assert.deepEqual(reserved.accounts,before.accounts)
    await detail.getByLabel('Invoice sudah diperiksa',{exact:true}).check()
    await detail.getByRole('button',{name:'Sahkan invoice',exact:true}).click()
    await ui.expect(detail).toContainText('Sisa pembayaran Rp500')
    const sold=fixture('read',f); assert.equal(sold.available,40); assert.equal(cents(sold.fg_value),60000n)
    ledger(f,before,sold,{ar:500,revenue:500,fg:-300,cogs:300})
    await open(ui,p,'Pembayaran Pelanggan'); await select()
    await detail.getByRole('button',{name:'Pembayaran invoice',exact:true}).click()
    await cashForm.getByLabel('Nomor pembayaran pelanggan',{exact:true}).fill(f.tag+'-PAY')
    await cashForm.getByLabel('Nominal pembayaran pelanggan',{exact:true}).fill('200')
    await cashForm.getByLabel('Cari rekening pembayaran pelanggan',{exact:true}).fill(f.bank_code)
    await cashForm.getByRole('button',{name:'Cari rekening pelanggan',exact:true}).click()
    const bank=cashForm.getByRole('region',{name:'Pilih rekening pembayaran pelanggan'}).locator('.cproc-receipt')
    await ui.expect(bank).toHaveCount(1); await bank.click()
    await cashForm.getByLabel('Pembayaran pelanggan sudah diperiksa',{exact:true}).check()
    await cashForm.getByRole('button',{name:'Catat pembayaran pelanggan',exact:true}).click()
    await ui.expect(cash).toHaveCount(0); await ui.expect(detail).toContainText('Sisa pembayaran Rp300')
    const paid=fixture('read',f); assert.equal(paid.available,40)
    ledger(f,before,paid,{ar:300,revenue:500,fg:-300,cogs:300,cash:200})
    assert.deepEqual(paid.report.snapshot.performance,sold.report.snapshot.performance)
    await open(ui,p,'Retur Penjualan'); await select()
    await detail.getByRole('button',{name:'Retur fisik invoice',exact:true}).click()
    await retForm.getByLabel('Nomor retur pelanggan',{exact:true}).fill(f.tag+'-RET')
    await retForm.getByLabel('Cari gudang retur',{exact:true}).fill(f.destination_name)
    await retForm.getByRole('button',{name:'Cari gudang retur',exact:true}).click()
    const destination=retForm.getByRole('region',{name:'Pilih gudang retur'}).locator('.cproc-receipt')
    await ui.expect(destination).toHaveCount(1); await destination.click()
    const allocation=retForm.getByRole('region',{name:'Pilih alokasi retur'}).locator('.cproc-receipt')
    await ui.expect(allocation).toHaveCount(1); await allocation.click()
    await retForm.getByLabel('Jumlah retur 1',{exact:true}).fill('5')
    await retForm.getByLabel('Nilai retur 1',{exact:true}).fill('125')
    await retForm.getByLabel('Grade retur 1',{exact:true}).selectOption('GRADE_A')
    await retForm.getByLabel('Catatan barang retur 1',{exact:true}).fill('Lima GOOD dari alokasi asli')
    await retForm.getByLabel('Retur pelanggan sudah diperiksa',{exact:true}).check()
    if(mobile) {
      // A second real tab shares this authenticated session and recovery
      // storage. It reads the same invoice before the first tab commits.
      peer=await user.context.newPage(); peer.setDefaultTimeout(20000)
      peer.on('pageerror',e=>peerErrors.push(e.message))
      peer.on('request',r=>{if(r.url().endsWith('/rest/v1/rpc/erp_cp7_save_sale_v1')) peerWrites++})
      await peer.goto(ui.origin); await open(ui,peer,'Retur Penjualan')
      const other=peer.locator('.csales')
      await other.getByLabel('Cari invoice',{exact:true}).fill(f.tag)
      await other.getByRole('button',{name:'Cari invoice',exact:true}).click()
      const row=other.getByRole('region',{name:'Daftar invoice'}).locator('.cproc-receipt')
      await ui.expect(row).toHaveCount(1); await row.click()
      await ui.expect(other.getByRole('button',{name:'Retur fisik invoice',exact:true})).toBeEnabled()
      await ui.expect(other.getByRole('complementary',{name:'Rincian invoice'})).toContainText('Sisa pembayaran Rp300')
    }
    let lost=false,first=null,replay=null
    if(mobile) await p.route('**/rest/v1/rpc/erp_cp7_save_sale_v1',async route=>{
      const body=route.request().postDataJSON()
      if(body.p_action==='RETURN'&&!lost) {
        first=body; const response=await route.fetch()
        if(response.status()!==200) {await route.fulfill({response}); return}
        lost=true; await route.abort('failed')
      } else {if(body.p_action==='RETURN'&&replay===null) replay=body; await route.continue()}
    })
    await retForm.getByRole('button',{name:'Catat retur pelanggan',exact:true}).click()
    if(mobile) {
      await ui.expect(ws.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible()
      const other=peer.locator('.csales')
      await ui.expect(other.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible()
      await ui.expect(other.getByRole('button',{name:'Retur fisik invoice',exact:true})).toBeDisabled()
      await ui.expect(other.getByRole('button',{name:'Pembayaran invoice',exact:true})).toBeDisabled()
      // Recovery is visible as soon as the envelope is persisted, including
      // while the RPC still runs. Only read the committed amount after the
      // intercepted real server response has confirmed COMMIT.
      await ui.expect.poll(()=>lost,{timeout:20000}).toBe(true)
      // Unrelated reads remain possible; they cannot silently clear the
      // ambiguous mutation or turn its new UUID into a second return.
      await other.getByRole('button',{name:'Muat ulang invoice',exact:true}).click()
      await ui.expect(other.getByRole('complementary',{name:'Rincian invoice'})).toContainText('Sisa pembayaran Rp175')
      await ui.expect(other.getByRole('button',{name:'Retur fisik invoice',exact:true})).toBeDisabled()
      const pending=await peer.evaluate(()=>Object.entries(localStorage).filter(([k])=>k.startsWith('erp.production.SALES.pending-mutation.v1:')).map(([,v])=>JSON.parse(v)))
      assert.equal(pending.length,1); assert.equal(pending[0].id,first.p_request)
      assert.equal(pending[0].action,'RETURN'); assert.deepEqual(pending[0].payload.document,first.p_payload)
      await p.reload(); await open(ui,p,'Retur Penjualan')
      await ws.getByRole('button',{name:'Reconcile transaksi',exact:true}).click()
      await ui.expect(ws.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0)
      assert.ok(lost); assert.deepEqual(replay,first)
      await ui.expect(other.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0)
      await other.getByRole('button',{name:'Muat ulang invoice',exact:true}).click()
      await ui.expect(other.getByRole('button',{name:'Retur fisik invoice',exact:true})).toBeEnabled()
      assert.equal(peerWrites,0); assert.deepEqual(peerErrors,[])
    }
    await ui.expect(ret).toHaveCount(0); await ui.expect(detail).toContainText('Sisa pembayaran Rp175')
    const returned=fixture('read',f)
    assert.equal(returned.report.snapshot.data_confidence.status,'READY')
    assert.equal(returned.available,45); assert.equal(cents(returned.fg_value),67500n)
    assert.equal(returned.returns.page.total,'1'); assert.equal(returned.cash.payments.total,'1')
    ledger(f,before,returned,{ar:175,revenue:375,fg:-225,cogs:225,cash:200})
    for(const [section,key,expected] of [['financial_position','cash',200],['financial_position','customer_ar',175],['financial_position','fg_inventory',-225],['performance','sales_revenue_gl',375],['performance','cogs_gl',225],['performance','gross_profit',150]]) {
      assert.equal(cents(returned.report.snapshot[section][key])-cents(before.report.snapshot[section][key]),BigInt(expected)*100n)
    }
    mkdirSync('cp6-proof/t3',{recursive:true})
    await ui.expect.poll(()=>ws.evaluate(el=>{const r=el.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
    await p.screenshot({path:`cp6-proof/t3/E01_SALE_RETURN_${suffix}.png`,fullPage:true})
    await open(ui,p,'Laporan & Tutup Buku','Keuangan')
    const report=p.locator('.cfinance-report')
    await ui.expect(report.getByRole('button',{name:'Tampilkan laporan',exact:true})).toBeEnabled()
    for(const name of ['Periode laporan dari','Periode laporan sampai','Posisi laporan pada']) await report.getByLabel(name,{exact:true}).fill(today)
    await report.getByRole('button',{name:'Tampilkan laporan',exact:true}).click()
    const performance=report.getByRole('region',{name:'Kinerja keuangan tercatat'}), position=report.getByRole('region',{name:'Posisi keuangan tercatat'})
    for(const [label,key] of [['Penjualan menurut jurnal','sales_revenue_gl'],['Harga pokok penjualan','cogs_gl'],['Laba kotor','gross_profit']]) await ui.expect(performance.locator('.cproc-total').filter({has:p.getByText(label,{exact:true})}).locator('strong')).toHaveText(money(returned.report.snapshot.performance[key]))
    for(const [label,key] of [['Kas dan bank','cash'],['Piutang pelanggan','customer_ar'],['Persediaan barang jadi','fg_inventory']]) await ui.expect(position.locator('.cproc-total').filter({has:p.getByText(label,{exact:true})}).locator('strong')).toHaveText(money(returned.report.snapshot.financial_position[key]))
    await ui.expect.poll(()=>report.evaluate(el=>{const r=el.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
    await p.evaluate(()=>window.scrollTo(0,0))
    await p.screenshot({path:`cp6-proof/t3/E01_REPORT_${suffix}.png`,fullPage:true})
    assert.deepEqual(fixture('read',f).accounts,returned.accounts)
    return {status:'PASS',journey:'E01',mobile,production_source_native_qualified:true,production_checkpoints:f.trace,browser_create_post_pay_return_report:true,fg:45,fg_value:'675',cash:'200',AR:'175',revenue:'375',COGS:'225',gross_profit:'150',lost_return_response_exact_UUID_replay:mobile?true:null,E12_second_authenticated_tab_same_invoice_fenced:mobile?true:null,E12_read_allowed_without_clearing_pending:mobile?true:null,E12_peer_write_requests:mobile?peerWrites:null,one_return:true,report_read_only:true,report_confidence:returned.report.snapshot.data_confidence,production_browser_write_claim:false,full_family_acceptance:false,screenshots:[`E01_SALE_RETURN_${suffix}.png`,`E01_REPORT_${suffix}.png`]}
  } catch(e) {
    let observed; try {observed=fixture('read',f)} catch(x) {observed={error:String(x)}}
    mkdirSync('cp6-proof/t3',{recursive:true})
    writeFileSync(`cp6-proof/t3/E01_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await p.locator('body').innerText().catch(()=>''),source:observed},null,2))
    await p.screenshot({path:`cp6-proof/t3/E01_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{})
    throw e
  } finally {if(peer) await peer.close().catch(()=>{}); await user.context.close()}
}
export async function cases(ui,today) {
  return [['F03_E01_BROWSER_DESKTOP',()=>journey(ui,today,false)],['F03_E01_BROWSER_MOBILE_LOST_RETURN',()=>journey(ui,today,true)]]
}
