#!/usr/bin/env node
// Original UI -> real local Auth -> original public facades -> disposable AI-R2.
// No fulfilled/mock business response, no schema/ACL grant, no posted-row deletion.
import assert from 'node:assert/strict'
import { execFileSync, spawn } from 'node:child_process'
import { createHash, randomBytes, randomUUID } from 'node:crypto'
import { mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import http from 'node:http'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { stripTypeScriptTypes } from 'node:module'
import { chromium, expect } from '@playwright/test'

const root = resolve(fileURLToPath(new URL('..', import.meta.url)))
const reportDir = resolve(process.env.CP6_UI_REPORT_DIR || 'cp6-proof/final-audit')
const pg = process.env.CP6_AUTH_PGURL
const controlPg = process.env.CP6_AUTH_CONTROL_PGURL
const anon = process.env.SUPABASE_ANON_KEY
const service = process.env.SUPABASE_SERVICE_ROLE_KEY
assert.equal(pg, 'postgresql://postgres:postgres@127.0.0.1:54322/cp6_auth')
assert.equal(controlPg, 'postgresql://postgres:postgres@127.0.0.1:54322/postgres')
assert.equal(process.env.SUPABASE_AUTH_URL, 'http://127.0.0.1:54321')
assert.equal(process.env.SUPABASE_REST_URL, 'http://127.0.0.1:54329')
assert.ok(anon && service)
const origin = 'http://127.0.0.1:4176'
const apiOrigin = 'http://127.0.0.1:54328'
const users = [], secrets = [anon, service]
let ownerId, reportBaseline, parseWorkspace, useCurrentPhysicalTime=false, lastSendPhysical
const workspaceObservations = new Set()
const f = {
  po: 'c8c40000-0000-4000-8000-000000000001',
  group: 'c8c40000-0000-4000-8000-000000000003',
  batch: 'c8c40000-0000-4000-8000-000000000008',
  vendor: 'c8c20000-0000-4000-8000-000000000002',
  process: 'c8c20000-0000-4000-8000-000000000003',
  location: 'c8c20000-0000-4000-8000-000000000001',
  product: 'c8c10000-0000-4000-8000-000000000004',
  size: 'CP6-RACE-S',
}
const lifecycle = ['DRAFT_INERT', 'DOUBLE_SUBMIT', 'RECEIPT_8', 'QC_5', 'QC_FILTER_SCOPE', 'QC_3',
  'RECEIPT_2', 'QC_2', 'BLOCK_PARENT_REVERSAL', 'REVERSE_QC_2',
  'REVERSE_QC_3', 'REVERSE_QC_5', 'REVERSE_RECEIPT_2', 'REVERSE_RECEIPT', 'REVERSE_DELIVERY']
const planned = ['ANONYMOUS', 'VIEWER', 'UNMAPPED', 'INACTIVE',
  ...['OPERATOR_DESKTOP', 'OWNER_MOBILE'].flatMap(x => lifecycle.map(y => `${x}_${y}`)),
  'FAILED_WASH_SEND', 'FAILED_WASH_LOST_REPLY', 'FAILED_WASH_REVERSE_COST', 'FAILED_WASH_REVERSE_SEND',
  'FULL_RETURN_SEND', 'FULL_RETURN_EXACT', 'FULL_RETURN_REDISPATCH',
  'FULL_RETURN_REVERSE_COST', 'FULL_RETURN_REVERSE_REDISPATCH']
const report = {
  status: 'INCOMPLETE', classification: 'WRITER_UI_REAL_AUTH_HTTP_ON_UNCHANGED_AI_R2',
  backend_head: '25fa4736329e5148dfdb3572bc169952cba23251',
  backend_tree: 'a5cb1e43d776a9ffc058f99c8d5c96ac7f6a9c0d',
  frontend_head: execFileSync('git', ['rev-parse', 'HEAD'], {cwd:root,encoding:'utf8'}).trim(),
  frontend_tree: execFileSync('git', ['rev-parse', 'HEAD^{tree}'], {cwd:root,encoding:'utf8'}).trim(),
  source_sha256: createHash('sha256').update(readFileSync(fileURLToPath(import.meta.url))).digest('hex'),
  planned_case_ids: planned, completed: [], current_phase: 'SETUP',
  schema_acl_modified: false, credentials_in_artifacts: false, production_go: false,
  independent_acceptance: false, database_disposal_required: true,
  browser_transport_failures: [],
  browser_cors_errors: [],
  workspace_diagnostics: [],
}
mkdirSync(reportDir, {recursive:true})
const save = () => writeFileSync(resolve(reportDir,'UI.json'), JSON.stringify(report,null,2)+'\n')
const stage = (id) => {report.current_phase=id; save(); console.log(`CP6 UI phase: ${id}`)}
function pass(id, detail = {}) {
  assert.ok(planned.includes(id)); assert.ok(!report.completed.some(x=>x.id===id))
  report.completed.push({id,status:'PASS',...detail}); save()
}
const query = (statement, url=pg) => execFileSync('psql', [url,'-X','-qAt','-v','ON_ERROR_STOP=1','-c',statement],
  {encoding:'utf8',stdio:['ignore','pipe','pipe']}).trim()
assert.equal(query('select current_database()'), 'cp6_auth')
if(process.argv.includes('--qualify-legacy-fixture')){
  // Observe the real workspace before discarding the ENTIRE old HTTP clone.
  // The original parser is transpiled without changing its validation rules.
  const source=readFileSync(resolve(root,'src/laundryQcModel.ts'),'utf8')
  const compiled=stripTypeScriptTypes(source,{mode:'strip'})
  const {parseLaundryQcWorkspace}=await import('data:text/javascript;base64,'+Buffer.from(compiled).toString('base64'))
  const raw=query(`begin; set local request.jwt.claims='{"role":"authenticated","sub":"c8c00000-0000-4000-8000-000000000101"}';
    select public.erp_get_laundry_qc_workspace_v1('LAUNDRY',null); rollback;`)
  let rejected
  try{parseLaundryQcWorkspace(JSON.parse(raw))}catch(error){rejected=error.message}
  const proof={status:rejected?.includes('bukan UUID valid')?'FIXTURE_UUID_REJECTION_CONFIRMED':'UNRESOLVED',
    parser_sha256:createHash('sha256').update(source).digest('hex'),
    workspace_sha256:createHash('sha256').update(raw).digest('hex'),error:rejected||null,
    product_parser_modified:false,posted_rows_modified:false,production_go:false}
  writeFileSync(resolve(reportDir,'LEGACY_FIXTURE.json'),JSON.stringify(proof,null,2)+'\n')
  assert.equal(proof.status,'FIXTURE_UUID_REJECTION_CONFIRMED')
  console.log('CP6 UI fixture qualification: '+proof.status)
  process.exit(0)
}
const day = query("select ((clock_timestamp() at time zone 'Asia/Jakarta')::date-1)::text")
assert.match(day, /^\d{4}-\d{2}-\d{2}$/)
const when = async (time) => {
  if(!useCurrentPhysicalTime)return `${day}T${time}`
  // Previous linked reversals restore custody at commit time. A later dispatch
  // must follow that physical event, never reuse yesterday's original dispatch.
  // The original input accepts whole seconds; cross one second before sampling.
  await new Promise(ok=>setTimeout(ok,1100))
  return query(`select to_char(clock_timestamp() at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS')`)
}
const state = () => JSON.parse(query(`select jsonb_build_object(
 'fg_qty',(select coalesce(sum(m.qty_signed),0) from erp.fg_stock_movements m join erp.fg_lots l on l.id=m.lot_id where l.po_id='${f.po}'),
 'wip',(select coalesce(sum(debit-credit),0) from erp.journal_lines where po_id='${f.po}' and account_id=erp.account_id('WIP')),
 'fg',(select coalesce(sum(debit-credit),0) from erp.journal_lines where po_id='${f.po}' and account_id=erp.account_id('FG_INVENTORY')),
 'accrued',(select coalesce(sum(debit-credit),0) from erp.journal_lines where po_id='${f.po}' and account_id=erp.account_id('ACCRUED_MANUFACTURING')),
 'ready',(select unsent_ready_qty_pcs from erp.v_wip_control_status_v1 where cutting_group_id='${f.group}'),
 'posted_delivery',(select count(*) from erp.laundry_deliveries where po_id='${f.po}' and status='POSTED'),
 'posted_qc',(select count(*) from erp.qc_inspections where po_id='${f.po}' and status='POSTED'),
 'qc_bs',(select coalesce(sum(i.qty_bs_pcs),0) from erp.qc_inspection_items i join erp.qc_inspections q on q.id=i.inspection_id where q.po_id='${f.po}' and q.status='POSTED'),
 'unbalanced',(select count(*) from (select e.id from erp.journal_entries e join erp.journal_lines l on l.journal_entry_id=e.id where exists(select 1 from erp.journal_lines s where s.journal_entry_id=e.id and s.po_id='${f.po}') group by e.id having sum(l.debit)<>sum(l.credit)) x),
 'journal_rows',(select count(*) from erp.journal_lines where po_id='${f.po}'),
 'fg_movements',(select count(*) from erp.fg_stock_movements m join erp.fg_lots l on l.id=m.lot_id where l.po_id='${f.po}'),
 'execution_context',(select count(*) from erp.cp6_laundry_qc_execution_context));`))
function checkState(id, expected, extra={}) {
  const actual=state()
  for(const [key,value] of Object.entries({...expected,unbalanced:0,execution_context:0})) assert.equal(actual[key],value,`${id}.${key}`)
  const snapshot=financialReport()
  const deltas={wip:snapshot.financial_position.wip_inventory-reportBaseline.financial_position.wip_inventory,
    fg:snapshot.financial_position.fg_inventory-reportBaseline.financial_position.fg_inventory}
  for(const key of ['wip','fg'])if(key in expected)assert.equal(deltas[key],expected[key],`${id}.report.${key}`)
  assert.equal(snapshot.data_confidence.status,reportBaseline.data_confidence.status,`${id}.report.confidence_changed`)
  pass(id,{expected,observed:actual,report_delta:deltas,report_confidence:snapshot.data_confidence,...extra})
}
function financialReport(){
  // Read-only native observer, not a claim that the reporting UI is connected.
  assert.match(ownerId,/^[0-9a-f-]{36}$/)
  return JSON.parse(query(`begin; set local request.jwt.claims='{"role":"authenticated","sub":"${ownerId}"}';
    select erp.get_owner_financial_snapshot_v2('${day}'::date,('${day}'::date+1),('${day}'::date+1)); rollback;`))
}
const latest = (table, number, predicate=`po_id='${f.po}'`) => JSON.parse(query(
  `select jsonb_build_object('id',id,'number',${number}) from erp.${table} where ${predicate} order by created_at desc,id desc limit 1`))
const delivery = () => latest('laundry_deliveries','delivery_number')
const receipt = () => latest('laundry_receipts','receipt_number',`delivery_id='${delivery().id}'`)
const qc = () => latest('qc_inspections','inspection_number')

async function authRequest(path, body, admin=false, method='POST') {
  const res=await fetch(`http://127.0.0.1:54321/auth/v1/${path}`,{method,
    headers:{apikey:admin?service:anon,Authorization:`Bearer ${admin?service:anon}`,'Content-Type':'application/json'},
    body:body===undefined?undefined:JSON.stringify(body)})
  assert.ok(res.ok,`AUTH_${method}_${res.status}`)
  return res.status===204?{}:res.json()
}
async function newUser(label) {
  const email=`cp6-ui-${label}-${randomUUID()}@example.invalid`, password=`Cp6!${randomBytes(24).toString('hex')}`
  secrets.push(email,password)
  const value=await authRequest('admin/users',{email,password,email_confirm:true},true)
  assert.match(value.id,/^[0-9a-f-]{36}$/)
  const user={id:value.id,email,password,label};users.push(user);return user
}
async function rpc(token,name,args) {
  const res=await fetch(`http://127.0.0.1:54329/rpc/${name}`,{method:'POST',
    headers:{apikey:anon,Authorization:`Bearer ${token}`,'Content-Type':'application/json'},body:JSON.stringify(args)})
  assert.equal(res.status,200,`RPC_${name}_${res.status}`);return res.json()
}
async function mapUser(token,user,permissions,active=true) {
  const role=await rpc(token,'erp_save_role_v1',{
    p_payload:{code:`UI_${randomBytes(6).toString('hex').toUpperCase()}`,name:`Synthetic UI ${user.label}`,
      description:'Disposable original UI audit',permission_keys:permissions,confirm_high_risk:true,change_reason:'CP6 UI role fixture'},
    p_client_request_id:randomUUID(),p_expected_version:null})
  const value=await rpc(token,'erp_save_app_user_v3',{
    p_payload:{auth_user_id:user.id,full_name:`Synthetic UI ${user.label}`,role_id:role.role_id,is_active:active,change_reason:'CP6 UI mapping fixture'},
    p_client_request_id:randomUUID(),p_expected_version:null})
  assert.match(value.app_user_id,/^[0-9a-f-]{36}$/)
}

let proxy, preview, browser, failure
const safeEnv = Object.fromEntries(['PATH','HOME','CI','TMPDIR','RUNNER_TEMP','PLAYWRIGHT_BROWSERS_PATH'].filter(k=>process.env[k]).map(k=>[k,process.env[k]]))
async function startApplication() {
  const parserSource=readFileSync(resolve(root,'src/laundryQcModel.ts'),'utf8')
  const parserCode=stripTypeScriptTypes(parserSource,{mode:'strip'})
  parseWorkspace=(await import('data:text/javascript;base64,'+Buffer.from(parserCode).toString('base64'))).parseLaundryQcWorkspace
  report.workspace_parser_sha256=createHash('sha256').update(parserSource).digest('hex')
  // One fixed origin for supabase-js; transparent forwarding to real services.
  proxy=http.createServer((req,res)=>{
    const allowedOrigin=req.headers.origin===origin
    // Node receives upstream headers in lowercase. Use the same case so one
    // local origin REPLACES the upstream wildcard, never two CORS values.
    const cors=allowedOrigin?{'access-control-allow-origin':origin,'vary':'Origin',
      'access-control-allow-headers':'authorization,apikey,content-type,x-client-info,x-supabase-api-version,accept-profile,content-profile',
      'access-control-allow-methods':'GET,POST,PUT,DELETE,OPTIONS'}:{}
    if(req.method==='OPTIONS'){res.writeHead(allowedOrigin?204:403,cors);res.end();return}
    const auth=req.url.startsWith('/auth/v1/'), rest=req.url.startsWith('/rest/v1/rpc/')
    if(!auth&&!rest){res.writeHead(404,cors);res.end();return}
    const headers={...req.headers};delete headers.host;delete headers.origin
    const upstream=http.request({hostname:'127.0.0.1',port:auth?54321:54329,
      path:auth?req.url:req.url.slice('/rest/v1'.length),method:req.method,headers}, reply=>{
        const clean={...reply.headers,...cors};delete clean['access-control-allow-credentials']
        if(reply.statusCode>=300&&reply.statusCode<400){res.writeHead(502,cors);res.end();reply.resume();return}
        res.writeHead(reply.statusCode,clean);reply.pipe(res)
      })
    upstream.on('error',()=>{if(!res.headersSent)res.writeHead(502,cors);res.end()});req.pipe(upstream)
  })
  await new Promise((ok,no)=>{proxy.once('error',no);proxy.listen(54328,'127.0.0.1',ok)})
  const health=await fetch(apiOrigin+'/auth/v1/health',{headers:{Origin:origin}})
  assert.equal(health.status,200)
  assert.equal(health.headers.get('access-control-allow-origin'),origin,'Exactly one CORS origin on the real Auth response')
  const preflight=await fetch(apiOrigin+'/auth/v1/token?grant_type=password',{method:'OPTIONS',headers:{
    Origin:origin,'Access-Control-Request-Method':'POST',
    'Access-Control-Request-Headers':'apikey,authorization,content-type,x-client-info,x-supabase-api-version'}})
  assert.equal(preflight.status,204)
  assert.equal(preflight.headers.get('access-control-allow-origin'),origin)
  assert.ok(preflight.headers.get('access-control-allow-headers').includes('x-supabase-api-version'))
  report.real_auth_cors_probe={status:'PASS',health_status:200,preflight_status:204,single_origin:true}
  execFileSync('npm',['run','build:cp6-disposable'],{cwd:root,env:{...safeEnv,
    VITE_ERP_RUNTIME_MODE:'DISPOSABLE_TEST',VITE_SUPABASE_URL:apiOrigin,VITE_SUPABASE_ANON_KEY:anon},
    stdio:['ignore','pipe','pipe']})
  preview=spawn(resolve(root,'node_modules/.bin/vite'),['preview','--outDir','cp6-ui-build','--host','127.0.0.1','--port','4176','--strictPort'],
    {cwd:root,env:safeEnv,stdio:'ignore'})
  await expect.poll(async()=>{try{return (await fetch(origin)).status}catch{return 0}},{timeout:15000}).toBe(200)
  const smokeArgs=['--yes','agent-browser@0.38.0','--session','cp6-disposable-smoke',
    '--executable-path',chromium.executablePath()]
  const smoke=(...args)=>execFileSync('npx',[...smokeArgs,...args],{cwd:root,
    env:{...safeEnv,AGENT_BROWSER_AUTOSAVE_INTERVAL_MS:'0'},encoding:'utf8',
    timeout:60000,stdio:['ignore','pipe','pipe']})
  try{
    smoke('open',origin)
    const snapshot=smoke('snapshot','-i')
    assert.ok(snapshot.includes('Email akun ERP')&&snapshot.includes('Kata sandi'))
    report.agent_browser_smoke={status:'PASS',version:'0.38.0',real_login_page:true}
  }finally{smoke('close')}
  browser=await chromium.launch()
}
async function pageFor(user,mobile=false) {
  const context=await browser.newContext({viewport:mobile?{width:390,height:844}:{width:1440,height:1000},
    timezoneId:'Pacific/Honolulu',isMobile:mobile,hasTouch:mobile})
  await context.route('**/*',route=>{
    const url=new URL(route.request().url())
    return [origin,apiOrigin].includes(url.origin)?route.continue():route.abort('blockedbyclient')
  })
  const page=await context.newPage();page.setDefaultTimeout(18000)
  page.on('requestfailed',request=>report.browser_transport_failures.push({
    phase:report.current_phase,path:new URL(request.url()).pathname,
    error:request.failure()?.errorText||'unknown'}))
  page.on('response',response=>{if(response.status()>=400)report.browser_transport_failures.push({
    phase:report.current_phase,path:new URL(response.url()).pathname,status:response.status()})})
  page.on('response',response=>{
    if(response.request().method()!=='POST'||!response.url().endsWith('/rpc/erp_get_laundry_qc_workspace_v1'))return
    const phase=report.current_phase
    const task=(async()=>{
      try{
        const value=await response.json(),request=response.request().postDataJSON()
        let parserError
        if(response.status()===200){try{parseWorkspace(value)}catch(error){parserError=error.message}}
        if(response.status()!==200||parserError){
          let detail=JSON.stringify({phase,http_status:response.status(),scope:request?.p_scope,query:request?.p_query,
            parser_error:parserError||null,server_error:response.status()===200?null:value,
            workspace_sha256:createHash('sha256').update(JSON.stringify(value)).digest('hex'),
            observed_workspace:response.status()===200?Object.fromEntries(
              ['contract_version','scope','readiness','collection_window','ready_batches','deliveries','qc_queue','qc_history','lookups']
                .filter(key=>key in value).map(key=>[key,value[key]])):null})
          for(const secret of secrets.filter(Boolean))detail=detail.split(secret).join('[REDACTED]')
          detail=detail.replace(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g,'[JWT REDACTED]')
          const evidence=JSON.parse(detail);report.workspace_diagnostics.push(evidence)
          console.log('CP6 UI workspace diagnosis: '+JSON.stringify({...evidence,observed_workspace:undefined}))
          save()
        }
      }catch(error){report.workspace_diagnostics.push({phase,observation_error:error.name})}
    })()
    workspaceObservations.add(task);void task.finally(()=>workspaceObservations.delete(task))
  })
  page.on('console',message=>{
    if(!message.text().includes('CORS'))return
    let text=message.text()
    for(const value of secrets.filter(Boolean))text=text.split(value).join('[REDACTED]')
    report.browser_cors_errors.push({phase:report.current_phase,message:text.slice(0,1000)})
  })
  await page.goto(origin)
  await expect(page.getByRole('heading',{name:'Masuk ke Atelier ERP'})).toBeVisible()
  if(!user)return page
  await page.getByLabel('Email akun ERP').fill(user.email)
  await page.getByLabel('Kata sandi').fill(user.password)
  await page.getByRole('button',{name:'Masuk',exact:true}).click()
  if(['inactive','unmapped'].includes(user.label)){
    await expect(page.getByRole('heading',{name:'Akun belum lolos guardrail'})).toBeVisible()
  }else await expect(page.locator('.top-title strong')).toBeVisible()
  return page
}
async function nav(page,name) {
  const menu=page.getByRole('button',{name:'Buka menu',exact:true})
  if(await menu.isVisible())await menu.click()
  const link=page.getByRole('button',{name:`• ${name}`,exact:true})
  if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Produksi'}).click()
  await link.click()
  await expect(page.getByRole('heading',{name,exact:true})).toBeVisible()
  await expect(page.getByRole('button',{name:'Muat ulang data',exact:true})).toBeEnabled()
  const error=await page.locator('.clq-alert.error').allTextContents()
  assert.deepEqual(error,[],`${name}: original workspace error`)
}
async function mutation(page,label,action,{double=false,loseReply=false}={}) {
  const button=typeof label==='string'?page.getByRole('button',{name:label,exact:true}):label
  await expect(button).toBeEnabled()
  const stateBefore=state()
  const matches=(request)=>request.url().endsWith('/rpc/erp_save_laundry_qc_action_v1')&&request.method()==='POST'&&request.postDataJSON()?.p_action===action
  if(loseReply){
    let lostRequestId
    await page.route('**/rpc/erp_save_laundry_qc_action_v1',async route=>{
      if(!matches(route.request())){await route.continue();return}
      lostRequestId=route.request().postDataJSON().p_client_request_id
      const reply=await route.fetch();assert.equal(reply.status(),200)
      const value=await reply.json();assert.equal(value.committed,true)
      await route.abort('connectionreset')
    },{times:1})
    await button.click()
    await expect(page.getByRole('button',{name:'Reconcile UUID lama',exact:true})).toBeEnabled()
    const response=page.waitForResponse(r=>matches(r.request()))
    // The original application automatically reconciles its persisted envelope after reload.
    await page.reload()
    const r=await response;assert.equal(r.status(),200)
    assert.equal(r.request().postDataJSON().p_client_request_id,lostRequestId)
    assert.equal((await r.json()).committed,true)
  }else{
    const response=page.waitForResponse(r=>matches(r.request()))
    if(double)await button.evaluate(b=>{b.click();b.click()});else await button.click()
    const r=await response
    const result=await r.json()
    if(r.status()!==200){
      let evidence=JSON.stringify({phase:report.current_phase,action,http_status:r.status(),
        request:r.request().postDataJSON(),response:result,state_before:stateBefore,state_after:state(),
        qc_ui_source_sha256:createHash('sha256').update(readFileSync(resolve(root,'src/ConnectedQcFinalPage.tsx'))).digest('hex')})
      for(const value of secrets.filter(Boolean))evidence=evidence.split(value).join('[REDACTED]')
      report.rejected_mutation=JSON.parse(evidence)
      save();console.log('CP6 UI rejected mutation: '+evidence)
    }
    assert.equal(r.status(),200,`${action}_HTTP_STATUS`)
    assert.equal(result.committed,true)
  }
  await expect(page.getByRole('button',{name:'Muat ulang data',exact:true})).toBeEnabled()
}
async function sendForm(page) {
  await page.getByRole('button',{name:'Kirim ke Laundry',exact:true}).click()
  await page.getByLabel('BATCH DISTRIBUSI AUTHORITATIVE',{exact:true}).selectOption(f.batch)
  await page.getByRole('button',{name:'Isi dari sisa siap',exact:true}).click()
  await page.getByRole('combobox',{name:/^VENDOR LAUNDRY/}).selectOption(f.vendor)
  await page.getByLabel('PROSES CUCI TARGET',{exact:true}).selectOption(f.process)
  await page.getByLabel('WARNA TARGET',{exact:true}).fill('NAVY')
  lastSendPhysical=await when('08:00')
  await page.getByLabel('WAKTU FISIK KELUAR',{exact:true}).fill(lastSendPhysical)
  await page.getByLabel('ALASAN / BUKTI SERAH TERIMA',{exact:true}).fill('CP6 UI synthetic physical count ten')
  await page.locator('.clq-confirm input').check()
}
async function receiveForm(page,qty=8,time='09:00') {
  await page.getByRole('button',{name:'Terima kembali',exact:true}).click()
  await page.getByLabel('SURAT KIRIM AKTIF',{exact:true}).selectOption(delivery().id)
  await page.getByLabel('PROSES AKTUAL',{exact:true}).selectOption(f.process)
  await page.getByLabel('WAKTU FISIK KEMBALI',{exact:true}).fill(await when(time))
  await page.getByLabel('ALASAN / BUKTI PENERIMAAN',{exact:true}).fill(`CP6 UI synthetic staged return ${qty} of ten`)
  await page.getByLabel(`Good kembali size ${f.size}`,{exact:true}).fill(String(qty))
  await page.locator('.clq-confirm input').check()
}
async function searchQc(page,query) {
  const response=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_get_laundry_qc_workspace_v1')
    &&r.request().postDataJSON()?.p_scope==='QC'&&r.request().postDataJSON()?.p_query===query)
  await page.getByPlaceholder('Cari PO, Potongan, receipt, atau histori…',{exact:true}).fill(query)
  assert.equal((await response).status(),200)
  await expect(page.getByRole('button',{name:'Muat ulang data',exact:true})).toBeEnabled()
}
async function qcForm(page,qty,time,bsQty=0) {
  await page.getByRole('button',{name:'Antrean finalisasi',exact:true}).click()
  await page.getByRole('combobox',{name:/^POTONGAN DENGAN GOOD LAUNDRY SIAP QC/}).selectOption(f.group)
  await page.getByLabel('WAKTU FISIK QC',{exact:true}).fill(await when(time))
  await page.getByLabel(`Good final size ${f.size}`,{exact:true}).fill(String(qty))
  await page.getByLabel(`BS QC size ${f.size}`,{exact:true}).fill(String(bsQty))
  await page.getByLabel(`Final SKU size ${f.size}`,{exact:true}).selectOption(f.product)
  await page.getByLabel('LOKASI FG TUJUAN',{exact:true}).selectOption(f.location)
  await page.getByLabel('ALASAN / BUKTI HASIL QC',{exact:true}).fill('CP6 UI synthetic exact size physical QC')
  await page.locator('.clq-confirm input').check()
}
async function reverse(page,document,button,action) {
  await page.getByRole('button',{name:'Riwayat & koreksi',exact:true}).click()
  const input=page.getByLabel(`Alasan reversal ${document.number}`,{exact:true})
  await input.fill('CP6 UI linked correction synthetic audit')
  await mutation(page,input.locator('..').getByRole('button',{name:button,exact:true}),action)
}

