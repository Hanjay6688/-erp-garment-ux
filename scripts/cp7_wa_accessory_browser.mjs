import assert from 'node:assert/strict'
import {mkdirSync,writeFileSync} from 'node:fs'

// Additive OW-01 journeys. Native fixtures supply only BOM, planning metadata
// and the frozen analysis. The actual owner chooses the accessory forwarding
// checkbox, saves settings, types the key, and enables WA in the real UI.
export const ACCESSORY_BROWSER_IDS=['WAF_BROWSER_ACCESSORY_NEED_DESKTOP','WAF_BROWSER_ACCESSORY_NEED_MOBILE']
const LABEL='Kebutuhan aksesori perlu diperiksa (dari analisis)'
// The wire preserves PostgreSQL decimal scale. Accept only the exact expected
// quantity; displayed text and provider text still have their own strict checks.
export function assertAccessoryGross186(value){
 assert.equal(typeof value,'string')
 assert.equal(value.trim(),value)
 assert.match(value,/^186(?:\.0+)?$/)
}
const LOCAL_PREVIEW_RPCS=['erp_cp7_claim_reminder_v2','erp_cp7_finish_reminder_v2','erp_cp7_resolve_reminder_claim_v2']
const WATCH_RPCS=['erp_cp7_get_alerts_v1','erp_cp7_get_wa_settings_v1','erp_cp7_save_wa_settings_v1','erp_cp7_set_wa_key_v1',
 'erp_cp7_send_wa_test_v1','erp_cp7_resolve_wa_dispatch_v1',...LOCAL_PREVIEW_RPCS]

function unknownMessage(body,unit){
 const text=body.toLowerCase()
 assert.ok(text.includes('aksesori perlu diperiksa'),body)
 assert.ok(text.includes('jumlah tambahan belum diketahui'),body)
 assert.match(text,/\bbom(?:\s*\([^)]*\))?\s*186\b/)
 assert.ok(body.includes('BOM (perkiraan) 186 '+unit),body)
 assert.doesNotMatch(text,/(?:beli|membeli|tambahan)\s*[:=]?\s*186\b/)
}

