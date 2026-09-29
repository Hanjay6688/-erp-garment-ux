import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_p12_browser_fixture.py',op,JSON.stringify(p)],{cwd:'../writer',encoding:'utf8'}).trim())
async function openPage(ui,p){
 const menu=p.getByRole('button',{name:'Buka menu',exact:true})
 await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:'Produksi'})).toBeAttached({timeout:20000})
 if(await menu.isVisible())await menu.click()
 const link=p.getByRole('button',{name:'• Susun Nota FG',exact:true})
 if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Produksi'}).click()
 await link.click();await ui.expect(p.locator('.cnota').getByRole('heading',{name:'Susun Nota FG',exact:true})).toBeVisible()
}
async function compose(ui,today,mobile){
 const f=fixture('create',{today,ops:mobile}),user=await ui.login(mobile?'ADMIN':'OWNER',{label:'p12-nota-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
 try{
  const p=user.page;await openPage(ui,p);const panel=p.locator('.cnota'),composer=panel.getByRole('region',{name:'Susunan nota'})
  async function search(){await p.getByLabel('Cari kartu nota',{exact:true}).fill(f.label);await p.getByRole('button',{name:'Cari kartu',exact:true}).click()}
  await search();await ui.expect(panel.locator('.cnota-source')).toHaveCount(2)
  if(!mobile){
   const grip=panel.locator('.cnota-source .cnota-grip').first();await grip.scrollIntoViewIfNeeded();const box=await grip.boundingBox();if(!box)throw Error('Missing draggable source grip')
   await p.mouse.move(box.x+box.width/2,box.y+box.height/2);await p.mouse.down();await p.mouse.move(box.x+box.width/2+18,box.y+box.height/2+4,{steps:8})
   const target=await composer.boundingBox();if(!target)throw Error('Missing Nota drop area')
   await p.mouse.move(target.x+target.width/2,target.y+100,{steps:18});await p.mouse.move(target.x+target.width/2+3,target.y+104,{steps:2});await p.mouse.up()
   await ui.expect(panel.locator('.cnota-selected article')).toHaveCount(1)
   await panel.locator('.cnota-source').getByRole('button',{name:'Tambahkan ke nota',exact:true}).click()
  }else{
   await panel.locator('.cnota-source').first().getByRole('button',{name:'Tambahkan ke nota',exact:true}).click()
   await panel.locator('.cnota-source').last().getByRole('button',{name:'Tambahkan ke nota',exact:true}).click()
  }
  await ui.expect(panel.locator('.cnota-selected article')).toHaveCount(2)
  await ui.expect(p.getByLabel('Tanggal nota WIB',{exact:true})).toHaveValue(today)
  await p.getByRole('button',{name:'Simpan draft nota',exact:true}).click();await ui.expect(panel.locator('.cnota-review')).toContainText('Draft')
  let actual=fixture('read',f);if(actual.notes.length!==1||actual.notes[0].status!=='DRAFT'||actual.allocated[0]!==0||JSON.stringify(actual.facts)!==JSON.stringify(f.facts))throw Error('Draft caused native financial/stock effects '+JSON.stringify(actual))
  if(mobile&& (await panel.innerText()).includes('Rp'))throw Error('Operational draft exposed money')
  const post=p.getByRole('button',{name:'Posting ke payroll',exact:true});await ui.expect(post).toBeDisabled()
  await p.getByLabel('Nota sudah diperiksa',{exact:true}).check();await ui.expect(post).toBeEnabled()
  let first=null,replay=null,lost=false
  if(mobile)await p.route('**/rest/v1/rpc/erp_cp7_save_nota_v1',async route=>{const body=route.request().postDataJSON();if(body.p_action==='POST'&&!lost){first=body;const result=await route.fetch();if(result.status()!==200)throw Error('Expected committed Nota before lost response');lost=true;await route.abort('failed')}else{if(body.p_action==='POST'&&replay===null)replay=body;await route.continue()}})
  await post.click();await ui.expect.poll(()=>fixture('read',f).notes[0]?.status,{timeout:20000}).toBe('POSTED')
  if(mobile){await ui.expect(panel.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible();await p.reload();await openPage(ui,p);await panel.getByRole('button',{name:'Reconcile transaksi',exact:true}).click();await ui.expect(panel.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0);if(!lost||JSON.stringify(first)!==JSON.stringify(replay))throw Error('Nota recovery changed intent, version or UUID');await search()}
  await ui.expect(panel.locator('.cnota-review')).toContainText('Masuk payroll')
  actual=fixture('read',f)
  if(actual.notes.length!==1||actual.payroll.length!==1||actual.payroll[0][1]!=='CALCULATED'||Number(actual.payroll[0][2])!==6000||actual.payroll[0][4]!==null||actual.allocated[0]!==2||actual.allocated[1]!==3||Number(actual.allocated[2])!==6000||JSON.stringify(actual.facts)!==JSON.stringify(f.facts))throw Error('Posted Nota differs from native oracle '+JSON.stringify(actual))
  if(mobile&&(await panel.innerText()).includes('Rp'))throw Error('Operational posted note exposed money')
  if(!mobile)await ui.expect(panel.locator('.cnota-total')).toHaveText('Rp6.000')
  await ui.expect.poll(()=>panel.evaluate(el=>{const b=el.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
  mkdirSync('cp6-proof/t3',{recursive:true});await p.evaluate(()=>window.scrollTo(0,0));await p.screenshot({path:`cp6-proof/t3/P12_NOTA_${mobile?'MOBILE':'DESKTOP'}.png`,fullPage:true})
  fixture('cancel',f);await p.getByRole('button',{name:'Muat ulang nota',exact:true}).click();await ui.expect(panel.locator('.cnota-review')).toContainText('Payroll dibatalkan');await ui.expect(panel.locator('.cnota-source')).toHaveCount(2)
  if(mobile){await p.route('**/rest/v1/rpc/erp_cp7_get_nota_workspace_v1',r=>r.abort('failed'));await p.getByRole('button',{name:'Muat ulang nota',exact:true}).click();await ui.expect(panel.locator('.cnota-source')).toHaveCount(0);await ui.expect(panel.locator('.cnota-review')).toHaveCount(0);await ui.expect(panel.locator('[role="alert"]').first()).toBeVisible()}
  return {status:'PASS',mobile,real_auth_browser_native_save_post:true,desktop_native_drag:!mobile,touch_button_fallback:mobile,two_complete_cards:true,component_qty:3,labor:'6000',native_calculated_not_paid:true,no_duplicate_fg_hpp_or_journal:true,native_cancel_control_not_connected_payroll_reverse:true,source_cards_return_after_cancel:true,ops_money_hidden:mobile?true:null,lost_reply_exact_uuid_payload_version:mobile?true:null,failed_refresh_retires_stale_cards:mobile?true:null,screenshot:`P12_NOTA_${mobile?'MOBILE':'DESKTOP'}.png`}
 }catch(error){
  const p=user.page,panel=p.locator('.cnota');mkdirSync('cp6-proof/t3',{recursive:true})
  // Synthetic fixture and public DTO only: never persist headers or Auth state.
  const direct=await user.rpc('erp_cp7_get_nota_workspace_v1',{p_section:'SOURCES',p_query:{contractor_id:f.contractor}})
  writeFileSync(`cp6-proof/t3/P12_NOTA_${mobile?'MOBILE':'DESKTOP'}_FAILURE.json`,JSON.stringify({error:String(error),panel:await panel.innerText().catch(()=>''),source:direct},null,2))
  await p.screenshot({path:`cp6-proof/t3/P12_NOTA_${mobile?'MOBILE':'DESKTOP'}_FAILURE.png`,fullPage:true});throw error
 }finally{await user.context.close()}
}
export async function cases(ui,today){return [['P12_NOTA_BROWSER_DESKTOP_DRAG',()=>compose(ui,today,false)],['P12_NOTA_BROWSER_MOBILE_RECOVERY',()=>compose(ui,today,true)]]}
