// Exact retained/candidate credit HPP SQL inside the explicit PG17 consumer
// model. Authority, monetary credit lifecycle and book storage are providers;
// these controls do not claim an actual Native or authenticated ERP pass.
import assert from 'node:assert/strict';
export async function runCreditControls(ctx) {
 const {db,input,x,id,query,scalar,insert,movement,control,saleSetup,postSaleModel,returnSetup,
  fractionalSale,fractionalReturn,values}=ctx;
 const observations=[];
 await db.exec(input.credit_cent_domain);
 for(const definition of Object.values(input.native_credit_helpers))await db.exec(definition);
 for(const definition of Object.values(input.credit_definitions))await db.exec(definition);
 for(const [n,key]of['FG_INVENTORY','COGS','OTHER_EXPENSE','OTHER_INCOME','OPENING_EQUITY','AR_CUSTOMER','SALES_REVENUE'].entries()) {
  await insert('erp.chart_accounts',{id:id(9000+n),is_active:true,is_postable:true});
  await insert('erp.accounting_account_mappings',{mapping_key:key,account_id:id(9000+n)});
 }
 await db.exec(`create table public.model_credit_work(return_id uuid primary key,projection jsonb);
 create function public.model_credit_input(p_return uuid)returns jsonb language sql stable as $$
  select jsonb_build_object('sale_id',r.sale_id,'items',(select jsonb_agg(jsonb_build_object(
   'allocation_id',i.sale_stock_allocation_id,'qty_pcs',i.qty_pcs,'location_id',i.location_id,
   'quality_grade',i.quality_grade,'refund_amount',i.refund_amount)order by i.sale_stock_allocation_id,i.id)
   from erp.sales_return_items i where i.return_id=r.id))from erp.sales_returns r where r.id=p_return$$;
 create or replace function cp7_credit.native_return_enter(p_return uuid)returns void language plpgsql as $$begin
  insert into public.model_credit_work values(p_return,cp7_credit.initial_hpp_projection_v1(public.model_credit_input(p_return)));end$$;
 create or replace function cp7_credit.native_return_complete(p_return uuid,p_refund numeric,p_net numeric)returns numeric language plpgsql as $$
 declare p jsonb;g jsonb;actual jsonb;lines jsonb;expected_lines jsonb;customer uuid;begin
  select projection into strict p from public.model_credit_work where return_id=p_return;
  for g in select *from jsonb_array_elements(p->'groups')loop
   if g->>'po_id'is null then select to_jsonb(t)into actual from erp.compute_non_po_product_hpp_targets_v2620f((g->>'product_id')::uuid)t;
   else select to_jsonb(t)into actual from erp.compute_po_hpp_gl_targets_v2620d((g->>'po_id')::uuid)t;end if;
   if actual is distinct from g->'after_target'then raise exception 'MODEL_CREDIT_ACTUAL_TARGET_MISMATCH';end if;
  end loop;
  select coalesce(jsonb_agg(l),'[]')into lines from public.model_journal j cross join lateral jsonb_array_elements(j.lines)l
   where j.source_type='SALES_RETURN'and j.source_id=p_return and l->>'mapping_key'in('FG_INVENTORY','COGS','OTHER_EXPENSE','OTHER_INCOME');
  select customer_id into strict customer from erp.sales_returns where id=p_return;
  -- Retained build_initial_return_for_draft_v1 adds this customer to every
  -- HPP line before store_initial_plan_v1 compares exact line semantics.
  select coalesce(jsonb_agg(l||jsonb_build_object('customer_id',customer)),'[]')into expected_lines
   from jsonb_array_elements(p->'lines')l;
  if cp7_credit.initial_line_semantics_v1(lines)is distinct from cp7_credit.initial_line_semantics_v1(expected_lines)then
   raise exception 'MODEL_CREDIT_EXACT_NATIVE_HPP_JOURNAL_MISMATCH'using detail=jsonb_build_object('actual',lines,'expected',expected_lines)::text;end if;
  return 0;end$$;
 alter function erp.post_journal(text,uuid,date,text,jsonb)rename to model_post_journal;
 create function erp.post_journal(p_type text,p_id uuid,p_date date,p_reason text,p_lines jsonb)returns uuid language plpgsql as $$
 declare j uuid;l jsonb;begin
  j:=erp.model_post_journal(p_type,p_id,p_date,p_reason,p_lines);
  insert into erp.journal_entries(id,source_type,source_id,status,economic_date,transaction_date)values(j,p_type,p_id,'POSTED',p_date,p_date);
  for l in select *from jsonb_array_elements(p_lines)loop
   insert into erp.journal_lines(id,journal_entry_id,account_id,product_id,po_id,customer_id,debit,credit)
   values(gen_random_uuid(),j,cp7_credit.account_by_mapping_v1(l->>'mapping_key'),(l->>'product_id')::uuid,(l->>'po_id')::uuid,
    (l->>'customer_id')::uuid,coalesce((l->>'debit')::numeric,0),coalesce((l->>'credit')::numeric,0));end loop;return j;end$$;
 create function cp7_credit.native_source_enter(text,uuid)returns void language plpgsql as $$begin return;end$$;
 create function cp7_credit.native_source_complete(text,uuid)returns void language plpgsql as $$begin return;end$$;
 create function cp7_credit.source_operation_native_reconcile_v1(text,uuid)returns void language plpgsql as $$begin return;end$$;
 create function cp7_credit.current_effective_paid(uuid)returns numeric language sql as $$
  select coalesce(sum(amount),0)::numeric from erp.sales_payments where sale_id=$1 and status='POSTED'$$;
 create function erp.reverse_journal(p_journal uuid,p_reason text)returns uuid language plpgsql as $$
 declare lines jsonb;j uuid;begin
  select jsonb_agg(l||jsonb_build_object('debit',l->'credit','credit',l->'debit'))into lines
   from public.model_journal mj cross join lateral jsonb_array_elements(mj.lines)l where mj.id=p_journal;
  if lines is null then raise exception 'MODEL_INVERSE_ORIGINAL_REQUIRED';end if;
  j:=erp.post_journal('JOURNAL_REVERSAL',p_journal,(statement_timestamp()at time zone'Asia/Jakarta')::date,p_reason,lines);
  update erp.journal_entries set status='REVERSED'where id=p_journal;
  update erp.journal_entries set reversal_of_id=p_journal where id=j;return j;end$$;
 `);
 async function baselineBook() {
  // Model the already reconciled baseline explicitly; subsequent exact Native
  // journal writes append actual lines via the storage provider above.
  await db.exec('delete from erp.journal_lines;delete from erp.journal_entries;');
  for(const b of (await query('select *from public.model_book')).rows) {
   const j=await scalar("insert into erp.journal_entries(id,source_type,status)values(gen_random_uuid(),'MODEL_BASELINE','POSTED')returning id");
   for(const[key,field]of[['FG_INVENTORY','fg'],['COGS','cogs'],['OTHER_EXPENSE','other_value']]) {
    const amount=Number(b[field]);await insert('erp.journal_lines',{id:await scalar('select gen_random_uuid()'),journal_entry_id:j,
     account_id:await scalar('select cp7_credit.account_by_mapping_v1($1)',[key]),product_id:b.product_id,debit:Math.max(amount,0),credit:Math.max(-amount,0)});
   }
  }
 }
 async function convertedDraft() {
  await saleSetup();
  await query('update erp.sales_headers set customer_id=$1,source_location_id=$2 where id=$3',[id(900),x.location,x.sale]);
  await query('update erp.sales_items set qty_pcs=2,unit_price_snapshot=185000,discount_amount=0 where sale_id=$1',[x.sale]);
  for(const lot of[x.root50,x.converted])await insert('erp.fg_stock_movements',{
   id:await scalar('select gen_random_uuid()'),lot_id:lot,product_id:x.target,location_id:x.location,quality_grade:'GRADE_A',
   qty_signed:-1,movement_type:'SALE_RESERVE',customer_id:id(900),source_type:'SALE_ITEM',source_id:x.saleItem,
   physical_at:'2026-01-02T00:00:00Z',system_created_at:'2026-01-02T00:00:00Z'});
  await query('select erp.post_sale($1)',[x.sale]);await returnSetup();
  await query('update erp.sales_returns set sale_id=$1,customer_id=$2 where id=$3',[x.sale,id(900),x.returned]);
  await query('update erp.sales_return_items set refund_amount=185000 where return_id=$1',[x.returned]);
  await query("update erp.fg_lots set cached_qty_pcs=0,produced_at='2026-01-01'where product_id=$1",[x.target]);
  await baselineBook();
 }
 const projection=async returned=>scalar('select cp7_credit.initial_hpp_projection_v1(public.model_credit_input($1))',[returned]);
 const observe=async label=>observations.push({label,plans:await scalar("select coalesce(jsonb_agg(to_jsonb(w)order by return_id),'[]')from public.model_credit_work w")});
 await control('Retained credit canonical projection reproduces the real moving-average mismatch before posting',async()=>{
  await convertedDraft();await db.exec(input.credit_originals['cp7_credit.initial_hpp_targets_v1(uuid,uuid,jsonb,boolean)']);
  await db.exec('savepoint original_mismatch');
  await assert.rejects(()=>projection(x.returned),e=>e.message.includes('CP7_CREDIT_HPP_CANONICAL_TARGET_MISMATCH'));
  await db.exec('rollback to savepoint original_mismatch');
  assert.equal(await scalar('select count(*)from cp7_sku_conversion.sales_return_values_v2'),0);
  assert.equal(await scalar("select count(*)from public.model_journal where source_type='SALES_RETURN'"),0);
 });
 await control('Converted return seals raw economic roots then matches exact Native target and journal 35',async()=>{
  await convertedDraft();const p=await projection(x.returned);
  assert.equal(p.groups.length,1);assert.equal(Number(p.groups[0].delta.fg_value),35);
  for(const lot of[x.root10,x.root30,x.root50,x.converted])assert(p.locked_lot_ids.includes(lot));
  assert.equal(p.economic_return_components.length,3);
  await query('select erp.post_sales_return($1)',[x.returned]);
  assert.deepEqual(await values(x.target),{hpp:70,fg:35,cogs:35,other:0});
  await observe('converted Native return with exact HPP credit prediction');
 });
 await control('Credit prediction preserves split return cent carry and cross-warehouse target/journal equality',async()=>{
  await fractionalSale();await baselineBook();
  const a=await fractionalReturn('credit split first',30,[[x.saleB,1]]);
  const b=await fractionalReturn('credit split second cross warehouse',31,[[x.saleB,1]],x.otherLocation);
  assert.deepEqual([a.snapshot,b.snapshot],[3.33,3.34]);
  await observe('fractional split and different destination');
 });
 await control('Credit prediction handles distinct allocation lines in one draft without double counting',async()=>{
  await fractionalSale();await baselineBook();
  const a=await fractionalReturn('credit multi allocation',32,[[x.saleA,1],[x.saleB,1]]);
  assert.equal(a.snapshot,6.67);
  const b=await fractionalReturn('credit final allocation',33,[[x.saleB,1]]);assert.equal(b.snapshot,3.33);
  await observe('multiple physical allocations and final remaining quantity');
 });
 await control('Credit prediction after current-root recost preserves immutable earlier return and next 4.50 value',async()=>{
  await fractionalSale();await baselineBook();const a=await fractionalReturn('credit before recost',34,[[x.saleB,1]]);
  const frozen=await scalar('select jsonb_agg(to_jsonb(v)order by sales_return_item_id)from cp7_sku_conversion.sales_return_values_v2 v');
  await query("select erp.post_opening_hpp_correction($1,4.5,'credit component recost','2026-01-04')",[x.root90]);
  // With the single-root fractional fixture, the new total is 13.50 and the
  // next piece is 4.50; the two-root 12.32/4.10 case is the Native6 fixture.
  const b=await fractionalReturn('credit after recost',35,[[x.saleB,1]]);assert.equal(b.snapshot,4.5);
  assert.equal(a.snapshot,3.33);
  assert.deepEqual(await scalar('select jsonb_agg(to_jsonb(v)order by sales_return_item_id)from cp7_sku_conversion.sales_return_values_v2 v where return_id=$1',[a.returned]),frozen);
  await observe('current-root recost between returns');
 });
 await control('Credit projection refuses unexplained book cent before any return value is prepared',async()=>{
  await convertedDraft();await query("update erp.journal_lines set debit=debit+0.01 where product_id=$1 and account_id=cp7_credit.account_by_mapping_v1('COGS')",[x.target]);
  await assert.rejects(()=>projection(x.returned),e=>e.message.includes('CP7_CREDIT_HPP_TARGET_BOOK_NOT_RECONCILED'));
 });
 await control('Exact Native return inverse plus modeled journal storage leaves the next credit projection at the correct cent',async()=>{
  await fractionalSale();await baselineBook();const a=await fractionalReturn('credit earlier inverse first',36,[[x.saleB,1]]);
  await fractionalReturn('credit earlier inverse second',37,[[x.saleB,1]]);
  const frozen=await scalar('select jsonb_agg(to_jsonb(v)order by sales_return_item_id)from cp7_sku_conversion.sales_return_values_v2 v');
  await query("select erp.reverse_sales_return($1,'model earlier inverse')",[a.returned]);
  assert.deepEqual(await values(x.outside),{hpp:10,fg:3.33,cogs:6.67,other:0});
  assert.deepEqual(await scalar('select jsonb_agg(to_jsonb(v)order by sales_return_item_id)from cp7_sku_conversion.sales_return_values_v2 v'),frozen);
  const b=await fractionalReturn('credit replacement after inverse',38,[[x.saleB,1]]);assert.equal(b.snapshot,3.34);
  await observe('earlier inverse and replacement with exact Native physical order');
 });
 await control('Credit projection accepts known zero HPP with an actual refund journal',async()=>{
  await fractionalSale();await query('update erp.hpp_versions set total_cost=0 where id=$1',[x.hpp90]);
  await query('update public.model_book set fg=0,cogs=0 where product_id=$1',[x.outside]);await baselineBook();
  const r=await fractionalReturn('credit known zero',39,[[x.saleB,1]]);assert.equal(r.snapshot,0);
  await observe('known zero is distinct from unknown');
 });
 await control('Pre-installation sale allocation retains its physical fallback without inventing SKU component history',async()=>{
  await saleSetup(x.source,[x.root10],[1]);
  await query("update erp.sales_headers set status='POSTED',customer_id=$1 where id=$2",[id(900),x.sale]);
  await query('update erp.sales_items set qty_pcs=1,unit_price_snapshot=185000,discount_amount=0 where sale_id=$1',[x.sale]);
  await query('update erp.sale_stock_allocations set unit_hpp_snapshot=10 where id=$1',[x.saleA]);
  await movement(x.root10,x.source,-1,'SALE_OUT',10);
  await query('update public.model_book b set fg=t.fg_value,cogs=t.cogs_value,other_value=t.other_out_value from erp.compute_non_po_product_hpp_targets_v2620f($1)t where b.product_id=$1',[x.source]);
  await baselineBook();
  await insert('erp.sales_returns',{id:x.returned,sale_id:x.sale,customer_id:id(900),status:'DRAFT',physical_at:'2026-01-03T00:00:00Z'});
  await insert('erp.sales_return_items',{id:x.returnItem,return_id:x.returned,sale_stock_allocation_id:x.saleA,
   product_id:x.source,lot_id:x.root10,location_id:x.location,quality_grade:'GRADE_A',qty_pcs:1,refund_amount:185000});
  await query("update erp.fg_lots set cached_qty_pcs=0,produced_at='2026-01-01'where id=$1",[x.root10]);
  const p=await projection(x.returned);assert.equal(Number(p.groups[0].delta.fg_value),10);
  await query('select erp.post_sales_return($1)',[x.returned]);
  assert.equal(await scalar('select count(*)from cp7_sku_conversion.sales_return_values_v2'),0);
  assert.deepEqual(await values(x.source),{hpp:60,fg:60,cogs:0,other:0});
  await observe('legacy physical fallback with exact Native return');
 });
 await control('Mixed PO economic roots produce two sealed groups and preserve each hypothetical target cent',async()=>{
  await query("update erp.fg_lots set po_id=$1,lot_origin='PRODUCTION'where id=$2",[x.po,x.root30]);
  await query('update erp.hpp_versions set total_cost=60.02 where id=$1',[x.hpp30]);
  await saleSetup();await query('update erp.sales_headers set customer_id=$1 where id=$2',[id(900),x.sale]);
  await query('update erp.sales_items set qty_pcs=2,unit_price_snapshot=185000,discount_amount=0 where sale_id=$1',[x.sale]);
  await query('select cp7_sku_conversion.prepare_sale_values_v2($1)',[x.sale]);
  await movement(x.root50,x.target,-1,'SALE_OUT');await movement(x.converted,x.target,-1,'SALE_OUT');
  await query("update erp.sales_headers set status='POSTED'where id=$1",[x.sale]);
  for(const product of[x.source,x.target,x.outside])await query('update public.model_book b set fg=t.fg_value,cogs=t.cogs_value,other_value=t.other_out_value from erp.compute_non_po_product_hpp_targets_v2620f($1)t where b.product_id=$1',[product]);
  await baselineBook();const po=(await query('select *from erp.compute_po_hpp_gl_targets_v2620d($1)',[x.po])).rows[0];
  await insert('erp.po_hpp_gl_state',{po_id:x.po,...po});
  const journal=await scalar("insert into erp.journal_entries(id,source_type,status)values(gen_random_uuid(),'MODEL_PO_BASELINE','POSTED')returning id");
  for(const[key,field]of[['FG_INVENTORY','fg_value'],['COGS','cogs_value'],['OTHER_EXPENSE','other_out_value']]) {
   const amount=Number(po[field]);await insert('erp.journal_lines',{id:await scalar('select gen_random_uuid()'),journal_entry_id:journal,
    account_id:await scalar('select cp7_credit.account_by_mapping_v1($1)',[key]),po_id:x.po,debit:Math.max(amount,0),credit:Math.max(-amount,0)});
  }
  await returnSetup();await query('update erp.sales_returns set sale_id=$1,customer_id=$2 where id=$3',[x.sale,id(900),x.returned]);
  await query('update erp.sales_return_items set refund_amount=185000 where return_id=$1',[x.returned]);
  const plan=await projection(x.returned);assert.equal(plan.groups.length,2);
  assert.deepEqual(plan.groups.map(g=>Number(g.delta.fg_value)).sort((a,b)=>a-b),[7.5,27.5]);
  assert(plan.locked_lot_ids.includes(x.root30));assert(plan.locked_lot_ids.includes(x.root10));
  await query('select cp7_sku_conversion.prepare_return_values_v2($1)',[x.returned]);
  await movement(x.root50,x.target,1,'SALE_RETURN');await query("update erp.sales_returns set status='POSTED'where id=$1",[x.returned]);
  for(const g of plan.groups) {
   const actual=await scalar(g.po_id?'select to_jsonb(t)from erp.compute_po_hpp_gl_targets_v2620d($1)t':'select to_jsonb(t)from erp.compute_non_po_product_hpp_targets_v2620f($1)t',[g.po_id??g.product_id]);
   assert.deepEqual(actual,g.after_target);
   const amount=await scalar('select sum(effective_value)::text from cp7_sku_conversion.sales_return_attributions_v2 where sales_return_item_id=$1 and po_id is not distinct from $2',[x.returnItem,g.po_id]);
   assert.equal(Number(amount),Number(g.delta.fg_value));
  }
  observations.push({label:'mixed PO and non-PO projected economic groups',plan});
 });
 await control('Credit projection refuses unknown economic root even when the selected physical lot has known HPP',async()=>{
  await convertedDraft();await query("update erp.hpp_versions set cost_state='ESTIMATED'where lot_id=$1",[x.root30]);
  await assert.rejects(()=>projection(x.returned),e=>e.message.includes('CP7_SKU_RETURN_COMPONENT_HPP_UNKNOWN'));
 });
 await control('Credit support and opening provenance include an economic root from another product',async()=>{
  await convertedDraft();const before=await scalar('select cp7_credit.initial_hpp_support_v1($1,null)',[x.target]);
  await query("update erp.hpp_versions set version_no=version_no+1 where lot_id=$1",[x.root30]);
  assert.notDeepEqual(await scalar('select cp7_credit.initial_hpp_support_v1($1,null)',[x.target]),before);
  await insert('erp.opening_lot_hpp_gl_state',{lot_id:x.root30,current_hpp:30,fg_revaluation:0,cogs_revaluation:0,expense_revaluation:0,income_revaluation:0,equity_revaluation:0});
  const opening=await scalar('select cp7_credit.initial_opening_hpp_source_v1($1,null)',[x.target]);
  assert(opening.states.some(s=>s.lot_id===x.root30));
 });
 return {classification:'EXACT_CREDIT_HPP_PROJECTION_AND_NATIVE_CONSUMER_SQL_WITH_EXPLICIT_MODEL_PROVIDERS',observations,
  actual_Native_cases:0,production_go:false,independent_acceptance:false};
}
