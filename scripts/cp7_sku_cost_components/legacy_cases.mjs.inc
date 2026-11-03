 const baseCentFindings=[];
 const legacyCounter=input.legacy_counter;
 const legacyMoreOnly=input.legacy_more_only;
 const legacyTarget=id(97701),legacyRequest=id(97702),legacyRework=id(97703),legacyMaterial=id(97601);
 async function legacyTargetSetup(){
  await insert('erp.products',{id:legacyTarget,sku:'MODEL-LEGACY-C',is_active:true,effective_from:'2020-01-01T00:00:00Z'});
  await insert('public.model_book',{product_id:legacyTarget,fg:0,cogs:0,other_value:0});
 }
 async function legacyPayload(lot,extra={}){
  return{source_lot_id:lot,target_product_id:legacyTarget,location_id:x.location,qty_pcs:1,
   physical_at:'2026-01-03T00:00:00Z',reason:'Exact Native legacy model',
   expected_version:await scalar('select erp.be_source_revision_v1($1,$2)',[lot,x.location]),...extra};
 }
 const legacyAction=(action,payload,request)=>scalar('select cp7_sku_conversion.action_v1($1,$2,$3)',[action,payload,request]);
 async function legacyBooks(sourceAmount,targetAmount){
  assert.deepEqual(await values(x.target),{hpp:sourceAmount,fg:sourceAmount,cogs:0,other:0});
  assert.deepEqual(await values(legacyTarget),{hpp:targetAmount,fg:targetAmount,cogs:0,other:0});
  for(const product of[x.target,legacyTarget])await query('select erp.assert_non_po_product_hpp_target_book_v2620f($1)',[product]);
 }
 async function legacyContextsClear(){
  for(const table of['erp.be_execution_context_v1','cp7_sku_conversion.execution_v1'])assert.equal(Number(await scalar('select count(*)from '+table)),0);
 }
 async function legacyMoneyRows(){
  return scalar("select jsonb_build_object('base',(select jsonb_agg(to_jsonb(e)order by id)from cp7_sku_conversion.base_money_events_v4 e),"+
   "'cost',(select jsonb_agg(to_jsonb(e)order by id)from cp7_sku_conversion.cost_money_events_v3 e),"+
   "'posts',(select jsonb_agg(to_jsonb(e)order by group_id,phase)from cp7_sku_conversion.valuation_postings_v2 e))");
 }
 async function legacyRefusal(label,operation,pattern){
  const before=await costSnapshot();await db.exec('savepoint legacy_refusal');
  await assert.rejects(operation,e=>pattern.test(e.message),label);
  await db.exec('rollback to savepoint legacy_refusal');assert.deepEqual(await costSnapshot(),before,label+' restores all rows');
 }
 if(!legacyMoreOnly)for(const lot of[x.root50,x.converted]){
  await control('CHAIN: BASE CENT: LEGACY exact Native physical and facade bodies '+lot,async()=>{
   await legacyTargetSetup();const payload=await legacyPayload(lot,{expected_returns:[{material_id:legacyMaterial,qty:'1',holder:'MODEL'}]});
   const rawBefore=await scalar('select erp.model_legacy_original_physical_revision($1,$2)',[lot,x.location]);
   const before=await costSnapshot();await db.exec('savepoint legacy_first_post');
   if(legacyCounter){
    let failure,result,observed;
    try{result=await legacyAction('POST',payload,legacyRequest);observed=[await values(x.target),await values(legacyTarget)];}
    catch(error){failure={message:error.message,code:error.code,where:error.where};}
    if(failure)assert.match(failure.message,/CP7_SKU_BASE_MONEY_CUSTODY_NOT_EXACT|NON_PO_HPP_SOURCE_VALUE_MISMATCH/,
     'A model infrastructure or fixture failure cannot be counted as a legacy financial counterexample');
    if(!failure)assert.deepEqual(observed.map(v=>v.fg),[60,10],'Retained original legacy physical price loses the required35/35 economic transfer');
    await db.exec('rollback to savepoint legacy_first_post');assert.deepEqual(await costSnapshot(),before);
    baseCentFindings.push({physicalSource:lot,first_unchanged_legacy_counter:{failure,result,observed},full_rows_restored:true,
     actual_ERP_cases:0});return;
   }
   const preview=await scalar('select erp.be_conversion_preview_v1($1)',[payload]);
   assert.equal(Number(preview.cost.source_value),35);assert.equal(Number(preview.cost.native_physical_value),lot===x.root50?50:10);
   const result=await legacyAction('POST',payload,legacyRequest);await legacyBooks(35,35);await legacyContextsClear();
   assert.equal(result.cost.source_value,preview.cost.source_value);assert.equal(result.pending_returns,1);
   assert.equal(await scalar('select source_lot_id from erp.product_conversion_allocations where conversion_id=$1',[legacyRequest]),lot);
   assert.equal(await scalar('select source_revision from erp.be_conversion_sources_v1 where conversion_id=$1',[legacyRequest]),rawBefore);
   const proof=await scalar('select to_jsonb(g)from cp7_sku_conversion.legacy_groups_v4 g where group_id=$1',[legacyRequest]);
   assert.equal(proof.original_preview.source_revision,payload.expected_version);assert.equal(proof.origin_kind,'FG');assert.equal(proof.rework_id,null);
   const afterPost=await costSnapshot();assert.deepEqual(await legacyAction('POST',payload,legacyRequest),result);assert.deepEqual(await costSnapshot(),afterPost);
   await legacyRefusal('same request changed payload',()=>legacyAction('POST',{...payload,reason:'changed'},legacyRequest),/MODEL_IDEMPOTENCY_PAYLOAD_CHANGED/);
   await costReconcile(4);await legacyBooks(37,37);
   const reversePayload={conversion_id:legacyRequest,reason:'Current-value Native legacy inverse'};
   const reversed=await legacyAction('REVERSE',reversePayload,id(97704));await legacyBooks(74,0);await legacyContextsClear();
   assert.equal(reversed.status,'REVERSED');
   assert.equal(await scalar('select status from erp.bc_outstanding_returns_v1 where id=(select outstanding_id from erp.be_conversion_returns_v1 where conversion_id=$1)',[legacyRequest]),'CANCELLED');
   const afterReverse=await costSnapshot();assert.deepEqual(await legacyAction('REVERSE',reversePayload,id(97704)),reversed);assert.deepEqual(await costSnapshot(),afterReverse);
   const moneyBeforeRepeat=await legacyMoneyRows();await legacyAction('REVERSE',reversePayload,id(97705));
   assert.deepEqual(await legacyMoneyRows(),moneyBeforeRepeat);await legacyBooks(74,0);await legacyContextsClear();
   assert.deepEqual(await scalar('select to_jsonb(g)from cp7_sku_conversion.legacy_groups_v4 g where group_id=$1',[legacyRequest]),proof);
   assert.equal(Number(await scalar('select count(*)from public.model_legacy_idempotency where namespace<>$1',['save_product_conversion_action_v1'])),0);
   baseCentFindings.push({physicalSource:lot,exact_Native_physical_post_and_reverse:true,expected_values:[[35,35],[37,37],[74,0]],
    pending_returns_and_original_facade_namespace_preserved:true,replay_without_new_money:true,actual_ERP_cases:0});
  });
 }
 if(!legacyCounter&&!legacyMoreOnly){
  for(const mode of['REWORK','REDYE'])await control('CHAIN: BASE CENT: LEGACY exact automatic '+mode+' bodies',async()=>{
   await legacyTargetSetup();
   await insert('erp.rework_orders',{id:legacyRework,cost_posted:true,status:'COMPLETED',qty_good_returned:1,
    good_fg_lot_id:x.root50,return_fg_location_id:x.location,completed_at:'2026-01-03T00:00:00Z'});
   await insert('erp.be_rework_targets_v1',{rework_id:legacyRework,target_product_id:legacyTarget,
    mode:mode==='REDYE'?'REDYE_SKU':'REWORK',reason:'Exact automatic '+mode});
   await query('select erp.be_complete_rework_target_v1($1)',[legacyRework]);await legacyBooks(35,35);await legacyContextsClear();
   const proof=await scalar('select to_jsonb(g)from cp7_sku_conversion.legacy_groups_v4 g where rework_id=$1',[legacyRework]);
   assert.equal(proof.origin_kind,mode);assert.notEqual(proof.native_request_id,proof.group_id);
   const beforeRepeat=await costSnapshot();await query('select erp.be_complete_rework_target_v1($1)',[legacyRework]);assert.deepEqual(await costSnapshot(),beforeRepeat);
   await query('select erp.be_reverse_rework_target_v1($1,$2)',[legacyRework,'Automatic legacy inverse']);await legacyBooks(70,0);await legacyContextsClear();
   const reversed=await costSnapshot();await query('select erp.be_reverse_rework_target_v1($1,$2)',[legacyRework,'Automatic legacy inverse']);assert.deepEqual(await costSnapshot(),reversed);
   baseCentFindings.push({origin:mode,separate_Native_context_request_preserved:true,expected_values:[[35,35],[70,0]],full_replay_exact:true,actual_ERP_cases:0});
  });
  await control('CHAIN: BASE CENT: LEGACY hidden preview and stale whole-source value',async()=>{
   await legacyTargetSetup();await query('update public.model_legacy_visibility set show_money=false');
   const payload=await legacyPayload(x.converted),preview=await scalar('select erp.be_conversion_preview_v1($1)',[payload]);
   assert.deepEqual(preview.cost,{});assert.equal(typeof preview.source_value_revision,'string');
   const raw=await scalar('select erp.model_legacy_original_physical_revision($1,$2)',[x.converted,x.location]);
   await query("select erp.post_opening_hpp_correction($1,50.01,'Other physical lot changes the economic pool','2026-01-03')",[x.root50]);
   assert.equal(await scalar('select erp.model_legacy_original_physical_revision($1,$2)',[x.converted,x.location]),raw);
   assert.notEqual(await scalar('select erp.be_source_revision_v1($1,$2)',[x.converted,x.location]),payload.expected_version);
   await legacyRefusal('other physical lot recost invalidates prior legacy preview',()=>legacyAction('POST',payload,legacyRequest),/STALE_VERSION/);
   baseCentFindings.push({hidden_money:true,other_lot_value_change_invalidates_legacy_revision:true,actual_ERP_cases:0});
  });
  await control('CHAIN: BASE CENT: LEGACY original guards and post-physical failure rollback',async()=>{
   await legacyTargetSetup();const valid=await legacyPayload(x.root50),refusals=[];
   for(const[label,changes,pattern]of[
    ['invalid PCS',{qty_pcs:'1'},/BD_QTY_INVALID/],['before source',{physical_at:'2025-12-31T00:00:00Z'},/BE_BEFORE_SOURCE/],
    ['missing timezone',{physical_at:'2026-01-03'},/BD_TIME_INVALID/],['stale',{expected_version:'stale'},/STALE_VERSION/],
    ['source capacity',{qty_pcs:2},/BE_SOURCE_CAPACITY/],['extra field',{invented:true},/unknown|tidak|field|key/i],
    ['invalid expected return after exact physical posting',{expected_returns:[{material_id:legacyMaterial,qty:'0',holder:'MODEL'}]},/BC_QTY_INVALID/]
   ]){await legacyRefusal(label,()=>legacyAction('POST',{...valid,...changes},legacyRequest),pattern);refusals.push(label);}
   await query("update erp.hpp_versions set cost_state='ESTIMATED'where lot_id=$1 and is_current",[x.root50]);
   const unknown=await legacyPayload(x.converted);
   await legacyRefusal('unknown other root refuses posting after revision can be read',()=>legacyAction('POST',unknown,legacyRequest),/CP7_SKU_POOL_HPP_UNKNOWN/);
   baseCentFindings.push({original_refusals:refusals,unknown_other_root_refused:true,post_physical_failure_restores_all_rows:true,actual_ERP_cases:0});
  });
  await control('CHAIN: BASE CENT: LEGACY private proof immutable and exact inverse membership',async()=>{
   await legacyTargetSetup();const payload=await legacyPayload(x.root50);await legacyAction('POST',payload,legacyRequest);
   for(const sql of['update cp7_sku_conversion.legacy_groups_v4 set origin_kind=origin_kind','delete from cp7_sku_conversion.legacy_groups_v4'])
    await legacyRefusal('immutable admitted legacy source',()=>query(sql),/MODEL_IMMUTABLE/);
   for(const role of['anon','authenticated','service_role']){
    assert.equal(await scalar("select has_table_privilege($1,'cp7_sku_conversion.legacy_groups_v4','SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",[role]),false);
    assert.equal(await scalar("select has_function_privilege($1,'cp7_sku_conversion.legacy_source_revision_v4(uuid,uuid,text)','EXECUTE')",[role]),false);
   }
   await query('update erp.be_conversion_sources_v1 set source_lot_id=$1 where conversion_id=$2',[x.converted,legacyRequest]);
   await legacyRefusal('wrong retained legacy Native source',()=>legacyAction('REVERSE',{conversion_id:legacyRequest,reason:'Refuse wrong source'},id(97704)),/CP7_SKU_LEGACY_MEMBER_NOT_EXACT/);
   baseCentFindings.push({immutable_private_proof:true,all_model_app_roles_denied:true,wrong_inverse_source_refused:true,actual_ERP_cases:0});
  });
 }
 // LEGACY_FOLLOWUP_CONTROLS
 assert.equal(baseCentFindings.length,legacyCounter?2:legacyMoreOnly?4:11);assert.deepEqual(await costSnapshot(),costBaseline);