try {
  stage('SETUP_AUTH')
  const owner=await newUser('owner'), operator=await newUser('operator'), viewer=await newUser('viewer')
  ownerId=owner.id
  const inactive=await newUser('inactive'), unmapped=await newUser('unmapped')
  query(`insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active) select '${randomUUID()}','${owner.id}','Synthetic UI owner','OWNER',id,true from erp.app_roles where role_code='OWNER'`)
  const session=await authRequest('token?grant_type=password',{email:owner.email,password:owner.password})
  secrets.push(session.access_token,session.refresh_token)
  const view=['production.laundry.view','production.final_sku.view']
  await mapUser(session.access_token,viewer,view)
  await mapUser(session.access_token,inactive,view,false)
  await mapUser(session.access_token,operator,[...view,'production.laundry.create','production.laundry.post','production.laundry.reverse','production.final_sku.post','production.final_sku.reverse'])
  reportBaseline=financialReport()
  report.baseline_report_confidence=reportBaseline.data_confidence
  assert.equal(reportBaseline.data_confidence.status,'READY','Baseline report must be READY')
  stage('BUILD_AND_SERVICES');await startApplication()
  stage('ANONYMOUS')
  let page=await pageFor();assert.equal(await page.locator('.top-title').count(),0);pass('ANONYMOUS')
  await page.context().close()
  for(const user of [unmapped,inactive]){
    const id=user.label.toUpperCase();stage(id);page=await pageFor(user)
    assert.equal(await page.locator('.top-title').count(),0);pass(id);await page.context().close()
  }
  stage('VIEWER');page=await pageFor(viewer);await nav(page,'Laundry')
  await expect(page.getByRole('button',{name:'Post pengiriman atomic',exact:true})).toBeDisabled()
  await nav(page,'QC & Final SKU')
  await expect(page.getByRole('button',{name:'Post QC + Final SKU atomic',exact:true})).toBeDisabled()
  pass('VIEWER',{read_scopes:['LAUNDRY','QC'],writes_disabled:true});await page.context().close()
  for(const [user,mobile,prefix] of [[operator,false,'OPERATOR_DESKTOP'],[owner,true,'OWNER_MOBILE']]){
    useCurrentPhysicalTime=mobile
    // Same completion contract, with mixed Good/BS on mobile. Only Good enters FG.
    const bsQty=mobile?2:0, stagedGood=8-bsQty, finalGood=10-bsQty
    stage(`${prefix}_DRAFT_INERT`);page=await pageFor(user,mobile);await nav(page,'Laundry')
    const before=state();await sendForm(page)
    assert.deepEqual(state(),before);pass(`${prefix}_DRAFT_INERT`,{observed:before})
    stage(`${prefix}_DOUBLE_SUBMIT`)
    await mutation(page,'Post pengiriman atomic','POST_DELIVERY',{double:true})
    assert.equal(query(`select count(*) from erp.laundry_deliveries where po_id='${f.po}' and status<>'REVERSED' and physical_at='${lastSendPhysical}+07:00'::timestamptz and created_at>physical_at`),'1',
      'One physical dispatch at WIB time despite browser Honolulu zone and double click')
    checkState(`${prefix}_DOUBLE_SUBMIT`,{fg_qty:0,wip:70,fg:0,accrued:-70,ready:0},
      {physical_input_wib:lastSendPhysical,browser_zone:'Pacific/Honolulu',backdated:!mobile})
    const sent=delivery()
    stage(`${prefix}_RECEIPT_8`);await receiveForm(page);await mutation(page,'Post penerimaan atomic','POST_RECEIPT')
    const returned=receipt();checkState(`${prefix}_RECEIPT_8`,{fg_qty:0,wip:70,fg:0,accrued:-70})
    await nav(page,'QC & Final SKU')
    stage(`${prefix}_QC_5`);await qcForm(page,5,'10:00');await mutation(page,'Post QC + Final SKU atomic','POST_FINAL_SKU')
    const firstQc=qc();checkState(`${prefix}_QC_5`,{fg_qty:5,wip:35,fg:35,accrued:-70,posted_qc:1})
    stage(`${prefix}_QC_FILTER_SCOPE`)
    const beforeFiltered=state()
    await searchQc(page,returned.number);await qcForm(page,3-bsQty,'11:00',bsQty)
    await expect(page.getByRole('button',{name:'Post QC + Final SKU atomic',exact:true})).toBeDisabled()
    assert.deepEqual(state(),beforeFiltered)
    pass(`${prefix}_QC_FILTER_SCOPE`,{receipt_filter_does_not_prove_full_group:true,ledger_unchanged:true})
    await searchQc(page,'CP6-RACE-PO')
    stage(`${prefix}_QC_3`);await qcForm(page,3-bsQty,'11:00',bsQty);await mutation(page,'Post QC + Final SKU atomic','POST_FINAL_SKU')
    const secondQc=qc();checkState(`${prefix}_QC_3`,{fg_qty:stagedGood,wip:70-stagedGood*7,fg:stagedGood*7,accrued:-70,posted_qc:2,qc_bs:bsQty},
      {selected_good:3-bsQty,selected_bs:bsQty,unit_cost:7})
    stage(`${prefix}_RECEIPT_2`);await nav(page,'Laundry');await receiveForm(page,2,'11:30')
    await mutation(page,'Post penerimaan atomic','POST_RECEIPT')
    const secondReceipt=receipt();checkState(`${prefix}_RECEIPT_2`,{fg_qty:stagedGood,wip:70-stagedGood*7,fg:stagedGood*7,accrued:-70,qc_bs:bsQty})
    stage(`${prefix}_QC_2`);await nav(page,'QC & Final SKU');await qcForm(page,2,'12:00')
    await mutation(page,'Post QC + Final SKU atomic','POST_FINAL_SKU')
    const thirdQc=qc();checkState(`${prefix}_QC_2`,{fg_qty:finalGood,wip:70-finalGood*7,fg:finalGood*7,accrued:-70,posted_qc:3,qc_bs:bsQty})
    await page.screenshot({path:resolve(reportDir,`${prefix}.png`),fullPage:true})
    stage(`${prefix}_BLOCK_PARENT_REVERSAL`);await nav(page,'Laundry')
    await page.getByRole('button',{name:'Riwayat & koreksi',exact:true}).click()
    await expect(page.getByLabel(`Alasan reversal ${returned.number}`,{exact:true})).toBeDisabled()
    pass(`${prefix}_BLOCK_PARENT_REVERSAL`,{blocked_by:'posted QC children'})
    await nav(page,'QC & Final SKU')
    stage(`${prefix}_REVERSE_QC_2`);await reverse(page,thirdQc,'Batalkan finalisasi','REVERSE_FINAL_SKU')
    checkState(`${prefix}_REVERSE_QC_2`,{fg_qty:stagedGood,wip:70-stagedGood*7,fg:stagedGood*7,accrued:-70,qc_bs:bsQty})
    stage(`${prefix}_REVERSE_QC_3`);await reverse(page,secondQc,'Batalkan finalisasi','REVERSE_FINAL_SKU')
    checkState(`${prefix}_REVERSE_QC_3`,{fg_qty:5,wip:35,fg:35,accrued:-70,qc_bs:0})
    stage(`${prefix}_REVERSE_QC_5`);await reverse(page,firstQc,'Batalkan finalisasi','REVERSE_FINAL_SKU')
    checkState(`${prefix}_REVERSE_QC_5`,{fg_qty:0,wip:70,fg:0,accrued:-70})
    await nav(page,'Laundry')
    stage(`${prefix}_REVERSE_RECEIPT_2`);await reverse(page,secondReceipt,'Batalkan penerimaan','REVERSE_RECEIPT')
    checkState(`${prefix}_REVERSE_RECEIPT_2`,{fg_qty:0,wip:70,fg:0,accrued:-70})
    stage(`${prefix}_REVERSE_RECEIPT`);await reverse(page,returned,'Batalkan penerimaan','REVERSE_RECEIPT')
    checkState(`${prefix}_REVERSE_RECEIPT`,{fg_qty:0,wip:70,fg:0,accrued:-70})
    stage(`${prefix}_REVERSE_DELIVERY`);await reverse(page,sent,'Batalkan pengiriman','REVERSE_DELIVERY')
    checkState(`${prefix}_REVERSE_DELIVERY`,{fg_qty:0,wip:0,fg:0,accrued:0,ready:10,posted_qc:0})
    await page.context().close()
  }
  useCurrentPhysicalTime=true
  stage('FAILED_WASH_SEND');page=await pageFor(operator);await nav(page,'Laundry');await sendForm(page)
  await mutation(page,'Post pengiriman atomic','POST_DELIVERY');const sent=delivery()
  checkState('FAILED_WASH_SEND',{fg_qty:0,wip:70,fg:0,accrued:-70,ready:0})
  stage('FAILED_WASH_LOST_REPLY')
  await page.getByRole('button',{name:'Cuci gagal berbayar',exact:true}).click()
  await page.getByLabel('SURAT KIRIM GAGAL CUCI',{exact:true}).selectOption(sent.id)
  await page.getByLabel('PROSES GAGAL CUCI',{exact:true}).selectOption(f.process)
  await page.getByLabel('POSISI FISIK GAGAL CUCI',{exact:true}).selectOption('RETRY_AT_VENDOR')
  await page.getByLabel('WAKTU GAGAL CUCI',{exact:true}).fill(await when('09:00'))
  await page.getByLabel(`Qty gagal cuci size ${f.size}`,{exact:true}).fill('4')
  await page.getByLabel('ALASAN TAGIHAN GAGAL CUCI',{exact:true}).fill('CP6 UI paid failure four pieces at seven')
  await page.locator('.clq-confirm input').check()
  await mutation(page,'Post jasa gagal cuci atomic','POST_FAILED_WASH',{loseReply:true})
  const attempt=receipt()
  checkState('FAILED_WASH_LOST_REPLY',{fg_qty:0,wip:98,fg:0,accrued:-98,ready:0},
    {control:'Real commit then transport response aborted; reload reconciled original persisted UUID',cost:4*7})
  stage('FAILED_WASH_REVERSE_COST');await reverse(page,attempt,'Batalkan biaya attempt','REVERSE_RECEIPT')
  checkState('FAILED_WASH_REVERSE_COST',{fg_qty:0,wip:70,fg:0,accrued:-70})
  stage('FAILED_WASH_REVERSE_SEND');await reverse(page,sent,'Batalkan pengiriman','REVERSE_DELIVERY')
  checkState('FAILED_WASH_REVERSE_SEND',{fg_qty:0,wip:0,fg:0,accrued:0,ready:10})
  stage('FULL_RETURN_SEND');await sendForm(page)
  await mutation(page,'Post pengiriman atomic','POST_DELIVERY');const fullReturnSend=delivery()
  checkState('FULL_RETURN_SEND',{fg_qty:0,wip:70,fg:0,accrued:-70,ready:0})
  stage('FULL_RETURN_EXACT')
  await page.getByRole('button',{name:'Cuci gagal berbayar',exact:true}).click()
  await page.getByLabel('SURAT KIRIM GAGAL CUCI',{exact:true}).selectOption(fullReturnSend.id)
  await page.getByLabel('PROSES GAGAL CUCI',{exact:true}).selectOption(f.process)
  await page.getByLabel('POSISI FISIK GAGAL CUCI',{exact:true}).selectOption('RETURN_UNPROCESSED')
  await expect(page.getByLabel(`Qty gagal cuci size ${f.size}`,{exact:true})).toHaveValue('10')
  await expect(page.getByLabel(`Qty gagal cuci size ${f.size}`,{exact:true})).toBeDisabled()
  await page.getByLabel('WAKTU GAGAL CUCI',{exact:true}).fill(await when('09:00'))
  await page.getByLabel('ALASAN TAGIHAN GAGAL CUCI',{exact:true}).fill('CP6 UI all ten physically returned unprocessed; paid cost seventy')
  await page.locator('.clq-confirm input').check()
  await mutation(page,'Post jasa gagal cuci atomic','POST_FAILED_WASH');const fullReturnCharge=receipt()
  checkState('FULL_RETURN_EXACT',{fg_qty:0,wip:70,fg:0,accrued:-70,ready:10},
    {custody:'RETURN_UNPROCESSED',physical_return:10,paid_attempt_cost:10*7})
  stage('FULL_RETURN_REDISPATCH');await sendForm(page)
  await mutation(page,'Post pengiriman atomic','POST_DELIVERY');const redispatch=delivery()
  assert.notEqual(redispatch.id,fullReturnSend.id)
  checkState('FULL_RETURN_REDISPATCH',{fg_qty:0,wip:140,fg:0,accrued:-140,ready:0},
    {old_attempt_cost:70,new_delivery_estimate:70,new_document:true})
  stage('FULL_RETURN_REVERSE_COST');await reverse(page,fullReturnCharge,'Batalkan biaya attempt','REVERSE_RECEIPT')
  checkState('FULL_RETURN_REVERSE_COST',{fg_qty:0,wip:70,fg:0,accrued:-70,ready:0},
    {physical_return_and_new_dispatch_preserved:true})
  stage('FULL_RETURN_REVERSE_REDISPATCH');await reverse(page,redispatch,'Batalkan pengiriman','REVERSE_DELIVERY')
  checkState('FULL_RETURN_REVERSE_REDISPATCH',{fg_qty:0,wip:0,fg:0,accrued:0,ready:10})
  assert.equal(report.completed.length,planned.length)
  report.status='WRITER_PASS'
}catch(error){
  failure=error
  let message=String(error.stack||error)
  for(const value of secrets.filter(Boolean))message=message.split(value).join('[REDACTED]')
  message=message.replace(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g,'[JWT REDACTED]')
  report.failure={phase:report.current_phase,message:message.slice(0,9000)}
  report.status='INCOMPLETE'
}finally{
  await Promise.all([...workspaceObservations])
  report.cleanup={status:'INCOMPLETE'};save()
  try{
    await browser?.close()
    if(preview){preview.kill('SIGTERM');await new Promise(ok=>{if(preview.exitCode!==null)ok();else preview.once('exit',ok)})}
    if(proxy){proxy.closeAllConnections();await new Promise(ok=>proxy.close(ok))}
    for(const user of [...users].reverse())await authRequest(`admin/users/${user.id}`,undefined,true,'DELETE')
    const authResidue=Number(query('select count(*) from auth.users',controlPg))
    const sessions=Number(query('select count(*) from auth.sessions',controlPg))
    assert.equal(authResidue,0);assert.equal(sessions,0)
    rmSync(resolve(root,'cp6-ui-build'),{recursive:true,force:true})
    report.cleanup={status:'PASS',auth_users:0,auth_sessions:0,browser_closed:true,proxy_closed:true,
      preview_closed:true,disposable_client_build_removed:true,posted_history:'retained until whole clone disposal'}
  }catch(error){report.cleanup={status:'FAIL',reason:error.name};failure ||=error;report.status='INCOMPLETE'}
  report.unfinished_case_ids=planned.filter(id=>!report.completed.some(x=>x.id===id))
  save()
}
console.log(`CP6 UI: ${report.status}; completed ${report.completed.length}/${planned.length}; cleanup ${report.cleanup.status}`)
if(failure){console.error(report.failure?.message||'CP6 UI cleanup failed');process.exitCode=1}
