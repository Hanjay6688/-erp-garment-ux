 const baseCentFindings=[];
 const baseForwardCounter=true;
 const pendingIdentityRefusals=[];
 async function checkPendingNativeIdentity(root,group,conversion){
  const before=await costSnapshot();
  const probes=[
   ['missing Native context','delete from erp.be_execution_context_v1',[]],
   ['wrong Native request','update erp.be_execution_context_v1 set request_id=$1',[x.root90]],
   ['wrong backend','update cp7_sku_conversion.execution_v1 set backend_pid=backend_pid+1',[]],
   ['wrong transaction','update cp7_sku_conversion.execution_v1 set transaction_id=transaction_id+1',[]],
   ['wrong owning group','update cp7_sku_conversion.execution_v1 set group_id=$1',[x.group]],
   ['wrong source lot','update cp7_sku_conversion.execution_v1 set source_lot_id=$1',[x.root30]],
   ['wrong target product','update cp7_sku_conversion.execution_v1 set target_id=$1',[x.source]],
   ['wrong location','update cp7_sku_conversion.execution_v1 set location_id=$1',[x.otherLocation]],
   ['wrong quantity','update cp7_sku_conversion.execution_v1 set qty=2',[]],
   ['wrong physical time',"update cp7_sku_conversion.execution_v1 set physical_at=physical_at+interval '1 second'",[]],
   ['wrong Native source','update erp.product_conversions set from_product_id=$1 where id=$2',[x.outside,conversion]],
   ['wrong Native target','update erp.product_conversions set to_product_id=$1 where id=$2',[x.source,conversion]],
   ['wrong Native quantity','update erp.product_conversions set qty_pcs=2 where id=$1',[conversion]],
   ['wrong Native location','update erp.product_conversions set location_id=$1 where id=$2',[x.otherLocation,conversion]],
   ['wrong allocation quantity','update erp.product_conversion_allocations set qty_pcs=2 where conversion_id=$1',[conversion]]];
  for(const[label,sql,args]of probes){
   await db.exec('savepoint pending_native_identity');await query(sql,args);
   await assert.rejects(()=>query('select cp7_sku_conversion.base_transition_value_v4($1,$2)',[root,x.target]),e=>e.message.includes('CP7_SKU_BASE_MONEY_CUSTODY_NOT_EXACT'));
   await db.exec('rollback to savepoint pending_native_identity');pendingIdentityRefusals.push(label);
  }
  assert.deepEqual(await costSnapshot(),before);
 }
 for(const physicalSource of[x.root50,x.converted]){
  await control('CHAIN: BASE CENT: Native source sync before member '+physicalSource,async()=>{
   const before=await costSnapshot();await db.exec('savepoint native_forward_before_member');
   if(baseForwardCounter&&physicalSource===x.root50){
    await assert.rejects(()=>nextConversion(physicalSource),e=>e.message.includes('CP7_SKU_BASE_MONEY_CUSTODY_NOT_EXACT'));
    await db.exec('rollback to savepoint native_forward_before_member');assert.deepEqual(await costSnapshot(),before);
    baseCentFindings.push({physicalSource,unchanged_product_refuses_legitimate_Native_inflight_source:true,
     failure:'CP7_SKU_BASE_MONEY_CUSTODY_NOT_EXACT',complete_modeled_rollback:true,actual_ERP_cases:0});
   }else{
    const child=await nextConversion(physicalSource);
    assert.deepEqual(await values(x.target),{hpp:35,fg:35,cogs:0,other:0});
    assert.deepEqual(await values(child.product),{hpp:35,fg:35,cogs:0,other:0});
    for(const product of[x.target,child.product])await query('select erp.assert_non_po_product_hpp_target_book_v2620f($1)',[product]);
    assert.equal(Number(await scalar('select count(*)from cp7_sku_conversion.execution_v1')),0);
    assert.equal(Number(await scalar('select count(*)from erp.be_execution_context_v1')),0);
    baseCentFindings.push({physicalSource,exact_Native_sync_before_member:true,expected:[35,35],execution_contexts_released:true,actual_ERP_cases:0});
   }
  });
 }
 assert.equal(pendingIdentityRefusals.length,baseForwardCounter?0:15);
 if(!baseForwardCounter)baseCentFindings.push({pending_identity_refusals:pendingIdentityRefusals,all_rows_restored:true,actual_ERP_cases:0});
 assert.equal(baseCentFindings.length,baseForwardCounter?2:3);assert.deepEqual(await costSnapshot(),costBaseline);
