 const costChainFindings=[];
 async function nextConversion(physicalSource){
  const product=id(99501),group=id(99502),conversion=id(99503),allocation=id(99504),lot=id(99505),hpp=id(99506);
  await insert('erp.products',{id:product});await insert('public.model_book',{product_id:product,fg:0,cogs:0,other_value:0});
  const sourcePool=await costPool(),targetPool=await scalar('select cp7_sku_conversion.pool_quote_v2($1,$2)',[product,x.location]);
  const preview={qty_pcs:1,source_product_id:x.target,target_product_id:product,location_id:x.location,
   physical_at:'2026-01-03T00:00:00Z',source_value_revision:sourcePool.revision,target_value_revision:targetPool.revision};
  await insert('cp7_sku_conversion.groups_v1',{request_id:group});
  await query('select cp7_sku_conversion.prepare_valuation_v2($1,$2)',[group,preview]);
  const physicalValue=Number(await scalar('select hpp_per_pcs from erp.hpp_versions where lot_id=$1 and is_current',[physicalSource]));
  // Explicit Native conversion postcondition model. Economic preparation and
  // finalization execute the actual prepared SQL; no Native conversion credit.
  await insert('erp.product_conversions',{id:conversion,from_product_id:x.target,to_product_id:product,status:'POSTED',physical_at:'2026-01-03T00:00:00Z'});
  await insert('erp.fg_lots',{id:lot,product_id:product,initial_qty_pcs:1,lot_origin:'CONVERSION',source_lot_id:physicalSource,lot_number:'MODEL-CHAIN'});
  await insert('erp.hpp_versions',{id:hpp,lot_id:lot,version_no:1,cost_state:'ADJUSTED',qty_basis_pcs:1,total_cost:physicalValue,is_current:true});
  await insert('erp.product_conversion_allocations',{id:allocation,conversion_id:conversion,source_lot_id:physicalSource,destination_lot_id:lot,qty_pcs:1,original_hpp_per_pcs:physicalValue,conversion_cost_allocated:0});
  await insert('cp7_sku_conversion.members_v1',{group_id:group,conversion_id:conversion});
  await insert('erp.be_conversion_sources_v1',{conversion_id:conversion,source_lot_id:physicalSource});
  await movement(physicalSource,x.target,-1,'REBRAND_OUT',physicalValue);await movement(lot,product,1,'REBRAND_IN',physicalValue);
  await query("select erp.post_journal('PRODUCT_CONVERSION',$1,'2026-01-03','modeled physical conversion',$2)",[conversion,[
   {mapping_key:'FG_INVENTORY',product_id:product,debit:physicalValue,credit:0},
   {mapping_key:'FG_INVENTORY',product_id:x.target,debit:0,credit:physicalValue}]]);
  await query('select cp7_sku_conversion.finalize_valuation_v2($1)',[group]);
  return{product,group,conversion,allocation,lot,hpp,physicalValue};
 }
 for(const[caseName,physicalSource,expectedBook]of[
  ['Physical lot without accessory cost',x.root50,38],
  ['Physical converted lot carrying all accessory cost',x.converted,36]]){
  await control('CHAIN: '+caseName+' exposes later economic source redistribution',async()=>{
   await costReconcile(2);const child=await nextConversion(physicalSource);
   await costBook();await query('select erp.assert_non_po_product_hpp_target_book_v2620f($1)',[child.product]);
   assert.deepEqual(await values(x.target),{hpp:36,fg:36,cogs:0,other:0});
   assert.deepEqual(await values(child.product),{hpp:36,fg:36,cogs:0,other:0});
   const carried=await scalar('select jsonb_agg(to_jsonb(c)order by c.line_no)from cp7_sku_conversion.cost_contributors_v3 c where group_id=$1',[child.group]);
   assert.equal(Number(carried[0].transfer_units),.5);assert.equal(Number(carried[0].transfer_value),1);
   const before=await costSnapshot();let failure;
   await db.exec('savepoint cost_chain_reprice');
   try{await costReconcile(4);}catch(error){failure={message:error.message,code:error.code,where:error.where};}
   await db.exec('rollback to savepoint cost_chain_reprice');
   assert.deepEqual(await costSnapshot(),before,'Failed later cost correction must restore every modeled table');
   assert(failure?.message.includes('NON_PO_HPP_SOURCE_VALUE_MISMATCH'),JSON.stringify(failure));
   assert(failure.message.includes('target total 37.00, book total '+expectedBook),failure.message);
   costChainFindings.push({caseName,physicalSource,physicalValue:child.physicalValue,
    expectedBefore:{originalProduct:36,descendantProduct:36},expectedAfter:{originalProduct:37,descendantProduct:37},failure,
    complete_modeled_rows_restored:true,product_fix_admitted:false,actual_ERP_cases:0});
  });
 }
 assert.equal(costChainFindings.length,2);
 assert.deepEqual(await costSnapshot(),costBaseline);
