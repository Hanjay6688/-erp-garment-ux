// Fresh real Auth/JWT -> public PostgREST -> committed AP -> original browser UI.
import assert from 'node:assert/strict'
import { execFileSync, spawn } from 'node:child_process'
import { randomBytes, randomUUID } from 'node:crypto'
import { writeFileSync } from 'node:fs'
import http from 'node:http'
import { resolve } from 'node:path'
import { chromium, expect } from '@playwright/test'

assert.equal(process.env.CP6_AP_FLOW_CONFIRM,'cp6_rollback')
const pg='postgresql://postgres:postgres@127.0.0.1:54322/cp6_rollback'
const root=process.cwd(), dir=resolve('cp6-proof/ap-flow'), origin='http://127.0.0.1:4176', api='http://127.0.0.1:54328'
const anon=process.env.SUPABASE_ANON_KEY, service=process.env.SUPABASE_SERVICE_ROLE_KEY
assert.ok(anon&&service)
const users=[], secrets=[anon,service], cases=[]
const report={status:'INCOMPLETE',classification:'WRITER_REAL_AUTH_BROWSER_AP',cases,production_go:false,independent_acceptance:false,
  product_responses_mocked:false,phase:'SETUP',console_errors:[]}
const sql=s=>execFileSync('psql',[pg,'-X','-qAt','-v','ON_ERROR_STOP=1','-c',s],{encoding:'utf8',stdio:['ignore','pipe','pipe']}).trim()
const q=v=>"'"+String(v).replaceAll("'","''")+"'"
const native=mode=>JSON.parse(execFileSync('python',['scripts/cp6_ap_flow_fixture.py',mode],{encoding:'utf8',stdio:['ignore','pipe','pipe']}))
const fixture=native('identities')
const save=()=>writeFileSync(resolve(dir,'FLOW.json'),JSON.stringify(report,null,2)+'\n')
function phase(id){report.phase=id;save();console.log('AP flow: '+id)}
function pass(id,detail={}){assert.ok(!cases.some(c=>c.id===id));cases.push({id,status:'PASS',...detail});save()}
function safe(value){let text=String(value);for(const s of secrets)text=text.replaceAll(s,'[REDACTED]');return text.replace(/eyJ[\w-]+\.[\w-]+\.[\w-]+/g,'[JWT]')}
const cents=v=>{const text=String(v),sign=text.startsWith('-')?-1n:1n,[whole,fraction='']=text.replace(/^-/,'').split('.');return sign*(BigInt(whole)*100n+BigInt(fraction.padEnd(2,'0').slice(0,2)))}
const delta=(before,after,key)=>cents(after.ledger[key])-cents(before.ledger[key])

