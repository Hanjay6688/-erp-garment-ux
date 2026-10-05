-- One physical roll/location is one future-plan budget across every actor and
-- target. Read the current Native draft composition, never the old CP7 estimate.
-- Posted groups already reduced physical stock and are not deducted again.
-- No stock reservation, issue, return, installation or costing fact is written.
create function cp7_plan_native.material_pool(p_roll uuid,p_location uuid)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with clock as materialized(select clock_timestamp()at),
 stock as(select coalesce(sum(m.qty_signed),0)qty from erp.material_stock_movements m cross join clock c
  where m.roll_id=p_roll and m.location_id=p_location and m.physical_at<=c.at),
 linked as materialized(select g.id group_id,g.row_version::text revision,r.id line_id,r.qty_issued qty
  from erp.cutting_groups g join erp.cutting_group_rolls r on r.cutting_group_id=g.id
  where r.roll_id=p_roll and g.source_location_id=p_location and not g.material_issue_posted
   and g.id in(select cutting_group_id from cp7_plan_native.intents)),
 planned as(select coalesce(sum(qty),0)qty from linked)
 select jsonb_build_object('roll_id',p_roll,'location_id',p_location,'native_available',s.qty::text,
  'linked_native_draft_qty',p.qty::text,'free_for_new_plan',case when s.qty<0 then null else greatest(0,s.qty-p.qty)::text end,
  'linked_native_drafts',coalesce((select jsonb_agg(jsonb_build_object('group_id',group_id,'group_revision',revision,
   'line_id',line_id,'qty_issued',qty::text)order by group_id,line_id)from linked),'[]'::jsonb),
  'basis','CURRENT_NATIVE_LINKED_UNPOSTED_DRAFT_BUDGET_NOT_STOCK_RESERVATION')from stock s cross join planned p
$$;

create function cp7_plan_native.preflight(p jsonb)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare s jsonb;r jsonb;product jsonb;cut jsonb;slot jsonb;roll jsonb;y jsonb;review jsonb;
 po erp.production_orders%rowtype;pattern erp.production_patterns%rowtype;native_roll erp.material_rolls%rowtype;
 target text;size uuid;total numeric:=0;roll_total numeric;issued numeric;consumed numeric;remaining numeric;available numeric;
 gap numeric;capacity numeric;seen uuid[]:='{}';material_rows jsonb:='[]';assumptions jsonb;native_payload jsonb;pool jsonb;
