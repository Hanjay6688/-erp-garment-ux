import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_p13_recost_fixture.py',op,JSON.stringify(p)],{cwd:'../writer',encoding:'utf8'}).trim())
async function open(ui,p){
 await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:'Keuangan'})).toBeAttached();const menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=p.getByRole('button',{name:'• HPP & Rekalkulasi',exact:true});if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Keuangan'}).click();await link.click()
 await ui.expect(p.getByRole('heading',{name:'HPP per SKU',exact:true})).toBeVisible()
}
async function recost(ui,today,mobile){
 const f=fixture('prepare',{today}),before=fixture('read',f),user=await ui.login('OWNER',{label:'p13-recost-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),p=user.page,suffix=mobile?'MOBILE':'DESKTOP',panel=p.getByRole('region',{name:'Antrean hitung ulang HPP',exact:true})
 try{
  await open(ui,p);await ui.expect(panel).toContainText('Siap dicoba sekarang: 1.')
  await panel.getByLabel('Alasan hitung ulang',{exact:true}).fill('Browser recost '+suffix);await panel.getByLabel('Saya sudah memeriksa antrean dan dampak perubahan biaya.',{exact:true}).check()
  let lost=false,first=null,replay=null
  if(mobile)await p.route('**/rest/v1/rpc/erp_cp7_process_recost_v1',async route=>{const body=route.request().postDataJSON();if(!lost){first=body;const response=await route.fetch();if(response.status()!==200){await route.fulfill({response});return}lost=true;await route.abort('failed')}else{replay=body;await route.continue()}})
  const action=panel.getByRole('button',{name:'Proses maksimal 20 pekerjaan',exact:true});await ui.expect(action).toBeEnabled();await action.click()
  await ui.expect.poll(()=>fixture('read',f).values).toEqual({hpp:90,fg:54,cogs:36})
  if(mobile){await ui.expect(panel.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible();await p.reload();await open(ui,p);await panel.getByRole('button',{name:'Reconcile transaksi',exact:true}).click();await ui.expect(panel.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0);assert.ok(lost);assert.deepEqual(replay,first)}
  await ui.expect(panel).toContainText('menyelesaikan 1 pekerjaan');await ui.expect(panel).toContainText('Tidak ada pekerjaan antrean terbuka.');await ui.expect(action).toBeDisabled()
  const after=fixture('read',f);assert.deepEqual(after.stock,before.stock);assert.deepEqual(after.report.filing,f.original);assert.deepEqual(after.report.snapshot.financial_position,f.position);assert.equal(Number(after.attempts)-Number(before.attempts),1);assert.equal(after.report.snapshot.data_confidence.status,'READY');assert.equal(after.report.snapshot.data_confidence.changed_since_filing,true)
  await ui.expect.poll(()=>panel.evaluate(el=>{const r=el.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
  mkdirSync('cp6-proof/t3',{recursive:true});await p.evaluate(()=>scrollTo(0,0));await p.screenshot({path:`cp6-proof/t3/P13_RECOST_${suffix}.png`,fullPage:true})
  await p.route('**/rest/v1/rpc/erp_cp7_get_recost_queue_v1',route=>route.abort('failed'));await panel.getByRole('button',{name:'Muat ulang antrean HPP',exact:true}).click();await ui.expect(panel.getByRole('alert')).toBeVisible();await ui.expect(action).toHaveCount(0)
  return {status:'PASS',mobile,actual_browser_native_recost:true,native_cost85_to90_FG51_to54_COGS34_to36:true,physical_movements_and_closed_day_GL_unchanged:true,original_filing_immutable:true,exact_lost_request_replay:mobile?true:null,one_native_queue_attempt:true,failed_queue_read_retires_actions:true,screenshot:`P13_RECOST_${suffix}.png`}
 }catch(e){mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync(`cp6-proof/t3/P13_RECOST_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await panel.innerText().catch(()=>''),native:fixture('read',f)},null,2));throw e}
 finally{await user.context.close()}
}
export async function cases(ui,today){return [['P13_RECOST_BROWSER_DESKTOP',()=>recost(ui,today,false)],['P13_RECOST_BROWSER_MOBILE_RECOVERY',()=>recost(ui,today,true)]]}
