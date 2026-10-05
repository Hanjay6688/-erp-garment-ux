create function cp7_plan_native.options(q jsonb)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;s jsonb;p jsonb;r jsonb;loc uuid;n integer;po_off integer;roll_off integer;pattern_off integer;
 po_q text;roll_q text;orders jsonb;patterns jsonb;rolls jsonb;locations jsonb;po_count bigint;pattern_count bigint;roll_count bigint;
begin
 a:=cp7_plan_native.access_now('READ');perform cp7_plan_native.fields(q,array['run_id','target_key','location_id','po_query','roll_query','po_offset','roll_offset','pattern_offset','limit']);
 if jsonb_typeof(q->'po_query')<>'string'or jsonb_typeof(q->'roll_query')<>'string'or length(q->>'po_query')>200 or length(q->>'roll_query')>200 then raise exception 'CP7_PLAN_OPTIONS';end if;
 n:=cp7_plan_native.decimal(q->'limit',true);po_off:=cp7_plan_native.decimal(q->'po_offset',true);roll_off:=cp7_plan_native.decimal(q->'roll_offset',true);pattern_off:=cp7_plan_native.decimal(q->'pattern_offset',true);
 if n not between 1 and 50 or greatest(po_off,roll_off,pattern_off)>1000000 then raise exception 'CP7_PLAN_OPTIONS';end if;
 s:=cp7_plan_native.analysis_source((q->>'run_id')::uuid);
 p:=(select x from jsonb_array_elements(s->'products')x where (x->>'root_id')||':'||(x->>'size_id')=q->>'target_key');
 r:=(select x from jsonb_array_elements(s->'netting'->'rows')x where x->>'target_key'=q->>'target_key');
 if p is null or r is null then raise exception 'CP7_PLAN_TARGET';end if;
 loc:=(q->>'location_id')::uuid;po_q:=lower(btrim(q->>'po_query'));roll_q:=lower(btrim(q->>'roll_query'));
 if loc is not null and not exists(select 1 from erp.locations where id=loc and is_active and location_type='RAW_MATERIAL_WAREHOUSE')then raise exception 'CP7_PLAN_NATIVE_LOCATION';end if;
 select count(*)into po_count from erp.production_orders x where x.model_id=(p->>'model_id')::uuid and x.status not in('FINISHED','CANCELLED')and(po_q=''or strpos(lower(x.po_number),po_q)>0);
 select coalesce(jsonb_agg(jsonb_build_object('id',id,'number',po_number,'model_id',model_id)order by po_number,id),'[]')into orders from(select x.id,x.po_number,x.model_id from erp.production_orders x where x.model_id=(p->>'model_id')::uuid and x.status not in('FINISHED','CANCELLED')and(po_q=''or strpos(lower(x.po_number),po_q)>0)order by x.po_number,x.id limit n offset po_off)x;
 select count(*)into pattern_count from erp.production_patterns where is_active;
 select coalesce(jsonb_agg(jsonb_build_object('id',id,'code',pattern_code,'name',pattern_name,'revision',revision)order by pattern_code,revision,id),'[]')into patterns from(select *from erp.production_patterns where is_active order by pattern_code,revision,id limit n offset pattern_off)x;
 with balances as(select x.id,x.roll_number,x.material_id,m.material_name,m.unit_code,coalesce(sum(sm.qty_signed),0)qty
  from erp.material_rolls x join erp.materials m on m.id=x.material_id
  left join erp.material_stock_movements sm on sm.roll_id=x.id and sm.location_id=loc and sm.physical_at<=clock_timestamp()
  where loc is not null and x.status in('AVAILABLE','HALF_USED')and m.is_active and m.material_type='FABRIC'
   and(roll_q=''or strpos(lower(x.roll_number||' '||m.material_name),roll_q)>0)
  group by x.id,x.roll_number,x.material_id,m.material_name,m.unit_code having coalesce(sum(sm.qty_signed),0)>0),
 paged as(select *from balances order by roll_number,id limit n offset roll_off)
 select(select count(*)from balances),coalesce(jsonb_agg(jsonb_build_object('id',id,'number',roll_number,'material_id',material_id,'material_name',material_name,'unit',unit_code,'available',pool->'native_available',
  'linked_native_draft_qty',pool->'linked_native_draft_qty','free_for_new_plan',pool->'free_for_new_plan')order by roll_number,id),'[]')into roll_count,rolls
 from paged cross join lateral(select cp7_plan_native.material_pool(id,loc)pool)budget;
 select coalesce(jsonb_agg(jsonb_build_object('id',id,'name',location_name)order by location_name,id),'[]')into locations from erp.locations where is_active and location_type='RAW_MATERIAL_WAREHOUSE';
 if jsonb_array_length(locations)>1000 then raise exception 'CP7_PLAN_OPTIONS_LOCATION_LIMIT';end if;
 if cp7_plan_native.access_now('READ')is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.plan-options.v2','actor_scope_id',a->>'actor','run_id',q->'run_id','target_key',q->'target_key',
  'source_hash',s->'source_hash','core_hash',s->'core_hash','model_id',p->'model_id','size_id',p->'size_id','product_sku',p->'sku','product_name',p->'product_name',
  'needed_pcs',r->'conditional_gap_pcs','capacity_pcs',s->'netting'->'new_start_capacity'->'capacity_pcs','production_state',r->'production_policy'->'policy'->'state',
  'assumptions',s->'analysis'->'assumptions','location_id',loc,'orders',orders,'patterns',patterns,'rolls',rolls,'locations',locations,
  'page',jsonb_build_object('limit',n,'po_offset',po_off,'po_total',po_count::text,'pattern_offset',pattern_off,'pattern_total',pattern_count::text,'roll_offset',roll_off,'roll_total',roll_count::text),
  'reservation_created',false,'production_go',false);
end $$;
create function cp7_plan_native.read(p_draft uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r cp7_plan_native.drafts%rowtype;i cp7_plan_native.intents%rowtype;g erp.cutting_groups%rowtype;outcome jsonb;
begin
 a:=cp7_plan_native.access_now('READ');select *into r from cp7_plan_native.drafts where id=p_draft and actor=(a->>'actor')::uuid;
 if r.id is null then raise exception using errcode='42501',message='CP7_PLAN_DRAFT_UNAVAILABLE';end if;
 select *into i from cp7_plan_native.intents where draft_id=r.id;if found then select *into g from erp.cutting_groups where id=i.cutting_group_id;end if;
 outcome:=jsonb_build_object('contract_version','cp7.plan-draft-read.v1','actor_scope_id',a->>'actor','draft_id',r.id,'plan_id',r.plan_id,'revision',r.revision::text,
  'run_id',r.run_id,'target_key',r.target_key,'source_hash',r.source_hash,'recorded_at',r.recorded_at,'payload',r.payload,
  'is_latest',r.revision=(select max(revision)from cp7_plan_native.drafts where plan_id=r.plan_id),
  'state',case when i.id is null then 'SAVED'when g.id is null then 'NATIVE_DRAFT_DELETED'when g.material_issue_posted then 'NATIVE_MATERIAL_POSTED'else'NATIVE_DRAFT_CREATED'end,
  'native_intent',case when i.id is null then null else jsonb_build_object('id',i.id,'cutting_group_id',i.cutting_group_id,'group_number',g.group_number,'material_issue_posted',g.material_issue_posted)end,
  'reservation_created',false,'production_go',false);
 if cp7_plan_native.access_now('READ')is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;return outcome;
end $$;
