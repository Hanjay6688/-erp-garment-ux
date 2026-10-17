// R3-03 (owner D16-1): the connected Reminder page (menu Pengaturan & Audit -> Reminder), desktop 1440 px and phone 390 px,
// real Auth and PostgREST on the committed copy. The journey starts from an empty list of a fresh OWNER login and goes through
// the screen only: add, edit, mark done, reopen, cancel with a reason; every step is read back from the Native rows
// (fixture r303_reminders_state: erp.manual_reminders and its audit rows), never from the command's answer, and each save
// carries its own request UUID and the version the screen read. Then a limited role: AUDITOR_VIEW_ONLY (desktop) holds the
// view key but the Native actor rule refuses its role, so the page says so in words and offers no form; PRODUKSI_QC (phone)
// has no Reminder key, so the menu is not there. No horizontal page scroll at either width.
import assert from'node:assert/strict'
import{mkdirSync}from'node:fs'
const addDays=(iso,n)=>{const d=new Date(iso+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+n);return d.toISOString().slice(0,10)}
const ROLE_REFUSAL='Pengingat hanya untuk akun internal Owner, Admin, atau Staff. Peran akun ini tidak termasuk, jadi pengingat tidak bisa dibuka atau diubah.'
async function openSidebar(page){const open=page.getByRole('button',{name:'Buka menu',exact:true});if(await open.isVisible())await open.click()}
async function openReminders(ui,page){
 await openSidebar(page)
 const link=page.getByRole('button',{name:'• Reminder',exact:true})
 if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Pengaturan & Audit'}).click()
 await link.click();await ui.expect(page.getByRole('heading',{name:'Pengingat',exact:true})).toBeVisible()
}
async function journey(ui,today,mobile,h){
 const name=`CP17_BROWSER_R3_03_REMINDERS_${mobile?'MOBILE':'DESKTOP'}`,seen={},requests=[]
 const roles=seen.roles=h.fixture('r303_reminders_roles',{})
 assert.deepEqual([roles.auditor.includes('settings.reminder.view'),roles.auditor.includes('settings.reminder.manage'),roles.produksi_qc],[true,false,[]])
 const user=await ui.login('OWNER',{label:'cp17-r3-03-reminders-'+(mobile?'mobile':'desktop'),mobile}),page=user.page
 const state=()=>h.fixture('r303_reminders_state',{auth_user_id:user.user.id})
 page.on('request',r=>{if(r.url().endsWith('/rpc/erp_cp7_save_reminder_v1'))requests.push(r.postDataJSON())})
 let limited=null
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  assert.deepEqual((seen.before=state()).rows,[])
  await openReminders(ui,page)
  const list=page.getByRole('region',{name:'Daftar pengingat',exact:true}),form=page.getByRole('complementary',{name:'Isian pengingat',exact:true})
  const item=title=>list.getByRole('article',{name:'Pengingat '+title,exact:true})
  const status=text=>ui.expect(page.getByRole('status').filter({hasText:text})).toBeVisible()
  await ui.expect(list).toContainText('Belum ada pengingat di daftar ini.')
  await ui.expect(page.getByRole('region',{name:'Ringkasan pengingat',exact:true})).toContainText('0 belum selesai · 0 sudah selesai · 0 dibatalkan')
  // Add.
  const due=addDays(today,1)+'T09:00',title='Telepon Laundry Intan',title2='Telepon Laundry Intan sore'
  await form.getByLabel('Judul pengingat',{exact:true}).fill(title)
  await form.getByLabel('Catatan pengingat',{exact:true}).fill('Tanyakan kiriman susulan POT-041')
  await form.getByLabel('Jatuh tempo pengingat (WIB)',{exact:true}).fill(due)
  await form.getByLabel('Prioritas pengingat',{exact:true}).selectOption('URGENT')
  await form.getByLabel('Modul pengingat',{exact:true}).fill('Laundry')
  assert.equal(requests.length,0)
  await form.getByRole('button',{name:'Tambah pengingat',exact:true}).click()
  await status(`Pengingat "${title}" ditambahkan.`)
  const s1=seen.created=state();assert.equal(s1.rows.length,1);const r=s1.rows[0]
  assert.deepEqual([r.title,r.note,r.due_wib,r.priority,r.module,r.status,r.row_version,r.audits],[title,'Tanyakan kiriman susulan POT-041',due,'URGENT','Laundry','OPEN',1,1])
  assert.deepEqual([requests[0].p_action,requests[0].p_expected,requests[0].p_payload.id,r.last_request],['SAVE',null,null,requests[0].p_request])
  await ui.expect(item(title)).toContainText('Besok');await ui.expect(item(title)).toContainText('Laundry · Penting')
  await h.noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_ADDED.png`,fullPage:true})
  // Edit (only an OPEN one), with the version read.
  await list.getByRole('button',{name:'Ubah '+title,exact:true}).click()
  await ui.expect(form.getByRole('button',{name:'Simpan perubahan',exact:true})).toBeDisabled()
  await form.getByLabel('Judul pengingat',{exact:true}).fill(title2)
  await form.getByRole('button',{name:'Simpan perubahan',exact:true}).click()
  await status(`Perubahan pengingat "${title2}" disimpan.`)
  const s2=seen.edited=state();assert.deepEqual([s2.rows.length,s2.rows[0].id,s2.rows[0].title,s2.rows[0].row_version,s2.rows[0].due_wib],[1,r.id,title2,2,due])
  assert.deepEqual([requests[1].p_action,requests[1].p_expected,requests[1].p_payload.id],['SAVE','1',r.id])
  // Done, then shown under "Sudah selesai" with no edit, then reopened.
  await list.getByRole('button',{name:'Tandai selesai '+title2,exact:true}).click()
  await status(`Pengingat "${title2}" ditandai selesai.`)
  const s3=seen.done=state();assert.deepEqual([s3.rows[0].status,s3.rows[0].row_version,s3.rows[0].completed],['DONE',3,true])
  await page.getByRole('group',{name:'Saring pengingat',exact:true}).getByRole('button',{name:'Sudah selesai',exact:true}).click()
  await ui.expect(item(title2)).toContainText('Selesai');await ui.expect(list.getByRole('button',{name:'Ubah '+title2,exact:true})).toHaveCount(0)
  await list.getByRole('button',{name:'Buka lagi '+title2,exact:true}).click()
  await status(`Pengingat "${title2}" dibuka lagi.`)
  const s4=seen.reopened=state();assert.deepEqual([s4.rows[0].status,s4.rows[0].row_version,s4.rows[0].completed],['OPEN',4,false])
  // Cancel with a reason: final, kept, shown under "Dibatalkan" with its reason and no action.
  await page.getByRole('group',{name:'Saring pengingat',exact:true}).getByRole('button',{name:'Belum selesai',exact:true}).click()
  await list.getByRole('button',{name:'Batalkan '+title2,exact:true}).click()
  const cancel=list.getByRole('group',{name:'Batalkan pengingat '+title2,exact:true}),go=cancel.getByRole('button',{name:'Batalkan pengingat',exact:true})
  await ui.expect(go).toBeDisabled();await cancel.getByLabel('Alasan batal '+title2,{exact:true}).fill('Sudah ditelepon pagi ini')
  await page.screenshot({path:`cp6-proof/t3/${name}_CANCEL.png`,fullPage:true});await go.click()
  await status(`Pengingat "${title2}" dibatalkan.`)
  const s5=seen.cancelled=state()
  assert.deepEqual([s5.rows.length,s5.rows[0].status,s5.rows[0].row_version,s5.rows[0].reason,s5.rows[0].cancelled,s5.rows[0].audits],[1,'CANCELLED',5,'Sudah ditelepon pagi ini',true,5])
  await page.getByRole('group',{name:'Saring pengingat',exact:true}).getByRole('button',{name:'Dibatalkan',exact:true}).click()
  await ui.expect(item(title2)).toContainText('Sudah ditelepon pagi ini');await ui.expect(item(title2).getByRole('button')).toHaveCount(0)
  assert.deepEqual(requests.map(x=>[x.p_action,x.p_expected]),[['SAVE',null],['SAVE','1'],['DONE','2'],['UNDONE','3'],['CANCEL','4']])
  assert.equal(new Set(requests.map(x=>x.p_request)).size,5);assert.deepEqual(requests[4].p_payload,{id:r.id,reason:'Sudah ditelepon pagi ini'})
  await h.noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_CANCELLED.png`,fullPage:true})
  // A limited role.
  let refusal
  if(!mobile){
   limited=await ui.login('AUDITOR_VIEW_ONLY',{label:'cp17-r3-03-reminders-auditor'});const p=limited.page
   await openReminders(ui,p)
   await ui.expect(p.getByRole('alert').filter({hasText:ROLE_REFUSAL})).toBeVisible()
   await ui.expect(p.getByLabel('Judul pengingat',{exact:true})).toHaveCount(0)
   await ui.expect(p.getByRole('region',{name:'Ringkasan pengingat',exact:true})).toHaveCount(0)
   assert.doesNotMatch(await p.getByRole('main',{name:'Pengingat',exact:true}).innerText(),/\d/)
   assert.deepEqual(h.fixture('r303_reminders_state',{auth_user_id:limited.user.id}).rows,[])
   await h.noSideScroll(ui,p);await p.screenshot({path:`cp6-proof/t3/${name}_AUDITOR.png`,fullPage:true});refusal='AUDITOR_VIEW_ONLY: refused in words, no form, no number'
  }else{
   limited=await ui.login('PRODUKSI_QC',{label:'cp17-r3-03-reminders-produksi',mobile:true});const p=limited.page
   await openSidebar(p);const section=p.locator('.sidebar .nav-main').filter({hasText:'Pengaturan & Audit'})
   if(await section.count())await section.click()
   await ui.expect(p.getByRole('button',{name:'• Reminder',exact:true})).toHaveCount(0)
   await h.noSideScroll(ui,p);refusal='PRODUKSI_QC: no Reminder menu'
  }
  return{status:'PASS',owner_decision:'D16-1',phone:mobile,steps:['ADD','EDIT','DONE','REOPEN','CANCEL'],native_row_versions:[1,2,3,4,5],
   audit_rows:5,requests:requests.length,distinct_request_ids:5,limited_role:refusal}
 }catch(error){try{seen.actual=state()}catch(e){seen.observation_error=String(e)};await h.failure(page,name,error,seen,requests);throw error}
 finally{if(limited)await limited.context.close();await user.context.close()}
}
export function cases(ui,today,h){
 return[['CP17_BROWSER_R3_03_REMINDERS_DESKTOP',()=>journey(ui,today,false,h)],['CP17_BROWSER_R3_03_REMINDERS_MOBILE',()=>journey(ui,today,true,h)]]
}