async function auth(path,body,admin=false,method='POST'){
  const res=await fetch('http://127.0.0.1:54321/auth/v1/'+path,{method,headers:{apikey:admin?service:anon,
    Authorization:`Bearer ${admin?service:anon}`,'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)})
  assert.ok(res.ok,`AUTH_${method}_${res.status}`);return res.status===204?{}:res.json()
}
async function user(label){
  const email=`cp6-ap-${label}-${randomUUID()}@example.invalid`,password=`Ap!${randomBytes(24).toString('hex')}`
  secrets.push(email,password)
  const created=await auth('admin/users',{email,password,email_confirm:true},true)
  const u={id:created.id,email,password,label};users.push(u)
  const session=await auth('token?grant_type=password',{email,password});u.token=session.access_token;secrets.push(u.token)
  return u
}
async function request(token,name,args){
  const response=await fetch('http://127.0.0.1:54329/rpc/'+name,{method:'POST',headers:{apikey:anon,
    Authorization:`Bearer ${token||anon}`,'Content-Type':'application/json'},body:JSON.stringify(args)})
  return {status:response.status,value:await response.json()}
}
async function rpc(token,name,args){const r=await request(token,name,args);assert.equal(r.status,200,`${name}: ${JSON.stringify(r.value)}`);return r.value}
const command=(token,family,action,payload,key=randomUUID())=>rpc(token,`erp_save_${family}_action_v1`,{p_action:action,p_payload:payload,p_client_request_id:key})
async function mapUser(owner,u,active=true){
  const role=await rpc(owner.token,'erp_save_role_v1',{p_payload:{code:'AP_'+randomBytes(6).toString('hex').toUpperCase(),name:'Disposable AP '+u.label,
    description:'Fresh transport permission proof',permission_keys:['settings.erp.view','finance.contractor_accessory.view'],confirm_high_risk:true,change_reason:'Disposable role'},p_client_request_id:randomUUID(),p_expected_version:null})
  await rpc(owner.token,'erp_save_app_user_v3',{p_payload:{auth_user_id:u.id,full_name:'AP '+u.label,role_id:role.role_id,is_active:active,change_reason:'Disposable mapping'},p_client_request_id:randomUUID(),p_expected_version:null})
}

let proxy,preview,browser,owner,page,failure
const safeEnv=Object.fromEntries(['PATH','HOME','CI','TMPDIR','RUNNER_TEMP','PLAYWRIGHT_BROWSERS_PATH'].filter(k=>process.env[k]).map(k=>[k,process.env[k]]))
async function start(){
  proxy=http.createServer((req,res)=>{
    const allowed=req.headers.origin===origin,cors=allowed?{'access-control-allow-origin':origin,vary:'Origin',
      'access-control-allow-headers':'authorization,apikey,content-type,x-client-info,x-supabase-api-version,accept-profile,content-profile',
      'access-control-allow-methods':'GET,POST,PUT,DELETE,OPTIONS'}:{}
    if(req.method==='OPTIONS'){res.writeHead(allowed?204:403,cors);res.end();return}
    const isAuth=req.url.startsWith('/auth/v1/'),isRest=req.url.startsWith('/rest/v1/rpc/')
    if(!isAuth&&!isRest){res.writeHead(404,cors);res.end();return}
    const headers={...req.headers};delete headers.host;delete headers.origin
    const upstream=http.request({hostname:'127.0.0.1',port:isAuth?54321:54329,path:isAuth?req.url:req.url.slice(8),method:req.method,headers},reply=>{
      const clean={...reply.headers,...cors};delete clean['access-control-allow-credentials']
      res.writeHead(reply.statusCode,clean);reply.pipe(res)
    })
    upstream.on('error',()=>{if(!res.headersSent)res.writeHead(502,cors);res.end()});req.pipe(upstream)
  })
  await new Promise((ok,no)=>{proxy.once('error',no);proxy.listen(54328,'127.0.0.1',ok)})
  await expect.poll(async()=>{try{return (await fetch('http://127.0.0.1:54329/')).status}catch{return 0}},{timeout:30000}).toBe(200)
  execFileSync('npm',['run','build:cp6-disposable'],{env:{...safeEnv,VITE_ERP_RUNTIME_MODE:'DISPOSABLE_TEST',VITE_SUPABASE_URL:api,VITE_SUPABASE_ANON_KEY:anon},stdio:['ignore','pipe','pipe']})
  preview=spawn(resolve('node_modules/.bin/vite'),['preview','--outDir','cp6-ui-build','--host','127.0.0.1','--port','4176','--strictPort'],{env:safeEnv,stdio:'ignore'})
  await expect.poll(async()=>{try{return(await fetch(origin)).status}catch{return 0}},{timeout:15000}).toBe(200)
  const smoke=(...args)=>execFileSync('npx',['--yes','agent-browser@0.38.0','--session','cp6-ap-flow','--executable-path',chromium.executablePath(),...args],
    {env:{...safeEnv,AGENT_BROWSER_AUTOSAVE_INTERVAL_MS:'0'},encoding:'utf8',timeout:60000,stdio:['ignore','pipe','pipe']})
  try{smoke('open',origin);assert.ok(smoke('snapshot','-i').includes('Email akun ERP'));pass('REAL_LOGIN_PAGE')}finally{smoke('close')}
  browser=await chromium.launch()
}
async function login(u,mobile=false){
  const context=await browser.newContext({viewport:mobile?{width:390,height:844}:{width:1440,height:1000},timezoneId:'Pacific/Honolulu',isMobile:mobile,hasTouch:mobile})
  await context.route('**/*',route=>[origin,api].includes(new URL(route.request().url()).origin)?route.continue():route.abort('blockedbyclient'))
  const p=await context.newPage();p.setDefaultTimeout(20000)
  p.on('pageerror',e=>report.console_errors.push(safe(e.message)))
  await p.goto(origin);await p.getByLabel('Email akun ERP').fill(u.email);await p.getByLabel('Kata sandi').fill(u.password)
  await p.getByRole('button',{name:'Masuk',exact:true}).click();await expect(p.locator('.top-title strong')).toBeVisible()
  return p
}
async function nav(p,name,group){
  const menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
  const link=p.getByRole('button',{name:'• '+name,exact:true})
  if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:group}).click()
  await link.click();await expect(p.getByRole('heading',{name,exact:true})).toBeVisible()
  await expect(p.getByRole('button',{name:'Muat ulang',exact:true})).toBeEnabled()
}
async function mutate(p,label,family,action,{lost=false}={}){
  const matches=req=>req.url().endsWith(`/rpc/erp_save_${family}_action_v1`)&&req.method()==='POST'&&req.postDataJSON()?.p_action===action
  if(!lost){
    const response=p.waitForResponse(r=>matches(r.request()));await p.getByRole('button',{name:label,exact:true}).click()
    const r=await response,v=await r.json();assert.equal(r.status(),200,JSON.stringify(v));
    await expect(p.getByRole('button',{name:'Muat ulang',exact:true})).toBeEnabled()
    return {value:v,args:r.request().postDataJSON()}
  }
  let original,committed
  await p.route(`**/rpc/erp_save_${family}_action_v1`,async route=>{
    assert.ok(matches(route.request()));original=route.request().postDataJSON()
    const response=await route.fetch();assert.equal(response.status(),200);committed=await response.json()
    await route.abort('connectionreset')
  },{times:1})
  await p.getByRole('button',{name:label,exact:true}).click()
  await expect(p.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeEnabled()
  const committedState=native('boundary')
  await nav(p,'Kain kantong','Gudang')
  await expect(p.getByRole('button',{name:'Sahkan pengurangan stok',exact:true})).toBeDisabled()
  await expect(p.getByRole('alert').filter({hasText:'belum selesai'})).toBeVisible()
  await p.reload();await nav(p,'Impor data awal','Pengaturan & Audit')
  const replay=p.waitForResponse(r=>matches(r.request()))
  await p.getByRole('button',{name:'Reconcile transaksi',exact:true}).click()
  const r=await replay;assert.equal(r.status(),200);assert.deepEqual(r.request().postDataJSON(),original)
  assert.deepEqual(await r.json(),committed);assert.deepEqual(native('boundary'),committedState)
  await expect(p.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0)
  pass('IMPORT_LOST_REPLY_RELOAD_GLOBAL_LOCK',{exact_uuid_payload_replayed:true,full_erp_boundary_unchanged_on_replay:true})
  return {value:committed,args:original}
}
async function upload(entity,text){
  await page.getByRole('combobox',{name:/^Jenis data/}).selectOption(entity)
  await page.getByLabel('Pilih file CSV',{exact:true}).setInputFiles({name:entity+'.csv',mimeType:'text/csv',buffer:Buffer.from(text)})
  await mutate(page,'Simpan perubahan draft','initial_import','SAVE_FILE')
  await expect(page.getByRole('button',{name:'Simpan perubahan draft',exact:true})).toHaveCount(0)
}
async function importFlow(){
  phase('IMPORT_BROWSER');await nav(page,'Impor data awal','Pengaturan & Audit')
  const code='UI-'+randomUUID().slice(0,12),customer='CU'+randomBytes(6).toString('hex')
  await page.getByLabel('Kode batch',{exact:true}).fill(code);await page.getByLabel('Tanggal saldo awal',{exact:true}).fill(fixture.day)
  const created=await mutate(page,'Buat draft','initial_import','CREATE');const batch=created.value.batch_id
  await upload('CUSTOMER',`customer_code,customer_name\n${customer},Pelanggan browser\n`)
  await upload('OPENING_BALANCE_ITEM',`balance_type,customer_code,amount,control_key\nCUSTOMER_RECEIVABLE,${customer},14.25,AR\n`)
  await upload('OPENING_CONTROL','control_key,balance_type,amount\nAR,CUSTOMER_RECEIVABLE,14.25\n')
  const before=native('state')
  await mutate(page,'Periksa seluruh draft','initial_import','VALIDATE')
  await expect(page.getByRole('button',{name:'Sahkan data awal',exact:true})).toBeEnabled()
  pass('IMPORT_REAL_CSV_PREVIEW_VALIDATE',{files:3,batch})
  await page.getByRole('combobox',{name:/^Jenis data/}).selectOption('OPENING_BALANCE_ITEM')
  await page.getByLabel('Nominal, baris 2',{exact:true}).fill('17.25')
  await mutate(page,'Simpan perubahan draft','initial_import','SAVE_FILE')
  await mutate(page,'Periksa seluruh draft','initial_import','VALIDATE')
  await expect(page.getByRole('button',{name:'Sahkan data awal',exact:true})).toBeDisabled()
  assert.deepEqual(native('state').all_ledger,before.all_ledger)
  pass('IMPORT_EDIT_AFTER_VALIDATE_MISMATCH_BLOCKED',{journal_unchanged:true})
  await page.getByRole('combobox',{name:/^Jenis data/}).selectOption('OPENING_CONTROL')
  await page.getByLabel('Total nominal, baris 2',{exact:true}).fill('17.25')
  await mutate(page,'Simpan perubahan draft','initial_import','SAVE_FILE');await mutate(page,'Periksa seluruh draft','initial_import','VALIDATE')
  await mutate(page,'Sahkan data awal','initial_import','FINALIZE',{lost:true})
  await expect(page.getByText(/Sudah disahkan/)).toBeVisible()
  const result=JSON.parse(sql(`select jsonb_build_object('count',count(*),'amount',sum(i.amount)::text) from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id where h.migration_batch_id=${q(batch)}::uuid`))
  assert.equal(result.count,1);assert.equal(cents(result.amount),1725n)
  await expect(page.getByRole('button',{name:'Sahkan data awal',exact:true})).toHaveCount(0)
  pass('IMPORT_LATEST_CONTENT_ONCE_CONTROL_NOT_BOOKED',{amount:'17.25',detail_count:1,posted_editor_absent:true})
  await page.screenshot({path:resolve(dir,'import-posted.png'),fullPage:true})
}
async function accessoryFlow(){
  phase('ACCESSORY_BROWSER');await nav(page,'Nota Ambil Aksesori','Keuangan')
  const f=fixture.accessory,number='UI-ACC-'+randomUUID().slice(0,12),before=native('state')
  await page.getByLabel('Nomor nota aksesori').fill(number)
  await page.getByLabel('Mandor aksesori').selectOption(f.contractor);await page.getByLabel('Gudang aksesori').selectOption(f.location)
  await page.getByLabel('Waktu ambil aksesori').fill(fixture.day+'T10:15:00')
  await page.getByRole('button',{name:'Perbarui harga dan stok',exact:true}).click()
  await expect(page.getByLabel('Tambah aksesori')).toBeEnabled();await page.getByLabel('Tambah aksesori').selectOption(f.material)
  await page.getByLabel('Jumlah PCS 1',{exact:true}).fill('5');await page.getByLabel('Harga per PCS 1',{exact:true}).fill('3.25')
  const draft=await mutate(page,'Simpan draft','accessory_issue','SAVE_DRAFT')
  assert.equal(native('state').accessory_stock,before.accessory_stock);assert.deepEqual(native('state').all_ledger,before.all_ledger)
  pass('ACCESSORY_DRAFT_INERT',{id:draft.value.id,qty:5})
  await page.getByLabel('Jumlah PCS 1',{exact:true}).fill('7')
  await page.getByRole('button',{name:'Periksa pengesahan',exact:true}).click()
  const posted=await mutate(page,'Sahkan nota','accessory_issue','POST')
  const item=JSON.parse(sql(`select jsonb_build_object('qty',qty::text,'price',unit_sale_price_snapshot::text,'total',total_receivable::text,'factor',base_qty_per_transaction_uom::text) from erp.contractor_material_issue_items where issue_id=${q(posted.value.id)}::uuid`))
  assert.equal(Number(item.qty),7);assert.equal(cents(item.price),325n);assert.equal(cents(item.total),2275n);assert.equal(Number(item.factor),1)
  assert.equal(cents(sql(`select coalesce(sum(l.debit),0)::text from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.source_id=${q(posted.value.id)}::uuid and j.source_type='CONTRACTOR_MATERIAL_RECEIVABLE'`)),2275n)
  assert.equal(Number(native('state').accessory_stock),293)
  assert.equal(cents(sql(`select selling_price::text from erp.contractor_accessory_price_versions where id=${q(f.price)}::uuid`)),3600n)
  pass('ACCESSORY_EDIT_5_TO_7_MANUAL_PRICE',{physical_pcs:7,total:'22.75',dozen_master:'36.00',stock:293})
  await expect(page.getByLabel('Alasan pembatalan nota')).toBeEnabled();await page.getByLabel('Alasan pembatalan nota').fill('Pembatalan bukti browser')
  await page.getByRole('button',{name:'Periksa pembatalan',exact:true}).click();await mutate(page,'Sahkan pembatalan nota','accessory_issue','REVERSE')
  assert.equal(Number(native('state').accessory_stock),300);assert.deepEqual(native('state').all_ledger,before.all_ledger)
  assert.equal(Number(sql(`select qty::text from erp.contractor_material_issue_items where issue_id=${q(posted.value.id)}::uuid`)),7)
  pass('ACCESSORY_LINKED_INVERSE',{stock:300,source_qty_unchanged:7,ledger_restored:true})
  await page.screenshot({path:resolve(dir,'accessory-reversed.png'),fullPage:true})
}
async function pocketFlow(){
  phase('POCKET_MOBILE_BROWSER');await page.context().close();page=await login(owner,true);await nav(page,'Kain kantong','Gudang')
  const f=fixture.pocket,before=native('state')
  await page.getByLabel('Roll kain kantong').selectOption({label:(await page.getByLabel('Roll kain kantong').locator('option').allTextContents()).find(x=>x.includes(f.code))})
  await page.getByLabel('Jumlah kain kantong').fill('15');await page.getByLabel('Tanggal pengurangan').fill(fixture.day)
  await page.getByLabel('Catatan kain kantong').fill('Stok gudang untuk kantong bersama')
  const out=await mutate(page,'Sahkan pengurangan stok','pocket_fabric','POST')
  const issued=native('state');assert.equal(Number(issued.pocket_stock),15)
  assert.equal(delta(before,issued,'MATERIAL_INVENTORY'),-1125n);assert.equal(delta(before,issued,'OTHER_EXPENSE'),1125n)
  for(const k of ['WIP','FG_INVENTORY','COGS'])assert.equal(delta(before,issued,k),0n)
  pass('POCKET_REMAINING_COUNT_STOCK_ONLY',{remaining:15,issued:5,expense:'11.25',hpp_unchanged:true})
  await page.getByLabel('Awal periode kain kantong').fill(fixture.period_start);await page.getByLabel('Akhir periode kain kantong').fill(fixture.day)
  await page.getByLabel('Alasan pembagian kain kantong').fill('Pembagian output jahit periode uji')
  const previewResponse=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_preview_pocket_fabric_period_v1'))
  await page.getByRole('button',{name:'Lihat pembagian',exact:true}).click();const previewValue=await(await previewResponse).json()
  assert.equal(previewValue.amount,'11.25');assert.ok(Number(previewValue.quantity)>0)
  const allocation=await mutate(page,'Sahkan pembagian ke HPP','pocket_fabric','POST_PERIOD')
  const allocated=native('state');assert.equal(allocated.pocket_stock,issued.pocket_stock)
  assert.equal(delta(issued,allocated,'OTHER_EXPENSE'),-1125n)
  assert.equal(['WIP','FG_INVENTORY','COGS'].reduce((n,k)=>n+delta(issued,allocated,k),0n),1125n)
  const denom=Number(sql(`select sum(e.qty_signed)::text from erp.sewing_terminal_events e join erp.work_completion_events w on w.id=e.source_work_completion_id where e.event_kind='SELESAI_DIJAHIT' and e.qty_signed>0 and w.status='POSTED' and (e.physical_at at time zone 'Asia/Jakarta')::date between ${q(fixture.period_start)}::date and ${q(fixture.day)}::date and not exists(select 1 from erp.sewing_terminal_events r where r.reversal_of_id=e.id)`))
  assert.equal(Number(previewValue.quantity),denom)
  pass('POCKET_PERIOD_REAL_OUTPUT_ALLOCATION',{denominator:denom,allocated:'11.25',stock_unchanged:true})
  const refusedBefore=native('boundary'),history=await rpc(owner.token,'erp_get_pocket_fabric_workspace_v1',{p_query:f.code})
  const h=history.history.find(x=>x.id===out.value.id)
  const refused=await request(owner.token,'erp_save_pocket_fabric_action_v1',{p_action:'REVERSE',p_payload:{id:h.id,expected_version:h.row_version,reason:'Allocated source refusal'},p_client_request_id:randomUUID()})
  assert.equal(refused.status,400);assert.match(refused.value.message,/Batalkan alokasi periode/);assert.deepEqual(native('boundary'),refusedBefore)
  pass('POCKET_ALLOCATED_SOURCE_INVERSE_REFUSED',{full_erp_boundary_unchanged:true})
  await page.getByRole('button',{name:'Batalkan alokasi '+fixture.period_start,exact:true}).click();await page.getByLabel('Alasan pembatalan alokasi').fill('Batalkan pembagian saja')
  await mutate(page,'Sahkan pembatalan alokasi','pocket_fabric','CANCEL_PERIOD');assert.deepEqual(native('state').all_ledger,issued.all_ledger);assert.equal(native('state').pocket_stock,issued.pocket_stock)
  pass('POCKET_CANCEL_ALLOCATION_RESTORES_EXPENSE',{period_id:allocation.value.id,stock_unchanged:true})
  const button=page.getByRole('button',{name:'Batalkan '+h.roll_number,exact:true});await button.click()
  await page.getByLabel('Alasan pembatalan',{exact:true}).fill('Kembalikan stok uji');await mutate(page,'Sahkan pembatalan','pocket_fabric','REVERSE')
  assert.equal(Number(native('state').pocket_stock),20);assert.deepEqual(native('state').all_ledger,before.all_ledger)
  pass('POCKET_LINKED_INVERSE_RESTORES_ALL',{stock:20,ledger_restored:true})
  await page.screenshot({path:resolve(dir,'pocket-mobile.png'),fullPage:true})
}

try{
  phase('SERVICES');await start();owner=await user('owner')
  sql(`insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active) select ${q(randomUUID())}::uuid,${q(owner.id)}::uuid,'AP real Auth owner','OWNER',id,true from erp.app_roles where role_code='OWNER'`)
  const viewer=await user('viewer'),unmapped=await user('unmapped'),inactive=await user('inactive')
  await mapUser(owner,viewer);await mapUser(owner,inactive,false)
  phase('HTTP_AUTHORIZATION')
  for(const [name,args] of [['erp_get_initial_import_workspace_v1',{p_batch_id:null}],['erp_get_accessory_issue_workspace_v1',{p_filters:{}}],['erp_get_pocket_fabric_workspace_v1',{p_query:''}]]){
    await rpc(owner.token,name,args);pass('OWNER_HTTP_'+name)
  }
  const actions=[['initial_import','CREATE',{batch_code:'REFUSED-'+randomUUID(),cutover_date:fixture.day}],
    ['accessory_issue','POST',{reason:'Denied writer probe'}],['pocket_fabric','POST',{reason:'Denied writer probe'}]]
  for(const actor of [{label:'anonymous',token:null},viewer,unmapped,inactive])for(const [family,action,payload] of actions){
    const before=native('boundary');const r=await request(actor.token,`erp_save_${family}_action_v1`,{p_action:action,p_payload:payload,p_client_request_id:randomUUID()})
    assert.ok([401,403,400].includes(r.status));assert.ok(r.value.code==='42501'||(r.value.code==='P0001'&&/required|permission|access/i.test(r.value.message)),JSON.stringify(r))
    assert.deepEqual(native('boundary'),before);pass(`DENIED_${actor.label}_${family}`,{http_status:r.status,code:r.value.code,full_erp_boundary_unchanged:true})
  }
  page=await login(owner);pass('REAL_PASSWORD_BROWSER_LOGIN',{timezone:'Pacific/Honolulu'})
  await importFlow();await accessoryFlow();await pocketFlow()
  phase('REAL_HTTP_BLOCKING_RACES')
  execFileSync('python',['scripts/cp6_ap_flow_races.py'],{env:{...process.env,CP6_AP_FLOW_TOKEN:owner.token},stdio:['ignore','pipe','pipe']})
  const state=native('state');assert.equal(state.unbalanced,0);native('verify')
  assert.deepEqual(report.console_errors,[]);assert.equal(cases.length,29);report.status='PASS'
}catch(error){
  failure=error;report.error=safe(error.stack||error).slice(0,12000)
  if(error.stderr)report.process_stderr=safe(error.stderr).slice(-12000)
  if(page)try{report.visible_text_on_failure=safe(await page.locator('body').innerText()).slice(0,18000)}catch{}
  if(page)try{await page.screenshot({path:resolve(dir,'failure.png'),fullPage:true})}catch{}
}finally{
  if(browser)await browser.close();if(preview)preview.kill();if(proxy)await new Promise(ok=>proxy.close(ok))
  const failures=[]
  for(const u of users)try{await auth('admin/users/'+u.id,undefined,true,'DELETE')}catch{failures.push(u.label)}
  report.auth_cleanup_failures=failures;if(failures.length)report.status='INCOMPLETE'
  save();console.log(`AP flow ${report.status}: ${cases.length} completed cases`)
}
if(failure||report.status!=='PASS'){console.error(report.error||'FLOW_CLEANUP_FAILED');process.exitCode=1}
