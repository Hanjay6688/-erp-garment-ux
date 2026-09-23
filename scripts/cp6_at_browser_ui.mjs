// Real Auth/JWT -> public PostgREST -> committed AT -> existing browser UI.
import assert from 'node:assert/strict'
import { execFileSync, spawn } from 'node:child_process'
import { randomBytes, randomUUID } from 'node:crypto'
import { writeFileSync } from 'node:fs'
import http from 'node:http'
import { resolve } from 'node:path'
import { chromium, expect } from '@playwright/test'

assert.equal(process.env.CP6_AT_BROWSER_CONFIRM,'cp6_rollback')
const pg='postgresql://postgres:postgres@127.0.0.1:54322/cp6_rollback'
const root=process.cwd(), dir=resolve('cp6-proof/at-browser'), origin='http://127.0.0.1:4176', api='http://127.0.0.1:54328'
const anon=process.env.SUPABASE_ANON_KEY, service=process.env.SUPABASE_SERVICE_ROLE_KEY
assert.ok(anon&&service)
const users=[], secrets=[anon,service], cases=[]
const report={status:'INCOMPLETE',classification:'WRITER_REAL_AUTH_BROWSER_AT_IDENTITY',cases,production_go:false,independent_acceptance:false,
  product_responses_mocked:false,phase:'SETUP',console_errors:[]}
const sql=s=>execFileSync('psql',[pg,'-X','-qAt','-v','ON_ERROR_STOP=1','-c',s],{encoding:'utf8',stdio:['ignore','pipe','pipe']}).trim()
const q=v=>"'"+String(v).replaceAll("'","''")+"'"
const native=(mode,...args)=>JSON.parse(execFileSync('python',['scripts/cp6_at_browser_fixture.py',mode,...args],{encoding:'utf8',stdio:['ignore','pipe','pipe']}))
const fixture=native('identities')
const save=()=>writeFileSync(resolve(dir,'FLOW.json'),JSON.stringify(report,null,2)+'\n')
function phase(id){report.phase=id;save();console.log('AT flow: '+id)}
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
  const email=`cp6-at-${label}-${randomUUID()}@example.invalid`,password=`At!${randomBytes(24).toString('hex')}`
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
  const smoke=(...args)=>execFileSync('npx',['--yes','agent-browser@0.38.0','--session','cp6-at-browser','--executable-path',chromium.executablePath(),...args],
    {env:{...safeEnv,AGENT_BROWSER_AUTOSAVE_INTERVAL_MS:'0'},encoding:'utf8',timeout:60000,stdio:['ignore','pipe','pipe']})
  try{smoke('open',origin);smoke('screenshot',resolve(dir,'login.png'));assert.ok(smoke('snapshot','-i').includes('Email akun ERP'));assert.match(smoke('eval',"document.querySelector('vite-error-overlay, [data-nextjs-dialog]') ? 'ERROR' : 'OK'"),/OK/);pass('REAL_LOGIN_PAGE')}finally{smoke('close')}
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

