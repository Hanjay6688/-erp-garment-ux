// Owner D15-6 (Sol SOL-R1-002): Buat Potongan with the PO made automatically, on the committed copy with real Auth and
// PostgREST, desktop and phone. The user fills only the cutting; the screen names the new PO number for tracking.
// Desktop: a draft first (no PO, no stock moved), reopened, then posted while the answer is lost on the way back; the
// screen's check sends the same request again and gets the same answer: one PO, one cutting, the roll issued once.
// Phone: posted straight away. Oracles read the Native rows (cp7_cp17_fix_browser_fixture.py auto_po_state).
import assert from'node:assert/strict'
import{mkdirSync}from'node:fs'
async function openCutting(ui,page,mobile){
 if(mobile){const menu=page.getByRole('button',{name:'Buka menu',exact:true});await ui.expect(menu).toBeVisible();await menu.click()}
 const link=page.getByRole('button',{name:'• Buat Potongan',exact:true})
 if(!await link.isVisible()){const branch=page.locator('.sidebar .nav-main').filter({hasText:'Produksi'});await ui.expect(branch).toBeVisible();await branch.click()}
 await ui.expect(link).toBeVisible();await link.click();await ui.expect(page.getByRole('heading',{name:'Buat Potongan',exact:true})).toBeVisible()
}
async function fillCutting(ui,page,f){
 const auto=page.locator('fieldset.ccut-po-mode').getByRole('radio',{name:'PO baru otomatis',exact:true});await ui.expect(auto).toBeChecked()
 await ui.expect(page.getByText('Nomor PO dibuat otomatis saat potongan disahkan',{exact:false})).toBeVisible()
 await page.getByLabel('Cari model',{exact:true}).fill(f.model_code);await page.getByRole('button',{name:'Cari model',exact:true}).click()
 await page.getByLabel('Model potongan',{exact:true}).selectOption(f.model)
 const sizes=page.locator('.ccut-size-list button');await ui.expect(sizes).toHaveText(f.sizes)
 for(const code of f.sizes)if(code!==f.size_code)await sizes.filter({hasText:new RegExp(`^${code}$`)}).click()
 await ui.expect(page.locator('.ccut-size-list button.active')).toHaveText([f.size_code])
 await page.getByLabel(/^Waktu potong \(WIB\)/).fill(f.cut_local)
 await page.getByRole('combobox',{name:/^Gudang bahan/}).selectOption(f.location)
 await page.locator('.ccut-roll-catalog button').filter({hasText:f.roll_number}).click()
 await page.getByLabel(`${f.roll_number} terpakai`,{exact:true}).fill('10');await page.getByLabel(`${f.roll_number} Size ${f.size_code}`,{exact:true}).fill('10')
 await page.getByPlaceholder('Cari kode, revisi, atau nama Pola…').fill(f.pattern_code)
 await page.getByRole('option',{name:new RegExp(`^${f.pattern_code} · ${f.pattern_revision}`)}).click()
}
async function journey(ui,today,mobile,h){
 const name=`CP17_BROWSER_R2_D15_6_AUTO_PO_${mobile?'MOBILE':'DESKTOP'}`,f=h.fixture('auto_po',{today}),state=()=>h.fixture('auto_po_state',f),seen={},requests=[]
 const user=await ui.login('OWNER',{label:'cp17-r2-auto-po-'+(mobile?'mobile':'desktop'),mobile}),page=user.page
 page.on('request',r=>{if(r.url().endsWith('/rpc/erp_cp7_save_cutting_auto_po_v1'))requests.push(r.postDataJSON())})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  let s=seen.before=state();assert.deepEqual([s.pos,s.drafts,s.requests,Number(s.stock),s.taken],[[],[],0,10,0])
  await openCutting(ui,page,mobile);await fillCutting(ui,page,f)
  const post=page.getByRole('button',{name:'Sahkan & buat PO',exact:true});await ui.expect(post).toBeEnabled()
  let lost=null
  if(!mobile){
   // A draft makes nothing: no PO, the roll untouched.
   await page.getByRole('button',{name:'Simpan draft',exact:true}).click()
   await ui.expect(page.locator('.ccut-message.success')).toHaveText('Draf PO otomatis tersimpan. Belum ada PO, stok, atau jurnal yang berubah.')
   s=seen.draft=state();assert.equal(s.drafts.length,1);assert.deepEqual([s.pos,s.drafts[0].slice(1),s.requests,Number(s.stock),s.taken],[[],['DRAFT',1,null],1,10,0])
   const draft=s.drafts[0][0]
   await page.getByRole('region',{name:'Draf PO otomatis',exact:true}).getByRole('button',{name:`Muat draf PO otomatis ${f.model_code} ${draft.slice(0,8)}`,exact:true}).click()
   await ui.expect(page.locator('.ccut-message.success')).toHaveText(`Draf PO otomatis ${f.model_code} dimuat. PO baru dibuat saat potongan disahkan.`)
   await ui.expect(page.getByLabel(`${f.roll_number} Size ${f.size_code}`,{exact:true})).toHaveValue('10')
   await page.screenshot({path:`cp6-proof/t3/${name}_DRAFT.png`,fullPage:true})
   // The answer of the post is lost on the way back: the server has committed, the screen does not know yet.
   await page.route('**/rest/v1/rpc/erp_cp7_save_cutting_auto_po_v1',async route=>{
    if(lost)return route.continue()
    const reply=await route.fetch();assert.equal(reply.status(),200);lost=await reply.json();await route.abort('failed')
   })
  }
  const replied=mobile?page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_save_cutting_auto_po_v1')):null
  await post.click()
  let answer=mobile?await(await replied).json():null
  if(!mobile){
   const check=page.getByRole('button',{name:'Periksa hasil Potongan dengan PO otomatis',exact:true});await ui.expect(check).toBeEnabled()
   await ui.expect(post).toBeDisabled()
   s=seen.lost=state();assert.equal(lost.po_number,f.expected);assert.equal(s.pos.length,1)
   assert.deepEqual([s.pos[0].slice(0,7),Number(s.stock),s.drafts[0].slice(1),s.requests,s.taken],[[f.expected,'CUTTING','CUTTING',f.model,10,1,1],0,['POSTED',2,f.expected],2,1])
   await check.click();answer=lost
  }
  assert.equal(answer.po_number,f.expected);const group=answer.group_number
  await ui.expect(page.locator('.ccut-message.success')).toHaveText(`${f.expected} dibuat otomatis; ${group} terposting (10 pcs). Nomor PO ini dipakai untuk pelacakan di Bagi Potongan dan WIP.`)
  s=seen.after=state();assert.equal(s.pos.length,1)
  assert.deepEqual([s.pos[0],Number(s.stock),s.taken],[[f.expected,'CUTTING','CUTTING',f.model,10,1,1,group],0,1])
  const posts=requests.filter(r=>r.p_payload.action==='POST')
  assert.equal(posts.length,mobile?1:2);assert.ok(posts.every(r=>r.p_request===posts[0].p_request&&JSON.stringify(r.p_payload)===JSON.stringify(posts[0].p_payload)))
  assert.equal('po_id'in posts[0].p_payload,false);assert.deepEqual(Object.keys(posts[0].p_payload.cutting).sort(),['cut_at','notes','pattern_id','rolls','size_slots','source_location_id'])
  if(mobile)assert.deepEqual([s.drafts,s.requests],[[],1]);else assert.deepEqual([s.drafts[0].slice(1),s.requests],[['POSTED',2,f.expected],2])
  await h.noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_COMMITTED.png`,fullPage:true})
  return{status:'PASS',owner_decision:'D15-6',phone:mobile,po_made_automatically:f.expected,cutting:group,draft_made_no_po_no_stock:!mobile,
   lost_answer_resent_same_uuid_same_answer:!mobile,one_po_one_cutting_roll_issued_once:true,user_filled_only_the_cutting:true}
 }catch(error){await h.failure(page,name,error,seen,requests);throw error}
 finally{await user.context.close()}
}
export function cases(ui,today,h){
 return[['CP17_BROWSER_R2_D15_6_AUTO_PO_DESKTOP',()=>journey(ui,today,false,h)],['CP17_BROWSER_R2_D15_6_AUTO_PO_MOBILE',()=>journey(ui,today,true,h)]]
}