async function journey(ui,mobile,h){
 const {fixture,openReminders,shot,watch,PHONE,KEY}=h
 const suffix=mobile?'MOBILE':'DESKTOP',shots=[]
 const prep=fixture('prepare',{})
 assert.equal(prep.test_reset,true)
 assert.match(prep.transport,/^http:\/\/fake-callmebot:8080\//)
 const user=await ui.login('OWNER',{label:'ow01-accessory-'+suffix.toLowerCase(),mobile}),page=user.page,w=watch(page,WATCH_RPCS)
 let panel=null
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  const source=fixture('accessory_need',{subject:user.user.id})
  assert.equal(source.no_WA_settings_written,true)
  assert.equal(fixture('state',{}).settings,null,'OW01_FIXTURE_PRESELECTED_WA_SETTINGS')
  await openReminders(ui,page)
  await page.getByRole('tab',{name:'Sambungan WhatsApp',exact:true}).click()
  panel=page.getByRole('region',{name:'Sambungan WhatsApp',exact:true})
  const settings=panel.getByRole('region',{name:'Pengaturan WhatsApp',exact:true})
  const save=settings.getByRole('button',{name:'Simpan pengaturan WhatsApp',exact:true})
  const checkbox=settings.getByLabel('Teruskan '+LABEL,{exact:true})
  await ui.expect(checkbox).toBeVisible()
  // Deliberately clear every checkbox, including all forwarding kinds. This
  // verifies that this user's UI choice creates the saved one-kind selection.
  for(const box of await settings.getByRole('checkbox').all())await box.uncheck()
  await ui.expect(checkbox).not.toBeChecked()
  await checkbox.check()
  await ui.expect(checkbox).toBeChecked()
  await settings.getByLabel('Nomor WA Bos',{exact:true}).fill(PHONE)
  await settings.getByLabel('Isi pesan WhatsApp',{exact:true}).selectOption('DETAILED')
  await settings.getByLabel('Analisis otomatis tiap (menit)',{exact:true}).fill('0')
  await settings.getByLabel('Ulangi pesan tiap (menit)',{exact:true}).fill('1440')
  for(const clear of await settings.getByRole('button',{name:/^Kosongkan jam ringkasan /}).all())if(await clear.isEnabled())await clear.click()
  await save.click()
  await ui.expect(settings.getByRole('status').filter({hasText:'Tersimpan (revisi 1).'})).toBeVisible()
  let state=fixture('state',{})
  assert.deepEqual([state.settings.actor,state.settings.kinds,state.settings.enabled,state.settings.digest_times,state.settings.quiet_enabled],
   [user.user.id,['ACCESSORY_NEED'],false,[],false])
  shots.push(await shot(ui,page,`OW01_${suffix}_ACCESSORY_CHECKBOX_SAVED.png`))
  const keyBox=panel.getByRole('region',{name:'Bagian kunci CallMeBot',exact:true}),keyInput=keyBox.getByLabel('Kunci CallMeBot',{exact:true})
  assert.equal(await keyInput.getAttribute('type'),'password')
  await keyInput.fill(KEY)
  await keyBox.getByRole('button',{name:'Simpan kunci CallMeBot',exact:true}).click()
  await ui.expect(keyBox.getByRole('status').filter({hasText:'Kunci tersimpan ('})).toBeVisible()
  await ui.expect(keyInput).toHaveValue('')
  assert.equal(fixture('state',{key:KEY}).key_matches,true)
  await settings.getByLabel('Nyalakan WhatsApp',{exact:true}).check()
  await save.click()
  await ui.expect(settings.getByRole('status').filter({hasText:'Tersimpan (revisi 2).'})).toBeVisible()
  state=fixture('state',{})
  assert.deepEqual([state.settings.actor,state.settings.kinds,state.settings.enabled],[user.user.id,['ACCESSORY_NEED'],true])
  const collected=fixture('accessory_need_collect',{proof:source.proof})
  assert.equal(collected.alert.episode,1)
  assertAccessoryGross186(collected.detail.gross_qty)
  assert.deepEqual([collected.detail.state,collected.detail.verdict,collected.detail.gross_state,
   collected.detail.installed_state,collected.detail.installed_proven,collected.detail.unused_allocated_state,collected.detail.unused_allocated_proven,
   collected.detail.additional_external_state,collected.detail.additional_external,collected.detail.threshold_status],
   ['DATA_REVIEW','REVIEW_REQUIRED_NOW','ASSUMED','UNKNOWN',null,'UNKNOWN',null,'UNKNOWN',null,'NOT_EVALUATED_UNKNOWN'])
  await page.getByRole('tab',{name:'Pengingat sistem',exact:true}).click()
  const sys=page.getByRole('region',{name:'Pengingat sistem',exact:true}),reload=sys.getByRole('button',{name:'Muat ulang pengingat sistem',exact:true})
  await ui.expect(reload).toBeEnabled();await reload.click()
  const group=sys.getByRole('region',{name:LABEL,exact:true})
  const row=group.getByRole('listitem',{name:'Pengingat sistem '+collected.alert.title,exact:true})
  await ui.expect(row).toBeVisible()
  await ui.expect(row).toContainText('jumlah tambahan belum diketahui')
  await ui.expect(row).toContainText('kebutuhan BOM (perkiraan) 186 '+collected.detail.unit)
  await ui.expect(row).toContainText('Pemasangan dan sisa yang dialokasikan belum terbukti')
  await ui.expect(row.locator('.csys-analysis-line')).toContainText('Data analisis per ')
  await ui.expect(row.locator('.csys-analysis-line')).toContainText(', dicek ulang ')
  assert.doesNotMatch(await row.innerText(),/(?:beli|membeli|tambahan)\s*[:=]?\s*186\b/i)
  shots.push(await shot(ui,page,`OW01_${suffix}_ACCESSORY_UNKNOWN.png`))
  const sent=fixture('tick',{name:'send_tick'})
  assert.equal(sent.outcome,'SENT',JSON.stringify(sent))
  const delivered=fixture('deliver',{dispatch:sent.dispatch_id})
  assert.equal(delivered.answered,true,'OW01_FAKE_PROVIDER_NO_ACCESSORY_ANSWER')
  assert.deepEqual([delivered.dispatch.kind,delivered.dispatch.status,delivered.dispatch.http],['INSTANT','PROVIDER_ACCEPTED',200])
  unknownMessage(delivered.dispatch.body,collected.detail.unit)
  state=fixture('state',{after:prep.fake_requests})
  assert.equal(state.fake.length,1,'OW01_ACCESSORY_BROWSER_PROVIDER_DUPLICATE')
  assert.equal(state.fake[0].phone,PHONE);assert.equal(state.fake[0].key_ok,true)
  assert.equal(state.fake[0].text,delivered.dispatch.body)
  const alert=state.alerts.find(a=>a.kind==='ACCESSORY_NEED'&&a.subject===source.condition_key)
  assert.ok(alert,'OW01_ACCESSORY_BROWSER_ALERT_MISSING')
  assert.deepEqual([alert.state,alert.outbox],['OPEN','ACCEPTED'])
  await reload.click()
  await ui.expect(row).toContainText('WA: terkirim')
  await ui.expect(row).toContainText('jumlah tambahan belum diketahui')
  shots.push(await shot(ui,page,`OW01_${suffix}_ACCESSORY_PROVIDER_ACCEPTED.png`))
  await page.getByRole('tab',{name:'Sambungan WhatsApp',exact:true}).click()
  await panel.getByRole('button',{name:'Muat ulang sambungan WhatsApp',exact:true}).click()
  const history=panel.getByRole('region',{name:'Riwayat pesan WhatsApp',exact:true})
  const item=history.getByRole('listitem',{name:'Pesan '+sent.dispatch_id,exact:true})
  await ui.expect(item).toContainText('Diterima CallMeBot')
  assert.equal(await item.getByLabel('Isi pesan '+sent.dispatch_id,{exact:true}).innerText(),state.fake[0].text)
  shots.push(await shot(ui,page,`OW01_${suffix}_ACCESSORY_HISTORY.png`))
  const answers=await w.texts()
  assert.equal(answers.filter(a=>a.status>=400).length,0,JSON.stringify(answers.filter(a=>a.status>=400).map(a=>[a.name,a.status])))
  assert.equal(answers.filter(a=>a.text.includes(KEY)).length,0,'OW01_KEY_RETURNED_IN_HTTP')
  assert.equal(w.sent.filter(r=>LOCAL_PREVIEW_RPCS.includes(r.name)).length,0,'OW01_BROWSER_USED_LOCAL_PREVIEW_WRITER')
  const sourceProof=fixture('accessory_need_source',{proof:source.proof})
  assert.deepEqual(sourceProof,{original_unchanged:true,local_claims:0,local_rechecks:0})
  const writes=w.sent.filter(r=>r.name==='erp_cp7_save_wa_settings_v1').map(r=>JSON.parse(r.body))
  assert.equal(writes.length,2)
  assert.deepEqual(writes.map(r=>r.p.kinds),[['ACCESSORY_NEED'],['ACCESSORY_NEED']])
  assert.deepEqual(writes.map(r=>r.p.enabled),[false,true])
  const settingsRequests=writes.map(r=>r.p_request)
  assert.equal(new Set(settingsRequests).size,2)
  assert.equal(w.sent.filter(r=>r.body.includes(KEY)).length,1)
  assert.equal((await page.content()).includes(KEY),false,'OW01_KEY_VISIBLE_IN_PAGE')
  const storage=await page.evaluate(()=>{const out=[];for(const s of[localStorage,sessionStorage])for(let i=0;i<s.length;i++)out.push(s.getItem(s.key(i)));return out.join('\n')})
  assert.equal(storage.includes(KEY),false,'OW01_KEY_IN_BROWSER_STORAGE')
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'OW01_ACCESSORY_HORIZONTAL_SCROLL')
  return{status:'PASS',phone:mobile,actual_checkbox_chosen_and_persisted:true,fixture_did_not_save_WA_settings:true,
   actual_Auth_and_PostgREST:true,provider_receipts:1,provider_body_equals_stored_history:true,gross_BOM_assumed:'186',
   additional_external:'UNKNOWN',physical_unknown_stays_unknown_after_delivery:true,no_local_preview_claim:true,no_horizontal_scroll:true,screenshots:shots,
   label:'Native source fixture; real UI settings; fake CallMeBot only'}
 }catch(error){
  writeFileSync(`cp6-proof/t3/OW01_${suffix}_FAILURE.json`,JSON.stringify({error:String(error),text:await(panel??page.locator('body')).innerText().catch(()=>'')},null,2))
  await page.screenshot({path:`cp6-proof/t3/OW01_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{})
  throw error
 }finally{
  try{fixture('restore',{})}catch{/* The disposable copy is removed by the harness. */}
  await user.context.close()
 }
}

export function accessoryCases(ui,helpers){
 return[[ACCESSORY_BROWSER_IDS[0],()=>journey(ui,false,helpers)],[ACCESSORY_BROWSER_IDS[1],()=>journey(ui,true,helpers)]]
}
