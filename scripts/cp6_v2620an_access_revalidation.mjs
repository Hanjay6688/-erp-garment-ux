// Real disposable Auth/HTTP proof of access changes between requests.
// Business SQL, browser source, JWT signature verification and ACLs are unchanged.
import assert from 'node:assert/strict'
import { createHash, randomUUID } from 'node:crypto'
import { writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect } from '@playwright/test'

export async function runAccessRevalidation(c) {
  const readers = [
    ['CUTTING', 'erp_get_cutting_workspace_v2', {}],
    ['PICKUP', 'erp_get_cutting_pickup_queue_v1', {p_filter:'ALL',p_limit:100,p_offset:0}],
    ['WIP', 'erp_get_wip_control_v1', {p_filter:'ALL',p_sort:'PATTERN'}],
    ['BS', 'erp_get_bs_resolution_workspace_v1', {p_filter:'ALL',p_kind:'ALL',p_limit:50,p_offset:0}],
    ['LAUNDRY', 'erp_get_laundry_qc_workspace_v1', {p_scope:'LAUNDRY'}],
    ['QC', 'erp_get_laundry_qc_workspace_v1', {p_scope:'QC'}],
  ]
  const envelope = (payload={}, extra={}) => ({p_payload:payload,p_client_request_id:randomUUID(),p_expected_version:null,...extra})
  const physical = c.query(`select to_char((clock_timestamp()-interval '1 minute') at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"')`)
  const unknown = randomUUID()
  const writers = [
    ['CUTTING_SAVE','erp_save_cutting_group_before_sewing_v2',envelope({action:'SAVE_DRAFT',change_reason:'Revoked session control'})],
    ['PICKUP_SAVE','erp_save_cutting_pickup_v1',envelope({action:'SAVE_DRAFT',change_reason:'Revoked session control'})],
    ['WIP_FLAG','erp_set_wip_control_flag_v1',envelope({cutting_group_id:unknown,flag_type:'OPERATOR_ACTION',status:'OPEN',note:'Disposable role control',change_reason:'Revoked session control'})],
    ['BS_CREATE','erp_save_bs_resolution_action_v1',envelope({bs_number:'RV-'+randomUUID().slice(0,12),untracked_type:'LEGACY',legacy_reference:'Disposable access control',qty_pcs:4,physical_at:physical,change_reason:'Revoked session control',components:[]},{p_action:'CREATE_MANUAL_BS'})],
    ['LAUNDRY_POST','erp_save_laundry_qc_action_v1',envelope({distribution_batch_id:unknown,vendor_id:unknown,wash_process_id:unknown,
      target_dyeing_color:'NAVY',physical_at:physical,reason:'Revoked session control',lines:[{size_id:unknown,qty_sent_pcs:1}]},{p_action:'POST_DELIVERY'})],
    ['QC_POST','erp_post_final_sku_allocation_v1',envelope({cutting_group_id:unknown,destination_location_id:unknown,physical_at:physical,
      reason:'Revoked session control',good_qty_pcs:1,completion_mode:'ALL_READY',lines:[{final_product_id:unknown,qty_good_pcs:1,qty_bs_pcs:0,
        source_laundry_receipt_line_id:unknown,source_laundry_receipt_batch_size_line_id:unknown}]})],
    ['ACCESS_READ','erp_get_access_admin_v1',{}],
    ['ROLE_SAVE','erp_save_role_v1',envelope({code:'RV_'+randomUUID().replaceAll('-','').slice(0,12).toUpperCase(),name:'No self grant',permission_keys:['settings.access.manage'],confirm_high_risk:true,change_reason:'Revoked session control'})],
    ['USER_SAVE','erp_save_app_user_v3',envelope({full_name:'No self grant',change_reason:'Revoked session control'})],
    ['FINAL_SEARCH','erp_search_final_sku_products_v1',{p_source_laundry_receipt_batch_size_line_id:unknown,p_physical_at:physical,p_limit:50}],
    ['LAUNDRY_SEARCH','erp_search_laundry_bs_products_v1',{p_delivery_batch_size_line_id:unknown,p_physical_at:physical,p_limit:50}],
  ]
  const deniedEndpoints = [...readers,...writers]
  const phases = ['REVOKED','DISABLED','REMAPPED','USER_METADATA']
  const planned = [
    ...readers.map(([id])=>'BASELINE_'+id),'BASELINE_ACCESS','BASELINE_BS_CREATE',
    ...phases.flatMap(phase=>deniedEndpoints.map(([id])=>phase+'_'+id)),
    'REVOKED_ACCESS','REVOKED_COMMITTED_REPLAY','RESTORED_COMMITTED_REPLAY',
    'DISABLED_ACCESS','DISABLED_COMMITTED_REPLAY','REMAPPED_ACCESS','USER_METADATA_ACCESS',
    'UI_REVOKED','UI_RESTORED','UI_DISABLED',
    ...readers.map(([id])=>'RESTORED_'+id),
  ]
  const report = {status:'INCOMPLETE',head:c.frontendHead,tree:c.frontendTree,planned_case_ids:planned,cases:[],
    product_reference_head:'08645547394a502584f5270ac64b4f116817c387',
    production_go:false,independent_acceptance:false,product_changed:false,schema_acl_modified:false,
    scope:'Committed access changes between HTTP requests on six connected production readers; permission-first writer refusals; one real BS create and exact replay; UI focus revalidation.',
    exclusions:['Revocation during an already running database transaction','Per-location and external customer isolation','Every action of every ERP module','Financial date policy','CSV transport'],
    negative_writer_source:'Only BS_CREATE and committed replay have a valid business source. Other writer/search controls qualify authorization before domain validation, not positive posting.'}
  const clean = value => {
    let result=JSON.stringify(value)
    for(const secret of c.secrets.filter(Boolean))result=result.split(secret).join('[REDACTED]')
    return JSON.parse(result.replace(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g,'[JWT REDACTED]'))
  }
  const save=()=>writeFileSync(resolve(c.reportDir,'ACCESS_REVALIDATION.json'),JSON.stringify(clean(report),null,2)+'\n')
  const check=async(id,fn)=>{
    assert.ok(planned.includes(id)&&!report.cases.some(row=>row.id===id),id)
    try { report.cases.push({id,status:'PASS',...await fn()}) }
    catch(error) { report.cases.push({id,status:'INCOMPLETE',error:String(error.stack||error).slice(0,4000)}) }
    save()
  }
  const anon=process.env.SUPABASE_ANON_KEY
  async function http(token,name,args) {
    const response=await fetch('http://127.0.0.1:54329/rpc/'+name,{method:'POST',
      headers:{apikey:anon,Authorization:`Bearer ${token}`,'Content-Type':'application/json'},body:JSON.stringify(args)})
    return {status:response.status,body:await response.json()}
  }
  // Read every ERP table, including access, audit and idempotency tables. Denials
  // must roll back the complete statement, not merely conserve aggregate money.
  const tables=JSON.parse(c.query("select jsonb_agg(tablename order by tablename) from pg_catalog.pg_tables where schemaname='erp'"))
  assert.ok(tables.length>=223)
  for(const table of tables)assert.match(table,/^[a-z0-9_]+$/)
  const snapshotSql=tables.map(table=>`select '${table}' as name,md5(coalesce(string_agg(to_jsonb(t)::text,'' order by to_jsonb(t)::text),'')) as digest from erp."${table}" t`).join(' union all ')
  const boundary=()=>createHash('sha256').update(c.query(`select jsonb_agg(s order by name) from (${snapshotSql}) s`)).digest('hex')
  report.boundary_tables=tables.length
  async function denied(token,entry,phase) {
    const before=boundary(), [,name,args]=entry
    const response=await http(token,name,args)
    assert.equal(boundary(),before,'Denied request changed ERP data')
    // The existing Laundry/QC command checks the active app-user mapping before
    // permission and uses this specific P0001 error for a disabled account.
    const inactiveGuard=phase==='DISABLED'&&['LAUNDRY_POST','QC_POST'].includes(entry[0])
      &&response.status===400&&response.body.code==='P0001'&&response.body.message==='Active ERP app user is required'
    if(!inactiveGuard) {
      assert.equal(response.status,403,`${name}: ${JSON.stringify(response)}`)
      assert.equal(response.body.code,'42501',`${name}: expected permission refusal`)
    }
    return {http_status:response.status,code:response.body.code,boundary_unchanged:true}
  }
  const denyAll=async(phase,token)=>{
    for(const entry of deniedEndpoints)await check(phase+'_'+entry[0],()=>denied(token,entry,phase))
  }
  let page
  save()
  try {
    const permissions=JSON.parse(c.query("select jsonb_agg(permission_key order by permission_key) from erp.app_permissions where is_active and permission_key like 'production.%'"))
    assert.ok(permissions.includes('production.bs_rework.create')&&permissions.includes('production.cutting.view'))
    const user=await c.newUser('access-revalidation')
    await c.mapUser(c.session.access_token,user,permissions)
    const session=await c.authRequest('token?grant_type=password',{email:user.email,password:user.password})
    c.secrets.push(session.access_token,session.refresh_token)
    const token=session.access_token
    const identity=()=>JSON.parse(c.query(`select jsonb_build_object('id',u.id,'role_id',u.role_id,'full_name',u.full_name,'row_version',u.row_version,'role_version',r.row_version,'role_code',r.role_code,'role_name',r.role_name) from erp.app_users u join erp.app_roles r on r.id=u.role_id where u.auth_user_id='${user.id}'`))
    const original=identity()
    async function setPermissions(keys) {
      const current=identity()
      await c.rpc(c.session.access_token,'erp_save_role_v1',envelope({id:current.role_id,code:current.role_code,name:current.role_name,
        permission_keys:keys,confirm_high_risk:true,change_reason:'Owner changes permissions between requests'},{p_expected_version:current.role_version}))
    }
    async function setUser(active,roleId=original.role_id) {
      const current=identity()
      await c.rpc(c.session.access_token,'erp_save_app_user_v3',envelope({id:current.id,auth_user_id:user.id,full_name:current.full_name,
        role_id:roleId,is_active:active,change_reason:'Owner changes access between requests'},{p_expected_version:current.row_version}))
    }
    async function access(expectedPermissions,reason) {
      const response=await http(token,'erp_get_my_access_v1',{})
      assert.equal(response.status,200)
      assert.equal(response.body.allowed,!reason)
      if(reason)assert.equal(response.body.reason,reason)
      else assert.deepEqual([...response.body.permissions].sort(),[...expectedPermissions].sort())
      return {allowed:response.body.allowed,reason:response.body.reason,permissions:response.body.permissions}
    }
    for(const [id,name,args] of readers)await check('BASELINE_'+id,async()=>{
      const response=await http(token,name,args);assert.equal(response.status,200,JSON.stringify(response));return {http_status:200}
    })
    await check('BASELINE_ACCESS',()=>access(permissions))
    const freshCreate=writers.find(([id])=>id==='BS_CREATE')
    const create=['BS_COMMITTED_REPLAY',freshCreate[1],envelope({...freshCreate[2].p_payload,
      bs_number:'RV-'+randomUUID().slice(0,12)},{p_action:'CREATE_MANUAL_BS'})]
    let committed
    await check('BASELINE_BS_CREATE',async()=>{
      const response=await http(token,create[1],create[2]);assert.equal(response.status,200,JSON.stringify(response))
      assert.equal(response.body.committed,true);assert.match(response.body.result.bs_case_id,/^[0-9a-f-]{36}$/)
      committed=response.body
      return {http_status:200,qty_pcs:4,bs_case_id:committed.result.bs_case_id}
    })
    page=await c.pageFor(user,false)
    const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
    const link=page.getByRole('button',{name:'• Barang BS & Rework',exact:true})
    if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Produksi'}).click()
    await link.click();await expect(page.getByRole('heading',{name:'Barang BS & Rework',exact:true})).toBeVisible()
    async function focus() {
      const [response]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/rpc/erp_get_my_access_v1')),
        page.evaluate(()=>window.dispatchEvent(new Event('focus')))])
      assert.equal(response.status(),200)
    }
    await setPermissions([])
    await check('REVOKED_ACCESS',()=>access([]))
    await denyAll('REVOKED',token)
    await check('REVOKED_COMMITTED_REPLAY',async()=>{assert.ok(committed);return denied(token,create)})
    await check('UI_REVOKED',async()=>{await focus();await expect(page.getByRole('heading',{name:'Tidak punya akses',exact:true})).toBeVisible();return {same_browser_session:true}})
    await setPermissions(permissions)
    await check('RESTORED_COMMITTED_REPLAY',async()=>{
      assert.ok(committed);const response=await http(token,create[1],create[2]);assert.equal(response.status,200)
      assert.deepEqual(response.body,committed)
      assert.equal(Number(c.query(`select count(*) from erp.bs_cases where bs_number='${create[2].p_payload.bs_number}'`)),1)
      return {http_status:200,exact_response:true,business_rows:1,same_bearer:true}
    })
    await check('UI_RESTORED',async()=>{await focus();await expect(page.getByRole('heading',{name:'Barang BS & Rework',exact:true})).toBeVisible();return {same_browser_session:true}})
    await setUser(false)
    await check('DISABLED_ACCESS',()=>access(null,'APP_USER_INACTIVE'))
    await denyAll('DISABLED',token)
    await check('DISABLED_COMMITTED_REPLAY',async()=>{assert.ok(committed);return denied(token,create)})
    await check('UI_DISABLED',async()=>{await focus();await expect(page.locator('.top-title')).toHaveCount(0);return {same_browser_session:true}})
    await page.context().close();page=null
    const other=await c.rpc(c.session.access_token,'erp_save_role_v1',envelope({code:'RV_'+randomUUID().replaceAll('-','').slice(0,12).toUpperCase(),
      name:'Pattern only remap',permission_keys:['master.pattern.view'],change_reason:'Owner assigns a different role'}))
    await setUser(true,other.role_id)
    await check('REMAPPED_ACCESS',()=>access(['master.pattern.view']))
    await denyAll('REMAPPED',token)
    // Change only self-editable metadata through real Auth; refresh normally so
    // the signed token actually contains that metadata. ERP roles remain mapped.
    const edited=await fetch('http://127.0.0.1:54321/auth/v1/user',{method:'PUT',headers:{apikey:anon,Authorization:`Bearer ${token}`,'Content-Type':'application/json'},
      body:JSON.stringify({data:{role:'OWNER',role_code:'OWNER',permissions:['settings.access.manage',...permissions]}})})
    assert.equal(edited.status,200)
    const refreshed=await c.authRequest('token?grant_type=refresh_token',{refresh_token:session.refresh_token})
    c.secrets.push(refreshed.access_token,refreshed.refresh_token)
    const claims=JSON.parse(Buffer.from(refreshed.access_token.split('.')[1],'base64url').toString('utf8'))
    assert.equal(claims.role,'authenticated');assert.equal(claims.user_metadata.role,'OWNER')
    await check('USER_METADATA_ACCESS',async()=>{
      const response=await http(refreshed.access_token,'erp_get_my_access_v1',{});assert.equal(response.status,200)
      assert.equal(response.body.profile.role_id,other.role_id);assert.deepEqual(response.body.permissions,['master.pattern.view'])
      return {self_metadata_ignored:true,normal_refreshed_session:true}
    })
    await denyAll('USER_METADATA',refreshed.access_token)
    await setUser(true)
    for(const [id,name,args] of readers)await check('RESTORED_'+id,async()=>{
      const response=await http(token,name,args);assert.equal(response.status,200,JSON.stringify(response));return {http_status:200,same_original_bearer:true}
    })
    assert.equal(report.cases.length,planned.length)
    if(report.cases.every(row=>row.status==='PASS'))report.status='WRITER_PASS'
  } catch(error) {report.setup_or_phase_failure=String(error.stack||error).slice(0,5000)}
  finally {await page?.context().close();report.unfinished_case_ids=planned.filter(id=>!report.cases.some(row=>row.id===id));save()}
  return report
}