begin
 perform cp7_plan_native.fields(p,array['run_id','target_key','plan_id','expected_revision','source_hash','cutting','reviewed_assumption_ids','reason']);
 if jsonb_typeof(p->'run_id')<>'string'or jsonb_typeof(p->'target_key')<>'string'or jsonb_typeof(p->'source_hash')<>'string'
  or p->>'source_hash'!~'^[0-9a-f]{64}$'or jsonb_typeof(p->'reason')<>'string'or length(btrim(p->>'reason'))not between 1 and 1000
  or jsonb_typeof(p->'reviewed_assumption_ids')is distinct from'array'then raise exception 'CP7_PLAN_REVIEW';end if;
 s:=cp7_plan_native.analysis_source((p->>'run_id')::uuid);target:=p->>'target_key';
 if p->>'source_hash'<>s->>'source_hash'then raise exception using errcode='40001',message='CP7_PLAN_SOURCE_CHANGED';end if;
 product:=(select x from jsonb_array_elements(s->'products')x where (x->>'root_id')||':'||(x->>'size_id')=target);
 r:=(select x from jsonb_array_elements(s->'netting'->'rows')x where x->>'target_key'=target);
 if product is null or r is null then raise exception 'CP7_PLAN_TARGET';end if;
 if product->'is_active'is distinct from'true'::jsonb or r->'production_policy'->'policy'->>'state'is distinct from'ACTIVE'then raise exception 'CP7_PLAN_PRODUCTION_DISABLED';end if;
 if r->>'conditional_gap_pcs'is null or s->'netting'->'allocation'->>'status'is distinct from'SCENARIO'
  or s->'netting'->'new_start_capacity'->>'status'is distinct from'SCENARIO'then raise exception 'CP7_PLAN_FEASIBILITY_UNKNOWN';end if;
 gap:=(r->>'conditional_gap_pcs')::numeric;capacity:=(s->'netting'->'new_start_capacity'->>'capacity_pcs')::numeric;
 if gap<=0 or capacity is null then raise exception 'CP7_PLAN_NO_NEW_NEED';end if;
 select coalesce(jsonb_agg(x->'id'order by x->>'id'),'[]'::jsonb)into assumptions from jsonb_array_elements(s->'analysis'->'assumptions')x;
 if exists(select 1 from jsonb_array_elements(p->'reviewed_assumption_ids')x where jsonb_typeof(x)<>'string')
  or(select count(distinct value)from jsonb_array_elements(p->'reviewed_assumption_ids'))<>jsonb_array_length(p->'reviewed_assumption_ids')
  or not ((p->'reviewed_assumption_ids')@>assumptions)
  or not (assumptions@>(p->'reviewed_assumption_ids'))then raise exception 'CP7_PLAN_ASSUMPTIONS_NOT_REVIEWED';end if;
 cut:=p->'cutting';perform cp7_plan_native.fields(cut,array['po_id','pattern_id','source_location_id','cut_at','notes','size_slots','rolls']);
 select *into po from erp.production_orders where id=(cut->>'po_id')::uuid;
 select *into pattern from erp.production_patterns where id=(cut->>'pattern_id')::uuid;
 if po.id is null or po.status in('FINISHED','CANCELLED')or po.model_id::text<>product->>'model_id'then raise exception 'CP7_PLAN_NATIVE_PO_MODEL';end if;
 if pattern.id is null or not pattern.is_active then raise exception 'CP7_PLAN_NATIVE_PATTERN';end if;
 if not exists(select 1 from erp.locations where id=(cut->>'source_location_id')::uuid and is_active and location_type='RAW_MATERIAL_WAREHOUSE')then raise exception 'CP7_PLAN_NATIVE_LOCATION';end if;
 if jsonb_typeof(cut->'cut_at')<>'string'or not isfinite((cut->>'cut_at')::timestamptz)or(cut->>'cut_at')::timestamptz>clock_timestamp()+interval'5 minutes'then raise exception 'CP7_PLAN_NATIVE_CUT_DATE';end if;
 if jsonb_typeof(cut->'size_slots')is distinct from'array'or jsonb_array_length(cut->'size_slots')<>1
  or jsonb_typeof(cut->'rolls')is distinct from'array'or jsonb_array_length(cut->'rolls')not between 1 and 100 then raise exception 'CP7_PLAN_NATIVE_COMPOSITION';end if;
 slot:=cut->'size_slots'->0;perform cp7_plan_native.fields(slot,array['slot_no','size_id','drawing_no']);size:=(product->>'size_id')::uuid;
 if slot->>'slot_no'<>'1'or(slot->>'size_id')::uuid<>size or cp7_plan_native.decimal(slot->'drawing_no',true)=0
  or not exists(select 1 from erp.sizes where id=size and is_active)
  or not exists(select 1 from erp.product_model_sizes where model_id=po.model_id and size_id=size)then raise exception 'CP7_PLAN_NATIVE_EXACT_SIZE';end if;
 for roll in select value from jsonb_array_elements(cut->'rolls')loop
  perform cp7_plan_native.fields(roll,array['roll_id','qty_issued','qty_consumed','qty_reported_remaining','yields']);
  select *into native_roll from erp.material_rolls where id=(roll->>'roll_id')::uuid;
  if native_roll.id is null or native_roll.id=any(seen)or native_roll.status not in('AVAILABLE','HALF_USED')then raise exception 'CP7_PLAN_NATIVE_ROLL';end if;
  seen:=array_append(seen,native_roll.id);issued:=cp7_plan_native.decimal(roll->'qty_issued');consumed:=cp7_plan_native.decimal(roll->'qty_consumed');remaining:=cp7_plan_native.decimal(roll->'qty_reported_remaining');
  if issued<=0 or consumed<=0 or consumed+remaining<>issued then raise exception 'CP7_PLAN_NATIVE_MATERIAL_RECONCILIATION';end if;
  pool:=cp7_plan_native.material_pool(native_roll.id,(cut->>'source_location_id')::uuid);
  available:=(pool->>'native_available')::numeric;
  if available<issued or not exists(select 1 from erp.materials where id=native_roll.material_id and is_active and material_type='FABRIC')then raise exception 'CP7_PLAN_NATIVE_MATERIAL_NOT_READY';end if;
  if pool->>'free_for_new_plan'is null or(pool->>'free_for_new_plan')::numeric<issued then raise exception using errcode='40001',message='CP7_PLAN_SHARED_MATERIAL_BUDGET_CHANGED';end if;
  if jsonb_typeof(roll->'yields')is distinct from'array'or jsonb_array_length(roll->'yields')<>1 then raise exception 'CP7_PLAN_NATIVE_EXACT_SIZE';end if;
  y:=roll->'yields'->0;perform cp7_plan_native.fields(y,array['slot_no','qty_pcs']);roll_total:=cp7_plan_native.decimal(y->'qty_pcs',true);
  if y->>'slot_no'<>'1'or roll_total<=0 then raise exception 'CP7_PLAN_NATIVE_EXACT_SIZE';end if;total:=total+roll_total;
  material_rows:=material_rows||jsonb_build_array(jsonb_build_object('roll_id',native_roll.id,'material_id',native_roll.material_id,
   'native_available',available::text,'linked_native_draft_qty',pool->'linked_native_draft_qty','free_for_new_plan',pool->'free_for_new_plan',
   'linked_native_drafts',pool->'linked_native_drafts','selected_issued',issued::text,'selected_consumption',consumed::text,'selected_remaining',remaining::text,
   'native_status',native_roll.status,'basis','OPERATOR_SELECTED_DRAFT_COMPOSITION_NOT_PROVEN_INSTALLED_OR_RESERVED'));
 end loop;
 if total>ceil(gap)or total>capacity then raise exception 'CP7_PLAN_QUANTITY_EXCEEDS_NEED_OR_CAPACITY';end if;
 if exists(select 1 from cp7_plan_native.intents i join erp.cutting_groups g on g.id=i.cutting_group_id where i.target_key=target and not g.material_issue_posted)
  or exists(select 1 from cp7_plan_native.intents i join erp.cutting_groups g on g.id=i.cutting_group_id where i.target_key=target and i.core_hash=s->>'core_hash')then raise exception using errcode='40001',message='CP7_PLAN_LINKED_INTENT_CONFLICT';end if;
 if exists(select 1 from cp7_plan_native.intents where target_key=target and recorded_at>=(s->>'captured_at')::timestamptz)then raise exception using errcode='40001',message='CP7_PLAN_INTENT_EPOCH_CHANGED';end if;
 native_payload:=cut||jsonb_build_object('action','SAVE_DRAFT','change_reason',btrim(p->>'reason'));
 return jsonb_build_object('contract_version','cp7.plan-preview.v2','source_hash',s->'source_hash','core_hash',s->'core_hash',
  'target_key',target,'product_sku',product->'sku','product_name',product->'product_name','needed_pcs',gap::text,
  'selected_new_pcs',total::text,'rounding_extra_pcs',greatest(0,total-gap)::text,'free_capacity_pcs',capacity::text,
  'unresolved_pcs',greatest(0,gap-total)::text,'material_rows',material_rows,'pattern_revision',pattern.revision,
  'composition_hash',encode(extensions.digest(convert_to(jsonb_build_object('po_id',po.id,'po_model',po.model_id,'po_status',po.status,'pattern_id',pattern.id,'pattern_version',pattern.row_version,'pattern_revision',pattern.revision,'material_rows',material_rows)::text,'UTF8'),'sha256'),'hex'),'native_payload',native_payload,'command','erp_save_cutting_group_before_sewing_v2:SAVE_DRAFT',
  'status','READY_FOR_EXPLICIT_NATIVE_DRAFT','reservation_created',false,'physical_production_confirmed',false,'production_go',false);
end $$;
