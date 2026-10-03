import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
import {cases as previous} from './cp7_cutting_input_browser.mjs'
import {openCutting,retiredPage} from './cp7_cutting_yield_browser.mjs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_cutting_learning_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const trim=v=>v.includes('.')?v.replace(/0+$/,'').replace(/\.$/,''):v
async function select(ui,page,f,mobile) {
  await openCutting(ui,page,mobile)
  await page.getByLabel('Cari draft Potongan',{exact:true}).fill(f.group_number)
  const response=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_get_cutting_workspace_v2')&&r.request().postDataJSON().p_draft_query===f.group_number)
  await page.getByRole('button',{name:'Cari draft',exact:true}).click();assert.equal((await response).status(),200)
  await page.locator('.ccut-drafts button').filter({hasText:f.group_number}).click()
}
async function image(ui,page,name) {
  mkdirSync('cp6-proof/t3',{recursive:true});await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
  await page.screenshot({path:'cp6-proof/t3/'+name,fullPage:true})
}
async function journey(ui,today,mobile,cohort) {
  const user=await ui.login('OWNER',{label:'cut-learning-'+mobile+'-'+cohort,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,actor=user.user.id
  const f=fixture('prepare',{today,actor,cohort}),state=()=>fixture('state',{fixture:f,actor}),panel=page.getByRole('region',{name:'Belajar dari hasil potong',exact:true}),suffix=(cohort?'MODEL':'OBSERVATION')+'_'+(mobile?'MOBILE':'DESKTOP')
  let lost=null
  try {
    await select(ui,page,f,mobile)
    const notes=page.getByLabel('Catatan',{exact:true});await notes.fill('CATATAN OPERATOR TETAP')
    const before=state()
    const source=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_get_cutting_model_workspace_v1'))
    await panel.getByRole('button',{name:'Muat penilaian potong',exact:true}).click();assert.equal((await source).status(),200)
    await ui.expect(panel.getByRole('button',{name:cohort?'Nilai hasil potong':'Catat aturan belajar potong',exact:true})).toBeAttached()
    assert.equal(state().native_hash,before.native_hash);assert.equal(await notes.inputValue(),'CATATAN OPERATOR TETAP')
    let command,commandName,expectedRequests
    if(cohort) {commandName='erp_cp7_capture_cutting_model_v1';command='Nilai hasil potong';expectedRequests=2}
    else {
      for(const [label,value] of [['Target cakupan (antara 0 dan 1)','0.75'],['Jumlah kejadian belajar','3'],['Jumlah kejadian kalibrasi','4'],['Jumlah kejadian pemeriksaan terpisah','3']]) await panel.getByLabel(label,{exact:true}).fill(value)
      await panel.getByRole('checkbox',{name:'Saya sudah memeriksa aturan belajar ini.',exact:true}).check()
      const saved=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_capture_cutting_model_v1'))
      await panel.getByRole('button',{name:'Catat aturan belajar potong',exact:true}).click();assert.equal((await saved).status(),200)
      await ui.expect(panel.locator('[data-cutting-policy]')).toContainText('kelompok belajar 3')
      assert.equal(state().native_hash,before.native_hash);assert.equal(state().policies,1)
      fixture('post',{fixture:f});const afterPost=state();assert.equal(afterPost.group.material_issue_posted,true)
      await panel.getByRole('button',{name:'Periksa sumber penilaian',exact:true}).click()
      await ui.expect(panel.getByRole('button',{name:'Catat hasil nyata potong',exact:true})).toBeEnabled()
      commandName='erp_cp7_capture_cutting_observation_v1';command='Catat hasil nyata potong';expectedRequests=1
    }
    const economicBefore=state()
    if(mobile) await page.route('**/rest/v1/rpc/'+commandName,async route=>{
      const result=await route.fetch();lost={args:route.request().postDataJSON(),status:result.status(),body:await result.json()};await route.abort('failed')
    })
    const response=mobile?null:page.waitForResponse(r=>r.url().endsWith('/rpc/'+commandName))
    await panel.getByRole('button',{name:command,exact:true}).click()
    let body
    if(mobile) {
      await ui.expect.poll(()=>lost?.status).toBe(200);await ui.expect(panel.getByRole('button',{name:'Pulihkan penilaian potong',exact:true})).toBeEnabled()
      assert.equal(state().native_hash,economicBefore.native_hash)
      await page.unroute('**/rest/v1/rpc/'+commandName);await page.reload();await openCutting(ui,page,mobile)
      const recovered=page.waitForResponse(r=>r.url().endsWith('/rpc/'+(cohort?'erp_cp7_get_cutting_model_request_v1':'erp_cp7_get_cutting_observation_request_v1')))
      await panel.getByRole('button',{name:'Pulihkan penilaian potong',exact:true}).click();const reply=await recovered
      assert.equal(reply.status(),200);assert.deepEqual(reply.request().postDataJSON(),lost.args);body=await reply.json();assert.deepEqual(body.result,lost.body.result)
    } else {const reply=await response;assert.equal(reply.status(),200);body=await reply.json()}
    if(cohort) {
      const e=body.result.model.evaluation;assert.equal(e.basis,'WITH_RECORDED_WIDTH');assert.equal(Number(e.interval.center_pcs),51)
      assert.deepEqual(['train_rows','calibration_rows','holdout_rows'].map(k=>new Set(e[k].map(x=>x.batch_key)).size),[3,4,3])
      await ui.expect(panel.locator('[data-cutting-assessment]')).toContainText('Rentang empiris '+trim(e.interval.lower_pcs)+'–'+trim(e.interval.upper_pcs)+' pcs; tengah 51 pcs.')
      await ui.expect(panel.locator('[data-cutting-assessment]')).toContainText('Hasil fisik belum diposting')
      assert.equal(state().model_requests,expectedRequests)
      if(mobile) {
        await select(ui,page,f,mobile)
        await panel.getByRole('button',{name:'Muat penilaian potong',exact:true}).click()
        await ui.expect(panel.getByRole('button',{name:'Nilai hasil potong',exact:true})).toBeEnabled()
        await panel.getByRole('button',{name:'Nilai hasil potong',exact:true}).click()
        await ui.expect(panel.locator('[data-cutting-assessment]')).toContainText('tengah 51 pcs')
      }
      const inputPanel=page.getByRole('region',{name:'Rencana bahan sebelum potong',exact:true})
      await inputPanel.getByRole('button',{name:'Muat rencana potong',exact:true}).click()
      await inputPanel.getByRole('button',{name:'Isi formulir dari catatan ini',exact:true}).click()
      await inputPanel.getByLabel('Lebar tercatat (cm) · '+f.roll.slice(0,8),{exact:true}).fill('')
      await inputPanel.getByRole('checkbox',{name:'Saya sudah memeriksa bahan dan susunan ukuran.',exact:true}).check()
      const changed=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_record_cutting_inputs_v1'))
      await inputPanel.getByRole('button',{name:'Catat rencana potong',exact:true}).click()
      assert.equal((await changed).status(),200)
      await ui.expect(panel.locator('[data-cutting-assessment]')).toHaveCount(0)
      await panel.getByRole('button',{name:'Muat penilaian potong',exact:true}).click()
      await ui.expect(panel).toContainText('lebar belum dicatat')
      const baseline=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_capture_cutting_model_v1'))
      await panel.getByRole('button',{name:'Nilai hasil potong',exact:true}).click();const revised=await baseline;assert.equal(revised.status(),200);const base=(await revised.json()).result.model.evaluation
      assert.equal(base.basis,'WITHOUT_WIDTH');assert.equal(Number(base.interval.lower_pcs),48);assert.equal(Number(base.interval.upper_pcs),54)
      await ui.expect(panel.locator('[data-cutting-assessment]')).toContainText('48–54 pcs')
    } else {
      assert.equal(body.result.observation.records[0].native_valid,true)
      assert.equal(Number(body.result.observation.records[0].actual_pcs),60)
      assert.equal(state().observations,1);assert.equal(state().observation_requests,expectedRequests)
      // Recovery without a selected draft remains usable via its own sealed request.
      await ui.expect(panel.locator('[data-cutting-observation]')).toContainText('60 pcs')
    }
    assert.equal(state().native_hash,economicBefore.native_hash)
    await image(ui,page,'CUT_LEARNING_'+suffix+'.png')
    {
      await notes.fill('ISIAN SAAT IZIN DIPERIKSA');fixture('deactivate',{actor});const revoked=state(),fresh=page.waitForRequest(r=>r.url().endsWith('/rpc/erp_cp7_get_cutting_input_workspace_v1'))
      await panel.getByRole('button',{name:'Periksa sumber penilaian',exact:true}).click();const denied=await (await fresh).response();assert.equal(denied.status(),403)
      await ui.expect(panel.locator('[data-cutting-assessment]')).toHaveCount(0);await ui.expect(panel.locator('[data-cutting-policy]')).toHaveCount(0);await retiredPage(ui,page,notes);assert.equal(state().native_hash,revoked.native_hash)
    }
    return {current403_retires_parent_siblings_and_preserves_own_notes:true,status:'PASS',mobile,actual_Native_cohort:cohort,real_clock_prospective_policy_and_POST_observation:!cohort,exact_lost_UUID_and_Original:mobile,complete_disjoint3_4_3_width51_and_unknown_width48_54:cohort,no_Native_stock_cash_AR_HPP_write:true,current403_and_old_quantitative_retirement:true,screenshot:'CUT_LEARNING_'+suffix+'.png'}
  } catch(e) {mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync('cp6-proof/t3/CUT_LEARNING_'+suffix+'_FAILURE.json',JSON.stringify({error:String(e),stack:e.stack,text:await panel.innerText().catch(()=>''),parent_text:await page.locator('.connected-cutting-page').innerText().catch(()=>''),lost},null,2));await page.screenshot({path:'cp6-proof/t3/CUT_LEARNING_'+suffix+'_FAILURE.png',fullPage:true}).catch(()=>{});throw e}
  finally {fixture('restore',{actor});await user.context.close()}
}
export function cases(ui,today){return previous(ui,today).concat([
 ['CUT_LEARNING_MODEL_DESKTOP',()=>journey(ui,today,false,true)],['CUT_LEARNING_MODEL_MOBILE',()=>journey(ui,today,true,true)],
 ['CUT_LEARNING_OBSERVATION_DESKTOP',()=>journey(ui,today,false,false)],['CUT_LEARNING_OBSERVATION_MOBILE',()=>journey(ui,today,true,false)]
])}
