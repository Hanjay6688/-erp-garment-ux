// Normal full App, real Auth form and actual PostgREST; never response fixtures.
import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {createHash} from 'node:crypto'
import {mkdirSync,readFileSync,writeFileSync} from 'node:fs'
import {dirname,resolve} from 'node:path'
import {fileURLToPath} from 'node:url'
import {IDS,equalCensus,pairOnly,previewOracle,postedOracle,observeConsole,requireConsoleEvidence,readable} from '../current-sku-pair-browser-qualification/evidence.mjs'

export {IDS}
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'../..')
const RPC={master:'erp_get_sku_workspace_v1',pair:'erp_save_sku_action_v1',read:'erp_get_product_conversion_workspace_v1',write:'erp_save_product_conversion_action_v1'}
const fixture=(operation,payload)=>JSON.parse(execFileSync('python',['../auditor/scripts/current-sku-combined-fixture-followup/browser_fixture.py',operation],
 {cwd:'../writer',input:JSON.stringify(payload),encoding:'utf8',maxBuffer:32*1024*1024,timeout:120000}).trim())
const args=response=>response.request().postDataJSON()
const rpc=name=>response=>response.url().endsWith('/rpc/'+name)
function admitted(){
 const pins=JSON.parse(readFileSync(resolve(ROOT,'scripts/current-sku-pair-browser-qualification/SOURCE.json'),'utf8'))
 assert.deepEqual(pins.case_ids,IDS)
 for(const[path,expected]of Object.entries(pins.files))assert.equal(createHash('sha256').update(readFileSync(resolve(ROOT,path))).digest('hex'),expected,'SKU29_BROWSER_SOURCE_CHANGED:'+path)
 return{backend_candidate:pins.backend_candidate,case_ids:pins.case_ids,source_sha256:createHash('sha256').update(JSON.stringify(pins)).digest('hex')}
}
async function success(promise){const response=await promise;assert.equal(response.status(),200,await response.text());return response.json()}
async function menu(page,section,item){
 const sidebar=page.locator('.sidebar'),toggle=page.getByRole('button',{name:'Buka menu',exact:true})
 if(await toggle.isVisible()&&!await sidebar.evaluate(e=>e.classList.contains('sidebar-open')))await toggle.click()
 const link=page.getByRole('button',{name:'• '+item,exact:true})
 if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:section}).click()
 await link.click()
}

