// R3-03 (owner D16-1): the Audit Trail screen, connected, desktop and phone, real Auth and PostgREST on the committed copy.
// The fixture (r303_audit) makes 25 customers through the master screen facade by a fresh OWNER-role user and renames the
// first; every audit reason carries the fixture tag. The screen finds those rows by the tag, pages inside one listing, opens
// one row with its values before and after, filters by data type, action and WIB dates, and (Owner only, settings.audit.export)
// downloads the rows shown as CSV. A view-only auditor reads without the download; a role without settings.audit.view has no
// menu entry. Every expectation comes from erp.audit_logs read directly (fixture r303_audit_state), never from the facade.
import assert from'node:assert/strict'
import{mkdirSync,readFileSync}from'node:fs'
const count=n=>new Intl.NumberFormat('id-ID').format(n)
const shownIds=page=>page.locator('[data-audit-id]').evaluateAll(es=>es.map(e=>e.getAttribute('data-audit-id')))
async function openAudit(ui,page){
 const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=page.getByRole('button',{name:'• Audit Trail',exact:true})
 if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Pengaturan & Audit'}).click()
 await link.click();await ui.expect(page.getByRole('heading',{name:'Audit Trail',exact:true})).toBeVisible()
}
async function position(ui,page,from,to,total){await ui.expect(page.getByText(`Baris ${count(from)}–${count(to)} dari ${count(total)} catatan`,{exact:true})).toBeVisible()}
async function search(ui,page,f,s){
 await page.getByLabel('Cari jejak audit',{exact:true}).fill(f.tag);await page.getByRole('button',{name:'Tampilkan',exact:true}).click()
 await position(ui,page,1,Math.min(25,s.total),s.total);assert.deepEqual(await shownIds(page),s.ids.slice(0,25))
}
async function detail(ui,page,s){
 await page.locator(`[data-audit-id="${s.first.id}"]`).click()
 const aside=page.getByRole('complementary',{name:'Rincian catatan audit',exact:true})
 await ui.expect(aside).toContainText('Catatan audit #'+s.first.id);await ui.expect(aside).toContainText('Alasan: '+s.first.reason)
 await ui.expect(page.locator(`[data-audit-id="${s.first.id}"]`)).toHaveAttribute('aria-pressed','true')
 for(const c of s.first.changed){
  const field=aside.locator(`[data-audit-field="${c.key}"]`)
  await ui.expect(field).toContainText('Sebelum: '+(c.before??'—'));await ui.expect(field).toContainText('Sesudah: '+(c.after??'—'))
 }
 return aside
}
async function noMenu(ui,page){
 const open=page.getByRole('button',{name:'Buka menu',exact:true});if(await open.isVisible())await open.click()
 const section=page.locator('.sidebar .nav-main').filter({hasText:'Pengaturan & Audit'});if(await section.count())await section.click()
 await ui.expect(page.getByRole('button',{name:'• Audit Trail',exact:true})).toHaveCount(0)
}
async function desktop(ui,today,h){
 const name='CP17_BROWSER_R3_03_AUDIT_DESKTOP',f=h.fixture('r303_audit',{today}),requests=[],seen={}
 const state=()=>h.fixture('r303_audit_state',f)
 const user=await ui.login('OWNER',{label:'cp17-r3-03-desktop'}),page=user.page
 page.on('request',r=>{if(r.url().endsWith('/rpc/erp_cp7_get_audit_trail_v1'))requests.push(r.postDataJSON())})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const s=seen.before=state();assert.ok(s.total>25,s.total)
  await openAudit(ui,page);await search(ui,page,f,s)
  const q1=requests.at(-1).p_query;assert.deepEqual([q1.q,q1.as_of,q1.after,q1.offset,q1.limit],[f.tag,null,null,0,25])
  const first=page.locator(`[data-audit-id="${s.ids[0]}"]`);await ui.expect(first).toContainText(s.names[0]);await ui.expect(first).toContainText('Alasan: '+s.reasons[0])
  // The next page stays inside the listing the first page fixed (as_of) and follows the last row shown (keyset).
  await page.getByRole('button',{name:'Halaman berikutnya',exact:true}).click()
  await position(ui,page,26,Math.min(50,s.total),s.total);assert.deepEqual(await shownIds(page),s.ids.slice(25,50))
  const q2=requests.at(-1).p_query;assert.equal(q2.after,s.ids[24]);assert.match(q2.as_of,/^[0-9]+$/)
  await page.getByRole('button',{name:'Halaman sebelumnya',exact:true}).click()
  await position(ui,page,1,25,s.total);assert.deepEqual([requests.at(-1).p_query.as_of,requests.at(-1).p_query.after],[q2.as_of,null])
  await detail(ui,page,s);assert.equal(requests.at(-1).p_query.id,s.first.id)
  await page.screenshot({path:`cp6-proof/t3/${name}_DETAIL.png`,fullPage:true})
  // The Owner holds settings.audit.export: the rows shown, as CSV.
  const [download]=await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name:'Unduh CSV halaman ini',exact:true}).click()])
  const csv=readFileSync(await download.path(),'utf8').replace(/^﻿/,'').trimEnd().split('\r\n')
  assert.equal(csv[0],'"ID catatan","Waktu (WIB)","Pengguna","Jenis data","Nomor data","Aksi","Alasan","Kolom berubah"')
  assert.deepEqual(csv.slice(1).map(l=>l.slice(1,l.indexOf('"',1))),s.ids.slice(0,25))
  assert.ok(csv[1].includes(`"${s.names[0]}","${s.types[0]}"`)&&csv[1].includes(`"${s.reasons[0]}"`),csv[1])
  // Filters: data type, action and the WIB dates of the fixture.
  const created=s.ids.filter((_,i)=>s.actions[i]==='INSERT'&&s.types[i]==='customers')
  await page.getByLabel('Jenis data audit',{exact:true}).selectOption('customers');await page.getByLabel('Aksi audit',{exact:true}).selectOption('INSERT')
  await page.getByLabel('Audit dari tanggal',{exact:true}).fill(s.day_from);await page.getByLabel('Audit sampai tanggal',{exact:true}).fill(s.day_to)
  await page.getByRole('button',{name:'Tampilkan',exact:true}).click()
  await position(ui,page,1,Math.min(25,created.length),created.length);assert.deepEqual(await shownIds(page),created.slice(0,25))
  const q3=requests.at(-1).p_query;assert.deepEqual([q3.entity_type,q3.action,q3.from,q3.to,q3.q,q3.as_of],['customers','INSERT',s.day_from,s.day_to,f.tag,null])
  await h.noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_FILTERED.png`,fullPage:true})
  assert.deepEqual(seen.after=state(),s)
  // A role without settings.audit.view (GUDANG in the access catalog) has no Audit Trail entry.
  const other=await ui.login('GUDANG',{label:'cp17-r3-03-gudang'})
  try{await noMenu(ui,other.page)}finally{await other.context.close()}
  return{status:'PASS',finding:'R3-03',rows:s.total,pages:[25,Math.min(25,s.total-25)],same_listing_as_of:q2.as_of,detail_changed_keys:s.first.changed.map(c=>c.key),
   csv_rows:csv.length-1,filtered_created_rows:created.length,requests:requests.length,gudang_menu:false,read_changed_nothing:true}
 }catch(error){try{seen.actual=state()}catch(e){seen.observation_error=String(e)};await h.failure(page,name,error,seen,requests);throw error}
 finally{await user.context.close()}
}
async function phone(ui,today,h){
 const name='CP17_BROWSER_R3_03_AUDIT_MOBILE',f=h.fixture('r303_audit',{today}),requests=[],seen={}
 const state=()=>h.fixture('r303_audit_state',f)
 const user=await ui.login('OWNER',{label:'cp17-r3-03-mobile',mobile:true}),page=user.page
 page.on('request',r=>{if(r.url().endsWith('/rpc/erp_cp7_get_audit_trail_v1'))requests.push(r.postDataJSON())})
 let viewer=null
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const s=seen.before=state()
  await openAudit(ui,page);await search(ui,page,f,s);await h.noSideScroll(ui,page)
  await detail(ui,page,s);await h.noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_DETAIL.png`,fullPage:true})
  await page.getByRole('button',{name:'Halaman berikutnya',exact:true}).click();await position(ui,page,26,Math.min(50,s.total),s.total);await h.noSideScroll(ui,page)
  // A view-only auditor (AUDITOR_VIEW_ONLY: settings.audit.view without settings.audit.export) reads the same rows, no download.
  viewer=await ui.login('AUDITOR_VIEW_ONLY',{label:'cp17-r3-03-viewer',mobile:true})
  await openAudit(ui,viewer.page);await search(ui,viewer.page,f,s)
  await ui.expect(viewer.page.getByRole('button',{name:'Unduh CSV halaman ini',exact:true})).toHaveCount(0)
  await ui.expect(viewer.page.getByText('Unduh CSV hanya untuk pengguna dengan hak ekspor audit.',{exact:true})).toBeVisible()
  await detail(ui,viewer.page,s);await h.noSideScroll(ui,viewer.page);await viewer.page.screenshot({path:`cp6-proof/t3/${name}_VIEW_ONLY.png`,fullPage:true})
  assert.deepEqual(seen.after=state(),s)
  return{status:'PASS',finding:'R3-03',phone:true,rows:s.total,owner_detail:true,owner_second_page:true,view_only_reads:true,view_only_download:false,read_changed_nothing:true}
 }catch(error){try{seen.actual=state()}catch(e){seen.observation_error=String(e)};await h.failure(viewer?.page??page,name,error,seen,requests);throw error}
 finally{await viewer?.context.close();await user.context.close()}
}
export function cases(ui,today,h){
 return[['CP17_BROWSER_R3_03_AUDIT_DESKTOP',()=>desktop(ui,today,h)],['CP17_BROWSER_R3_03_AUDIT_MOBILE',()=>phone(ui,today,h)]]
}
