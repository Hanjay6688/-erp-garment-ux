import assert from'node:assert/strict'
import{execFileSync}from'node:child_process'
import{mkdirSync,writeFileSync}from'node:fs'
const fixture=(operation,payload)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_cutting_correction_browser_fixture.py',operation],{input:JSON.stringify(payload),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const endpoint='**/rest/v1/rpc/erp_cp7_reopen_cutting_v1'
async function menu(page){const open=page.getByRole('button',{name:'Buka menu',exact:true});if(await open.isVisible())await open.click();const link=page.getByRole('button',{name:'• Bagi Potongan',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Produksi'}).click();await link.click()}
async function observed(page,button){const pending=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_reopen_cutting_v1')).then(response=>({response}),error=>({error}));await button.click();const result=await pending;if(result.error)throw result.error;return result.response}
async function readable(region){
 const ratios=await region.evaluate(el=>{
  const luminance=color=>{const rgb=color.match(/[\d.]+/g).slice(0,3).map(n=>Number(n)/255).map(n=>n<=.04045?n/12.92:((n+.055)/1.055)**2.4);return rgb[0]*.2126+rgb[1]*.7152+rgb[2]*.0722}
  const panel=getComputedStyle(el),bg=luminance(panel.backgroundColor)
  return[el,...el.querySelectorAll('p,h2,label,button,input:not([type="checkbox"])')].filter(node=>!node.disabled).map(node=>{
   const style=getComputedStyle(node),color=luminance(style.color),own=style.backgroundColor,background=own==='rgba(0, 0, 0, 0)'?bg:luminance(own)
   return(Math.max(color,background)+.05)/(Math.min(color,background)+.05)
  })
 });assert.ok(ratios.length>1&&ratios.every(r=>r>=4.5),'Cutting correction review and committed text must remain readable against their actual surfaces')
}
async function journey(ui,today,mobile){
 const f=fixture('prepare',{today}),user=await ui.login(mobile?'ADMIN':'OWNER',{label:'cutting-correction-'+mobile,mobile,timezoneId:'America/Los_Angeles'}),page=user.page,suffix=mobile?'MOBILE':'DESKTOP',requests=[],screenshots=[]
 const state=()=>fixture('state',{fixture:f.fixture}),panel=()=>page.getByRole('region',{name:'Koreksi potongan tercatat',exact:true})
 page.on('request',r=>{if(r.url().endsWith('/rpc/erp_cp7_reopen_cutting_v1'))requests.push(r.postDataJSON())})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const before=state();assert.equal(before.stock,'0.000000')
  await menu(page);await page.getByLabel('Cari distribusi potongan',{exact:true}).fill(f.workspace.number);await page.getByRole('button',{name:'Cari Potongan',exact:true}).click()
  await page.locator('.cpick-queue button').filter({hasText:f.workspace.number}).click();await ui.expect(page.locator('[data-cutting-group-id]')).toHaveAttribute('data-cutting-group-id',f.fixture.group)
  await panel().getByRole('button',{name:'Periksa koreksi potongan',exact:true}).click();await ui.expect(panel().getByLabel('Alasan koreksi potongan',{exact:true})).toBeEnabled()
  assert.deepEqual(state(),before);assert.equal(requests.length,0)
  await readable(panel())
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
  let image=`CP7_CUTTING_REOPEN_REVIEW_${suffix}.png`;await page.screenshot({path:'cp6-proof/t3/'+image,fullPage:true});screenshots.push(image)
  await panel().getByLabel('Alasan koreksi potongan',{exact:true}).fill('Potongan belum dijemput dan aliran bahan asal sudah diperiksa')
  await panel().getByLabel('Potongan dan pembalikan bahan sudah diperiksa',{exact:true}).check()
  let original
  if(!mobile){let intercepted;await page.route(endpoint,async route=>{try{const response=await route.fetch();intercepted={status:response.status()};if(response.status()===200){original=await response.json();await route.abort('failed')}else await route.fulfill({response})}catch(error){intercepted={error:String(error)};await route.abort('failed').catch(()=>{})}})
   await panel().getByRole('button',{name:'Buka potongan sebagai draft koreksi',exact:true}).click();await ui.expect.poll(()=>intercepted!==undefined).toBe(true);assert.equal(intercepted.status,200,JSON.stringify(intercepted));assert.equal(state().history.length,1)
   await ui.expect(panel().getByRole('button',{name:'Periksa hasil koreksi potongan',exact:true})).toBeVisible();const first=structuredClone(requests[0])
   await page.unroute(endpoint);await page.reload();await menu(page)
   const response=await observed(page,panel().getByRole('button',{name:'Periksa hasil koreksi potongan',exact:true}));assert.equal(response.status(),200);assert.deepEqual(response.request().postDataJSON(),first);assert.deepEqual(await response.json(),original)
  }else{const response=await observed(page,panel().getByRole('button',{name:'Buka potongan sebagai draft koreksi',exact:true}));assert.equal(response.status(),200);original=await response.json()}
  await ui.expect(panel()).toContainText(f.workspace.number+' sudah dibuka sebagai draft koreksi')
  await readable(panel())
  const after=state();assert.equal(Number(after.stock),Number(before.stock)+Number(after.issued));assert.deepEqual(after.gl_delta,after.expected_gl_delta)
  assert.equal(after.original_nonlifecycle_facts_unchanged,true);assert.equal(after.original_movements_unchanged,true);assert.equal(after.group.material_issue_posted,false);assert.equal(after.group.material_return_posted,false);assert.equal(after.group.picked_up_at,null);assert.equal(after.history.length,1)
  assert.equal(after.history[0].group_id,f.fixture.group);assert.equal(after.history[0].original_source.group.material_issue_posted,true);assert.equal(after.history[0].request_id,requests[0].p_request)
  assert.equal(requests[0].p_payload.group_id,f.fixture.group);assert.equal(requests[0].p_payload.po_id,f.fixture.po);assert.equal(requests[0].p_expected,f.workspace.row_version);assert.equal(requests.length,mobile?1:2)
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
  image=`CP7_CUTTING_REOPEN_COMMITTED_${suffix}.png`;await page.screenshot({path:'cp6-proof/t3/'+image,fullPage:true});screenshots.push(image)
  return{status:'PASS',mobile,actual_Auth_read_and_unchanged_Native_inverse:true,old_original_roll_size_clock_and_movement_facts_preserved:true,original_movement_observation:after.original_movement_observation,stock10_restored_and_source_GL_neutral:true,one_immutable_original_receipt:true,actual_committed_lost_reply_reload_same_UUID:!mobile,review_and_committed_text_contrast_at_least4_5:true,device_timezone_America_Los_Angeles:true,screenshots}
 }catch(error){let actual;try{actual=state()}catch(failure){actual={observation_error:String(failure)}}writeFileSync(`cp6-proof/t3/CP7_CUTTING_REOPEN_${suffix}_FAILURE.json`,JSON.stringify({error:String(error),stack:error.stack,text:await page.locator('main').innerText().catch(()=>''),state:actual,requests},null,2));await page.screenshot({path:`cp6-proof/t3/CP7_CUTTING_REOPEN_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw error}
 finally{await page.unroute(endpoint).catch(()=>{});await user.context.close()}
}
export function cases(ui,today){return[['CP7_CUTTING_REOPEN_BROWSER_DESKTOP',()=>journey(ui,today,false)],['CP7_CUTTING_REOPEN_BROWSER_MOBILE',()=>journey(ui,today,true)]]}
