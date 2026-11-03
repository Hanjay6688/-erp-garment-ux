 if(!legacyCounter){
  await control('CHAIN: BASE CENT: LEGACY FOLLOWUP exact two-child SKU action after legacy revision binding',async()=>{
   await legacyTargetSetup();let payload={source_product_id:x.target,target_product_id:legacyTarget,location_id:x.location,
    qty_pcs:2,physical_at:'2026-01-03T00:00:00Z',reason:'Two exact Native children under one SKU quote'};
   const preview=await scalar('select cp7_sku_conversion.preview_v1($1)',[payload]);
   assert.equal(preview.allocations.length,2);assert.equal(Number(preview.cost.source_value),70);
   payload={...payload,expected_version:preview.source_revision};
   const posted=await legacyAction('POST',payload,legacyRequest);assert.equal(posted.conversion_ids.length,2);
   await legacyBooks(0,70);await legacyContextsClear();
   assert.equal(Number(await scalar('select count(*)from cp7_sku_conversion.legacy_groups_v4')),0);
   const members=await scalar('select jsonb_agg(to_jsonb(m)order by line_no)from cp7_sku_conversion.members_v1 m where group_id=$1',[legacyRequest]);
   assert.equal(members.length,2);
   const beforeRepeat=await costSnapshot();assert.deepEqual(await legacyAction('POST',payload,legacyRequest),posted);assert.deepEqual(await costSnapshot(),beforeRepeat);
   await costReconcile(4);await legacyBooks(0,74);
   await legacyAction('REVERSE',{conversion_id:legacyRequest,reason:'Whole two-child Native group inverse'},id(97704));
   await legacyBooks(74,0);await legacyContextsClear();
   assert.deepEqual(await scalar('select jsonb_agg(to_jsonb(m)order by line_no)from cp7_sku_conversion.members_v1 m where group_id=$1',[legacyRequest]),members);
   baseCentFindings.push({exact_two_child_SKU_action:true,legacy_bridge_not_nested:true,expected_values:[[0,70],[0,74],[74,0]],
    original_members_immutable:true,actual_ERP_cases:0});
  });
  await control('CHAIN: BASE CENT: LEGACY FOLLOWUP automatic rework preserves outer Native context',async()=>{
   await legacyTargetSetup();
   await insert('erp.rework_orders',{id:legacyRework,cost_posted:true,status:'COMPLETED',qty_good_returned:1,
    good_fg_lot_id:x.root50,return_fg_location_id:x.location,completed_at:'2026-01-03T00:00:00Z'});
   await insert('erp.be_rework_targets_v1',{rework_id:legacyRework,target_product_id:legacyTarget,mode:'REDYE_SKU',reason:'Existing outer request'});
   await query('insert into erp.be_execution_context_v1 values(pg_backend_pid(),txid_current(),$1)',[legacyRequest]);
   const outer=await scalar('select to_jsonb(b)from erp.be_execution_context_v1 b');
   await query('select erp.be_complete_rework_target_v1($1)',[legacyRework]);await legacyBooks(35,35);
   assert.deepEqual(await scalar('select to_jsonb(b)from erp.be_execution_context_v1 b'),outer);
   assert.equal(Number(await scalar('select count(*)from cp7_sku_conversion.execution_v1')),0);
   await query('select erp.be_reverse_rework_target_v1($1,$2)',[legacyRework,'Keep outer context on inverse']);await legacyBooks(70,0);
   assert.deepEqual(await scalar('select to_jsonb(b)from erp.be_execution_context_v1 b'),outer);
   assert.equal(Number(await scalar('select count(*)from cp7_sku_conversion.execution_v1')),0);
   await query('delete from erp.be_execution_context_v1');await legacyContextsClear();
   baseCentFindings.push({outer_Native_context_unchanged_on_post_and_reverse:true,expected_values:[[35,35],[70,0]],actual_ERP_cases:0});
  });
  await control('CHAIN: BASE CENT: LEGACY FOLLOWUP source revision never conceals corrupt base custody',async()=>{
   await query('update erp.fg_lots set initial_qty_pcs=initial_qty_pcs+1 where id=$1',[x.root50]);
   await legacyRefusal('non-unknown source corruption propagates',()=>scalar('select erp.be_source_revision_v1($1,$2)',[x.converted,x.location]),/CP7_SKU_BASE_MONEY_CUSTODY_NOT_EXACT/);
   baseCentFindings.push({source_corruption_is_not_an_unknown_price_fallback:true,actual_ERP_cases:0});
  });
  await control('CHAIN: BASE CENT: LEGACY FOLLOWUP unrelated private frame refuses before new group',async()=>{
   await legacyTargetSetup();
   await query("insert into cp7_sku_conversion.execution_v1(backend_pid,transaction_id,group_id,mode,source_lot_id,target_id,location_id,qty,physical_at)values(pg_backend_pid(),txid_current(),$1,'POST',$2,$3,$4,1,'2026-01-03T00:00:00Z')",[x.group,x.root10,x.source,x.location]);
   const payload=await legacyPayload(x.root50);
   await legacyRefusal('foreign private frame cannot own a new legacy group',()=>legacyAction('POST',payload,legacyRequest),/CP7_SKU_LEGACY_EXECUTION_CONFLICT/);
   baseCentFindings.push({foreign_private_frame_refused_without_new_facts:true,actual_ERP_cases:0});
  });
 }
