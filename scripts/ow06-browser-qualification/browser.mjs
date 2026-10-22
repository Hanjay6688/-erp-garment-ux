import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'

export const IDS=['OW06_DESKTOP_TRANSFER_TWO_RECEIPTS_LOST_REPLY_CORRECT_REVERSE','OW06_MOBILE390_TRANSFER_TWO_RECEIPTS_CORRECT_REVERSE']
const fixed=(op,args)=>JSON.parse(execFileSync('python',['../auditor/scripts/ow06-browser-qualification/fixture.py',op],
 {cwd:'../writer',input:JSON.stringify(args),encoding:'utf8',maxBuffer:8*1024*1024}).trim())
const SAVE='erp_cp7_save_supplier_transfer_v1',endpoint='**/rest/v1/rpc/'+SAVE
const isSave=r=>r.url().endsWith('/rpc/'+SAVE)
async function response(promise){const r=await promise;assert.equal(r.status(),200,await r.text());return r.json()}
async function procurementMenu(page){const open=page.getByRole('button',{name:'Buka menu',exact:true});if(await open.isVisible())await open.click()
 const link=page.getByRole('button',{name:'• Pembelian & Penerimaan',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click();await link.click()}

async function journey(ui,today,mobile){
 const f=fixed('prepare',{today}),suffix=mobile?'MOBILE390':'DESKTOP'
 const user=await ui.login('OWNER',{label:'ow06-'+(mobile?'phone':'desktop'),mobile,timezoneId:'America/Los_Angeles'}),page=user.page,expect=ui.expect,requests=[]
 page.on('request',r=>{if(isSave(r))requests.push(r.postDataJSON())})
 const observe=()=>fixed('observe',{fixture:f})
 const panel=()=>page.getByRole('region',{name:'Transfer supplier',exact:true})
 const create=()=>panel().getByRole('form',{name:'Transfer supplier baru',exact:true})
 const correct=()=>panel().getByRole('form',{name:'Koreksi transfer supplier',exact:true})
 const [first,second]=f.numbers
 async function open(){await procurementMenu(page);await page.getByLabel('Cari penerimaan',{exact:true}).fill(first)
  await page.getByRole('button',{name:'Cari penerimaan',exact:true}).click();await page.locator('button.cproc-receipt').filter({hasText:first}).click()
  await expect(panel().getByRole('button',{name:'Muat ulang transfer supplier',exact:true})).toBeEnabled()}
 async function fill(form,amounts,reason){
  // Cross-search retention: the second receipt is found by a new search, the first amount stays chosen.
  for(const [number,amount] of [[first,amounts[0]],[second,amounts[1]]]){
   await form.getByLabel('Cari penerimaan untuk transfer',{exact:true}).fill(number)
   await form.getByRole('button',{name:'Cari penerimaan untuk transfer',exact:true}).click()
   await form.getByLabel('Dibayar untuk '+number,{exact:true}).fill(amount)}
  await expect(form.getByRole('region',{name:'Alokasi transfer terpilih',exact:true})).toContainText(first)
  await expect(form.getByRole('region',{name:'Alokasi transfer terpilih',exact:true})).toContainText(second)
  await form.getByLabel('Waktu transfer supplier WIB',{exact:true}).fill(f.at_local)
  await form.getByLabel('Cari rekening transfer supplier',{exact:true}).fill(f.bank_code)
  await form.getByRole('button',{name:'Cari rekening transfer',exact:true}).click()
  await form.getByRole('button',{name:`${f.bank_code} · ${f.bank_name}`,exact:true}).click()
  await form.getByLabel('Keterangan transfer supplier',{exact:true}).fill(reason)
  await form.getByLabel('Transfer supplier sudah diperiksa',{exact:true}).check()}
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});await open();const start=observe()
  assert.equal(Number(start.cash_delta),0);assert.equal(start.transfers.length,0)
  await panel().getByRole('button',{name:'Buat transfer supplier baru',exact:true}).click()
  await fill(create(),['400','600'],'Satu transfer bank untuk dua surat jalan')
  await expect(create()).toContainText('Total transfer Rp1.000')
  const sahkan=create().getByRole('button',{name:'Sahkan transfer supplier',exact:true});await expect(sahkan).toBeEnabled()
  let made
  if(!mobile){let intercepted
   await page.route(endpoint,async route=>{try{const r=await route.fetch();intercepted={status:r.status()};if(r.status()===200){made=await r.json();await route.abort('failed')}else await route.fulfill({response:r})}catch(error){intercepted={error:String(error)};await route.abort('failed')}})
   await sahkan.click();await expect.poll(()=>intercepted!==undefined).toBe(true);assert.equal(intercepted.status,200,JSON.stringify(intercepted))
   await expect(panel().getByRole('button',{name:'Periksa status transfer supplier',exact:true})).toBeEnabled()
   assert.equal(observe().transfers.length,1)
   const request=structuredClone(requests[0]);await page.unroute(endpoint);await page.reload();await open()
   const reconcile=panel().getByRole('button',{name:'Periksa status transfer supplier',exact:true});await expect(reconcile).toBeEnabled()
   const again=page.waitForResponse(isSave);await reconcile.click();const replay=await response(again)
   assert.deepEqual(replay,made);assert.deepEqual(requests[1],request)
  }else{const waiting=page.waitForResponse(isSave);await sahkan.click();made=await response(waiting)}
  const created=observe()
  assert.equal(Number(created.cash_delta),-1000);assert.deepEqual(f.receipts.map(id=>Number(created.paid[id])),[400,600])
  assert.deepEqual(created.journals,[['POSTED','1000.00','1000.00','2']]);assert.equal(created.transfers.length,1);assert.equal(created.contexts,0)
  const number=created.transfers[0][0]
  await panel().getByRole('button',{name:'Buka transfer '+number,exact:true}).click()
  const detail=()=>panel().getByRole('region',{name:'Rincian transfer '+number,exact:true})
  await expect(detail()).toContainText('Kas keluar satu kali');await expect(detail()).toContainText(first);await expect(detail()).toContainText(second)
  await detail().getByRole('button',{name:'Koreksi transfer '+number,exact:true}).click()
  await fill(correct(),['250','500'],'Nilai transfer dibetulkan sesuai bukti bank')
  let waiting=page.waitForResponse(isSave)
  await correct().getByRole('button',{name:'Sahkan koreksi transfer supplier',exact:true}).click()
  const fixedReply=await response(waiting);assert.notEqual(fixedReply.transfer_id,made.transfer_id)
  const corrected=observe()
  assert.equal(Number(corrected.cash_delta),-750);assert.deepEqual(f.receipts.map(id=>Number(corrected.paid[id])),[250,500])
  assert.deepEqual(corrected.transfers.map(x=>x[1]),['REVERSED','POSTED'])
  const replacement=corrected.transfers[1][0]
  await panel().getByRole('button',{name:'Buka transfer '+replacement,exact:true}).click()
  await panel().getByRole('region',{name:'Rincian transfer '+replacement,exact:true}).getByRole('button',{name:'Batalkan transfer '+replacement,exact:true}).click()
  const cancel=panel().getByRole('region',{name:'Batalkan transfer supplier',exact:true})
  await cancel.getByLabel('Alasan pembatalan transfer supplier',{exact:true}).fill('Transfer dibatalkan bank, dana kembali')
  await cancel.getByLabel('Pembatalan transfer supplier sudah diperiksa',{exact:true}).check()
  waiting=page.waitForResponse(isSave);await cancel.getByRole('button',{name:'Balikkan transfer supplier sekarang',exact:true}).click();await response(waiting)
  const end=observe()
  assert.equal(Number(end.cash_delta),0);assert.deepEqual(f.receipts.map(id=>Number(end.paid[id])),[0,0])
  assert.deepEqual(end.transfers.map(x=>x[1]),['REVERSED','REVERSED']);assert.equal(end.contexts,0)
  const actions=requests.map(r=>r.p_payload.action)
  assert.deepEqual(actions,mobile?['CREATE','CORRECT','REVERSE']:['CREATE','CREATE','CORRECT','REVERSE'])
  assert.deepEqual(requests.find(r=>r.p_payload.action==='CREATE').p_payload.allocations.map(a=>a.amount),['400.00','600.00'])
  const viewport=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}))
  assert.ok(viewport.scroll<=viewport.width+1,JSON.stringify(viewport));if(mobile)assert.equal(viewport.width,390)
  await page.screenshot({path:`cp6-proof/t3/CP7_OW06_TRANSFER_${suffix}.png`,fullPage:true})
  return {status:'PASS',real_login:true,fixture_created_by_Native_SQL:true,all_journey_writes_from_actual_UI:true,timezone:'America/Los_Angeles',
   mobile,viewport,created:'400.00+600.00',bank_after_create:'-1000.00',lost_committed_reply_same_UUID_recovered:!mobile,
   corrected:'250.00+500.00',bank_after_correction:'-750.00',reversed_whole_transfer:true,bank_after_reverse:'0.00',
   second_receipt_chosen_after_new_search:true,production_go:false}
 }catch(error){writeFileSync(`cp6-proof/t3/CP7_OW06_TRANSFER_${suffix}_FAILURE.json`,JSON.stringify({error:String(error),stack:error.stack,
   text:await page.locator('main').innerText().catch(()=>''),state:(()=>{try{return observe()}catch(e){return String(e)}})(),requests},null,2))
  await page.screenshot({path:`cp6-proof/t3/CP7_OW06_TRANSFER_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw error}
 finally{await page.unroute(endpoint).catch(()=>{});await user.context.close()}
}
export async function cases(ui,today){return IDS.map((id,i)=>[id,()=>journey(ui,today,Boolean(i))])}
