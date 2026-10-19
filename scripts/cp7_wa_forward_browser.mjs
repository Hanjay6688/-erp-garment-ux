import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
// WA-4b (owner D17-3..D17-6) in the real UI, real Auth and PostgREST on the committed browser copy; the provider is only the
// fake CallMeBot of the CI stack (test number +620000000000, a FAKEKEY-* key). Each owner journey starts from a copy whose
// WhatsApp module was reset (TEST_RESET, labelled, cp7_wa_forward_browser_fixture.py prepare): Reminder -> Pengingat
// sistem says it is not running yet and offers the WhatsApp tab; the owner saves the number (quiet hours and digest times
// cleared, so the run does not depend on the hour), types the key into the password box (it is never shown, stored in the
// browser or answered back; Vault holds exactly that key), sends a test message that the fake server receives, switches
// WhatsApp on, and a fabric below its minimum is collected and sent by the server ticks (run by the fixture as pg_cron runs
// them); Pengingat sistem shows it with "WA: terkirim" and Riwayat pesan shows the exact text the fake server received.
// Desktop 1440 px and phone 390 px, no horizontal page scroll. An ADMIN account sees Pengingat sistem without the WhatsApp
// tab, WhatsApp chips or any call to the owner's WhatsApp functions, and is refused when calling one directly.
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_wa_forward_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const PHONE='+620000000000',KEY='FAKEKEY-WA3B'
const OWNER_RPCS=['erp_cp7_get_wa_settings_v1','erp_cp7_save_wa_settings_v1','erp_cp7_set_wa_key_v1','erp_cp7_send_wa_test_v1','erp_cp7_resolve_wa_dispatch_v1']
const RPCS=['erp_cp7_get_alerts_v1',...OWNER_RPCS]
const KIND_LABEL={FABRIC_BELOW_MINIMUM:'Stok kain di bawah minimum',AR_DUE:'Piutang pelanggan jatuh tempo',AP_DUE:'Tagihan supplier jatuh tempo',
 PRODUCTION_GAP:'Kekurangan produksi (dari analisis)',FABRIC_NEED:'Kain perlu dibeli (dari analisis)'}
