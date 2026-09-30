import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_f03_e24_issue_browser_fixture.py',op,JSON.stringify(p)],{cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim().split('\n').at(-1))
async function open(ui,p){
  await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:'Keuangan'})).toBeAttached()
  const menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
  const link=p.getByRole('button',{name:'• Nota Ambil Aksesori',exact:true})
  if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Keuangan'}).click()
  await link.click();await ui.expect(p.getByRole('heading',{name:'Nota Ambil Aksesori',exact:true})).toBeVisible()
  await ui.expect(p.getByRole('button',{name:'Muat ulang',exact:true})).toBeEnabled()
}
async function flow(ui,today,mobile){
  const f=fixture('prepare',{today}),suffix=mobile?'MOBILE':'DESKTOP'
  const owner=await ui.login('OWNER',{label:'e24-issue-'+suffix,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
  const p=owner.page,form=p.getByRole('region',{name:'Form nota aksesori',exact:true})
  try{
    await open(ui,p);await p.getByRole('button',{name:'Nota baru',exact:true}).click()
    await form.getByLabel('Nomor nota aksesori',{exact:true}).fill(f.issue_number)
    await form.getByLabel('Mandor aksesori',{exact:true}).selectOption(f.mandor)
    await form.getByLabel('Gudang aksesori',{exact:true}).selectOption(f.other)
    await form.getByLabel('Waktu ambil aksesori',{exact:true}).fill(f.issue_at.slice(0,16))
    await form.getByLabel('Cari barang aksesori',{exact:true}).fill(f.code)
    await form.getByRole('button',{name:'Perbarui harga dan stok',exact:true}).click()
    await ui.expect(form.getByLabel('Tambah aksesori',{exact:true})).toBeEnabled()
    await form.getByLabel('Tambah aksesori',{exact:true}).selectOption(f.material)
    await form.getByLabel('Jumlah PCS 1',{exact:true}).fill('7')
    await form.getByLabel('Harga per PCS 1',{exact:true}).fill('3.25')
    await form.getByRole('button',{name:'Simpan draft',exact:true}).click()
    await ui.expect.poll(()=>fixture('read',f).document?.status).toBe('DRAFT')
    const draft=fixture('read',f)
    assert.deepEqual(draft.stock,f.before.stock);assert.deepEqual(draft.accounts,f.before.accounts)
    let lost=false,first=null,replay=null
    if(mobile)await p.route('**/rest/v1/rpc/erp_save_accessory_issue_action_v1',async route=>{
      const body=route.request().postDataJSON()
      if(body.p_action==='POST'&&!lost){first=body;const response=await route.fetch();if(response.status()!==200){await route.fulfill({response});return}lost=true;await route.abort('failed')}
      else{if(body.p_action==='POST'&&replay===null)replay=body;await route.continue()}
    })
    await form.getByRole('button',{name:'Periksa pengesahan',exact:true}).click()
    await form.getByRole('button',{name:'Sahkan nota',exact:true}).click()
    if(mobile){
      await ui.expect(p.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible()
      await p.reload();await open(ui,p);await p.getByRole('button',{name:'Reconcile transaksi',exact:true}).click()
      await ui.expect(p.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0)
      assert.ok(lost);assert.deepEqual(replay,first)
    }
    await ui.expect(form.getByRole('heading')).toContainText('POSTED')
    const posted=fixture('verify_posted',f)
    assert.equal(posted.document.id,draft.document.id)
    assert.equal(Date.parse(posted.document.physical_local+'+07:00'),Date.parse(f.issue_at))
    await ui.expect.poll(()=>p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
    mkdirSync('cp6-proof/t3',{recursive:true});await p.screenshot({path:`cp6-proof/t3/E24_NOTE_${suffix}.png`,fullPage:true})
    await form.getByLabel('Alasan pembatalan nota',{exact:true}).fill('Barang dikembalikan ke gudang pengambilan')
    await form.getByRole('button',{name:'Periksa pembatalan',exact:true}).click()
    await form.getByRole('button',{name:'Sahkan pembatalan nota',exact:true}).click()
    await ui.expect(form.getByRole('heading')).toContainText('REVERSED')
    const restored=fixture('read',f)
    assert.deepEqual(restored.stock,f.before.stock);assert.deepEqual(restored.accounts,f.before.accounts);assert.deepEqual(restored.source,f.before.source)
    return {status:'PASS',mobile,CP7_native_receipt_transfer_source:true,actual_note_save_post_inverse_browser:true,issued7_receivable:'22.75',stock_main20_other3:true,
      invoice_AP0_GRNI60_unchanged:true,every_account_and_source_stock_restored:true,exact_lost_post_recovery:mobile?true:null,screenshots:[`E24_NOTE_${suffix}.png`],full_family_acceptance:false}
  }catch(e){
    mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync(`cp6-proof/t3/E24_NOTE_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await p.locator('body').innerText().catch(()=> '')},null,2))
    await p.screenshot({path:`cp6-proof/t3/E24_NOTE_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e
  }finally{await owner.context.close()}
}
export async function cases(ui,today){return [['F03_E24_NOTE_BROWSER_DESKTOP',()=>flow(ui,today,false)],['F03_E24_NOTE_BROWSER_MOBILE_RECOVERY',()=>flow(ui,today,true)]]}
