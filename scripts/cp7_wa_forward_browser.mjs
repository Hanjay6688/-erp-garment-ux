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
// SS-1: the server shows FG_AT_REORDER_POINT to every account with warehouse.fg.view, so the admin case needs its group name.
// SS-2/SS-3 likewise for the fabric and accessory reorder kinds (Bahan & Roll with Kain & Benchmark; Aksesori).
const KIND_LABEL={FABRIC_BELOW_MINIMUM:'Stok kain di bawah minimum',FABRIC_AT_REORDER_POINT:'Stok kain menipis',ACCESSORY_AT_REORDER_POINT:'Stok aksesori menipis',
 FG_AT_REORDER_POINT:'Stok barang jadi menipis',AR_DUE:'Piutang pelanggan jatuh tempo',AP_DUE:'Tagihan supplier jatuh tempo',
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
function watch(page,names=RPCS){
 const sent=[],answers=[]
 page.on('request',r=>{const name=names.find(n=>r.url().endsWith('/rpc/'+n));if(name)sent.push({name,body:r.postData()??''})})
 page.on('response',r=>{const name=names.find(n=>r.url().endsWith('/rpc/'+n));if(name)answers.push({name,status:r.status(),text:r.text().catch(()=>'')})})
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
// SS-1 (owner D17-8, D17-9): Titik pesan ulang on Ringkasan Barang Jadi, real UI, Auth and PostgREST on the browser copy. The
// fixture makes one finished good at or under its formula point with the Native commands (cp7_stock_formula_cases: stock
// found at opname, PATTERN sold and posted, profile lead time 7 days); the owner presses "Hitung sekarang", finds it by SKU,
// sees "Perlu produksi" with the fixture's free stock and the oracle's point, sets a manual point one under the free stock
// (the item becomes "Aman"; the evaluation says MANUAL at manual revision 1), then removes it (the formula point again,
// revision 2). Desktop 1440 px and phone 390 px, no horizontal page scroll.
const FG_RPCS=['erp_cp7_get_fg_reorder_v1','erp_cp7_refresh_fg_reorder_v1','erp_cp7_save_fg_reorder_manual_v1','erp_cp7_save_stock_formula_settings_v1']
const whole=n=>new Intl.NumberFormat('id-ID').format(n),pcs=n=>whole(n)+' pcs'
async function openFgSummary(ui,page){
 await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).waitFor({state:'attached'})
 await openSidebar(page)
 const link=page.getByRole('button',{name:'• Ringkasan Barang Jadi',exact:true})
 if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click()
 await link.click();await ui.expect(page.getByRole('heading',{name:'Barang jadi',exact:true})).toBeVisible()
}
const noScroll=(ui,page)=>ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
async function fgReorderJourney(ui,mobile){
 const suffix=mobile?'MOBILE':'DESKTOP',shots=[],reason='WAF FG browser '+suffix.toLowerCase()
 const item=fixture('fg',{stock:140})
 assert.ok(Number.isInteger(item.point)&&Number.isInteger(item.free)&&item.free>=2&&item.free<=item.point,JSON.stringify(item))
 const manual=item.free-1
 const user=await ui.login('OWNER',{label:'waf-fg-'+suffix.toLowerCase(),mobile}),page=user.page,w=watch(page,FG_RPCS)
 let panel=null
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  await openFgSummary(ui,page)
  panel=page.getByRole('region',{name:'Titik pesan ulang',exact:true})
  await ui.expect(panel.getByRole('heading',{name:'Titik pesan ulang (safety stock)',exact:true})).toBeVisible()
  // Hitung sekarang: the server evaluates every item now, then the list is read again.
  await panel.getByRole('button',{name:'Hitung sekarang',exact:true}).click()
  await ui.expect(panel.getByRole('status').filter({hasText:'Selesai dihitung '})).toBeVisible()
  await ui.expect(panel.locator('.cfr-run').first()).toContainText(/Dihitung \d/)
  await panel.getByLabel('Cari barang untuk titik pesan ulang',{exact:true}).fill(item.sku)
  await panel.getByRole('button',{name:'Cari',exact:true}).click()
  const row=panel.getByRole('article',{name:`Titik pesan ulang ${item.label} (SKU ${item.sku})`,exact:true})
  const chip=row.locator('.cfr-chip'),free=row.locator('[data-cfr="free"]'),point=row.locator('[data-cfr="point"]')
  await ui.expect(row).toBeVisible()
  await ui.expect(chip).toHaveText('Perlu produksi');await ui.expect(free).toHaveText(pcs(item.free));await ui.expect(point).toHaveText(pcs(item.point))
  await ui.expect(row.locator('[data-cfr="wip"]')).toHaveText('0 pcs')
  await ui.expect(row.getByText('Asal angka: rumus',{exact:true})).toBeVisible()
  await row.getByText('Rincian rumus',{exact:true}).click()
  await ui.expect(row.locator('.cfr-formula')).toContainText('Lama produksi: 7 hari (dari profil perencanaan).')
  await ui.expect(row.locator('.cfr-formula')).toContainText(`dibulatkan ke atas = ${pcs(item.point)}.`)
  if(mobile)await noScroll(ui,page)
  shots.push(await shot(ui,page,`WAF_FG_${suffix}_AT_OR_BELOW.png`))
  // A manual point one under the free stock: the item is no longer at or under its point.
  await row.getByRole('button',{name:'Atur angka manual',exact:true}).click()
  const form=row.getByRole('group',{name:'Angka manual',exact:true})
  await form.getByLabel('Titik pesan ulang manual (pcs)',{exact:true}).fill(String(manual))
  await form.getByLabel('Alasan angka manual',{exact:true}).fill(reason)
  if(mobile)await noScroll(ui,page)
  await form.getByRole('button',{name:'Simpan angka manual',exact:true}).click()
  await ui.expect(row.getByRole('status').filter({hasText:`Angka manual tersimpan: ${whole(manual)} pcs`})).toBeVisible()
  await ui.expect(chip).toHaveText('Aman');await ui.expect(point).toHaveText(pcs(manual))
  await ui.expect(row.getByText(`Asal angka: angka manual (rumus: ${whole(item.point)})`,{exact:true})).toBeVisible()
  let st=fixture('fg_state',{target_key:item.target_key})
  assert.deepEqual([st.evaluation.basis,st.evaluation.point,st.evaluation.manual_point,st.evaluation.formula_point,st.evaluation.state,st.manual.revision,
   st.manual.reorder_point_pcs,st.manual.reason],['MANUAL',manual,manual,item.point,'ABOVE',1,manual,reason],JSON.stringify(st))
  if(mobile)await noScroll(ui,page)
  shots.push(await shot(ui,page,`WAF_FG_${suffix}_MANUAL.png`))
  // Removed: the formula's point again.
  await row.getByRole('button',{name:'Atur angka manual',exact:true}).click()
  await form.getByLabel('Alasan angka manual',{exact:true}).fill(reason+' selesai')
  await form.getByRole('button',{name:'Hapus angka manual',exact:true}).click()
  await ui.expect(row.getByRole('status').filter({hasText:'Angka manual dihapus'})).toBeVisible()
  await ui.expect(chip).toHaveText('Perlu produksi');await ui.expect(point).toHaveText(pcs(item.point))
  await ui.expect(row.getByText('Asal angka: rumus',{exact:true})).toBeVisible()
  st=fixture('fg_state',{target_key:item.target_key})
  assert.deepEqual([st.evaluation.basis,st.evaluation.point,st.evaluation.manual_point,st.evaluation.state,st.manual.revision,st.manual.reorder_point_pcs],
   ['FORMULA',item.point,null,'AT_OR_BELOW',2,null],JSON.stringify(st))
  if(mobile)await noScroll(ui,page)
  shots.push(await shot(ui,page,`WAF_FG_${suffix}_FORMULA_AGAIN.png`))
  // Exactly the payloads of the two saves, each with its own request id; no refused answer on the way.
  const answers=await w.texts()
  assert.equal(answers.filter(a=>a.status>=400).length,0,JSON.stringify(answers.filter(a=>a.status>=400).map(a=>[a.name,a.status,a.text.slice(0,300)])))
  const saves=w.sent.filter(r=>r.name==='erp_cp7_save_fg_reorder_manual_v1').map(r=>JSON.parse(r.body))
  assert.deepEqual(saves.map(s=>s.p_payload),[{root_id:item.root_id,expected_revision:0,reorder_point_pcs:manual,reason},
   {root_id:item.root_id,expected_revision:1,reorder_point_pcs:null,reason:reason+' selesai'}])
  assert.equal(new Set(saves.map(s=>s.p_request)).size,2)
  assert.equal(w.sent.filter(r=>r.name==='erp_cp7_refresh_fg_reorder_v1').length,1)
  return{status:'PASS',phone:mobile,sku:item.sku,free:item.free,formula_point:item.point,manual_point:manual,chips:['Perlu produksi','Aman','Perlu produksi'],
   basis_after_manual:'MANUAL',manual_revisions:[1,2],formula_point_after_removal:item.point,distinct_request_ids:2,no_horizontal_scroll:true,screenshots:shots,
   label:'TEST_FIXTURE SS-1 item; real Auth and PostgREST'}
 }catch(e){writeFileSync(`cp6-proof/t3/WAF_FG_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),text:await (panel??page.locator('body')).innerText().catch(()=>'')},null,2))
  await page.screenshot({path:`cp6-proof/t3/WAF_FG_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{await user.context.close()}
}
// SS-2/SS-3 (owner D17-9): Titik pesan ulang of fabric and accessories, real UI, Auth and PostgREST on the browser copy. The
// fixture makes one fabric (130 YD, SPARSE cut) and one accessory (280 PCS, SPARSE used) with the Native helpers of
// cp7_stock_formula_cases, without lama kirim. The owner opens Master Data › Kain & Benchmark, presses "Hitung sekarang",
// finds the fabric (no lama kirim: no point), saves lama kirim 6 days there and sees the oracle's point, "Rumus" and
// "Menipis"; Gudang › Bahan & Roll shows the same numbers; on Gudang › Aksesori the accessory gets the manual number 0 and
// is "Tanpa titik" (never reminded). The evaluations and setting rows are read back. Desktop 1440 px and phone 390 px, no
// horizontal page scroll.
const MAT_RPCS=['erp_cp7_get_material_reorder_v1','erp_cp7_refresh_material_reorder_v1','erp_cp7_save_material_reorder_v1']
// A decimal text as the screen writes it (formatReceiptDecimal): dots between thousands, a decimal comma, no trailing zeros.
const decimalText=v=>{const [i,f='']=String(v).split('.'),t=f.replace(/0+$/,'');return i.replace(/\B(?=(\d{3})+(?!\d))/g,'.')+(t?','+t:'')}
const qty=(v,unit)=>decimalText(v)+(unit?' '+unit:'')
async function openMenu(page,section,item){
 const main=page.locator('.sidebar .nav-main').filter({hasText:section}).first()
 await main.waitFor({state:'attached'});await openSidebar(page)
 const link=page.getByRole('button',{name:'• '+item,exact:true})
 if(!await link.isVisible())await main.click()
 await link.click()
}
async function materialReorderJourney(ui,mobile){
 const suffix=mobile?'MOBILE':'DESKTOP',shots=[],reason='WAF material browser '+suffix.toLowerCase()
 const item=fixture('material',{lead:6}),f=item.fabric,a=item.accessory
 assert.ok(Number(f.free)<=Number(f.point)&&f.unit&&a.unit,JSON.stringify(item))
 const user=await ui.login('OWNER',{label:'waf-mat-'+suffix.toLowerCase(),mobile}),page=user.page,w=watch(page,MAT_RPCS)
 let panel=null
 const cell=(row,key)=>row.locator(`[data-cmr="${key}"]`),chipOf=row=>row.locator('.cfr-chip')
 const find=async(name,noun,m)=>{
  panel=page.getByRole('region',{name,exact:true})
  await ui.expect(panel.getByRole('heading',{name:name+' (safety stock)',exact:true})).toBeVisible()
  await panel.getByLabel(`Cari ${noun} untuk titik pesan ulang`,{exact:true}).fill(m.sku)
  await panel.getByRole('button',{name:'Cari',exact:true}).click()
  const row=panel.getByRole('article',{name:`Titik pesan ulang ${m.name} (SKU ${m.sku})`,exact:true})
  await ui.expect(row).toBeVisible();return row
 }
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  // Master Data › Kain & Benchmark: the new fabric is evaluated by "Hitung sekarang"; without lama kirim it has no point.
  await openMenu(page,'Master Data','Kain & Benchmark')
  panel=page.getByRole('region',{name:'Titik pesan ulang kain',exact:true})
  await panel.getByRole('button',{name:'Hitung sekarang',exact:true}).click()
  await ui.expect(panel.getByRole('status').filter({hasText:'Selesai dihitung '})).toBeVisible()
  let row=await find('Titik pesan ulang kain','kain',f)
  await ui.expect(chipOf(row)).toHaveText('Tanpa titik');await ui.expect(cell(row,'basis')).toHaveText('Belum cukup data: lama kirim belum diisi')
  await ui.expect(cell(row,'lead')).toHaveText('belum diisi');await ui.expect(cell(row,'free')).toHaveText(qty(f.free,f.unit))
  await ui.expect(cell(row,'ordered')).toHaveText(qty('0',f.unit))
  if(mobile)await noScroll(ui,page)
  await row.getByRole('button',{name:'Atur lama kirim',exact:true}).click()
  let form=row.getByRole('group',{name:'Lama kirim',exact:true})
  await ui.expect(form.getByLabel('Angka manual',{exact:true})).toHaveCount(0)
  await ui.expect(form).toContainText('Angka minimum diatur di Master Data › Kain & Benchmark.')
  await form.getByLabel('Lama kirim (hari)',{exact:true}).fill(item.lead)
  await form.getByLabel('Alasan perubahan bahan',{exact:true}).fill(reason)
  if(mobile)await noScroll(ui,page)
  await form.getByRole('button',{name:'Simpan',exact:true}).click()
  await ui.expect(row.getByRole('status').filter({hasText:`Tersimpan (revisi 1): lama kirim ${decimalText(item.lead)} hari.`})).toBeVisible()
  await ui.expect(cell(row,'lead')).toHaveText(decimalText(item.lead));await ui.expect(cell(row,'basis')).toHaveText('Rumus')
  await ui.expect(cell(row,'point')).toHaveText(qty(f.point,f.unit));await ui.expect(chipOf(row)).toHaveText('Menipis')
  let st=fixture('material_state',{ids:[f.id,a.id]})
  const fe=st[f.id].evaluation,fs=st[f.id].setting
  assert.deepEqual([fe.basis,fe.state,Number(fe.point),Number(fe.lead_days),fe.setting_revision,fe.manual_source,fs.revision,Number(fs.lead_days),fs.manual_point,fs.reason],
   ['FORMULA','AT_OR_BELOW',Number(f.point),Number(item.lead),1,null,1,Number(item.lead),null,reason],JSON.stringify(st[f.id]))
  shots.push(await shot(ui,page,`WAF_MAT_${suffix}_MASTER_FABRIC.png`))
  // Gudang › Bahan & Roll: the same fabric, the same lama kirim and point.
  await openMenu(page,'Gudang','Bahan & Roll')
  row=await find('Titik pesan ulang kain','kain',f)
  await ui.expect(cell(row,'lead')).toHaveText(decimalText(item.lead));await ui.expect(cell(row,'point')).toHaveText(qty(f.point,f.unit))
  await ui.expect(cell(row,'basis')).toHaveText('Rumus');await ui.expect(chipOf(row)).toHaveText('Menipis')
  if(mobile)await noScroll(ui,page)
  shots.push(await shot(ui,page,`WAF_MAT_${suffix}_BAHAN_ROLL.png`))
  // Gudang › Aksesori: the manual number 0 means never reminded.
  await openMenu(page,'Gudang','Aksesori')
  row=await find('Titik pesan ulang aksesori','aksesori',a)
  await ui.expect(chipOf(row)).toHaveText('Tanpa titik');await ui.expect(cell(row,'basis')).toHaveText('Belum cukup data: lama kirim belum diisi')
  await ui.expect(cell(row,'free')).toHaveText(qty(a.free,a.unit));await ui.expect(row.locator('[data-cmr="ordered"]')).toHaveCount(0)
  await row.getByRole('button',{name:'Atur lama kirim & angka manual',exact:true}).click()
  form=row.getByRole('group',{name:'Lama kirim dan angka manual',exact:true})
  await ui.expect(form).toContainText('0 = tidak pernah diingatkan, kosong = pakai rumus.')
  await form.getByLabel('Angka manual',{exact:true}).fill('0')
  await form.getByLabel('Alasan perubahan bahan',{exact:true}).fill(reason)
  if(mobile)await noScroll(ui,page)
  await form.getByRole('button',{name:'Simpan',exact:true}).click()
  await ui.expect(row.getByRole('status').filter({hasText:`Tersimpan (revisi 1): lama kirim kosong, angka manual ${qty('0',a.unit)} (tidak pernah diingatkan).`})).toBeVisible()
  await ui.expect(chipOf(row)).toHaveText('Tanpa titik');await ui.expect(cell(row,'basis')).toHaveText('Angka manual 0: tidak pernah diingatkan')
  await ui.expect(cell(row,'point')).toHaveText(qty('0',a.unit))
  st=fixture('material_state',{ids:[a.id]})
  const ae=st[a.id].evaluation,as=st[a.id].setting
  assert.deepEqual([ae.basis,ae.state,Number(ae.point),ae.manual_source,ae.setting_revision,as.revision,as.lead_days,Number(as.manual_point),as.reason],
   ['MANUAL','NO_POINT',0,'ACCESSORY_MANUAL',1,1,null,0,reason],JSON.stringify(st[a.id]))
  if(mobile)await noScroll(ui,page)
  shots.push(await shot(ui,page,`WAF_MAT_${suffix}_ACCESSORY_NEVER.png`))
  // Exactly the two saves' payloads, each with its own request id; no refused answer on the way.
  const answers=await w.texts()
  assert.equal(answers.filter(x=>x.status>=400).length,0,JSON.stringify(answers.filter(x=>x.status>=400).map(x=>[x.name,x.status,x.text.slice(0,300)])))
  const saves=w.sent.filter(r=>r.name==='erp_cp7_save_material_reorder_v1').map(r=>JSON.parse(r.body))
  assert.deepEqual(saves.map(x=>x.p_payload),[{material_id:f.id,expected_revision:0,lead_days:item.lead,manual_point:null,reason},
   {material_id:a.id,expected_revision:0,lead_days:null,manual_point:'0',reason}])
  assert.equal(new Set(saves.map(x=>x.p_request)).size,2)
  assert.deepEqual(w.sent.filter(r=>r.name==='erp_cp7_refresh_material_reorder_v1').map(r=>JSON.parse(r.body)),[{p_material_type:'FABRIC'}])
  return{status:'PASS',phone:mobile,fabric:{sku:f.sku,free:f.free,point:f.point,lead_days:item.lead,set_on:'Master Data › Kain & Benchmark',
   same_on:'Gudang › Bahan & Roll'},accessory:{sku:a.sku,manual_point:'0',status:'Tanpa titik'},distinct_request_ids:2,no_horizontal_scroll:true,
   screenshots:shots,label:'TEST_FIXTURE SS-2/SS-3 materials; real Auth and PostgREST'}
 }catch(e){writeFileSync(`cp6-proof/t3/WAF_MAT_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),text:await (panel??page.locator('body')).innerText().catch(()=>'')},null,2))
  await page.screenshot({path:`cp6-proof/t3/WAF_MAT_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{await user.context.close()}
}
export function cases(ui){
 return[['WAF_BROWSER_DESKTOP_OWNER_SETS_UP_TESTS_AND_FORWARDS',()=>ownerJourney(ui,false)],['WAF_BROWSER_MOBILE_OWNER_SETS_UP_TESTS_AND_FORWARDS',()=>ownerJourney(ui,true)],
  ['WAF_BROWSER_ADMIN_SEES_SYSTEM_REMINDERS_WITHOUT_WA',()=>adminJourney(ui)],['WAF_BROWSER_FG_REORDER_DESKTOP',()=>fgReorderJourney(ui,false)],
  ['WAF_BROWSER_FG_REORDER_MOBILE',()=>fgReorderJourney(ui,true)],['WAF_BROWSER_MATERIAL_REORDER_DESKTOP',()=>materialReorderJourney(ui,false)],
  ['WAF_BROWSER_MATERIAL_REORDER_MOBILE',()=>materialReorderJourney(ui,true)]]
}
