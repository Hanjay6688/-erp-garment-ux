import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'

const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_f03_return_documents_browser_fixture.py',op,JSON.stringify(p)],{cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim().split('\n').at(-1))
const wib=iso=>new Date(new Date(iso).getTime()+7*60*60*1000).toISOString().slice(0,19)
async function open(ui,p){
  await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:'Gudang'})).toBeAttached()
  const menu=p.getByRole('button',{name:'Buka menu',exact:true})
  if(await menu.isVisible())await menu.click()
  const link=p.getByRole('button',{name:'• Pembelian & Penerimaan',exact:true})
  if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click()
  await link.click()
  await ui.expect(p.getByRole('heading',{name:'Pembelian & penerimaan',exact:true})).toBeVisible()
}

async function flow(ui,today,mobile){
  const f=fixture('prepare',{today}),suffix=mobile?'MOBILE':'DESKTOP'
  const user=await ui.login('OWNER',{label:'complete-return-'+suffix,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
  const p=user.page,panel=p.getByRole('region',{name:'Retur supplier',exact:true})
  try{
    await open(ui,p)
    await p.getByLabel('Cari penerimaan',{exact:true}).fill(f.first.tag)
    await p.getByRole('button',{name:'Cari penerimaan',exact:true}).click()
    const source=p.locator('.cproc-receipt').filter({hasText:f.first.tag})
    await ui.expect(source).toHaveCount(1);await source.click()
    await ui.expect(panel).toContainText('Sumber '+f.first.tag)
    await panel.getByRole('button',{name:'Buat retur supplier',exact:true}).click()
    await panel.getByLabel('Nomor retur supplier',{exact:true}).fill(f.return_number)
    await panel.getByLabel('Waktu retur supplier WIB',{exact:true}).fill(wib(f.return_at))
    await panel.getByLabel('Roll retur 1',{exact:true}).selectOption(f.first.roll)
    await panel.getByLabel('Jumlah retur 1',{exact:true}).fill('2')
    await panel.getByRole('button',{name:'Tambah penerimaan lain',exact:true}).click()
    const picker=panel.getByRole('region',{name:'Pilih penerimaan retur gabungan',exact:true})
    await picker.getByLabel('Cari penerimaan retur',{exact:true}).fill(f.second.tag)
    await picker.getByRole('button',{name:'Cari penerimaan retur',exact:true}).click()
    await picker.getByRole('button').filter({hasText:f.second.tag}).click()
    await panel.getByLabel('Roll retur 2',{exact:true}).selectOption(f.second.roll)
    await panel.getByLabel('Jumlah retur 2',{exact:true}).fill('3')
    await panel.getByRole('button',{name:'Simpan draft retur',exact:true}).click()
    await ui.expect(panel.locator('.cproc-return-detail')).toContainText('Draft retur')
    const saved=fixture('read',f)
    assert.deepEqual(saved.amounts,f.before.amounts);assert.deepEqual(saved.accounts,f.before.accounts)
    assert.equal(saved.documents.length,1);assert.equal(saved.documents[0].lines.length,2)
    assert.equal(saved.documents[0].single_receipt,false)
    await panel.getByRole('button',{name:'Perbaiki draft retur',exact:true}).click()
    await ui.expect(panel.getByLabel('Jumlah retur 2',{exact:true})).toHaveValue('3.000000')
    await panel.getByLabel('Alasan retur supplier',{exact:true}).fill('Dua penerimaan supplier diperiksa; kedua sumber ikut dikembalikan')
    await panel.getByRole('button',{name:'Simpan draft retur',exact:true}).click()
    await ui.expect(panel.locator('.cproc-return-detail')).toContainText('kedua sumber ikut dikembalikan')
    const edited=fixture('read',f)
    assert.equal(edited.documents[0].id,saved.documents[0].id)
    assert.equal(edited.documents[0].physical_at,saved.documents[0].physical_at)
    assert.deepEqual(edited.amounts,f.before.amounts);assert.deepEqual(edited.accounts,f.before.accounts)
    let lost=false,first=null,replay=null
    if(mobile)await p.route('**/rest/v1/rpc/erp_cp7_save_supplier_return_v1',async route=>{
      const body=route.request().postDataJSON()
      if(body.p_action==='POST_DOCUMENT'&&!lost){
        first=body;const response=await route.fetch()
        if(response.status()!==200){await route.fulfill({response});return}
        lost=true;await route.abort('failed')
      }else{if(body.p_action==='POST_DOCUMENT'&&replay===null)replay=body;await route.continue()}
    })
    await panel.getByRole('button',{name:'Tinjau pengiriman retur',exact:true}).click()
    await ui.expect(panel.getByRole('button',{name:'Sahkan pengiriman retur',exact:true})).toBeDisabled()
    await panel.getByLabel('Retur sudah diperiksa',{exact:true}).check()
    await panel.getByRole('button',{name:'Sahkan pengiriman retur',exact:true}).click()
    if(mobile){
      await ui.expect(panel.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible()
      await p.reload();await open(ui,p)
      await panel.getByRole('button',{name:'Reconcile transaksi',exact:true}).click()
      await ui.expect(panel.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0)
      assert.ok(lost);assert.deepEqual(replay,first)
      assert.deepEqual(first.p_payload.reviewed_purchase_ids,[f.first.receipt.purchase_id,f.second.receipt.purchase_id].sort())
    }
    await ui.expect(panel.locator('.cproc-return-detail')).toContainText('Retur sudah dikirim')
    const posted=fixture('read',f),doc=posted.documents[0]
    assert.deepEqual(posted.amounts.map(r=>r.map(Number)),[[80,0,8,10],[140,0,7,20]])
    assert.equal(doc.lines.length,2);assert.equal(Number(doc.finance.ap_relief_amount),80)
    assert.equal(posted.contexts,0);assert.equal(Date.parse(doc.physical_at),Date.parse(f.return_at))
    for(const x of [f.first,f.second])await ui.expect(panel.locator('.cproc-return-detail')).toContainText('Sumber '+x.tag)
    await ui.expect.poll(()=>panel.evaluate(el=>{const b=el.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
    mkdirSync('cp6-proof/t3',{recursive:true})
    await p.screenshot({path:`cp6-proof/t3/P09_COMBINED_RETURN_${suffix}.png`,fullPage:true})
    await panel.getByRole('button',{name:'Tinjau pembatalan retur',exact:true}).click()
    await panel.getByLabel('Alasan tindakan retur',{exact:true}).fill('Barang kembali diperiksa; seluruh penerimaan dipulihkan')
    await panel.getByLabel('Retur sudah diperiksa',{exact:true}).check()
    await panel.getByRole('button',{name:'Batalkan retur supplier',exact:true}).click()
    await ui.expect(panel.locator('.cproc-return-detail')).toContainText('Retur dibatalkan')
    const restored=fixture('read',f)
    assert.deepEqual(restored.amounts,f.before.amounts);assert.deepEqual(restored.accounts,f.before.accounts)
    assert.equal(restored.documents.length,1);assert.equal(restored.documents[0].status,'REVERSED');assert.equal(restored.contexts,0)
    return {status:'PASS',mobile,complete_receipts:2,real_browser_pick_save_edit_post_reverse:true,source_setup_native:true,AP:[80,140],stock:[8,7],all_accounts_and_stock_restored:true,exact_UUID_recovery:mobile?true:null,full_family_acceptance:false,screenshots:[`P09_COMBINED_RETURN_${suffix}.png`]}
  }catch(e){
    mkdirSync('cp6-proof/t3',{recursive:true})
    writeFileSync(`cp6-proof/t3/P09_COMBINED_RETURN_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await p.locator('body').innerText().catch(()=> '')},null,2))
    await p.screenshot({path:`cp6-proof/t3/P09_COMBINED_RETURN_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{})
    throw e
  }finally{await user.context.close()}
}
export async function cases(ui,today){return [['P09_COMBINED_RETURN_BROWSER_DESKTOP',()=>flow(ui,today,false)],['P09_COMBINED_RETURN_BROWSER_MOBILE_RECOVERY',()=>flow(ui,today,true)]]}
