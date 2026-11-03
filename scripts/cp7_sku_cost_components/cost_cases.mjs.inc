 // All original consumers and credit controls above remain unchanged. These
 // cases execute the same eight retained Native cost bodies as the first
 // failing counterexample, with the explicitly derived bounded source hook
 // only when enabled in the pinned input. Authority/material valuation are models.
 for(const definition of Object.values(input.cost_functions))await db.exec(definition);
 await db.exec(`create table public.model_material_value(value numeric not null);
 insert into public.model_material_value values(2);
 create function erp._cp6_material_adjustment_revaluation_state(uuid)returns jsonb language sql stable as
 $$select jsonb_build_object('current_value',-value)from public.model_material_value$$;`);
 await insert('erp.be_conversion_sources_v1',{conversion_id:x.conversion,source_lot_id:x.root10});
 const costDocument=id(99001),costAdjustment=id(99002),costAccount=id(99003);
 await insert('erp.chart_accounts',{id:costAccount,is_active:true,is_postable:true});
 await insert('erp.bc_documents_v1',{id:costDocument,status:'POSTED'});
 await insert('erp.bc_adjustment_purposes_v1',{document_id:costDocument,adjustment_id:costAdjustment,account_id:costAccount});
 await insert('erp.be_conversion_cost_sources_v1',{document_id:costDocument,conversion_id:x.conversion,kind:'USAGE'});
 const costSnapshot=async()=>{
  const result={},tables=(await query("select schemaname||'.'||tablename name from pg_tables where schemaname in('erp','cp7_sku_conversion','cp7_credit','public')order by 1")).rows;
  for(const{name}of tables)result[name]=await scalar("select coalesce(jsonb_agg(v order by v::text),'[]'::jsonb)from(select to_jsonb(r)v from "+name+' r)s');
  return result;
 };
 await actualBookBaseline();
 const costBaseline=await costSnapshot();
 const costReconcile=async amount=>{
  await query('update public.model_material_value set value=$1',[amount]);
  return query("select erp.be_reconcile_cost_document_v1($1,'2026-01-03')",[costDocument]);
 };
 const costBook=async()=>{
  for(const product of[x.source,x.target,x.outside])await query('select erp.assert_non_po_product_hpp_target_book_v2620f($1)',[product]);
 };
 const costPool=()=>scalar('select cp7_sku_conversion.pool_quote_v2($1,$2)',[x.target,x.location]);
 async function costSale(count=2){
  const lots=count===2?[x.root50,x.converted]:[x.root50];
  await saleSetup(x.target,lots,lots.map(()=>1));
  await query('update erp.sales_headers set source_location_id=$1,customer_id=$2 where id=$3',[x.location,id(900),x.sale]);
  await query('update erp.sales_items set qty_pcs=$1,unit_price_snapshot=185000,discount_amount=0 where id=$2',[count,x.saleItem]);
  for(const lot of lots)await insert('erp.fg_stock_movements',{id:id(++serial),lot_id:lot,product_id:x.target,location_id:x.location,
   quality_grade:'GRADE_A',qty_signed:-1,movement_type:'SALE_RESERVE',customer_id:id(900),source_type:'SALE_ITEM',source_id:x.saleItem,
   physical_at:'2026-01-02T00:00:00Z',system_created_at:'2026-01-02T00:00:00Z'});
  await query('select erp.post_sale($1)',[x.sale]);
 }
 async function actualBookBaseline(){
  await db.exec('delete from erp.journal_lines;delete from erp.journal_entries;');
  for(const b of(await query('select *from public.model_book')).rows){
   const j=await scalar("insert into erp.journal_entries(id,source_type,status)values(gen_random_uuid(),'MODEL_BASELINE','POSTED')returning id");
   for(const[key,field]of[['FG_INVENTORY','fg'],['COGS','cogs'],['OTHER_EXPENSE','other_value']]){
    const amount=Number(b[field]);await insert('erp.journal_lines',{id:await scalar('select gen_random_uuid()'),journal_entry_id:j,
     account_id:await scalar('select cp7_credit.account_by_mapping_v1($1)',[key]),product_id:b.product_id,debit:Math.max(amount,0),credit:Math.max(-amount,0)});
   }
  }
 }
 async function costReturn(sequence,allocation=x.saleA,location=x.location){
  const returned=id(88000+sequence),item=id(89000+sequence);
  await insert('erp.sales_returns',{id:returned,sale_id:x.sale,customer_id:id(900),status:'DRAFT',physical_at:'2026-01-03T00:00:00Z'});
  const lot=await scalar('select lot_id from erp.sale_stock_allocations where id=$1',[allocation]);
  await insert('erp.sales_return_items',{id:item,return_id:returned,sale_stock_allocation_id:allocation,
   product_id:x.target,lot_id:lot,location_id:location,quality_grade:'GRADE_A',qty_pcs:1,refund_amount:185000});
  await query("update erp.fg_lots set cached_qty_pcs=0,produced_at='2026-01-01'where product_id=$1",[x.target]);
  await query('select erp.post_sales_return($1)',[returned]);
  const value=Number(await scalar('select effective_value from cp7_sku_conversion.sales_return_values_v2 where return_id=$1',[returned]));
  return{returned,item,value};
 }
 await control('Original unsold cost counterexample now accepts the exact Native 70 plus 2 book and target',async()=>{
  const before=await costPool();await costReconcile(2);await costBook();
  assert.deepEqual(await values(x.source),{hpp:60,fg:60,cogs:0,other:0});
  assert.deepEqual(await values(x.target),{hpp:72,fg:72,cogs:0,other:0});
  const after=await costPool();assert.equal(Number(after.qty),2);assert.equal(Number(after.value),72);assert.notEqual(after.revision,before.revision);
  assert.equal(Number(await scalar('select count(*)from erp.be_conversion_cost_events_v1 where document_id=$1',[costDocument])),1);
 });
 await control('Late material price correction changes 2 to 3 through exact Native propagation',async()=>{
  await costReconcile(2);await costReconcile(3);await costBook();
  assert.deepEqual(await values(x.target),{hpp:73,fg:73,cogs:0,other:0});
  assert.equal(Number((await costPool()).value),73);
 });
 await control('Sale before cost exists retains zero cost ownership and receives half the late cost',async()=>{
  await costSale(1);const facts=await scalar("select jsonb_agg(to_jsonb(c)order by c.line_no)from cp7_sku_conversion.sale_cost_components_v3 c");
  assert.equal(Number(facts[0].component_units),.5);assert.equal(Number(facts[0].booked_value),0);
  await costReconcile(2);await costBook();assert.deepEqual(await values(x.target),{hpp:72,fg:36,cogs:36,other:0});
  assert.deepEqual(await scalar("select jsonb_agg(to_jsonb(c)order by c.line_no)from cp7_sku_conversion.sale_cost_components_v3 c"),facts);
 });
 await control('Cost before sale is present in exact Native sale snapshot and current COGS',async()=>{
  await costReconcile(2);await costSale(1);await costBook();
  assert.equal(Number(await scalar('select effective_value from cp7_sku_conversion.sale_allocation_values_v2 where sale_id=$1',[x.sale])),36);
  assert.deepEqual(await values(x.target),{hpp:72,fg:36,cogs:36,other:0});
 });
 await control('All stock sold before invoice retains complete current cost and independent return proof',async()=>{
  await costSale();await costReconcile(2);await costBook();
  assert.deepEqual(await values(x.target),{hpp:72,fg:0,cogs:72,other:0});
  const first=await costReturn(1);assert.equal(first.value,36);await costBook();
  assert.deepEqual(await values(x.target),{hpp:72,fg:36,cogs:36,other:0});
 });
 await control('Recost between partial returns preserves original facts and includes the other warehouse',async()=>{
  await costSale();await costReconcile(2);
  const first=await costReturn(1,x.saleA,x.otherLocation);
  const firstFact=await scalar('select to_jsonb(v)from cp7_sku_conversion.sales_return_values_v2 v where return_id=$1',[first.returned]);
  await costReconcile(4);await costBook();
  const second=await costReturn(2,x.saleB);assert.equal(first.value,36);assert.equal(second.value,37);
  assert.deepEqual(await values(x.target),{hpp:74,fg:74,cogs:0,other:0});
  assert.equal(Number((await costPool()).value),37);
  assert.equal(Number((await scalar('select cp7_sku_conversion.pool_quote_v2($1,$2)',[x.target,x.otherLocation])).value),37);
  assert.deepEqual(await scalar('select to_jsonb(v)from cp7_sku_conversion.sales_return_values_v2 v where return_id=$1',[first.returned]),firstFact);
  await costBook();
 });
 await control('Signed Native recovery cost remains negative while the total sale and return values stay correct',async()=>{
  await query("update erp.be_conversion_cost_sources_v1 set kind='RECOVERY'where document_id=$1",[costDocument]);
  await costReconcile(-2);await costSale(1);await costBook();
  assert.deepEqual(await values(x.target),{hpp:68,fg:34,cogs:34,other:0});
  assert.equal(Number(await scalar('select booked_value from cp7_sku_conversion.sale_cost_components_v3')), -1);
  const returned=await costReturn(1);assert.equal(returned.value,34);await costBook();
  assert.deepEqual(await values(x.target),{hpp:68,fg:68,cogs:0,other:0});
 });
 await control('Unchanged Native propagation refuses a negative physical lot even when the average pool could absorb it',async()=>{
  await query("update erp.be_conversion_cost_sources_v1 set kind='RECOVERY'where document_id=$1",[costDocument]);
  const before=await costSnapshot();await db.exec('savepoint unchanged_native_recovery_floor');
  await assert.rejects(()=>costReconcile(-11),e=>e.message.includes('BE_RECOVERY_EXCEEDS_VALUE'));
  await db.exec('rollback to savepoint unchanged_native_recovery_floor');assert.deepEqual(await costSnapshot(),before);
 });
 await control('Mixed PO cost projection keeps the real cost PO and independent credit source totals',async()=>{
  // Explicit PO Native postcondition model: this does not execute the PO
  // accessory command, WIP journal, permission or completeness lifecycle.
  await db.exec(input.po_extra_original[0]);
  await query("update erp.fg_lots set po_id=$1,lot_origin='PRODUCTION'where id=$2",[x.po,x.root10]);
  await query('update erp.fg_lots set po_id=$1 where id=$2',[x.po,x.converted]);
  await insert('erp.be_conversion_cost_events_v1',{id:id(99400),document_id:costDocument,adjustment_id:costAdjustment,
   previous_amount:0,target_amount:2,economic_date:'2026-01-03'});
  await query('update erp.hpp_versions set total_cost=12 where id=$1',[x.hppConverted]);
  assert.equal(Number((await costPool()).value),72);
  await saleSetup();await query('select cp7_sku_conversion.prepare_sale_values_v2($1)',[x.sale]);
  await movement(x.root50,x.target,-1,'SALE_OUT');await movement(x.converted,x.target,-1,'SALE_OUT');
  await query("update erp.sales_headers set status='POSTED'where id=$1",[x.sale]);
  const po=(await query('select *from erp.compute_po_hpp_gl_targets_v2620d($1)',[x.po])).rows[0];
  assert.deepEqual(Object.fromEntries(Object.entries(po).map(([k,v])=>[k,Number(v)])),
   {base_output_qty:2,hpp_total_cost:22,fg_value:15,cogs_value:7,other_out_value:0});
  assert.deepEqual(await values(x.target),{hpp:65,fg:0,cogs:65,other:0});
  const canonical=await scalar("select cp7_credit.initial_hpp_targets_v1(null,$1,'[]'::jsonb,false)->'target'",[x.po]);
  assert.deepEqual(canonical,Object.fromEntries(Object.entries(po).map(([k,v])=>[k,Number(v)])));
  const costRows=await scalar('select jsonb_agg(to_jsonb(c)order by c.sale_stock_allocation_id)from cp7_sku_conversion.sale_cost_components_v3 c');
  assert.equal(costRows.length,2);assert(costRows.every(c=>c.po_id===x.po&&Number(c.booked_value)===1));
 });
 assert.deepEqual(await costSnapshot(),costBaseline,'Every modeled table must be restored after every cost control');
 results.push({label:'Complete modeled rows restored across retained and new cost tables',result:'PASS'});
