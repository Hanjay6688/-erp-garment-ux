// Assertions on the pinned product, using the existing local
// Auth/proxy/browser fixture. No business response is supplied by this module.
import assert from 'node:assert/strict'
import {randomUUID, createHash} from 'node:crypto'
import {writeFileSync, readFileSync} from 'node:fs'
import {resolve} from 'node:path'
import {fileURLToPath} from 'node:url'
import {expect} from '@playwright/test'

const actions={CREATE_MANUAL_BS:'create',CLASSIFY_BS:'create',SAVE_REWORK:'create',SAVE_CLAIM:'create',
  COMPLETE_REWORK:'post',DISPOSE_BS:'post',HOLD_BS:'post',RELEASE_HOLD:'post',RESOLVE_CLAIM:'post',
  REVERSE_DISPOSITION:'reverse',REVERSE_REWORK_COMPLETION:'reverse',REVERSE_CLAIM_RESOLUTION:'reverse'}

export async function runIndependentGaps(c){
  const {query,reportDir,owner,session,authRequest,newUser,mapUser,secrets,pageFor,f,nav,
    sendForm,receiveForm,qcForm,mutation,state,financialReport,when,reverse}=c
  const report={status:'INCOMPLETE',candidate_head:c.frontendHead,candidate_tree:c.frontendTree,
    previous_product_checkpoint:'555d8f29ea2d3f58dc2c7d10e7cd80099cdd3b49',
    author_role:process.env.CP6_RUNTIME_GENERATION==='AJ'?'WRITER':'INDEPENDENT_AUDITOR',
    independent_acceptance:false,
    backend_head:c.backendHead,backend_tree:c.backendTree,production_go:false,
    source_sha256:createHash('sha256').update(readFileSync(fileURLToPath(import.meta.url))).digest('hex'),
    cases:[],permission_rows:[],positive_money_permission_rows:[],scope:'Real UI/HTTP observations; native invoice fixture is labelled separately; no CSV interface exists',
    schema_acl_modified:false,all_permission_combinations_claimed:false}
  const roleSessions=[]
  const clean=x=>{
    let text=JSON.stringify(x)
    for(const secret of secrets.filter(Boolean))text=text.split(secret).join('[REDACTED]')
    return JSON.parse(text.replace(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g,'[JWT REDACTED]'))
  }
  const save=()=>writeFileSync(resolve(reportDir,'INDEPENDENT_UI_GAPS.json'),JSON.stringify(clean(report),null,2)+'\n')
  const record=(id,data={})=>{assert.ok(!report.cases.some(x=>x.id===id));report.cases.push({id,status:'PASS',...data});save()}
  const allowed=(bits,...kinds)=>{
    for(const kind of kinds)report.permission_rows.push({bits,action:kind,expectation:'ALLOW_VALID_OPERATION',status:200})
    save()
  }
  const group=async(id,fn)=>{
    try{await fn()}catch(error){report.cases.push({id,status:'INCOMPLETE',error:String(error.stack||error).slice(0,7000)});save()}
  }
  async function request(token,name,body){
    const r=await fetch(`http://127.0.0.1:54329/rpc/${name}`,{method:'POST',
      headers:{apikey:process.env.SUPABASE_ANON_KEY,Authorization:`Bearer ${token||process.env.SUPABASE_ANON_KEY}`,'Content-Type':'application/json'},
      body:JSON.stringify(body)})
    return {status:r.status,body:await r.json()}
  }
  const body=(action,payload,version=null,key=randomUUID())=>({p_action:action,p_payload:payload,p_expected_version:version,p_client_request_id:key})
  const rawAction=(token,action,payload,version=null,key)=>request(token,'erp_save_bs_resolution_action_v1',body(action,payload,version,key))
  async function action(token,kind,payload,version=null,key){
    const r=await rawAction(token,kind,payload,version,key)
    assert.equal(r.status,200,`${kind}: ${JSON.stringify(r.body)}`)
    return r.body
  }
  const todayPhysical=()=>query("select (clock_timestamp()-interval '1 minute')::text")
  const idRx=/^[0-9a-f-]{36}$/
  const bv=id=>{assert.match(id,idRx);return Number(query(`select row_version from erp.bs_cases where id='${id}'`))}
  const rv=id=>{assert.match(id,idRx);return Number(query(`select row_version from erp.rework_orders where id='${id}'`))}
  const snapshot=()=>JSON.parse(query(`select jsonb_build_object(
    'stock',(select coalesce(sum(qty_signed),0) from erp.fg_stock_movements),
    'money',(select coalesce(sum(debit),0) from erp.journal_lines),
    'journals',(select count(*) from erp.journal_entries),
    'entitlements',(select count(*) from erp.contractor_accessory_reimbursement_entitlements),
    'entitlement_rows',(select md5(coalesce(string_agg(to_jsonb(t)::text,'' order by id),'')) from erp.contractor_accessory_reimbursement_entitlements t),
    'hpp_rows',(select md5(coalesce(string_agg(to_jsonb(t)::text,'' order by id),'')) from erp.hpp_versions t),
    'journal_rows',(select md5(coalesce(string_agg(to_jsonb(t)::text,'' order by id),'')) from erp.journal_lines t),
    'context',(select count(*) from erp.bs_resolution_execution_context),
    'unbalanced',(select count(*) from (select journal_entry_id from erp.journal_lines group by journal_entry_id having sum(debit)<>sum(credit)) j))`))
  const businessBoundary=()=>JSON.parse(query(`select jsonb_build_object(
    'cases',(select md5(coalesce(string_agg(to_jsonb(t)::text,'' order by id),'')) from erp.bs_cases t),
    'orders',(select md5(coalesce(string_agg(to_jsonb(t)::text,'' order by id),'')) from erp.rework_orders t),
    'resolutions',(select md5(coalesce(string_agg(to_jsonb(t)::text,'' order by id),'')) from erp.bs_resolutions t),
    'claims',(select md5(coalesce(string_agg(to_jsonb(t)::text,'' order by id),'')) from erp.laundry_claims t),
    'context',(select count(*) from erp.bs_resolution_execution_context))`))
  async function manual(token= session.access_token,quantity=4){
    const number='IND-BS-'+randomUUID().slice(0,12)
    const r=await action(token,'CREATE_MANUAL_BS',{bs_number:number,untracked_type:'LEGACY',legacy_reference:'Disposable count '+number,
      qty_pcs:quantity,physical_at:todayPhysical(),change_reason:'Independent original manual BS path',components:[]})
    const id=r.result.bs_case_id;assert.match(id,idRx);return {id,number}
  }
  async function bsNav(page){
    const menu=page.getByRole('button',{name:'Buka menu',exact:true})
    if(await menu.isVisible())await menu.click()
    const link=page.getByRole('button',{name:'• Barang BS & Rework',exact:true})
    if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Produksi'}).click()
    await link.click();await expect(page.getByRole('heading',{name:'Barang BS & Rework',exact:true})).toBeVisible()
    await expect(page.getByRole('button',{name:'Refetch',exact:true})).toBeEnabled()
    assert.deepEqual(await page.locator('.cbsr-alert.error').allTextContents(),[])
  }
  async function selectCase(page,number){
    await page.getByPlaceholder('Nomor, PO, model, Pola, pihak…').fill(number)
    const [reply]=await Promise.all([
      page.waitForResponse(r=>r.url().endsWith('/rpc/erp_get_bs_resolution_workspace_v1')&&r.request().postDataJSON()?.p_query===number),
      page.locator('.cbsr-search').getByRole('button',{name:'Cari',exact:true}).click(),
    ])
    assert.equal(reply.status(),200)
    await expect(page.locator('.cbsr-detail h2')).toHaveText(number)
  }
  async function bsMutation(page,button,kind){
    const control=typeof button==='string'?page.getByRole('button',{name:button,exact:true}):button
    await expect(control).toBeEnabled()
    const [r]=await Promise.all([
      page.waitForResponse(r=>r.url().endsWith('/rpc/erp_save_bs_resolution_action_v1')&&r.request().postDataJSON()?.p_action===kind),
      control.click(),
    ])
    const value=await r.json()
    report.last_mutation={action:kind,request:r.request().postDataJSON(),http_status:r.status(),response:value}
    save();assert.equal(r.status(),200,JSON.stringify(report.last_mutation))
    await expect(page.locator('.cbsr-busy')).toHaveCount(0)
    await expect(page.getByRole('button',{name:'Refetch',exact:true})).toBeEnabled()
    assert.deepEqual(await page.locator('.cbsr-alert.error').allTextContents(),[])
    return {request:r.request().postDataJSON(),response:value}
  }

  save()
  await group('PERMISSION_MATRIX_EXECUTION',async()=>{
    // All eight create/post/reverse bit combinations: prove every missing
    // capability refuses before payload processing, plus actual allowed create
    // and hold/release commands. This is deliberately not "all roles PASS".
    for(let bits=0;bits<8;bits++){
      const caps=['create','post','reverse'].filter((_,i)=>bits&(1<<i))
      const user=await newUser(`bs-bits-${bits}`)
      await mapUser(session.access_token,user,['production.bs_rework.view',...caps.map(x=>'production.bs_rework.'+x)])
      const login=await authRequest('token?grant_type=password',{email:user.email,password:user.password})
      secrets.push(login.access_token,login.refresh_token)
      roleSessions.push({bits,capabilities:caps,token:login.access_token,user})
      for(const [kind,cap] of Object.entries(actions)){
        if(caps.includes(cap))continue
        const before=snapshot(),boundary=businessBoundary()
        const r=await rawAction(login.access_token,kind,{change_reason:'Independent absent permission control'})
        assert.ok(r.status!==200,`Missing ${cap} accepted ${kind}`)
        assert.match(r.body.message||'',/permission|izin/i,JSON.stringify(r.body))
        assert.deepEqual(snapshot(),before)
        assert.deepEqual(businessBoundary(),boundary)
        report.permission_rows.push({bits,capabilities:caps,action:kind,expectation:'DENY_MISSING_PERMISSION',status:r.status,code:r.body.code})
        save()
      }
      if(caps.includes('create')){
        const m=await manual(login.access_token)
        allowed(bits,'CREATE_MANUAL_BS')
        record(`ROLE_${bits}_CREATE`,{actual_case_id:m.id})
      }
      if(caps.includes('post')){
        const m=await manual()
        const before=snapshot()
        await action(login.access_token,'HOLD_BS',{bs_case_id:m.id,physical_at:todayPhysical(),change_reason:'Independent granular post hold'},bv(m.id))
        assert.equal(query(`select status from erp.bs_cases where id='${m.id}'`),'ON_HOLD')
        await action(login.access_token,'RELEASE_HOLD',{bs_case_id:m.id,physical_at:todayPhysical(),change_reason:'Independent granular post release'},bv(m.id))
        assert.equal(query(`select status from erp.bs_cases where id='${m.id}'`),'OPEN')
        assert.deepEqual(snapshot(),before)
        allowed(bits,'HOLD_BS','RELEASE_HOLD')
        record(`ROLE_${bits}_HOLD_RELEASE`,{ledger_unchanged:true})
      }
    }
    record('PERMISSION_MATRIX',{missing_permission_pairs:report.permission_rows.filter(r=>r.expectation==='DENY_MISSING_PERMISSION').length,exact_masks:[0,1,2,3,4,5,6,7]})
  })

  async function prepareRework(){
    const bs=await manual()
    const made=await action(session.access_token,'SAVE_REWORK',{rework_number:'ROLE-RW-'+randomUUID().slice(0,12),
      bs_case_id:bs.id,destination_type:'LAUNDRY',contractor_id:null,vendor_id:f.vendor,qty_sent:4,
      physical_sent_at:todayPhysical(),status:'IN_PROGRESS',accessory_bom_version_id:null,
      accessory_bom_item_ids:[],components:[],change_reason:'Role matrix original legacy all-BS rewash'})
    return made.result.rework_order_id
  }
  async function completeLegacy(id,token=session.access_token){
    return action(token,'COMPLETE_REWORK',{rework_order_id:id,qty_good:0,qty_bs:4,completed_at:todayPhysical(),
      return_fg_location_id:null,change_reason:'All four physical pieces returned BS; no invented FG'},rv(id))
  }
  const claimVersion=id=>{assert.match(id,idRx);return Number(query(`select row_version from erp.laundry_claims where id='${id}'`))}
  async function makeClaim(delivery,token=session.access_token,type='STUCK'){
    const r=await action(token,'SAVE_CLAIM',{action:'SAVE',claim_number:'ROLE-CL-'+randomUUID().slice(0,12),
      vendor_id:f.vendor,delivery_id:delivery,receipt_line_id:null,qty_claimed:1,claim_type:type,
      compensation_amount:0,opened_at:query('select clock_timestamp()::text'),
      notes:'One physical piece still with vendor',change_reason:'Independent ordinary claim source'})
    return r.result.laundry_claim_id||r.result.claim_id
  }
  async function rejectClaim(id){
    assert.match(id,idRx)
    return action(session.access_token,'SAVE_CLAIM',{id,action:'REJECT',change_reason:'Independent linked claim release'},claimVersion(id))
  }
  async function remainingRoleCases(delivery){
    for(const profile of roleSessions){
      const {bits,capabilities:caps,token}=profile
      if(caps.includes('create')){
        await group(`ROLE_${bits}_CLASSIFY_REWORK_CLAIM`,async()=>{
          const m=await manual()
          await action(token,'CLASSIFY_BS',{bs_case_id:m.id,cause_source:'UNKNOWN',components:[],change_reason:'Independent granular classification'},bv(m.id))
          const order=await action(token,'SAVE_REWORK',{rework_number:'GRANULAR-'+randomUUID().slice(0,12),bs_case_id:m.id,
            destination_type:'LAUNDRY',vendor_id:f.vendor,contractor_id:null,qty_sent:4,physical_sent_at:todayPhysical(),
            status:'IN_PROGRESS',accessory_bom_version_id:null,accessory_bom_item_ids:[],components:[],change_reason:'Independent granular rewash create'})
          const orderId=order.result.rework_order_id
          await action(token,'SAVE_REWORK',{id:orderId,action:'CANCEL',change_reason:'Independent unreturned order cancellation'},rv(orderId))
          const claim=await makeClaim(delivery,token)
          await rejectClaim(claim)
          allowed(bits,'CLASSIFY_BS','SAVE_REWORK','SAVE_CLAIM')
          record(`ROLE_${bits}_CLASSIFY_REWORK_CLAIM`,{classification:true,rewash_create_cancel:true,real_claim:true})
        })
      }
      if(caps.includes('post')){
        await group(`ROLE_${bits}_COMPLETE_DISPOSE`,async()=>{
          const before=snapshot(),order=await prepareRework()
          await completeLegacy(order,token)
          const m=await manual()
          await action(token,'DISPOSE_BS',{bs_case_id:m.id,resolution_type:'WRITE_OFF',qty_pcs:1,compensation_amount:0,
            physical_at:todayPhysical(),change_reason:'Independent granular writeoff'},bv(m.id))
          assert.deepEqual(snapshot(),before)
          allowed(bits,'COMPLETE_REWORK','DISPOSE_BS')
          record(`ROLE_${bits}_COMPLETE_DISPOSE`,{all_bs_complete:true,writeoff:true,no_financial_rows:true})
        })
      }
      for(const kind of ['RESOLVE_CLAIM','REVERSE_DISPOSITION','REVERSE_REWORK_COMPLETION','REVERSE_CLAIM_RESOLUTION']){
        if(!caps.includes(actions[kind]))continue
        await group(`ROLE_${bits}_${kind}_OWNER_BOUNDARY`,async()=>{
          let payload,version,claim
          if(kind==='REVERSE_DISPOSITION'){
            const m=await manual()
            const posted=await action(session.access_token,'DISPOSE_BS',{bs_case_id:m.id,resolution_type:'SCRAP',qty_pcs:1,
              compensation_amount:0,physical_at:todayPhysical(),change_reason:'Independent reversal role source'},bv(m.id))
            const resolution=posted.result.resolution_id
              ||query(`select id from erp.bs_resolutions where bs_case_id='${m.id}' order by created_at desc limit 1`)
            payload={resolution_id:resolution,change_reason:'Nonowner with exact reverse permission'};version=bv(m.id)
          }else if(kind==='REVERSE_REWORK_COMPLETION'){
            const order=await prepareRework();await completeLegacy(order)
            payload={rework_order_id:order,change_reason:'Nonowner with exact reverse permission'};version=rv(order)
          }else{
            claim=await makeClaim(delivery)
            if(kind==='REVERSE_CLAIM_RESOLUTION')await action(session.access_token,'RESOLVE_CLAIM',{
              laundry_claim_id:claim,resolution:'WRITTEN_OFF',change_reason:'Owner confirms zero-compensation physical claim'},claimVersion(claim))
            payload={laundry_claim_id:claim,resolution:'WRITTEN_OFF',change_reason:'Nonowner with exact post/reverse permission'}
            version=claimVersion(claim)
          }
          const before=snapshot(),boundary=businessBoundary()
          const response=await rawAction(token,kind,payload,version)
          assert.notEqual(response.status,200,'Nonowner accepted owner-only action '+kind)
          assert.match(response.body.message||'',/owner|admin/i,JSON.stringify(response.body))
          assert.deepEqual(snapshot(),before);assert.deepEqual(businessBoundary(),boundary)
          report.permission_rows.push({bits,action:kind,expectation:'DENY_OWNER_ADMIN_REQUIRED',status:response.status})
          // An OWNER performs the identical valid operation, so a generic bad
          // payload cannot qualify the role denial.
          await action(session.access_token,kind,payload,version)
          if(claim){
            if(kind==='RESOLVE_CLAIM')await action(session.access_token,'REVERSE_CLAIM_RESOLUTION',{
              laundry_claim_id:claim,change_reason:'Owner linked zero-compensation claim correction'},claimVersion(claim))
            await rejectClaim(claim)
          }
          record(`ROLE_${bits}_${kind}_OWNER_BOUNDARY`,{nonowner_atomic_refusal:true,identical_owner_payload_accepted:true})
        })
      }
    }
  }

  await group('LEGACY_UI_LIFECYCLE',async()=>{
    const page=await pageFor(owner)
    try{
      await bsNav(page)
      await page.getByRole('button',{name:'BS legacy',exact:true}).click()
      const modal=page.getByRole('dialog'), number='UI-LEGACY-'+randomUUID().slice(0,8)
      await modal.getByLabel('NOMOR BS · OPSIONAL',{exact:true}).fill(number)
      await modal.getByLabel('REFERENSI LEGACY · WAJIB',{exact:true}).fill('Physical book entry independent fixture')
      await modal.getByLabel('QTY PCS',{exact:true}).fill('4')
      await modal.getByLabel('ALASAN PENCATATAN · WAJIB',{exact:true}).fill('Four physical synthetic legacy defects')
      const before=snapshot()
      await bsMutation(page,'Simpan kasus authoritative','CREATE_MANUAL_BS')
      assert.deepEqual(snapshot(),before)
      record('UI_LEGACY_CREATE',{quantity:4,ledger_unchanged:true})
      await selectCase(page,number)
      await page.locator('.cbsr-route-tabs').getByRole('button',{name:'Hold',exact:true}).click()
      await page.locator('.cbsr-route-form').getByLabel('ALASAN · WAJIB',{exact:true}).fill('Independent physical hold')
      await bsMutation(page,'Simpan HOLD','HOLD_BS');record('UI_HOLD')
      await page.locator('.cbsr-route-tabs').getByRole('button',{name:'Hold',exact:true}).click()
      await page.locator('.cbsr-route-form').getByLabel('ALASAN · WAJIB',{exact:true}).fill('Independent physical release')
      await bsMutation(page,'Release HOLD','RELEASE_HOLD');record('UI_RELEASE_HOLD')
      await page.locator('.cbsr-route-tabs').getByRole('button',{name:'Scrap / write-off',exact:true}).click()
      await page.locator('.cbsr-route-form').getByLabel('QTY',{exact:true}).fill('1')
      await page.locator('.cbsr-route-form').getByLabel('ALASAN · WAJIB',{exact:true}).fill('Independent one piece scrap')
      await bsMutation(page,'Post disposition','DISPOSE_BS');record('UI_SCRAP')
      const reversal=page.locator('.cbsr-inline-reverse').first()
      await reversal.getByPlaceholder('Alasan reversal Owner/Admin').fill('Independent linked scrap correction')
      await bsMutation(page,reversal.getByRole('button',{name:'Reverse',exact:true}),'REVERSE_DISPOSITION')
      assert.deepEqual(snapshot(),before)
      record('UI_REVERSE_SCRAP',{ledger_unchanged:true})
      await page.screenshot({path:resolve(reportDir,'INDEPENDENT_LEGACY_UI.png'),fullPage:true})
    }finally{await page.context().close()}
  })

  await group('POSITIVE_MONEY_CLAIM_UI_LIFECYCLE',async()=>{
    const page=await pageFor(owner)
    let operatorPage
    const balances=()=>JSON.parse(query(`select jsonb_object_agg(k,amount) from (
      select k,coalesce((select sum(l.debit-l.credit) from erp.journal_lines l
        join erp.journal_entries e on e.id=l.journal_entry_id
        where e.status in('POSTED','REVERSED') and l.account_id=erp.account_id(k)),0) amount
      from unnest(array['AP_VENDOR','OTHER_EXPENSE','WIP','FG_INVENTORY','ACCRUED_MANUFACTURING']) k) b`))
    const nowBrowser=p=>p.evaluate(()=>{const n=new Date();return new Date(n.getTime()-n.getTimezoneOffset()*60000).toISOString().slice(0,19).replace(/:00$/,'')})
    const pick=(p,scope,caption)=>scope.locator('label').filter({has:p.getByText(caption,{exact:true})}).locator('select')
    async function showAll(p){
      const [r]=await Promise.all([p.waitForResponse(r=>r.url().endsWith('/rpc/erp_get_bs_resolution_workspace_v1')&&r.request().postDataJSON()?.p_filter==='ALL'),
        p.locator('.cbsr-tabs').getByRole('button',{name:'Semua',exact:true}).click()])
      assert.equal(r.status(),200);await expect(p.getByRole('button',{name:'Refetch',exact:true})).toBeEnabled()
    }
    async function moneyDenied(profile,kind,payload,version,ownerOnly=false){
      const before=snapshot(),boundary=businessBoundary(),r=await rawAction(profile.token,kind,payload,version)
      assert.notEqual(r.status,200,`Positive money ${profile.bits}:${kind} unexpectedly accepted`)
      assert.match(r.body.message||'',ownerOnly?/owner|admin/i:/permission|izin/i,JSON.stringify(r.body))
      assert.deepEqual(snapshot(),before);assert.deepEqual(businessBoundary(),boundary)
      report.positive_money_permission_rows.push({bits:profile.bits,action:kind,status:r.status,
        expectation:ownerOnly?'DENY_OWNER_ADMIN_REQUIRED':'DENY_MISSING_PERMISSION',atomic:true});save()
    }
    try{
      const baseline=balances(),initial=state()
      assert.equal(initial.ready,10);assert.equal(initial.fg_qty,0);assert.equal(initial.wip,0)
      await nav(page,'Laundry');await sendForm(page);await mutation(page,'Post pengiriman atomic','POST_DELIVERY')
      const sent=JSON.parse(query(`select jsonb_build_object('id',id,'number',delivery_number) from erp.laundry_deliveries where po_id='${f.po}' and status='SENT' order by created_at desc limit 1`))
      await receiveForm(page,8)
      await page.getByLabel(`BS Laundry size ${f.size}`,{exact:true}).fill('2')
      await page.getByLabel(`SKU BS size ${f.size}`,{exact:true}).selectOption(f.product)
      await page.locator('.clq-confirm input').check()
      await mutation(page,'Post penerimaan atomic','POST_RECEIPT')
      const returned=JSON.parse(query(`select jsonb_build_object('id',id,'number',receipt_number) from erp.laundry_receipts where delivery_id='${sent.id}' and status='POSTED' order by created_at desc limit 1`))
      const line=query(`select id from erp.laundry_receipt_lines where receipt_id='${returned.id}'`)
      assert.match(line,idRx)
      const bs=JSON.parse(query(`select jsonb_build_object('id',id,'number',bs_number) from erp.bs_cases where source_laundry_receipt_line_id='${line}'`))
      assert.match(bs.id,idRx)
      // The product has no invoice HTTP facade. Establish a real payable only
      // through its existing native DRAFT -> post function, with mapped OWNER;
      // this setup is not reported as invoice UI/Auth/HTTP coverage.
      const invoice=randomUUID()
      query(`begin; set local request.jwt.claims='{"role":"authenticated","sub":"${owner.id}"}';
        insert into erp.vendor_invoices(id,invoice_number,vendor_id,invoice_date,received_at,due_date,status,total_amount,notes,created_by)
        values('${invoice}','UI-MONEY-${invoice}','${f.vendor}',(statement_timestamp() at time zone 'Asia/Jakarta')::date,
          statement_timestamp(),(statement_timestamp() at time zone 'Asia/Jakarta')::date+30,'DRAFT',70,
          'Native payable fixture for real claim UI; ten actual returned pieces at seven',erp.current_app_user_id());
        insert into erp.vendor_invoice_items(invoice_id,receipt_line_id,description,qty_pcs,actual_rate,actual_amount)
        values('${invoice}','${line}','Actual returned 8 Good plus 2 BS',10,7,70);
        select erp.post_vendor_invoice('${invoice}'); commit;`)
      const invoiced=balances()
      assert.equal(invoiced.AP_VENDOR-baseline.AP_VENDOR,-70)
      assert.equal(state().wip,70)
      record('CLAIM_PAYABLE_NATIVE_FIXTURE',{invoice_id:invoice,amount:70,qty:10,rate:7,
        interface:'NATIVE_EXISTING_DRAFT_POST_FUNCTION',role:'postgres with mapped OWNER context',invoice_http_ui_claimed:false})
      await bsNav(page);await showAll(page)
      await page.getByRole('button',{name:'Claim Laundry',exact:true}).click()
      const modal=page.getByRole('dialog',{name:'Buat claim Laundry',exact:true})
      await pick(page,modal,'JENIS').selectOption('DAMAGE')
      await pick(page,modal,'BARIS PENERIMAAN BS').selectOption(line)
      const claimNumber='UI-CENTS-'+randomUUID().slice(0,12)
      await modal.getByLabel('NOMOR CLAIM',{exact:true}).fill(claimNumber)
      await modal.getByLabel('QTY CLAIM · MAKS 2',{exact:true}).fill('2')
      await modal.getByLabel('NILAI KOMPENSASI',{exact:true}).fill('14,25')
      await modal.getByLabel('WAKTU DIBUKA',{exact:true}).fill(await nowBrowser(page))
      await modal.getByLabel('ALASAN / BUKTI · WAJIB',{exact:true}).fill('Two damaged pieces, agreed compensation fourteen and twenty five cents')
      const beforeDraft=snapshot(),created=await bsMutation(page,'Simpan claim','SAVE_CLAIM')
      assert.equal(created.request.p_payload.compensation_amount,14.25)
      assert.deepEqual(snapshot(),beforeDraft)
      const claim=query(`select id from erp.laundry_claims where claim_number='${claimNumber}'`)
      assert.match(claim,idRx)
      assert.equal(Number(query(`select compensation_amount from erp.laundry_claims where id='${claim}'`)),14.25)
      await selectCase(page,claimNumber)
      await page.locator('.cbsr-actions.claim textarea').fill('Vendor accepted documented two-piece compensation')
      await bsMutation(page,'Terima claim','SAVE_CLAIM');assert.deepEqual(snapshot(),beforeDraft)
      record('UI_CLAIM_CENTS_CREATE_ACCEPT',{qty:2,input:'14,25',http_amount:14.25,stored_amount:14.25,ledger_inert:true})
      const settlePayload={laundry_claim_id:claim,resolution:'SETTLED',change_reason:'Positive value role qualification'}
      for(const profile of roleSessions)await moneyDenied(profile,'RESOLVE_CLAIM',settlePayload,claimVersion(claim),profile.capabilities.includes('post'))
      await page.locator('.cbsr-actions.claim textarea').fill('Owner settles exact agreed compensation against real vendor payable')
      await bsMutation(page,'Resolve','RESOLVE_CLAIM')
      const settled=balances()
      assert.equal(settled.AP_VENDOR-invoiced.AP_VENDOR,14.25)
      assert.equal(settled.OTHER_EXPENSE-invoiced.OTHER_EXPENSE,-14.25)
      assert.equal(settled.WIP,invoiced.WIP);assert.equal(state().fg_qty,0)
      const journal=JSON.parse(query(`select jsonb_build_object('count',count(distinct e.id),'debit',sum(l.debit),'credit',sum(l.credit))
        from erp.journal_entries e join erp.journal_lines l on l.journal_entry_id=e.id
        where e.source_type='LAUNDRY_CLAIM_SETTLEMENT' and e.source_id='${claim}'`))
      assert.deepEqual(journal,{count:1,debit:14.25,credit:14.25})
      record('UI_CLAIM_CENTS_SETTLE',{expected_ap_reduction:14.25,journal,observed:balances()})
      for(const profile of roleSessions)await moneyDenied(profile,'REVERSE_CLAIM_RESOLUTION',{
        laundry_claim_id:claim,change_reason:'Positive settled amount requires owner reversal'},claimVersion(claim),profile.capabilities.includes('reverse'))
      await selectCase(page,bs.number)
      const classification=page.locator('.cbsr-fold');await classification.locator('summary').click()
      await pick(page,classification,'SUMBER PENYEBAB').selectOption('LAUNDRY')
      await pick(page,classification,'VENDOR TANGGUNG JAWAB').selectOption(f.vendor)
      await classification.getByLabel('ALASAN PERUBAHAN · WAJIB',{exact:true}).fill('Two returned defects belong to the original laundry vendor')
      await bsMutation(page,'Simpan klasifikasi','CLASSIFY_BS')
      const disposition={bs_case_id:bs.id,resolution_type:'CASH_COMPENSATION',qty_pcs:2,compensation_amount:14.25,
        source_laundry_claim_id:claim,physical_at:query('select clock_timestamp()::text'),change_reason:'Apply agreed settled claim once to its actual BS source'}
      const afterSettlement=snapshot()
      for(const profile of roleSessions){
        if(!profile.capabilities.includes('post'))await moneyDenied(profile,'DISPOSE_BS',disposition,bv(bs.id))
        else{
          const r=await action(profile.token,'DISPOSE_BS',disposition,bv(bs.id))
          const resolution=r.result.bs_resolution_id
          assert.match(resolution,idRx);assert.deepEqual(snapshot(),afterSettlement)
          await action(session.access_token,'REVERSE_DISPOSITION',{resolution_id:resolution,change_reason:'Owner linked reversal after positive value role control'},bv(bs.id))
          assert.deepEqual(snapshot(),afterSettlement)
          report.positive_money_permission_rows.push({bits:profile.bits,action:'DISPOSE_BS',status:200,expectation:'ALLOW_VALID_OPERATION',amount:14.25,linked_owner_reversal:true});save()
        }
      }
      operatorPage=await pageFor(roleSessions.find(x=>x.bits===2).user)
      await bsNav(operatorPage);await showAll(operatorPage);await selectCase(operatorPage,bs.number)
      await operatorPage.locator('.cbsr-route-tabs').getByRole('button',{name:'Kompensasi',exact:true}).click()
      const form=operatorPage.locator('.cbsr-route-form')
      await pick(operatorPage,form,'CLAIM SETTLED · SALDO TERSEDIA').selectOption(claim)
      await form.getByLabel('QTY · MAKS 2',{exact:true}).fill('2')
      await form.getByLabel('NILAI DIPAKAI · MAKS Rp14,25',{exact:true}).fill('14.25')
      await form.getByLabel('WAKTU FISIK',{exact:true}).fill(await nowBrowser(operatorPage))
      await form.getByLabel('ALASAN · WAJIB',{exact:true}).fill('Apply exact approved amount to two damaged pieces; no second payable credit')
      const applied=await bsMutation(operatorPage,'Post disposition','DISPOSE_BS')
      assert.equal(applied.request.p_payload.compensation_amount,14.25)
      const resolution=applied.response.result.bs_resolution_id
      assert.match(resolution,idRx)
      assert.equal(Number(query(`select compensation_amount from erp.bs_resolutions where id='${resolution}'`)),14.25)
      assert.deepEqual(snapshot(),afterSettlement);assert.deepEqual(balances(),settled)
      const originalProfile=roleSessions.find(x=>x.bits===2)
      // Same browser user; its token and the API token resolve to the same actor.
      const replayBefore=businessBoundary(),replay=await request(originalProfile.token,'erp_save_bs_resolution_action_v1',applied.request)
      assert.equal(replay.status,200);assert.deepEqual(replay.body,applied.response)
      assert.deepEqual(businessBoundary(),replayBefore);assert.deepEqual(snapshot(),afterSettlement)
      record('UI_COMPENSATION_CENTS_APPLY',{qty:2,amount:14.25,granular_nonowner_post:true,ledger_unchanged:true,same_actor_replay_exact:true})
      const exhausted=await rawAction(originalProfile.token,'DISPOSE_BS',{...disposition,qty_pcs:1,compensation_amount:0.25},bv(bs.id))
      assert.notEqual(exhausted.status,200);assert.match(exhausted.body.message||'',/closed|available|exceed/i)
      assert.deepEqual(snapshot(),afterSettlement);assert.deepEqual(businessBoundary(),replayBefore)
      const dependent=await rawAction(session.access_token,'REVERSE_CLAIM_RESOLUTION',{
        laundry_claim_id:claim,change_reason:'Dependent compensation must be reversed first'},claimVersion(claim))
      assert.notEqual(dependent.status,200);assert.match(dependent.body.message||'',/CLAIM_RESOLUTION_IN_USE_BY_ACTIVE_BS_CASH_COMPENSATION/)
      assert.deepEqual(snapshot(),afterSettlement);assert.deepEqual(businessBoundary(),replayBefore)
      for(const profile of roleSessions)await moneyDenied(profile,'REVERSE_DISPOSITION',{
        resolution_id:resolution,change_reason:'Positive allocation reversal requires owner'},bv(bs.id),profile.capabilities.includes('reverse'))
      record('CLAIM_MONEY_DEPENDENCY_REFUSALS',{exhausted_status:exhausted.status,dependent_status:dependent.status,atomic:true})
      await selectCase(page,bs.number)
      const inline=page.locator('.cbsr-inline-reverse')
      await inline.getByPlaceholder('Alasan reversal Owner/Admin').fill('Owner corrects linked compensation allocation first')
      await bsMutation(page,inline.getByRole('button',{name:'Reverse',exact:true}),'REVERSE_DISPOSITION')
      assert.deepEqual(snapshot(),afterSettlement)
      assert.equal(Number(query(`select count(*) from erp.audit_logs where entity_type='bs_resolutions' and entity_id='${resolution}' and action='REVERSE'`)),1)
      await selectCase(page,claimNumber)
      await page.locator('.cbsr-actions.claim textarea').fill('Owner reverses the settlement after its dependent allocation')
      const reversed=await bsMutation(page,'Reverse resolution','REVERSE_CLAIM_RESOLUTION')
      assert.deepEqual(balances(),invoiced)
      // The original canonical reversal cancels the claim and releases source
      // capacity atomically. There is no second reject action on this state.
      assert.equal(reversed.response.result.status,'REJECTED')
      assert.equal(query(`select status from erp.laundry_claims where id='${claim}'`),'REJECTED')
      record('UI_CLAIM_MONEY_LINKED_REVERSAL',{allocation_audit_history:true,balances_restored_to_invoice:true,claim_status:'REJECTED'})
      query(`begin; set local request.jwt.claims='{"role":"authenticated","sub":"${owner.id}"}';
        select erp.reverse_vendor_invoice('${invoice}','Native fixture invoice linked correction after real UI claim lifecycle'); commit;`)
      await nav(page,'Laundry');await reverse(page,returned,'Batalkan penerimaan','REVERSE_RECEIPT')
      await reverse(page,sent,'Batalkan pengiriman','REVERSE_DELIVERY')
      assert.deepEqual(balances(),baseline)
      assert.equal(state().wip,0);assert.equal(state().fg_qty,0);assert.equal(state().ready,10)
      assert.equal(financialReport().data_confidence.status,'READY')
      assert.equal(report.positive_money_permission_rows.length,32)
      record('UI_CLAIM_MONEY_LIFECYCLE_COMPLETE',{action_mask_pairs:32,positive_amount:14.25,balances_restored:true,
        native_invoice_setup_teardown:true,all_claim_and_compensation_mutations_real_auth_http:true})
      await page.screenshot({path:resolve(reportDir,'CLAIM_MONEY_LINKED_REVERSAL_UI.png'),fullPage:true})
    }catch(error){
      report.money_dom={alerts:await page.locator('.cbsr-alert,.clq-alert').allTextContents(),
        detail:await page.locator('.cbsr-detail,.cbsr-modal-layer').allTextContents()}
      await page.screenshot({path:resolve(reportDir,'CLAIM_MONEY_INCOMPLETE_UI.png'),fullPage:true}).catch(()=>{})
      throw error
    }finally{await operatorPage?.context().close();await page.context().close()}
  })

  await group('NATIVE_REWORK_UI_LIFECYCLE',async()=>{
    const user=await newUser('independent-bs-operator')
    await mapUser(session.access_token,user,['production.laundry.view','production.laundry.create','production.laundry.post',
      'production.final_sku.view','production.final_sku.post','production.bs_rework.view','production.bs_rework.create','production.bs_rework.post'])
    const page=await pageFor(user)
    try{
      const initial=state(),baselineReport=financialReport()
      assert.equal(initial.fg_qty,0);assert.equal(initial.wip,0)
      await nav(page,'Laundry');await sendForm(page);await mutation(page,'Post pengiriman atomic','POST_DELIVERY')
      const sent=query(`select id from erp.laundry_deliveries where po_id='${f.po}' and status='SENT' order by created_at desc limit 1`)
      assert.match(sent,idRx)
      await remainingRoleCases(sent)
      // Keep collecting after an individual permission control fails. Restore
      // the shared source's claim capacity through normal linked corrections.
      const remainingClaims=JSON.parse(query(`select coalesce(jsonb_agg(jsonb_build_object('id',id,'status',status)),'[]') from erp.laundry_claims where delivery_id='${sent}' and status<>'REJECTED'`))
      for(const claim of remainingClaims){
        if(['SETTLED','WRITTEN_OFF'].includes(claim.status))await action(session.access_token,'REVERSE_CLAIM_RESOLUTION',{
          laundry_claim_id:claim.id,change_reason:'Independent source cleanup through linked claim reversal'},claimVersion(claim.id))
        await rejectClaim(claim.id)
      }
      await receiveForm(page,10,'09:00');await mutation(page,'Post penerimaan atomic','POST_RECEIPT')
      assert.deepEqual(await page.locator('.clq-alert.error').allTextContents(),[])
      record('INDEPENDENT_RECEIPT_PROCESS',{ordinary_process_name_accepted:true,real_http:true,observed:state()})
      await nav(page,'QC & Final SKU');await qcForm(page,0,'10:00',10)
      const [qcResponse]=await Promise.all([
        page.waitForResponse(r=>r.url().endsWith('/rpc/erp_save_laundry_qc_action_v1')&&r.request().postDataJSON()?.p_action==='POST_FINAL_SKU'),
        mutation(page,'Post QC + Final SKU atomic','POST_FINAL_SKU'),
      ])
      const rq=qcResponse.request().postDataJSON()
      assert.equal(rq.p_payload.good_qty_pcs,0);assert.equal(rq.p_payload.completion_mode,'ALL_READY')
      assert.equal(state().fg_qty,0);assert.equal(state().qc_bs,10)
      record('INDEPENDENT_QC_ALL_BS',{expected:{good:0,bs:10,mode:'ALL_READY'},observed:state()})
      const bs=JSON.parse(query(`select jsonb_build_object('id',id,'number',bs_number) from erp.bs_cases where po_id='${f.po}' and qty_pcs=10 and status='OPEN' order by created_at desc limit 1`))
      assert.ok(bs?.id)
      await bsNav(page);await selectCase(page,bs.number)
      const classification=page.locator('.cbsr-fold')
      await classification.locator('summary').click()
      const component=classification.locator('fieldset input[type=checkbox]').first()
      await component.check()
      await classification.locator('input[aria-label^="Qty "]').first().fill('10')
      await classification.getByLabel('ALASAN PERUBAHAN · WAJIB',{exact:true}).fill('Original ten pieces already earned original component; no double entitlement')
      await bsMutation(page,'Simpan klasifikasi','CLASSIFY_BS')
      record('UI_NATIVE_CLASSIFY',{completed_before:10})
      let totalGood=0
      for(const route of ['Rework','Rewash']){
        await page.locator('.cbsr-route-tabs').getByRole('button',{name:route,exact:true}).click()
        const form=page.locator('.cbsr-route-form'), number='INDEP-'+route+'-'+randomUUID().slice(0,8)
        await form.getByLabel('NOMOR ORDER · WAJIB',{exact:true}).fill(number)
        // A wrapping label's text includes its option text in Playwright's
        // label lookup. Bind its exact caption, then select its actual control.
        const target=form.locator('label').filter({has:page.getByText(route==='Rework'?'MANDOR REWORK':'VENDOR REWASH',{exact:true})}).locator('select')
        await target.selectOption(route==='Rework'?'a1000000-0000-4000-8000-000000000001':f.vendor)
        await form.getByLabel('QTY DIKIRIM',{exact:true}).fill('5')
        // BS legacy UI uses browser-local input: explicitly confirm this real
        // browser time; this test does not claim its input is labelled WIB.
        await form.getByLabel('WAKTU FISIK',{exact:true}).fill(await page.evaluate(()=>{const n=new Date();return new Date(n.getTime()-n.getTimezoneOffset()*60000).toISOString().slice(0,19).replace(/:00$/,'')}))
        await form.locator('label').filter({has:page.getByText('GUDANG FG BILA GOOD',{exact:true})}).locator('select').selectOption(f.location)
        await form.getByLabel('CATATAN / ALASAN',{exact:true}).fill('Independent five physical pieces to '+route)
        if(route==='Rework')await form.locator('fieldset').first().locator('input[type=checkbox]').first().check()
        const before=snapshot()
        await bsMutation(page,'Buat order '+route.toLowerCase(),'SAVE_REWORK')
        assert.deepEqual(snapshot(),before)
        const order=JSON.parse(query(`select jsonb_build_object('id',id,'qty_sent',qty_sent) from erp.rework_orders where rework_number='${number}'`))
        assert.equal(order.qty_sent,5)
        record(`UI_${route}_CREATE`,{order:order.id,ledger_unchanged:true})
        for(const [good,bad] of [[1,0],[1,1]]){
          const completion=page.locator('.cbsr-completion-form')
          await completion.getByLabel('GOOD KUMULATIF',{exact:true}).fill(String(good))
          await completion.getByLabel('BS KUMULATIF',{exact:true}).fill(String(bad))
          await completion.getByLabel('ALASAN HASIL FISIK',{exact:true}).fill('Independent cumulative physical partial '+good+'+'+bad)
          await bsMutation(page,'Simpan partial','SAVE_REWORK')
          assert.deepEqual(snapshot(),before)
          assert.equal(query(`select status from erp.rework_orders where id='${order.id}'`),'PARTIAL')
          record(`UI_${route}_PARTIAL_${good}_${bad}`,{cumulative_good:good,cumulative_bs:bad,no_fg_journal_or_entitlement:true})
        }
        const completion=page.locator('.cbsr-completion-form')
        await completion.getByLabel('GOOD KUMULATIF',{exact:true}).fill('0')
        await expect(page.getByRole('button',{name:'Post hasil & recovery',exact:true})).toBeDisabled()
        await expect(page.getByRole('button',{name:'Simpan partial',exact:true})).toHaveCount(0)
        record(`UI_${route}_CUMULATIVE_DECREASE_BLOCKED`)
        await completion.getByLabel('GOOD KUMULATIF',{exact:true}).fill('3')
        await completion.getByLabel('BS KUMULATIF',{exact:true}).fill('2')
        await completion.getByLabel('ALASAN HASIL FISIK',{exact:true}).fill('All five returned, three recovered and two remain BS')
        await completion.getByLabel('WAKTU SELESAI',{exact:true}).fill(await page.evaluate(()=>{const n=new Date();return new Date(n.getTime()-n.getTimezoneOffset()*60000).toISOString().slice(0,19).replace(/:00$/,'')}))
        const posted=await bsMutation(page,'Post hasil & recovery','COMPLETE_REWORK')
        totalGood+=3
        const actual=state()
        assert.equal(actual.fg_qty,totalGood)
        assert.equal(actual.unbalanced,0);assert.equal(actual.execution_context,0)
        const replayBefore=snapshot()
        // Different actors have different idempotency domains: observe replay
        // as the same original browser session, never the owner token.
        const originalReplay=await page.evaluate(async({request,api})=>{
          const stored=Object.values(localStorage).map(x=>{try{return JSON.parse(x)}catch{return null}}).find(x=>x?.access_token)
          if(!stored)throw Error('Original browser session unavailable')
          const r=await fetch(api+'/rest/v1/rpc/erp_save_bs_resolution_action_v1',{method:'POST',
            headers:{apikey:request.key,Authorization:'Bearer '+stored.access_token,'Content-Type':'application/json'},body:JSON.stringify(request.body)})
          return {status:r.status,body:await r.json()}
        },{request:{body:posted.request,key:process.env.SUPABASE_ANON_KEY},api:'http://127.0.0.1:54328'})
        assert.equal(originalReplay.status,200);assert.deepEqual(originalReplay.body,posted.response)
        assert.deepEqual(snapshot(),replayBefore)
        const finalReport=financialReport()
        assert.equal(actual.wip+actual.fg,70)
        assert.equal(finalReport.data_confidence.status,'READY')
        assert.equal(Number(query(`select coalesce(sum(amount_payable),0) from erp.rework_component_lines where rework_order_id='${order.id}'`)),0)
        record(`UI_${route}_COMPLETE`,{expected_fg:totalGood,observed:actual,
          money_conserved:actual.wip+actual.fg===70,same_actor_replay_exact:true,
          report_confidence:finalReport.data_confidence,
          report_deltas:{fg:finalReport.financial_position.fg_inventory-baselineReport.financial_position.fg_inventory,
            wip:finalReport.financial_position.wip_inventory-baselineReport.financial_position.wip_inventory},
          original_actor_replay_status:originalReplay.status})
      }
      await page.screenshot({path:resolve(reportDir,'INDEPENDENT_REWORK_UI.png'),fullPage:true})
    }catch(error){
      report.rework_dom={route_form:await page.locator('.cbsr-route-form').allTextContents(),
        completion_form:await page.locator('.cbsr-completion-form').allTextContents(),
        alerts:await page.locator('.cbsr-alert').allTextContents()}
      await page.screenshot({path:resolve(reportDir,'INDEPENDENT_REWORK_INCOMPLETE.png'),fullPage:true}).catch(()=>{})
      throw error
    }finally{await page.context().close()}
  })
  report.status=report.cases.some(x=>x.status!=='PASS')?'INCOMPLETE':'PASS_REVIEWED_SCOPE'
  report.role_coverage={planned_action_mask_pairs:96,observed_action_mask_pairs:report.permission_rows.length,
    unique_pairs:new Set(report.permission_rows.map(r=>r.bits+':'+r.action)).size,
    missing_permission_refusals:report.permission_rows.filter(r=>r.expectation==='DENY_MISSING_PERMISSION').length,
    owner_required_refusals:report.permission_rows.filter(r=>r.expectation==='DENY_OWNER_ADMIN_REQUIRED').length,
    valid_operation_acceptances:report.permission_rows.filter(r=>r.expectation==='ALLOW_VALID_OPERATION').length}
  if(report.role_coverage.unique_pairs!==96)report.status='INCOMPLETE'
  report.known_remaining=['CSV upload/parser absent',
    ...(!report.cases.some(x=>x.id==='UI_CLAIM_MONEY_LIFECYCLE_COMPLETE'&&x.status==='PASS')
      ?['Positive-money claim/compensation UI lifecycle is INCOMPLETE; zero-compensation controls do not close it']:[]),
    'Eight granular nonowner masks and owner controls do not enumerate every role in every module']
  save()
  return report
}