async function journey(ui,today,mobile){
 const source=admitted(),f=fixture('prepare',{today}),suffix=mobile?'MOBILE390':'DESKTOP'
 const run=f.groups[0].id.replaceAll('-','').slice(0,12).toUpperCase()
 const user=await ui.login(mobile?'ADMIN':'OWNER',{label:'SKU29-'+suffix,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
 const page=user.page,expect=ui.expect,shots=[],contrasts=[],calls=[],reads=[],expectedNetwork=[],progress={},capture=observeConsole(page)
 const pairWorkspace=()=>page.locator('.sku-workspace'),conversion=()=>page.locator('.initial-import').filter({has:page.getByRole('heading',{name:'Ganti Merek / SKU',exact:true})})
 const pairing=()=>pairWorkspace().locator('.panel').filter({has:page.getByRole('heading',{level:2,name:/^Padanan /})})
 const destination=()=>conversion().locator('.panel').filter({has:page.getByRole('heading',{name:'2. Tujuan dan waktu fisik',exact:true})})
 const history=()=>conversion().locator('.panel').filter({has:page.getByRole('heading',{name:'Riwayat konversi',exact:true})})
 const groupSource=f.groups[0].id,groupTarget=f.groups[1].id
 const writeListener=request=>{const name=request.url().split('/').at(-1),row={rpc:name,url:request.url()};if([RPC.pair,RPC.write].includes(name))calls.push({...row,args:request.postDataJSON()});if([RPC.master,RPC.read].includes(name))reads.push({...row,args:request.postDataJSON()})}
 page.on('request',writeListener)
 let snapshotNo=0,made,lostResponse,firstBody,replayBody
 const state=step=>fixture('observe',{fixture:f,label:`SKU29_${suffix}_${run}_${String(++snapshotNo).padStart(2,'0')}_${step}`})
 const shot=async(label,panel)=>{
  await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
  assert.equal(page.viewportSize().width,mobile?390:1440)
  mkdirSync('cp6-proof/t3',{recursive:true});const prefix=`cp6-proof/t3/SKU29_${suffix}_${run}_${label}`
  await page.screenshot({path:prefix+'_PAGE.png',fullPage:true});await panel.screenshot({path:prefix+'_FOCUS.png'})
  shots.push(prefix+'_PAGE.png',prefix+'_FOCUS.png');contrasts.push({state:label,scope:'VISIBLE_FEATURE_PANEL_NORMAL_TEXT_DISABLED_CONTROLS_EXEMPT',...await readable(panel)})
 }
 async function searchGroup(groupId){
  const label=f.group_labels[groupId]
  await pairWorkspace().getByLabel('Cari SKU atau merek',{exact:true}).fill(label.sku)
  const pending=page.waitForResponse(response=>rpc(RPC.master)(response)&&args(response).p_filters?.query===label.sku)
  await pairWorkspace().getByRole('button',{name:'Cari / muat ulang',exact:true}).click();await success(pending)
  return pairWorkspace().getByRole('row').filter({has:page.getByRole('button',{name:'Atur padanan '+label.sku,exact:true})})
 }
 async function editPair(groupId){
  const row=await searchGroup(groupId);await expect(row).toHaveCount(1)
  const pending=page.waitForResponse(response=>rpc(RPC.master)(response)&&args(response).p_filters?.pair_source_id===groupId)
  await row.getByRole('button',{name:'Atur padanan '+f.group_labels[groupId].sku,exact:true}).click();await success(pending);await expect(pairing()).toBeVisible()
 }
 async function choosePair(target){
  if(target){const query=f.group_labels[target].sku;await pairing().getByLabel('Cari padanan',{exact:true}).fill(query)
   const pending=page.waitForResponse(response=>rpc(RPC.master)(response)&&args(response).p_filters?.pair_query===query)
   await pairing().getByRole('button',{name:'Cari padanan',exact:true}).click();await success(pending)
  }
  await pairing().getByLabel('SKU padanan',{exact:true}).selectOption(target||'')
  await pairing().getByLabel('Alasan padanan',{exact:true}).fill('Padanan lintas merek diperiksa melalui layar owner29')
  const pending=page.waitForResponse(response=>rpc(RPC.pair)(response)&&args(response).p_action==='SAVE_PAIR')
  await pairing().getByRole('button',{name:'Simpan padanan dua arah',exact:true}).click();const result=await success(pending)
  await expect(pairing().getByRole('button',{name:'Simpan padanan dua arah',exact:true})).toBeEnabled()
  return result
 }
 async function searchTarget(query){
  await destination().getByLabel('Cari SKU tujuan',{exact:true}).fill(query)
  const pending=page.waitForResponse(response=>rpc(RPC.read)(response)&&args(response).p_filters?.target_query===query)
  await destination().getByRole('button',{name:'Cari tujuan',exact:true}).click();return success(pending)
 }
 async function selectTarget(id){
  const pending=page.waitForResponse(response=>rpc(RPC.read)(response)&&args(response).p_filters?.selection?.target_product_id===id)
  await destination().getByLabel('SKU tujuan',{exact:true}).selectOption(id);const value=await success(pending)
  await expect(destination().getByLabel('SKU tujuan',{exact:true})).toHaveValue(id);return value
 }
 async function selectSource(){
  await conversion().getByLabel('Cari SKU asal',{exact:true}).fill(f.products.source.sku)
  let pending=page.waitForResponse(response=>rpc(RPC.read)(response)&&args(response).p_filters?.query===f.products.source.sku)
  await conversion().getByRole('button',{name:'Cari SKU asal',exact:true}).click();await success(pending)
  pending=page.waitForResponse(response=>rpc(RPC.read)(response)&&args(response).p_filters?.selection?.source_product_id===f.source)
  await conversion().getByLabel('SKU asal dan gudang',{exact:true}).selectOption(f.source+':'+f.location);await success(pending)
 }
 async function openConversion(){await menu(page,'Gudang','Ganti Merek');await expect(conversion().getByRole('heading',{name:'Ganti Merek / SKU',exact:true})).toBeVisible();await expect(conversion().getByLabel('SKU asal dan gudang',{exact:true})).toBeEnabled()}
 async function openInverse(member){
  const row=history().getByRole('row').filter({hasText:member.number});await expect(row).toHaveCount(1)
  await row.getByRole('button',{name:'Batalkan '+f.products.source.sku,exact:true}).click()
  await history().getByLabel('Alasan pembatalan',{exact:true}).fill('Seluruh perubahan fisik dikembalikan setelah turunan sah dibatalkan')
  await expect(history()).toContainText('Seluruh konversi 4 PCS akan dibatalkan bersama.')
 }
 try{
  await menu(page,'Master Data','Produk & SKU');await expect(pairWorkspace().getByRole('heading',{name:'Produk & SKU',exact:true})).toBeVisible()
  const beforePair=state('BEFORE_PAIR')
  await editPair(groupSource);const pair=await choosePair(groupTarget);assert.equal(pair.source_group_id,groupSource);assert.equal(pair.target_group_id,groupTarget)
  let row=await searchGroup(groupSource);await expect(row).toContainText(f.group_labels[groupTarget].brand_name+' · '+f.group_labels[groupTarget].sku)
  const first=state('PAIR_FIRST');pairOnly(beforePair,first,groupSource,groupTarget,1)
  row=await searchGroup(groupTarget);await expect(row).toContainText(f.group_labels[groupSource].brand_name+' · '+f.group_labels[groupSource].sku)
  await editPair(groupTarget);await expect(pairing().getByLabel('SKU padanan',{exact:true})).toHaveValue(groupSource)
  await shot('PAIR_TWO_SIDES',pairing())
  await choosePair(groupSource);const duplicate=state('PAIR_REVERSE_DUPLICATE');pairOnly(first,duplicate,groupSource,groupTarget,1)
  assert.equal(duplicate.pairs.length,1)
  await choosePair(null);const unpaired=state('PAIR_DELETE_REVERSE_SIDE');pairOnly(duplicate,unpaired,groupTarget,null,1)
  row=await searchGroup(groupSource);await expect(row).toContainText('Belum ada')
  row=await searchGroup(groupTarget);await expect(row).toContainText('Belum ada')
  progress.pair={one_group_relation_for_all_sizes:true,both_sides_visible:true,reverse_input_one_canonical_pair:true,delete_from_reverse_side:true,
   source_sizes:f.group_labels[groupSource].members.map(m=>m.size),target_sizes:f.group_labels[groupTarget].members.map(m=>m.size),all_non_pair_rows_sequences_and_catalog_unchanged:true}

  await openConversion();await selectSource()
  await searchTarget(f.products.other.sku);await selectTarget(f.other)
  const writesBefore=calls.length,previewsBefore=reads.filter(call=>call.args.p_filters?.preview).length
  const browse=await searchTarget(f.products.target.sku)
  assert.equal(browse.selection.target_product_id,null);assert.ok(!browse.targets.some(target=>target.id===f.other))
  await expect(destination().getByLabel('SKU tujuan',{exact:true})).toHaveValue('')
  await expect(destination().getByRole('button',{name:'Lihat pratinjau',exact:true})).toBeDisabled()
  await expect(destination().getByRole('button',{name:'Catat konversi fisik',exact:true})).toHaveCount(0)
  assert.equal(calls.length,writesBefore);assert.equal(reads.filter(call=>call.args.p_filters?.preview).length,previewsBefore)
  const selected=await selectTarget(f.target)
  assert.deepEqual(selected.selection.source_stock,{physical:10,reserved:1,available:9});assert.deepEqual(selected.selection.target_stock,{physical:4,reserved:0,available:4})
  assert.ok(selected.targets.find(target=>target.id===f.target)?.recommended===false,'NONPADANAN_REQUIRED')
  await expect(destination().getByLabel('SKU tujuan',{exact:true}).locator('option:checked')).toContainText(f.products.target.brand)
  await expect(destination().getByLabel('SKU tujuan',{exact:true}).locator('option:checked')).toContainText('ukuran '+f.products.target.size)
  await destination().getByLabel('Jumlah PCS',{exact:true}).fill('4')
  await destination().getByLabel('Waktu fisik · WIB',{exact:true}).fill(f.physical_local)
  await destination().getByLabel('Alasan',{exact:true}).fill('Koreksi fisik campuran merek dan ukuran lewat layar owner29')
  await expect(destination()).toContainText('Asal · fisik 10 → 6 PCS · tersedia 9 PCS · dicadangkan 1 PCS.')
  await expect(destination()).toContainText('Tujuan · fisik 4 → 8 PCS · tersedia 4 PCS · dicadangkan 0 PCS.')
  const beforePreview=state('BEFORE_PREVIEW')
  const pendingPreview=page.waitForResponse(response=>rpc(RPC.read)(response)&&args(response).p_filters?.preview?.target_product_id===f.target)
  await destination().getByRole('button',{name:'Lihat pratinjau',exact:true}).click();const reviewed=await success(pendingPreview)
  previewOracle(reviewed.preview,f);const afterPreview=state('AFTER_PREVIEW');equalCensus(beforePreview.census,afterPreview.census)
  await expect(destination()).toContainText('nilai sumber Rp60,06');await expect(destination()).toContainText('Reservasi tetap.')
  await shot('FIFO_PREVIEW',destination())
  progress.selection={old_invisible_target_cleared_no_preview_or_write:true,selected_brand_and_size_visible:true,nonpadanan_different_model_and_size:true,preview_full22_rows_and_sequences_unchanged:true}

  const endpoint='**/rest/v1/rpc/'+RPC.write
  if(!mobile){
   await page.route(endpoint,async route=>{
    if(route.request().postDataJSON().p_action!=='POST')return route.continue()
    // Forward an unexpected second request to the real server as well. The
    // exact request count below must fail; do not fabricate its response.
    if(firstBody!==undefined)return route.continue()
    firstBody=route.request().postDataJSON();const response=await route.fetch()
    if(response.status()!==200)return route.fulfill({response})
    lostResponse=await response.json();expectedNetwork.push({url:route.request().url(),text:'Failed to load resource: net::ERR_FAILED',reason:'ONE_REAL_SUCCESSFUL_COMMITTED_REPLY_DELIBERATELY_LOST'})
    await route.abort('failed')
   })
   await destination().getByRole('button',{name:'Catat konversi fisik',exact:true}).dblclick()
   await expect(conversion().getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeEnabled();assert.ok(lostResponse)
   const committed=state('LOST_COMMITTED_REPLY');postedOracle(committed,f,lostResponse)
   await page.unroute(endpoint);await page.reload();await openConversion()
   const retry=page.waitForResponse(response=>rpc(RPC.write)(response)&&args(response).p_action==='POST')
   await conversion().getByRole('button',{name:'Reconcile transaksi',exact:true}).click();const response=await retry
   replayBody=args(response);made=await success(Promise.resolve(response));assert.deepEqual(replayBody,firstBody);assert.deepEqual(made,lostResponse)
   await expect(conversion().getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0)
   const recovered=state('RECONCILED_SAME_UUID');equalCensus(committed.census,recovered.census);postedOracle(recovered,f,made)
  }else{
   const pending=page.waitForResponse(response=>rpc(RPC.write)(response)&&args(response).p_action==='POST')
   await destination().getByRole('button',{name:'Catat konversi fisik',exact:true}).dblclick();made=await success(pending)
  }
  await expect(conversion().getByRole('button',{name:'Muat ulang',exact:true})).toBeEnabled()
  let posted=state('POSTED');postedOracle(posted,f,made)
  assert.equal(calls.filter(call=>call.rpc===RPC.write&&call.args.p_action==='POST').length,mobile?1:2)
  await selectSource();await searchTarget(f.products.target.sku);const current=await selectTarget(f.target)
  assert.deepEqual(current.selection.source_stock,{physical:6,reserved:1,available:5});assert.deepEqual(current.selection.target_stock,{physical:8,reserved:0,available:8})
  await destination().getByLabel('Jumlah PCS',{exact:true}).fill('')
  await expect(destination()).toContainText('Asal · fisik 6 → — PCS · tersedia 5 PCS · dicadangkan 1 PCS.')
  await expect(history()).toContainText('dari konversi 4 PCS. Pembatalan berlaku untuk seluruh konversi.')
  progress.post={one_complete_group_two_Native_parts_value:'60.06',source_available:5,source_reserved:1,target_physical:8,
   actual_double_click_one_new_group:true,actual_lost_committed_reply_same_UUID_after_reload:!mobile,all_read_after_replay_rows_sequences_catalog_unchanged:!mobile}

  const active=fixture('block_inverse',{fixture:f});const blockedBefore=state('ACTIVE_DRAFT_BEFORE_REFUSAL')
  await openInverse(posted.members[0])
  const pendingRefusal=page.waitForResponse(response=>rpc(RPC.write)(response)&&args(response).p_action==='REVERSE')
  await history().getByRole('button',{name:'Konfirmasi pembatalan',exact:true}).click();const refused=await pendingRefusal
  assert.equal(refused.status(),400);const refusal=await refused.json();assert.equal(refusal.code,'P0001');assert.match(refusal.message,/downstream/i)
  expectedNetwork.push({url:refused.url(),text:'Failed to load resource: the server responded with a status of 400 (Bad Request)',reason:'VERIFIED_NATIVE_ACTIVE_DOWNSTREAM_REFUSAL'})
  await expect(conversion().getByRole('alert')).toBeVisible();await expect(conversion().getByRole('button',{name:'Muat ulang',exact:true})).toBeEnabled()
  const blockedAfter=state('ACTIVE_DRAFT_AFTER_REFUSAL');equalCensus(blockedBefore.census,blockedAfter.census)
  assert.deepEqual(blockedAfter.ledgers,blockedBefore.ledgers);assert.ok(blockedAfter.members.every(member=>member.status==='POSTED'))
  await shot('ACTIVE_DRAFT_REFUSAL',history())
  fixture('release_inverse',{fixture:f,sale_id:active.sale_id})
  await openInverse(posted.members[1]);const pendingInverse=page.waitForResponse(response=>rpc(RPC.write)(response)&&args(response).p_action==='REVERSE')
  await history().getByRole('button',{name:'Konfirmasi pembatalan',exact:true}).click();const reversed=await success(pendingInverse)
  assert.deepEqual(new Set(reversed.conversion_ids),new Set(made.conversion_ids))
  await expect(conversion().getByRole('button',{name:'Muat ulang',exact:true})).toBeEnabled()
  const final=state('WHOLE_GROUP_REVERSED')
  assert.deepEqual(final.source,{physical:10,reserved:1,available:9});assert.deepEqual(final.target,{physical:4,reserved:0,available:4})
  assert.deepEqual(final.accounts,f.baseline_accounts);assert.equal(final.groups.length,1);assert.equal(final.members.length,2)
  assert.ok(final.members.every(member=>member.status==='REVERSED'));assert.deepEqual(final.pairs,[])
  assert.equal(final.census.catalog_sha256,beforePair.census.catalog_sha256)
  await expect(history()).toContainText('REVERSED');await shot('WHOLE_GROUP_REVERSED',history())
  assert.equal(calls.filter(call=>call.rpc===RPC.pair).length,3);assert.equal(calls.filter(call=>call.rpc===RPC.write&&call.args.p_action==='REVERSE').length,2)
  const consoleEvidence=requireConsoleEvidence(capture,expectedNetwork)
  return{status:'PASS',actual_Auth_form_normal_full_App:true,actual_public_PostgREST:true,role:mobile?'ADMIN':'OWNER',viewport:mobile?390:1440,
   ...progress,actual_active_Native_draft_use:active,actual_UI_refusal_zero_all22_rows_sequences_effect:true,actual_UI_whole_group_inverse_from_other_member:true,
   final_source:final.source,final_target:final.target,Native_financial_accounts_restored:true,console_evidence:consoleEvidence,unexpected_console_errors:0,
   console_capture_scope:'FEATURE_JOURNEY_AFTER_REAL_LOGIN_HOST_SEPARATELY_CAPTURES_PAGE_ERRORS_FROM_CONTEXT_CREATION',
   visible_text_contrast:contrasts,no_horizontal_page_overflow_at_feature_checkpoints:true,screenshots:shots,source_pins:source,write_requests:calls,read_requests:reads,
   prerequisite_creation:f.preparation,active_sale_fixture_not_screen_creation:true,full_manual_group_accessory_recovery_claim:false,
   expected_returns_first_child_limitation_not_closed:true,outer_full_backup_Auth_restore_still_required:true,production_go:false,independent_acceptance:false}
 }catch(error){
  mkdirSync('cp6-proof/t3',{recursive:true});let actual;try{actual=state('FAILURE')}catch(e){actual={error:String(e)}}
  writeFileSync(`cp6-proof/t3/SKU29_${suffix}_${run}_FIRST_FAILURE.json`,JSON.stringify({error:String(error),stack:error.stack,progress,actual,calls,reads,
   console_errors:capture.errors,page_errors:capture.pageErrors,expected_network:expectedNetwork,screenshots:shots,text:await page.locator('main').innerText().catch(()=>''),source},null,2)+'\n')
  await page.screenshot({path:`cp6-proof/t3/SKU29_${suffix}_${run}_FIRST_FAILURE.png`,fullPage:true}).catch(()=>{});throw error
 }finally{capture.stop();page.off('request',writeListener);await page.unroute('**/rest/v1/rpc/'+RPC.write).catch(()=>{});await user.context.close()}
}

export function cases(ui,today){admitted();return IDS.map((id,index)=>[id,()=>journey(ui,today,index===1)])}