async function openSidebar(page){const open=page.getByRole('button',{name:'Buka menu',exact:true});if(await open.isVisible())await open.click()}
async function openReminders(ui,page){
 await openSidebar(page)
 const link=page.getByRole('button',{name:'• Reminder',exact:true})
 if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Pengaturan & Audit'}).click()
 await link.click();await ui.expect(page.getByRole('heading',{name:'Pengingat',exact:true})).toBeVisible()
}
async function shot(ui,page,name){await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:'cp6-proof/t3/'+name,fullPage:true});return name}
// Every request to the module's public functions (body as sent) and every answer (status and text), in order.
function watch(page){
 const sent=[],answers=[]
 page.on('request',r=>{const name=RPCS.find(n=>r.url().endsWith('/rpc/'+n));if(name)sent.push({name,body:r.postData()??''})})
 page.on('response',r=>{const name=RPCS.find(n=>r.url().endsWith('/rpc/'+n));if(name)answers.push({name,status:r.status(),text:r.text().catch(()=>'')})})
 const texts=async()=>{for(const a of answers)if(typeof a.text!=='string')a.text=await a.text;return answers}
 return{sent,answers,texts}
}
const tabNames=page=>page.getByRole('tablist',{name:'Bagian pengingat',exact:true}).getByRole('tab')
async function ownerJourney(ui,mobile){
 const suffix=mobile?'MOBILE':'DESKTOP',shots=[]
 const prep=fixture('prepare',{});assert.equal(prep.test_reset,true);assert.match(prep.transport,/^http:\/\/fake-callmebot:8080\//)
 const user=await ui.login('OWNER',{label:'waf-'+suffix.toLowerCase(),mobile}),page=user.page,w=watch(page)
 let wa=null
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  await openReminders(ui,page)
  await ui.expect(tabNames(page)).toHaveText(['Pengingat saya','Pengingat sistem','Sambungan WhatsApp'])
  // Before any save: the system reminders say they are not running, and offer the owner the WhatsApp tab.
  await page.getByRole('tab',{name:'Pengingat sistem',exact:true}).click()
  const sys=page.getByRole('region',{name:'Pengingat sistem',exact:true})
  await ui.expect(sys.getByRole('note').filter({hasText:'Pengingat sistem belum berjalan.'})).toBeVisible()
  await sys.getByRole('button',{name:'Buka tab Sambungan WhatsApp',exact:true}).click()
  wa=page.getByRole('region',{name:'Sambungan WhatsApp',exact:true})
  const status=wa.getByRole('region',{name:'Status sambungan',exact:true})
  await ui.expect(status).toContainText('Belum pernah disimpan');await ui.expect(status).toContainText('Belum ada kunci');await ui.expect(status).toContainText('Belum diisi')
  await ui.expect(wa.getByRole('note').filter({hasText:'Alamat uji (bukan CallMeBot)'})).toBeVisible()
  const testBox=wa.getByRole('region',{name:'Pesan uji',exact:true}),sendTest=testBox.getByRole('button',{name:'Kirim pesan uji ke WhatsApp Bos',exact:true})
  await ui.expect(sendTest).toBeDisabled();await ui.expect(testBox).toContainText('Simpan nomor WA Bos di Pengaturan dulu.')
  // Settings: the number; quiet hours and digest times cleared, so nothing waits for the hour the run happens at.
  const settings=wa.getByRole('region',{name:'Pengaturan WhatsApp',exact:true}),save=settings.getByRole('button',{name:'Simpan pengaturan WhatsApp',exact:true})
  await settings.getByLabel('Nomor WA Bos',{exact:true}).fill(PHONE)
  await settings.getByLabel('Pakai jam tenang',{exact:true}).uncheck()
  for(const i of[1,2]){const clear=settings.getByRole('button',{name:'Kosongkan jam ringkasan '+i,exact:true});if(await clear.isEnabled())await clear.click()}
  await save.click();await ui.expect(settings.getByRole('status').filter({hasText:'Tersimpan (revisi 1).'})).toBeVisible()
  let st=fixture('state',{key:KEY})
  assert.deepEqual([st.settings.revision,st.settings.enabled,st.settings.phone,st.settings.quiet_enabled,st.settings.digest_times,st.key_matches],[1,false,PHONE,false,[],false])
  assert.equal(st.settings.actor,user.user.id)
  shots.push(await shot(ui,page,`WAF_${suffix}_SETTINGS_SAVED.png`))
  // The key: typed once into the password box, sent once, the box emptied, never shown again.
  const keyBox=wa.getByRole('region',{name:'Bagian kunci CallMeBot',exact:true}),keyInput=keyBox.getByLabel('Kunci CallMeBot',{exact:true})
  assert.equal(await keyInput.getAttribute('type'),'password')
  await keyInput.fill(KEY);await keyBox.getByRole('button',{name:'Simpan kunci CallMeBot',exact:true}).click()
  await ui.expect(keyBox.getByRole('status').filter({hasText:'Kunci tersimpan ('})).toBeVisible()
  await ui.expect(keyInput).toHaveValue('');await ui.expect(status).toContainText('Kunci tersimpan sejak')
  st=fixture('state',{key:KEY});assert.equal(st.key_matches,true,'WAF_VAULT_KEY_NOT_THE_TYPED_ONE')
  // The test message reaches the fake server; its answer is recorded by the next send tick.
  await ui.expect(sendTest).toBeEnabled();await sendTest.click()
  const queued=testBox.getByRole('status').filter({hasText:'Pesan uji masuk antrean kirim (pesan nomor '});await ui.expect(queued).toBeVisible()
  const testId=Number((await queued.innerText()).match(/pesan nomor (\d+)\)/)[1])
  const test=fixture('deliver',{dispatch:testId});assert.equal(test.answered,true,'WAF_FAKE_NEVER_ANSWERED_TEST')
  assert.deepEqual([test.dispatch.kind,test.dispatch.status,test.dispatch.http],['TEST','PROVIDER_ACCEPTED',200])
  st=fixture('state',{after:prep.fake_requests})
  assert.equal(st.fake.length,1,JSON.stringify(st.fake.map(f=>f.status)));assert.equal(st.fake[0].phone,PHONE);assert.equal(st.fake[0].key_ok,true)
  assert.equal(st.fake[0].text,test.dispatch.body);assert.ok(st.fake[0].text.startsWith('✅ Pesan uji ERP Enteng'))
  await wa.getByRole('button',{name:'Muat ulang sambungan WhatsApp',exact:true}).click()
  const history=wa.getByRole('region',{name:'Riwayat pesan WhatsApp',exact:true}),testItem=history.getByRole('listitem',{name:'Pesan '+testId,exact:true})
  await ui.expect(testItem).toContainText('Pesan uji · nomor '+testId);await ui.expect(testItem).toContainText('Diterima CallMeBot')
  assert.equal(await testItem.getByLabel('Isi pesan '+testId,{exact:true}).innerText(),st.fake[0].text)
  await ui.expect(testItem).toContainText('Jawaban CallMeBot:')
  shots.push(await shot(ui,page,`WAF_${suffix}_TEST_ACCEPTED.png`))
  // WhatsApp on.
  await settings.getByLabel('Nyalakan WhatsApp',{exact:true}).check();await save.click()
  await ui.expect(settings.getByRole('status').filter({hasText:'Tersimpan (revisi 2).'})).toBeVisible()
  await ui.expect(status.getByText('Menyala',{exact:true})).toBeVisible()
  assert.equal(fixture('state',{}).settings.enabled,true)
  // A fabric below its minimum: collected and sent by the server, received by the fake server.
  const mat=fixture('fabric',{minimum:55,label:'WA4B'+suffix.slice(0,1)})
  assert.equal(fixture('tick',{name:'collect_tick'}).outcome,'COLLECTED')
  const sent=fixture('tick',{name:'send_tick'});assert.equal(sent.outcome,'SENT',JSON.stringify(sent))
  const instant=fixture('deliver',{dispatch:sent.dispatch_id});assert.equal(instant.answered,true,'WAF_FAKE_NEVER_ANSWERED_INSTANT')
  assert.deepEqual([instant.dispatch.kind,instant.dispatch.status,instant.dispatch.http],['INSTANT','PROVIDER_ACCEPTED',200])
  st=fixture('state',{after:prep.fake_requests})
  const alert=st.alerts.find(a=>a.kind==='FABRIC_BELOW_MINIMUM'&&a.subject===mat.material_id)
  assert.ok(alert,'WAF_FABRIC_ALERT_MISSING');assert.deepEqual([alert.state,alert.outbox],['OPEN','ACCEPTED'])
  assert.equal(st.fake.length,2);assert.equal(st.fake[1].phone,PHONE);assert.equal(st.fake[1].key_ok,true);assert.equal(st.fake[1].text,instant.dispatch.body)
  assert.ok(instant.dispatch.body.includes('Stok kain di bawah minimum ('),instant.dispatch.body)
  // Pengingat sistem: the alert with its WhatsApp state.
  await page.getByRole('tab',{name:'Pengingat sistem',exact:true}).click()
  await sys.getByRole('button',{name:'Muat ulang pengingat sistem',exact:true}).click()
  const group=sys.getByRole('region',{name:KIND_LABEL.FABRIC_BELOW_MINIMUM,exact:true}),row=group.getByRole('listitem',{name:'Pengingat sistem '+alert.title,exact:true}).first()
  await ui.expect(row).toBeVisible();await ui.expect(row).toContainText('WA: terkirim')
  await ui.expect(sys.getByRole('note').filter({hasText:'Pengingat sistem belum berjalan.'})).toHaveCount(0)
  shots.push(await shot(ui,page,`WAF_${suffix}_SYSTEM_FORWARDED.png`))
  // Riwayat pesan: the instant message, the exact text the fake server received.
  await page.getByRole('tab',{name:'Sambungan WhatsApp',exact:true}).click()
  await wa.getByRole('button',{name:'Muat ulang sambungan WhatsApp',exact:true}).click()
  const item=history.getByRole('listitem',{name:'Pesan '+sent.dispatch_id,exact:true})
  await ui.expect(item).toContainText('Pesan langsung · nomor '+sent.dispatch_id);await ui.expect(item).toContainText('Diterima CallMeBot')
  assert.equal(await item.getByLabel('Isi pesan '+sent.dispatch_id,{exact:true}).innerText(),instant.dispatch.body)
  shots.push(await shot(ui,page,`WAF_${suffix}_HISTORY.png`))
  // The key went out once, in its own request, and came back nowhere: no answer, no page text, no browser storage.
  const answers=await w.texts()
  assert.equal(w.sent.filter(r=>r.body.includes(KEY)).length,1);assert.equal(w.sent.find(r=>r.body.includes(KEY)).name,'erp_cp7_set_wa_key_v1')
  assert.equal(answers.filter(a=>a.text.includes(KEY)).length,0,'WAF_KEY_IN_AN_ANSWER')
  assert.equal(answers.filter(a=>a.status>=400).length,0,JSON.stringify(answers.filter(a=>a.status>=400).map(a=>[a.name,a.status])))
  assert.equal((await page.content()).includes(KEY),false,'WAF_KEY_ON_THE_PAGE')
  const stored=await page.evaluate(()=>{const all=[];for(const s of[localStorage,sessionStorage])for(let i=0;i<s.length;i++){const k=s.key(i);all.push(k+'='+s.getItem(k))}return all.join('\n')})
  assert.equal(stored.includes(KEY),false,'WAF_KEY_IN_BROWSER_STORAGE');assert.equal(stored.includes(PHONE),false,'WAF_PHONE_IN_BROWSER_STORAGE')
  const writes=w.sent.filter(r=>r.name!=='erp_cp7_get_wa_settings_v1'&&r.name!=='erp_cp7_get_alerts_v1').map(r=>JSON.parse(r.body).p_request)
  assert.equal(writes.length,4);assert.equal(new Set(writes).size,4)
  return{status:'PASS',phone:mobile,test_reset:true,first_save_starts_system_reminders:true,key_typed_once_never_returned:true,vault_holds_typed_key:true,
   test_message_received_by_fake:true,instant_message_received_by_fake:true,history_text_equals_received:true,system_reminder_wa_chip:'WA: terkirim',
   distinct_request_ids:4,quiet_hours_and_digest_cleared:true,no_horizontal_scroll:true,screenshots:shots,label:'TEST_RESET; fake CallMeBot only'}
 }catch(e){writeFileSync(`cp6-proof/t3/WAF_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),text:await (wa??page.locator('body')).innerText().catch(()=>'')},null,2));await page.screenshot({path:`cp6-proof/t3/WAF_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{try{fixture('restore',{})}catch{/* the case already failed; the copy is dropped after the run */}await user.context.close()}
}
async function adminJourney(ui){
 const prep=fixture('prepare',{});assert.equal(prep.test_reset,true)
 const configured=fixture('configure',{});assert.equal(configured.collect,'COLLECTED')
 const user=await ui.login('ADMIN',{label:'waf-admin'}),page=user.page,w=watch(page)
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  const st=fixture('state',{subject:user.user.id})
  await openReminders(ui,page)
  await ui.expect(tabNames(page)).toHaveText(['Pengingat saya','Pengingat sistem'])
  await page.getByRole('tab',{name:'Pengingat sistem',exact:true}).click()
  const sys=page.getByRole('region',{name:'Pengingat sistem',exact:true})
  await ui.expect(sys.getByRole('button',{name:'Muat ulang pengingat sistem',exact:true})).toBeEnabled()
  await ui.expect(sys.getByRole('note').filter({hasText:'Pengingat sistem belum berjalan.'})).toHaveCount(0)
  // The groups are exactly the kinds this account may read through the source screens' permissions.
  const groups=st.visible.map(k=>KIND_LABEL[k])
  for(const label of groups)await ui.expect(sys.getByRole('region',{name:label,exact:true})).toBeVisible()
  for(const [k,label] of Object.entries(KIND_LABEL))if(!st.visible.includes(k))await ui.expect(sys.getByRole('region',{name:label,exact:true})).toHaveCount(0)
  const open=st.alerts.filter(a=>a.state==='OPEN'&&st.visible.includes(a.kind))
  for(const a of open.slice(0,5))await ui.expect(sys.getByRole('listitem',{name:'Pengingat sistem '+a.title,exact:true}).first()).toBeVisible()
  await ui.expect(sys.getByText(/^WA: /)).toHaveCount(0)
  await ui.expect(page.getByRole('region',{name:'Sambungan WhatsApp',exact:true})).toHaveCount(0)
  assert.deepEqual([...new Set(w.sent.map(r=>r.name))],['erp_cp7_get_alerts_v1'])
  const refused=await user.rpc('erp_cp7_get_wa_settings_v1',{})
  assert.ok(refused.status>=400&&JSON.stringify(refused.body).includes('CP7_WA_OWNER_ONLY'),JSON.stringify(refused))
  await shot(ui,page,'WAF_ADMIN_SYSTEM_REMINDERS.png')
  return{status:'PASS',tabs:['Pengingat saya','Pengingat sistem'],visible_kinds:st.visible,open_rows_checked:Math.min(open.length,5),wa_chips:0,
   owner_rpcs_called:0,direct_owner_rpc_refused:refused.status,screenshots:['WAF_ADMIN_SYSTEM_REMINDERS.png'],label:'TEST_RESET'}
 }catch(e){await page.screenshot({path:'cp6-proof/t3/WAF_ADMIN_FAILURE.png',fullPage:true}).catch(()=>{});throw e}
 finally{try{fixture('restore',{})}catch{/* the case already failed; the copy is dropped after the run */}await user.context.close()}
}
export function cases(ui){
 return[['WAF_BROWSER_DESKTOP_OWNER_SETS_UP_TESTS_AND_FORWARDS',()=>ownerJourney(ui,false)],['WAF_BROWSER_MOBILE_OWNER_SETS_UP_TESTS_AND_FORWARDS',()=>ownerJourney(ui,true)],
  ['WAF_BROWSER_ADMIN_SEES_SYSTEM_REMINDERS_WITHOUT_WA',()=>adminJourney(ui)]]
}