const matches=req=>req.url().endsWith('/rpc/erp_save_initial_import_action_v1')&&req.method()==='POST'&&req.postDataJSON()?.p_action==='WIP_OUTPUT'
async function clickWip(label,status=200){
  const response=page.waitForResponse(r=>matches(r.request()))
  await page.getByRole('button',{name:label,exact:true}).click()
  const r=await response,v=await r.json();assert.equal(r.status(),status,JSON.stringify(v))
  await expect(page.getByRole('button',{name:'Muat ulang',exact:true})).toBeEnabled()
  return {value:v,args:r.request().postDataJSON()}
}
async function fill(f,brand){
  for(const [name,value] of [['Hasil WIP baik','4'],['Produk hasil WIP',f.code],['Merek hasil WIP',brand],
    ['Gudang hasil WIP',f.location],['Tanggal hasil WIP',f.day],['Catatan hasil WIP','Pemeriksaan hasil WIP AT']]){
    await page.getByLabel(name,{exact:true}).fill(value)
  }
}
async function flow(f,index){
  phase('WIP_'+(f.versioned?'VERSIONED':'CROSS_BRAND'))
  await nav(page,'Impor data awal','Pengaturan & Audit')
  await page.getByRole('combobox',{name:'Batch impor',exact:true}).selectOption(f.batch_id)
  await expect(page.getByLabel('Rincian produksi awal',{exact:true})).toBeVisible()
  await page.getByLabel('Rincian produksi awal',{exact:true}).selectOption(f.opening_item_id)
  await fill(f,'')
  const initial=native('state',f.batch_id),before=native('boundary')
  const denied=await clickWip('Sahkan hasil WIP awal',400)
  assert.match(denied.value.message,/AMBIGUOUS/)
  assert.deepEqual(native('boundary'),before)
  pass('AMBIGUOUS_REFUSED_'+index,{http_status:400,all_erp_data_unchanged:true})
  await page.getByLabel('Merek hasil WIP',{exact:true}).fill('  '+f.brand+'  ')
  let accepted
  if(index===0){
    let envelope,committed
    await page.route('**/rpc/erp_save_initial_import_action_v1',async route=>{
      assert.ok(matches(route.request()));envelope=route.request().postDataJSON()
      const response=await route.fetch();assert.equal(response.status(),200);committed=await response.json()
      await route.abort('connectionreset')
    },{times:1})
    await page.getByRole('button',{name:'Sahkan hasil WIP awal',exact:true}).click()
    await expect(page.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeEnabled()
    await expect(page.getByLabel('Merek hasil WIP',{exact:true})).toBeDisabled()
    const posted=native('boundary')
    await page.reload();await nav(page,'Impor data awal','Pengaturan & Audit')
    const retry=page.waitForResponse(r=>matches(r.request()))
    await page.getByRole('button',{name:'Reconcile transaksi',exact:true}).click()
    const response=await retry
    assert.equal(response.status(),200);assert.deepEqual(response.request().postDataJSON(),envelope)
    assert.deepEqual(await response.json(),committed);assert.deepEqual(native('boundary'),posted)
    await expect(page.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0)
    accepted={value:committed,args:envelope}
    pass('LOST_REPLY_RELOAD_EXACT_REPLAY',{brand:f.brand,uuid_payload_preserved:true,all_erp_data_unchanged_on_retry:true})
  }else accepted=await clickWip('Sahkan hasil WIP awal')
  assert.equal(accepted.args.p_payload.brand_code,f.brand)
  assert.equal(accepted.args.p_payload.product_sku,f.code)
  const after=native('state',f.batch_id),active=after.outputs.filter(x=>!x[5])
  assert.equal(active.length,1);assert.equal(active[0][2],f.expected_product);assert.equal(active[0][3],4)
  assert.equal(cents(active[0][4]),2000n);assert.equal(after.remaining,4)
  assert.equal(delta(initial,after,'WIP'),-2000n);assert.equal(delta(initial,after,'FG_INVENTORY'),2000n)
  assert.equal(Number(after.stocks[f.expected_product])-Number(initial.stocks[f.expected_product]),4)
  assert.equal(after.stocks[f.first_product],initial.stocks[f.first_product])
  native('verify')
  pass('EXACT_BRAND_STOCK_HPP_'+index,{product_id:f.expected_product,quantity:4,cost:'20.00',versioned:f.versioned})
  await page.screenshot({path:resolve(dir,'wip-'+index+'.png'),fullPage:true})
  await page.getByLabel('Catatan hasil WIP',{exact:true}).fill('AT restore original WIP with linked inverse')
  await clickWip('Batalkan hasil '+f.day)
  const restored=native('state',f.batch_id)
  assert.equal(restored.remaining,8);assert.deepEqual(restored.stocks,initial.stocks)
  assert.deepEqual(restored.all_ledger,initial.all_ledger);native('verify')
  pass('LINKED_INVERSE_'+index,{wip_restored:8,full_net_ledger_restored:true,stocks_restored:true})
}

try{
  phase('SERVICES');await start();owner=await user('owner')
  sql(`insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active) select ${q(randomUUID())}::uuid,${q(owner.id)}::uuid,'AT real Auth owner','OWNER',id,true from erp.app_roles where role_code='OWNER'`)
  const f=fixture.cases[0],payload={batch_id:f.batch_id,opening_item_id:f.opening_item_id,expected_remaining:'8',qty_pcs:'4',
    product_sku:f.code,brand_code:f.brand,location_code:f.location,date:f.day,reason:'Denied anonymous request'}
  const before=native('boundary'),denied=await request(null,'erp_save_initial_import_action_v1',{p_action:'WIP_OUTPUT',p_payload:payload,p_client_request_id:randomUUID()})
  assert.ok([400,401,403].includes(denied.status));assert.deepEqual(native('boundary'),before)
  pass('ANONYMOUS_REFUSED',{http_status:denied.status,all_erp_data_unchanged:true})
  page=await login(owner);pass('REAL_PASSWORD_BROWSER_LOGIN',{timezone:'Pacific/Honolulu'})
  for(const [index,f] of fixture.cases.entries())await flow(f,index)
  assert.deepEqual(report.console_errors,[]);report.status='PASS'
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
  save();console.log(`AT flow ${report.status}: ${cases.length} completed cases`)
}
if(failure||report.status!=='PASS'){console.error(report.error||'FLOW_CLEANUP_FAILED');process.exitCode=1}
