// CI browser audit of the actual frozen builds, with network interception.
// Auth/access are MOCKED; all business reads are deliberately denied. This
// proves routing, rendered demo leakage, refusal presentation and viewport
// behavior. It does not prove positive Native commands, actual Auth or hosted.
import assert from 'node:assert/strict'
import {createRequire} from 'node:module'
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs'
import {resolve,dirname} from 'node:path'
import {fileURLToPath} from 'node:url'
const here=dirname(fileURLToPath(import.meta.url))
const root=resolve(process.env.SOL_CANDIDATE_DIR||'../auditor')
const require=createRequire(resolve(root,'package.json'))
const {chromium}=require('@playwright/test')
const mode=process.env.SOL_MODE,origin='http://127.0.0.1:4176'
assert.ok(['DEMO_SIMULATION','UAT_AUTH_SIMULATION','DISPOSABLE_TEST'].includes(mode))
const menus=JSON.parse(readFileSync(resolve(here,'MENUS.json'),'utf8'));assert.equal(menus.length,48)
const permissions=[...new Set([...readFileSync(resolve(root,'src/auth/accessCatalog.ts'),'utf8').matchAll(/'([a-z_]+\.[a-z_.]+)'/g)].map(x=>x[1]))]
const uid='d1a90000-0000-4000-8000-000000000001'
const user={id:uid,aud:'authenticated',role:'authenticated',email:'sol-screen@example.invalid',phone:'',email_confirmed_at:'2026-10-15T00:00:00Z',confirmed_at:'2026-10-15T00:00:00Z',last_sign_in_at:'2026-10-15T00:00:00Z',app_metadata:{provider:'email',providers:['email']},user_metadata:{},identities:[],created_at:'2026-10-15T00:00:00Z',updated_at:'2026-10-15T00:00:00Z'}
const jwt=[{alg:'HS256',typ:'JWT'},{sub:uid,aud:'authenticated',role:'authenticated',exp:4102444800}].map(x=>Buffer.from(JSON.stringify(x)).toString('base64url')).join('.')+'.sol-mock-signature'
const bundle={allowed:true,profile:{id:'d1a90000-0000-4000-8000-000000000002',auth_user_id:uid,full_name:'Sol synthetic Owner',role_id:'d1a90000-0000-4000-8000-000000000003',role_code:'OWNER',role_name:'Owner',is_active:true,row_version:1,role_row_version:1},permissions,external_portals:{mandor:'NOT CONNECTED',laundry:'NOT CONNECTED',store:'NOT CONNECTED'}}
const report={label:'SOL_R2_MODE_WIDTH_AND_REFUSAL',candidate_sha:'2e9d6a468c110684c278d585418eb404250d1150',mode,evidence_origin:'INDEPENDENT_UI_MOCK_RERUN',environment:'CI_CHROMIUM_HTTP_MOCK',business_layer:'INTENTIONALLY_DENIED',auth:'MOCKED',hosted_requests:0,production_go:false,planned:menus.flatMap(m=>['desktop','phone'].map(v=>`${mode}/${v}/${m.page}`)),cases:{}}
const output=resolve(process.env.SOL_OUTPUT||'cp6-proof/sol-menu',mode+'.json');mkdirSync(dirname(output),{recursive:true})
const save=()=>writeFileSync(output,JSON.stringify(report,null,2)+'\n')
save()
const browser=await chromium.launch({headless:true})
try{
 for(const viewport of [{name:'desktop',width:1440,height:900},{name:'phone',width:390,height:844}]){
  const context=await browser.newContext({viewport:{width:viewport.width,height:viewport.height},serviceWorkers:'block'})
  const page=await context.newPage();const rpc=[],errors=[],unexpected=[]
  page.on('pageerror',e=>errors.push(String(e)))
  await context.route('**/*',async route=>{
   const req=route.request(),u=new URL(req.url())
   if(u.origin===origin)return route.continue()
   const mock=(body,status=200)=>route.fulfill({status,contentType:'application/json',headers:{'access-control-allow-origin':origin,'access-control-allow-headers':'authorization,apikey,content-type,x-client-info,x-supabase-api-version,accept-profile,content-profile','access-control-allow-methods':'GET,POST,PUT,DELETE,OPTIONS'},body:JSON.stringify(body)})
   if(!['siimvrusnzxexizpyoib.supabase.co','127.0.0.1'].includes(u.hostname)){unexpected.push({method:req.method(),host:u.hostname,path:u.pathname});return route.abort()}
   if(req.method()==='OPTIONS')return route.fulfill({status:204,headers:{'access-control-allow-origin':origin,'access-control-allow-headers':'authorization,apikey,content-type,x-client-info,x-supabase-api-version,accept-profile,content-profile','access-control-allow-methods':'GET,POST,PUT,DELETE,OPTIONS'}})
   if(u.pathname==='/auth/v1/token')return mock({access_token:jwt,token_type:'bearer',expires_in:3600,expires_at:4102444800,refresh_token:'sol-synthetic-refresh',user})
   if(u.pathname==='/auth/v1/user')return mock(user)
   if(u.pathname.endsWith('/rpc/erp_get_my_access_v1'))return mock(bundle)
   const name=u.pathname.includes('/rpc/')?u.pathname.split('/').at(-1):null
   if(name){rpc.push({name,method:req.method(),response:'SOL_INTENTIONALLY_DENIED_403'});return mock({code:'42501',message:'SOL_SCREEN_AUDIT_READ_DENIED',details:'All business reads deliberately refused in this HTTP-mock routing audit.'},403)}
   unexpected.push({method:req.method(),host:u.hostname,path:u.pathname});return route.abort()
  })
  try{
   await page.goto(origin)
   if(mode!=='DEMO_SIMULATION'){
    await page.getByLabel('Email akun ERP').fill(user.email);await page.getByLabel('Kata sandi').fill('sol-synthetic-password')
    await page.getByRole('button',{name:'Masuk',exact:true}).click()
   }
   await page.locator('.top-title strong').waitFor({state:'visible',timeout:15000})
   for(const menu of menus){
    const key=`${mode}/${viewport.name}/${menu.page}`,start=rpc.length,errStart=errors.length
    try{
     const opener=page.getByRole('button',{name:'Buka menu',exact:true});if(!await page.locator('.sidebar.sidebar-open').count()&&await opener.isVisible())await opener.click()
     if(mode==='UAT_AUTH_SIMULATION'&&menu.uat==='HIDDEN'){
      const branch=page.locator('.sidebar .nav-main').filter({hasText:menu.group})
      if(await branch.count()){
       const active=await branch.getAttribute('class')
       if(!active?.split(' ').includes('active'))await branch.click()
      }
      const target=page.getByRole('button',{name:'• '+menu.label,exact:true})
      assert.equal(await target.count(),0,'D15-2 hidden menu must be absent, including collapsed sections')
      report.cases[key]={status:'PASS',scope:'HIDDEN_MENU_ABSENT_ONLY',menu,viewport:viewport.name,rpc:[],page_errors:[]}
      save();console.log(JSON.stringify({menu:key,status:'PASS',hidden:true}));continue
     }

     if(menu.group){
      const target=page.getByRole('button',{name:'• '+menu.label,exact:true})
      if(!await target.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:menu.group}).click()
      await target.click()
     }else await page.locator('.sidebar').getByRole('button',{name:'Dashboard',exact:true}).click()
     await page.waitForFunction(expected=>document.querySelector('.top-title strong')?.textContent===expected,menu.page==='dashboard'?'Ringkasan bisnis':menu.label,{timeout:8000})
     await page.waitForFunction(()=>!document.querySelector('.page-wrap .placeholder h2')?.textContent?.startsWith('Menyiapkan'),null,{timeout:12000})
     await page.waitForLoadState('networkidle',{timeout:5000}).catch(()=>{})
     const observed=await page.locator('.page-wrap').evaluate(el=>{
      const text=el.innerText
      return {text,headings:[...el.querySelectorAll('h1,h2,h3')].map(e=>e.textContent),buttons:[...el.querySelectorAll('button')].map(e=>({text:e.innerText,aria:e.getAttribute('aria-label'),disabled:e.disabled})),inputs:[...el.querySelectorAll('input,select,textarea')].map(e=>({tag:e.tagName,type:e.type,label:e.getAttribute('aria-label'),placeholder:e.getAttribute('placeholder'),disabled:e.disabled})),root_classes:[...el.children].map(e=>e.className),simulation_label:/SIMULASI UX|data contoh|simulasi/i.test(text),money_strings:[...text.matchAll(/Rp[\d.,\s]+(?:jt|rb|miliar)?/g)].map(x=>x[0]).slice(0,80),document_width:document.documentElement.scrollWidth,viewport:innerWidth,overflow_elements:[...el.querySelectorAll('*')].filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&(r.right>innerWidth+2||r.left< -2)}).slice(0,12).map(e=>({tag:e.tagName,class:e.className,text:(e.textContent||'').slice(0,100)}))}
     })
     const sample=mode==='DEMO_SIMULATION'||(mode==='DISPOSABLE_TEST'&&menu.test==='SAMPLE'); const widthOk=observed.document_width<=observed.viewport; const labelsOk=mode==='DEMO_SIMULATION'||!sample||observed.simulation_label; const leak=mode==='UAT_AUTH_SIMULATION'&&observed.money_strings.length>0; const row={status:errors.length===errStart&&widthOk&&labelsOk&&!leak?'PASS':'FAIL',width_ok:widthOk,sample_label_ok:labelsOk,unlabelled_uat_money:leak,scope:'MODE_ROUTE_WIDTH_AND_REFUSAL_ONLY',menu,viewport:viewport.name,...observed,rpc:rpc.slice(start),page_errors:errors.slice(errStart)}
     report.cases[key]=row
    }catch(e){report.cases[key]={status:'INCOMPLETE',menu,viewport:viewport.name,error:String(e),rpc:rpc.slice(start),page_errors:errors.slice(errStart)}}
    save();console.log(JSON.stringify({menu:key,status:report.cases[key].status,rpc:report.cases[key].rpc.map(x=>x.name)}))
   }
  }catch(e){report[viewport.name+'_setup_error']=String(e)}
  finally{report[viewport.name+'_unexpected_network']=unexpected;await context.close();save()}
 }
}finally{await browser.close()}
report.counts=Object.values(report.cases).reduce((a,x)=>(a[x.status]=(a[x.status]||0)+1,a),{})
report.status=Object.keys(report.cases).length===96&&!report.counts.FAIL&&!report.counts.INCOMPLETE&&!report.desktop_unexpected_network?.length&&!report.phone_unexpected_network?.length?'PASS':'INCOMPLETE'
report.limit='Mock Auth/access, all business reads 403. Hidden rows prove absence only; visible rows prove rendered route, width, sample labels, refusal. No positive Native feature acceptance.';save()
console.log(JSON.stringify({label:report.label,mode,status:report.status,counts:report.counts}))
if(report.status!=='PASS')process.exitCode=1
