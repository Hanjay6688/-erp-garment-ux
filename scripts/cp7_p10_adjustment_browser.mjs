import {execFileSync} from 'node:child_process'
const fixture=(op,payload)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_p10_browser_fixture.py',op,JSON.stringify(payload)],{cwd:'../writer',encoding:'utf8'}).trim())
async function openPage(ui,p){
 const menu=p.getByRole('button',{name:'Buka menu',exact:true})
 await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:'Gudang'})).toBeAttached({timeout:20000})
 if(await menu.isVisible())await menu.click()
 const link=p.getByRole('button',{name:'• Stock Adjustment',exact:true})
 if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click()
 await link.click();await p.getByRole('navigation',{name:'Jenis persediaan'}).getByRole('button',{name:'Barang jadi',exact:true}).click()
 await ui.expect(p.getByRole('heading',{name:'Penyesuaian barang jadi',exact:true})).toBeVisible()
}
async function correction(ui,today,mobile){
 const f=fixture('create_adjust',{today,ops:mobile}),user=await ui.login(mobile?'ADMIN':'OWNER',{label:'p10-adjust-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
 try{
  const p=user.page;await openPage(ui,p);const panel=p.locator('.cfga')
  async function add(source){await p.getByLabel('Cari sumber penyesuaian FG',{exact:true}).fill(source.sku);await p.getByRole('button',{name:'Cari sumber FG',exact:true}).click();const card=panel.locator('.cfg-position').filter({hasText:source.sku});await ui.expect(card).toHaveCount(1);const add=card.getByRole('button');await ui.expect(add).toBeEnabled();await add.click()}
  await add(f);if(!mobile)await add(f.second)
  await p.getByLabel('Nomor penyesuaian FG',{exact:true}).fill(f.number)
  await p.getByLabel('Alasan penyesuaian FG',{exact:true}).fill('Hasil pemeriksaan ulang di gudang')
  await p.getByLabel('Perubahan FG 1',{exact:true}).fill('-2');if(!mobile)await p.getByLabel('Perubahan FG 2',{exact:true}).fill('2')
  await p.getByRole('button',{name:'Simpan draft FG',exact:true}).click();await ui.expect(panel.locator('.cfga-detail')).toContainText(f.number)
  let actual=fixture('read_adjust',f);if(actual.document?.status!=='DRAFT'||actual.qty[0]!==10||actual.second_qty[0]!==10)throw Error('Draft changed physical stock')
  const edit=p.getByRole('button',{name:'Edit draft FG',exact:true});await ui.expect(edit).toBeEnabled();await edit.click()
  // Native draft item UUID order may change; identify the actual source lot/SKU.
  await panel.locator('form .cproc-item').filter({hasText:mobile?f.sku:f.second.sku}).getByRole('textbox').fill(mobile?'-3':'1')
  await p.getByRole('button',{name:'Simpan draft FG',exact:true}).click();await ui.expect(edit).toBeEnabled()
  const post=p.getByRole('button',{name:'Sahkan koreksi FG',exact:true});await ui.expect(post).toBeDisabled()
  await p.getByLabel('Jumlah, lot, ukuran, dan alasan sudah saya periksa.',{exact:true}).check();await ui.expect(post).toBeEnabled()
  let first=null,replay=null,lost=false
  if(mobile)await p.route('**/rest/v1/rpc/erp_cp7_save_fg_adjustment_v1',async route=>{const body=route.request().postDataJSON();if(body.p_action==='POST'&&!lost){first=body;const result=await route.fetch();if(result.status()!==200)throw Error('Expected committed FG correction before loss');lost=true;await route.abort('failed')}else{if(body.p_action==='POST'&&replay===null)replay=body;await route.continue()}})
  await post.click();await ui.expect.poll(()=>fixture('read_adjust',f).document?.status,{timeout:20000}).toBe('POSTED')
  if(mobile){await ui.expect(panel.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible();await p.reload();await openPage(ui,p);await panel.getByRole('button',{name:'Reconcile transaksi',exact:true}).click();await ui.expect(panel.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0);if(!lost||JSON.stringify(first)!==JSON.stringify(replay))throw Error('FG correction recovery changed intent or UUID')}
  await ui.expect(panel.locator('.cfga-detail')).toContainText('Sudah disahkan');await ui.expect(p.getByRole('button',{name:'Muat ulang FG',exact:true})).toBeEnabled()
  actual=fixture('read_adjust',f);if(actual.qty[0]!== (mobile?7:8)||actual.second_qty[0]!== (mobile?10:11))throw Error('FG correction native stock mismatch '+JSON.stringify(actual))
  if(mobile&& (await panel.innerText()).includes('Rp'))throw Error('Operational FG correction leaked money')
  if(!mobile)await ui.expect(panel.locator('.cfga-detail .cproc-item')).toHaveCount(2)
  await ui.expect.poll(()=>panel.evaluate(el=>{const b=el.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
  await p.evaluate(()=>window.scrollTo(0,0));await p.screenshot({path:`cp6-proof/t3/P10_ADJUST_${mobile?'MOBILE':'DESKTOP'}.png`,fullPage:true})
  await p.getByLabel('Jumlah, lot, ukuran, dan alasan sudah saya periksa.',{exact:true}).check();await p.getByRole('button',{name:'Batalkan koreksi FG',exact:true}).click();await ui.expect(panel.locator('.cfga-detail')).toContainText('Dibatalkan')
  const after=fixture('read_adjust',f);if(after.qty[0]!==10||after.second_qty[0]!==10||JSON.stringify(after.accounts)!==JSON.stringify(f.accounts))throw Error('FG correction inverse did not restore stock and all accounts')
  return {status:'PASS',mobile,real_ui_auth_native_write:true,complete_line_count:mobile?1:2,draft_edit_post_inverse:true,stock_after:mobile?[7,10]:[8,11],inverse_stock:[10,10],all_accounts_restored:true,ops_money_hidden:mobile?true:null,lost_reply_exact_uuid_payload:mobile?true:null,screenshot:`P10_ADJUST_${mobile?'MOBILE':'DESKTOP'}.png`}
 }finally{await user.context.close()}
}
export function adjustmentCases(ui,today){return [['P10_ADJUST_BROWSER_DESKTOP',()=>correction(ui,today,false)],['P10_ADJUST_BROWSER_MOBILE_RECOVERY',()=>correction(ui,today,true)]]}
