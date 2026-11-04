 // Begin at an explicitly modeled completed Native PO/rework GOOD boundary.
 // The exact automatic BE helpers and physical conversion/inverse run below.
 const automaticFindings=[];
 let automaticObservations=[];
 const ax=Object.fromEntries(['source','target','good','other','targetLot','po','otherPo','bs','rework',
  'goodHpp','otherHpp','targetHpp','model','size','wipAccount','doc','adjustment'].map((n,i)=>[n,id(100001+i)]));
 await insert('erp.chart_accounts',{id:ax.wipAccount,is_active:true,is_postable:true});
 await insert('erp.accounting_account_mappings',{mapping_key:'WIP',account_id:ax.wipAccount});

 async function autoFixture(mode='REWORK',uncertainty='PO_PENDING',zeroGood=false){
  for(const product of[ax.source,ax.target])await insert('erp.products',{id:product,sku:'AUTO-'+product.slice(-4),
   is_active:true,effective_from:'2020-01-01T00:00:00Z',model_id:ax.model,size_id:ax.size});
  await insert('erp.production_orders',{id:ax.po,status:'IN_PROGRESS'});
  await insert('erp.production_orders',{id:ax.otherPo,status:'IN_PROGRESS'});
  await insert('public.model_auto_pending',{po_id:ax.po,pending:uncertainty==='PO_PENDING'?1:0,laundry_unknown:uncertainty==='LAUNDRY_UNKNOWN'});
  await insert('public.model_auto_pending',{po_id:ax.otherPo,pending:0,laundry_unknown:false});
  await insert('erp.bs_cases',{id:ax.bs,po_id:ax.po,product_id:ax.source,qty_pcs:2,status:'PARTIAL',physical_at:'2026-01-02T00:00:00Z'});
  await insert('erp.rework_orders',{id:ax.rework,bs_case_id:ax.bs,qty_sent:2,qty_good_returned:zeroGood?0:1,
   qty_bs_returned:zeroGood?2:1,cost_posted:true,status:'COMPLETED',good_fg_lot_id:zeroGood?null:ax.good,
   return_fg_location_id:x.location,physical_sent_at:'2026-01-02T00:00:00Z',completed_at:'2026-01-03T00:00:00Z',row_version:1});
  await insert('erp.be_rework_targets_v1',{rework_id:ax.rework,target_product_id:ax.target,
   mode:mode==='REDYE'?'REDYE_SKU':'REWORK_SKU',reason:'Explicit modeled completed PO GOOD automatic conversion'});
  for(const[lot,product,po,cost,hpp,origin]of[
   ...(zeroGood?[]:[[ax.good,ax.source,ax.po,50,ax.goodHpp,'PRODUCTION']]),
   [ax.other,ax.source,ax.otherPo,20,ax.otherHpp,'PRODUCTION'],
   [ax.targetLot,ax.target,null,90,ax.targetHpp,'OPENING']]){
   await insert('erp.fg_lots',{id:lot,product_id:product,po_id:po,initial_qty_pcs:1,lot_origin:origin,
    lot_number:'AUTO-'+lot.slice(-4),produced_at:'2026-01-03T00:00:00Z',cached_qty_pcs:1,is_open:true});
   await insert('erp.hpp_versions',{id:hpp,lot_id:lot,version_no:1,cost_state:lot===ax.good&&uncertainty==='ESTIMATED'?'ESTIMATED':'ADJUSTED',
    qty_basis_pcs:1,total_cost:cost,is_current:true});
   await insert('erp.fg_stock_movements',{id:await scalar('select gen_random_uuid()'),lot_id:lot,product_id:product,
    location_id:x.location,quality_grade:'GRADE_A',qty_signed:1,unit_hpp_snapshot:cost,
    movement_type:lot===ax.good?'REWORK_IN':po?'PRODUCTION':'OPENING',source_type:lot===ax.good?'REWORK_ORDER':null,
    source_id:lot===ax.good?ax.rework:null,physical_at:'2026-01-03T00:00:00Z',system_created_at:'2026-01-03T00:00:00Z'});
  }
  await insert('public.model_book',{product_id:ax.source,fg:0,cogs:0,other_value:0});
  await insert('public.model_book',{product_id:ax.target,fg:90,cogs:0,other_value:0});
  await query(`insert into erp.fg_inventory_balances(product_id,location_id,quality_grade,cached_qty_pcs)
   select product_id,location_id,quality_grade,sum(qty_signed)::integer from erp.fg_stock_movements
   where product_id in($1,$2)group by product_id,location_id,quality_grade
   on conflict(product_id,location_id,quality_grade)do update set cached_qty_pcs=excluded.cached_qty_pcs`,[ax.source,ax.target]);
  await actualBookBaseline();
  for(const[po,amount]of[[ax.po,zeroGood?0:50],[ax.otherPo,20]]){
   if(amount){const j=await scalar('select gen_random_uuid()');
    await insert('erp.journal_entries',{id:j,source_type:'MODEL_PO_SOURCE_BASELINE',status:'POSTED',economic_date:'2026-01-03',transaction_date:'2026-01-03'});
    for(const[key,debit,credit]of[['FG_INVENTORY',amount,0],['WIP',0,amount]])await insert('erp.journal_lines',{
     id:await scalar('select gen_random_uuid()'),journal_entry_id:j,po_id:po,
     account_id:await scalar('select erp.account_id($1)',[key]),debit,credit});
   }
   await query('select erp.refresh_po_hpp_gl_baseline($1)',[po]);
   if(amount)await query('select erp.assert_po_hpp_target_book_v2620e($1)',[po]);
  }
 }
 async function autoNoFrames(){
  for(const table of['erp.be_execution_context_v1','cp7_sku_conversion.execution_v1','cp7_sku_conversion.automatic_context_v5'])
   assert.equal(Number(await scalar('select count(*)from '+table)),0,table+' must release its owning context');
 }
 async function autoCon(){return(await query("select c.*from erp.product_conversions c join erp.be_conversion_sources_v1 s on s.conversion_id=c.id where s.rework_id=$1 order by c.id",[ax.rework])).rows;}
 async function autoHoldings(product){
  const base=(await query("select root_lot_id,component_units::text units,unit_value::text unit from cp7_sku_conversion.pool_components_v2($1,$2,'GRADE_A')",[product,x.location])).rows;
  const costs=(await query(`select e.root_lot_id,sum(e.units_delta)::text units,
   erp.be_allocation_extra_v1(a.id)::text extra,a.qty_pcs from cp7_sku_conversion.cost_events_v3 e
   join erp.product_conversion_allocations a on a.destination_lot_id=e.root_lot_id
   where e.product_id=$1 and e.location_id=$2 group by e.root_lot_id,a.id,a.qty_pcs`,[product,x.location])).rows;
  return {base:base.reduce((n,r)=>n+Number(r.units)*Number(r.unit),0),
   cost:costs.reduce((n,r)=>n+Number(r.units)*Number(r.extra)/Number(r.qty_pcs),0)};
 }
 async function autoAssertValues(source,target){
  const a=await autoHoldings(ax.source),b=await autoHoldings(ax.target);
  assert.ok(Math.abs(a.base+a.cost-source)<0.000001,JSON.stringify(a));
  assert.ok(Math.abs(b.base+b.cost-target)<0.000001,JSON.stringify(b));
  const poBooks=[];
  for(const po of[ax.po,ax.otherPo]){
   await query('select erp.assert_po_hpp_target_book_v2620e($1)',[po]);
   poBooks.push({po,target:await scalar('select to_jsonb(t)from erp.compute_po_hpp_gl_targets_v2620d($1)t',[po]),
    book:await scalar('select to_jsonb(t)from erp.compute_po_hpp_gl_book_v2620e($1)t',[po])});
  }
  automaticObservations.push({source:a,target:b,poBooks});
 }
 async function autoPost(){
  await query('select erp.be_complete_rework_target_v1($1)',[ax.rework]);
  const rows=await autoCon();assert.equal(rows.length,1);assert.equal(rows[0].status,'POSTED');
  const conversion=rows[0].id;
  const quoted=(await query('select *from cp7_sku_conversion.valuation_quotes_v2 where group_id=$1',[conversion])).rows[0];
  assert.equal(Number(quoted.source_before_value),70);assert.equal(Number(quoted.source_before_qty),2);
  assert.equal(Number(quoted.transfer_value),35);
  const physical=await scalar('select original_hpp_per_pcs::text from erp.product_conversion_allocations where conversion_id=$1',[conversion]);
  assert.equal(Number(physical),50,'Native selects the real GOOD lot; economic moving average remains 35');
  const admission=await scalar("select conversion_proof from cp7_sku_conversion.automatic_admissions_v5 where conversion_id=$1 and phase='POST'",[conversion]);
  assert.equal(admission.legacy.original_preview.valuation_provisional,true);
  automaticObservations.push({conversion,quote:quoted,Native_physical_unit_HPP:physical,admission});
  await autoAssertValues(35,125);await autoNoFrames();return conversion;
 }
 async function autoRefusal(operation,pattern){return legacyRefusal('Automatic refusal preserves every modeled row',operation,pattern);}
 await control('Native book and modeled balance both exclude PO-tagged FG product lines',async()=>{
  await autoFixture();
  await query("select erp.post_journal('MODEL_PO_TAGGED_NATIVE_LINES',$1,'2026-01-03','PO-tag model preflight',$2)",[
   id(100199),[{mapping_key:'FG_INVENTORY',product_id:ax.target,po_id:ax.po,debit:50,credit:0},
    {mapping_key:'FG_INVENTORY',product_id:ax.source,po_id:ax.po,debit:0,credit:50}]]);
  assert.equal(Number(await scalar('select fg_value::text from erp.compute_non_po_product_hpp_book_v2620f($1)',[ax.target])),90);
  assert.equal(Number(await scalar('select fg::text from public.model_book where product_id=$1',[ax.target])),90);
 });
 await control('Genuine modeled completed PO GOOD first reproduces the old automatic pending refusal',async()=>{
  await autoFixture();await autoRefusal(()=>query('select erp.be_complete_rework_target_v1($1)',[ax.rework]),/^CP7_SKU_POOL_HPP_UNKNOWN:/);
 });
 await db.exec('set check_function_bodies=on');
 await db.exec(input.automatic_product.ddl);
 for(const definition of Object.values(input.automatic_product.definitions))await db.exec(definition);
 await db.exec('set check_function_bodies=off');
 const automaticBaseline=await costSnapshot();
 async function autoControl(label,operation){
  automaticObservations=[];
  await control('AUTOMATIC '+label,async()=>{await operation();automaticFindings.push({case:label,status:'PASS',observations:automaticObservations});});
  assert.deepEqual(await costSnapshot(),automaticBaseline);
 }
 for(const mode of['REWORK','REDYE'])for(const uncertainty of['PO_PENDING','ESTIMATED','LAUNDRY_UNKNOWN'])
  await autoControl(mode+' '+uncertainty+' forward, replay and exact inverse',async()=>{
   await autoFixture(mode,uncertainty);const conversion=await autoPost();
   const before=await costSnapshot();await query('select erp.be_complete_rework_target_v1($1)',[ax.rework]);
   assert.deepEqual(await costSnapshot(),before,'Completed replay cannot create a second conversion');
   await autoRefusal(()=>scalar("select cp7_sku_conversion.pool_quote_v2($1,$2,'GRADE_A')",[ax.source,x.location]),/^CP7_SKU_POOL_HPP_UNKNOWN:/);
   await query('select erp.be_reverse_rework_target_v1($1,$2)',[ax.rework,'Exact Native automatic inverse']);
   assert.equal(await scalar('select status from erp.product_conversions where id=$1',[conversion]),'REVERSED');
   await autoAssertValues(70,90);await autoNoFrames();
   const rows=await scalar('select count(*)from cp7_sku_conversion.automatic_admissions_v5 where conversion_id=$1',[conversion]);assert.equal(Number(rows),2);
  });
 await autoControl('PO source price revision keeps immutable history and current inverse',async()=>{
  await autoFixture();const conversion=await autoPost();
  const originalAdmission=await scalar("select to_jsonb(a)from cp7_sku_conversion.automatic_admissions_v5 a where conversion_id=$1 and phase='POST'",[conversion]);
  await query('update erp.hpp_versions set is_current=false where id=$1',[ax.goodHpp]);
  await insert('erp.hpp_versions',{id:id(100100),lot_id:ax.good,version_no:2,cost_state:'ESTIMATED',qty_basis_pcs:1,total_cost:60,is_current:true,supersedes_id:ax.goodHpp});
  await query('select erp.propagate_conversion_hpp_for_po($1)',[ax.po]);
  await query("select erp.sync_po_hpp_to_gl($1,'2026-01-03')",[ax.po]);
  assert.equal(Number(await scalar('select total_cost::text from erp.hpp_versions where id=$1',[ax.goodHpp])),50);
  await autoAssertValues(40,130);
  await query('select erp.be_reverse_rework_target_v1($1,$2)',[ax.rework,'Current source price inverse']);
  await autoAssertValues(80,90);await autoNoFrames();
  assert.deepEqual(await scalar("select to_jsonb(a)from cp7_sku_conversion.automatic_admissions_v5 a where conversion_id=$1 and phase='POST'",[conversion]),originalAdmission);
 });
 await autoControl('Native late cost event, active-source inverse refusal, zero recost and inverse',async()=>{
  await autoFixture('REDYE');const conversion=await autoPost();
  await insert('erp.bc_documents_v1',{id:ax.doc,status:'POSTED'});
  await insert('erp.bc_adjustment_purposes_v1',{document_id:ax.doc,adjustment_id:ax.adjustment,account_id:costAccount});
  await insert('erp.be_conversion_cost_sources_v1',{document_id:ax.doc,conversion_id:conversion,kind:'USAGE'});
  await query('update public.model_material_value set value=2.01');
  await query("select erp.be_reconcile_cost_document_v1($1,'2026-01-03')",[ax.doc]);
  await autoAssertValues(35,127.01);await autoNoFrames();
  await autoRefusal(()=>query('select erp.be_reverse_rework_target_v1($1,$2)',[ax.rework,'Active source must refuse']),/BE_REVERSE_DEPENDANTS/);
  // Explicitly modeled legal document-cancellation postcondition, followed
  // by the exact Native source reconciliation; not the full BC command.
  await query("update erp.bc_documents_v1 set status='REVERSED'where id=$1",[ax.doc]);
  await query("select erp.be_reconcile_cost_document_v1($1,'2026-01-03')",[ax.doc]);
  await autoAssertValues(35,125);
  assert.equal(Number(await scalar('select count(*)from erp.be_conversion_cost_events_v1 where document_id=$1',[ax.doc])),2);
  await query('select erp.be_reverse_rework_target_v1($1,$2)',[ax.rework,'Source cancellation then inverse']);
  await autoAssertValues(70,90);await autoNoFrames();
 });
 await autoControl('Unrelated flags cannot authorize a manual pending quote',async()=>{
  await autoFixture();await query("select set_config('cp7.sku.automatic','true',true)");
  await autoRefusal(()=>scalar("select cp7_sku_conversion.pool_quote_v2($1,$2,'GRADE_A')",[ax.source,x.location]),/^CP7_SKU_POOL_HPP_UNKNOWN:/);
  await autoNoFrames();
 });
 await autoControl('Exact automatic scope cannot authorize a different child or product',async()=>{
  await autoFixture();const child=id(100300),outer=id(100301);
  await insert('erp.be_execution_context_v1',{backend_pid:await scalar('select pg_backend_pid()'),transaction_id:await scalar('select txid_current()'),request_id:outer,syncing_nonpo:false});
  await query("select cp7_sku_conversion.automatic_enter_v5($1,'POST',$2)",[ax.rework,child]);
  assert.equal(await scalar('select cp7_sku_conversion.automatic_valid_v5()'),true);
  const quote=await scalar("select cp7_sku_conversion.pool_quote_v2($1,$2,'GRADE_A')",[ax.source,x.location]);
  assert.equal(quote.state,'PROVISIONAL');assert.equal(Number(quote.average),35);
  assert.equal(await scalar("select cp7_sku_conversion.automatic_scope_v5($1,$2,'GRADE_A')",[x.target,x.location]),false);
  await autoRefusal(()=>query('select cp7_sku_conversion.automatic_assert_native_v5($1,null,null,null)',[id(100302)]),/AUTOMATIC_NATIVE_CHILD_NOT_EXACT/);
  const targetRow=(await query('select *from erp.be_rework_targets_v1 where rework_id=$1',[ax.rework])).rows[0];
  const payload={source_lot_id:ax.good,target_product_id:ax.target,location_id:x.location,qty_pcs:1,
   physical_at:'2026-01-03T00:00:00Z',reason:targetRow.reason,
   expected_version:await scalar('select erp.be_source_revision_v1($1,$2)',[ax.good,x.location])};
  await autoRefusal(()=>query('select cp7_sku_conversion.automatic_assert_native_v5($1,$2,$3,$4)',[child,'REWORK',ax.rework,{...payload,reason:'Unrelated reason'}]),/AUTOMATIC_NATIVE_PAYLOAD_NOT_EXACT/);
  await autoRefusal(()=>query('select cp7_sku_conversion.automatic_assert_native_v5($1,$2,$3,$4)',[child,'REWORK',ax.rework,{...payload,expected_returns:[]}]),/AUTOMATIC_NATIVE_PAYLOAD_NOT_EXACT/);
  await query('select erp.be_post_conversion_v1($1,$2,$3,$4)',[payload,child,'REWORK',ax.rework]);
  const costRoot=await scalar('select destination_lot_id from erp.product_conversion_allocations where conversion_id=$1',[child]);
  await autoRefusal(()=>scalar("select cp7_sku_conversion.automatic_cost_unit_v5($1,$2,$3,'GRADE_A')",[costRoot,ax.source,x.otherLocation]),/^CP7_SKU_POOL_HPP_UNKNOWN:/);
  await query("select cp7_sku_conversion.automatic_leave_v5($1,'POST',$2)",[ax.rework,child]);
  assert.equal(Number(await scalar('select count(*)from cp7_sku_conversion.automatic_context_v5')),0);
  assert.equal(await scalar('select request_id from erp.be_execution_context_v1'),outer);
 });
 await autoControl('Outer Native context remains owned by the caller',async()=>{
  await autoFixture();const outer=id(100303);
  await insert('erp.be_execution_context_v1',{backend_pid:await scalar('select pg_backend_pid()'),transaction_id:await scalar('select txid_current()'),request_id:outer,syncing_nonpo:false});
  await query('select erp.be_complete_rework_target_v1($1)',[ax.rework]);
  assert.equal(await scalar('select request_id from erp.be_execution_context_v1'),outer);
  assert.equal(Number(await scalar('select count(*)from cp7_sku_conversion.automatic_context_v5')),0);
  await autoAssertValues(35,125);
  await query('select erp.be_reverse_rework_target_v1($1,$2)',[ax.rework,'Caller-owned Native context inverse']);
  assert.equal(await scalar('select request_id from erp.be_execution_context_v1'),outer);
  assert.equal(Number(await scalar('select count(*)from cp7_sku_conversion.automatic_context_v5')),0);
  await autoAssertValues(70,90);
 });
 await autoControl('Changed Native request invalidates an existing private lease',async()=>{
  await autoFixture();const child=id(100304),outer=id(100305);
  await insert('erp.be_execution_context_v1',{backend_pid:await scalar('select pg_backend_pid()'),transaction_id:await scalar('select txid_current()'),request_id:outer,syncing_nonpo:false});
  await query("select cp7_sku_conversion.automatic_enter_v5($1,'POST',$2)",[ax.rework,child]);
  await query('update erp.be_execution_context_v1 set request_id=$1',[id(100306)]);
  assert.equal(await scalar('select cp7_sku_conversion.automatic_valid_v5()'),false);
  await autoRefusal(()=>scalar("select cp7_sku_conversion.pool_quote_v2($1,$2,'GRADE_A')",[ax.source,x.location]),/^CP7_SKU_POOL_HPP_UNKNOWN:/);
 });
 for(const kind of['wrong_PO_lineage','missing_numeric_HPP'])await autoControl(kind+' refuses atomically',async()=>{
  await autoFixture();
  if(kind==='wrong_PO_lineage')await query('update erp.bs_cases set po_id=$1 where id=$2',[ax.otherPo,ax.bs]);
  else await query('update erp.hpp_versions set qty_basis_pcs=0 where id=$1',[ax.goodHpp]);
  await autoRefusal(()=>query('select erp.be_complete_rework_target_v1($1)',[ax.rework]),/CP7_SKU_AUTOMATIC_/);
  await autoNoFrames();
 });
 await autoControl('Late admission failure restores all Native physical and economic effects',async()=>{
  await autoFixture();await db.exec(`create function public.model_reject_automatic_admission()returns trigger language plpgsql as $$begin raise exception 'MODEL_LATE_AUTOMATIC_ADMISSION_FAILURE';end$$;
   create trigger model_reject_automatic_admission before insert on cp7_sku_conversion.automatic_admissions_v5 for each row execute function public.model_reject_automatic_admission();`);
  await autoRefusal(()=>query('select erp.be_complete_rework_target_v1($1)',[ax.rework]),/MODEL_LATE_AUTOMATIC_ADMISSION_FAILURE/);
  await autoNoFrames();
 });
 await autoControl('Zero GOOD retains the original no-conversion path',async()=>{
  await autoFixture('REWORK','PO_PENDING',true);const before=await costSnapshot();
  await query('select erp.be_complete_rework_target_v1($1)',[ax.rework]);
  assert.deepEqual(await costSnapshot(),before);await autoNoFrames();
 });
 await autoControl('Known manual FG average and inverse remain unchanged',async()=>{
  await legacyTargetSetup();const payload=await legacyPayload(x.root50);
  const preview=await scalar('select erp.be_conversion_preview_v1($1)',[payload]);
  assert.equal('valuation_provisional'in preview,false);assert.equal('source_value_state'in preview,false);
  const quote=await scalar("select cp7_sku_conversion.pool_quote_v2($1,$2,'GRADE_A')",[x.target,x.location]);
  assert.equal('final_cost_ready'in quote,false);
  const posted=await legacyAction('POST',payload,legacyRequest);assert.equal(posted.status,'POSTED');
  await legacyBooks(35,35);assert.equal(Number(await scalar('select count(*)from cp7_sku_conversion.automatic_admissions_v5')),0);
  await legacyAction('REVERSE',{conversion_id:legacyRequest,reason:'Original known manual inverse'},id(100120));
  await legacyBooks(70,0);await autoNoFrames();
 });
 await autoControl('Private automatic factories and history expose no role grants',async()=>{
  for(const role of['anon','authenticated','service_role']){
   assert.equal(await scalar("select has_table_privilege($1,'cp7_sku_conversion.automatic_context_v5','INSERT')",[role]),false);
   assert.equal(await scalar("select has_function_privilege($1,'cp7_sku_conversion.automatic_enter_v5(uuid,text,uuid)','EXECUTE')",[role]),false);
  }
 });
 assert.deepEqual(await costSnapshot(),automaticBaseline);
