create or replace function cp7_plan_native.history_source(p_target text,p_model uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;pol cp7_yield_policy.policies%rowtype;clk timestamptz:=clock_timestamp();root uuid;size uuid;kernel text;first_day date;
 w_start timestamptz;ps_ids uuid[];ps_n integer;m_ids uuid[];m_n integer;todo uuid[];done uuid[]:='{}';res jsonb:='[]';part jsonb;
 unverified integer:=0;bi integer;lv jsonb:='[]';used jsonb;chosen jsonb;level text;st text;rs text;k integer;ng integer;cut numeric;fg numeric;
 lvl text;stale_or_unverifiable integer;outside integer;unattributed integer;not_spent integer;
begin
 a:=cp7_private.access_now();
 if p_target!~'^[0-9a-f-]{36}:[0-9a-f-]{36}$'then raise exception 'CP7_PLAN_TARGET';end if;
 select *into pol from cp7_yield_policy.policies order by revision desc limit 1;
 if pol.id is null then
  return jsonb_build_object('status','PENDING_POLICY_VALUE','reason','OWNER_HISTORY_YIELD_POLICY_NOT_APPROVED',
   'window_days',null,'minimum_sample',null,'lower_bound',null,'numerator',null,'denominator',null,'target_key',p_target);
 end if;
 root:=split_part(p_target,':',1)::uuid;size:=split_part(p_target,':',2)::uuid;
 first_day:=(clk at time zone 'Asia/Jakarta')::date-pol.window_days+1;w_start:=first_day::timestamp at time zone 'Asia/Jakarta';
 if pol.state='PAUSED'then st:='POLICY_PAUSED';rs:='HISTORY_YIELD_POLICY_PAUSED';
 elsif p_model is null or(select count(*)from erp.products p where coalesce(p.identity_root_id,p.id)=root and p.size_id=size
   and p.effective_from<=clk and(p.effective_to is null or p.effective_to>clk))<>1
  or not exists(select 1 from erp.products p where coalesce(p.identity_root_id,p.id)=root and p.size_id=size and p.model_id=p_model
   and p.effective_from<=clk and(p.effective_to is null or p.effective_to>clk))then st:='UNKNOWN';rs:='TARGET_MODEL_CHANGED';
 else
  begin kernel:=cp7_supply_native.proof_kernel();
  exception when others then kernel:=null;
  end;
  if kernel is null then st:='UNKNOWN';rs:='PROOF_KERNEL_UNAVAILABLE';end if;
 end if;
 if st is null then
  -- Product+size candidates: the model's groups with posted QC of this root and size.
  select coalesce(array_agg(x.id order by x.id),'{}'::uuid[]),count(*)into ps_ids,ps_n from(
   select g.id from erp.cutting_groups g join erp.production_orders po on po.id=g.po_id
   where po.model_id=p_model and g.material_issue_posted and g.cut_at<=clk
    and exists(select 1 from cp7_supply_native.exhaustion_proofs x where x.group_id=g.id and x.kernel_version=kernel and x.captured_at>=w_start)
    and exists(select 1 from erp.qc_inspection_items i join erp.qc_inspections q on q.id=i.inspection_id join erp.products p on p.id=i.final_product_id
     where i.cutting_group_id=g.id and q.status='POSTED'and coalesce(p.identity_root_id,p.id)=root and p.size_id=size)
   order by g.id)x;
  select coalesce(array_agg(x.id order by x.id),'{}'::uuid[]),count(*)into m_ids,m_n from(
   select g.id from erp.cutting_groups g join erp.production_orders po on po.id=g.po_id
   where po.model_id=p_model and g.material_issue_posted and g.cut_at<=clk
    and exists(select 1 from cp7_supply_native.exhaustion_proofs x where x.group_id=g.id and x.kernel_version=kernel and x.captured_at>=w_start)
   order by g.id)x;
  foreach lvl in array array['PRODUCT_SIZE','MODEL']loop
   if lvl='MODEL'and chosen is not null then
    lv:=lv||jsonb_build_array(jsonb_build_object('level',lvl,'status','NOT_EVALUATED','reason','PRODUCT_SIZE_SUFFICIENT'));continue;end if;
   todo:=array(select x from unnest(case when lvl='PRODUCT_SIZE'then ps_ids else m_ids end)x where not x=any(done)order by x);
   bi:=1;
   while bi<=cardinality(todo)loop
    part:=cp7_plan_native.history_groups(todo[bi:least(bi+49,cardinality(todo))],clk,kernel);
    if part->>'status'<>'COMPLETE'then st:='UNKNOWN';rs:=part->>'reason';exit;end if;
    res:=res||(part->'groups');unverified:=unverified+jsonb_array_length(part->'unverified');
    bi:=bi+50;
   end loop;
   exit when st is not null;
   done:=done||todo;
   -- The groups of this level that count: proven, spent in every pool, of
   -- this model only (cut and QC), finished inside the window.
   with gr as(select x from jsonb_array_elements(res)x where(x->>'group_id')::uuid=any(case when lvl='PRODUCT_SIZE'then ps_ids else m_ids end)),
   ok as(select x from gr where x->>'model_id'=p_model::text and x->'qc_models'<@jsonb_build_array(p_model)
     and not exists(select 1 from jsonb_array_elements(x->'pools')p where p->'spent'<>'true'::jsonb)
     and x->>'finished_at'is not null and((x->>'finished_at')::timestamptz at time zone 'Asia/Jakarta')::date>=first_day),
   pl as(select o.x->>'group_id'g,p from ok o,jsonb_array_elements(o.x->'pools')p
     where lvl='MODEL'or(p->>'size_id'=size::text and jsonb_array_length(p->'qc_roots')>0 and p->'qc_roots'<@jsonb_build_array(root)))
   select count(distinct g),coalesce(sum((p->>'input_pcs')::numeric),0),coalesce(sum((p->>'fg_pcs')::numeric),0),
    coalesce((select jsonb_agg(jsonb_build_object('group_id',o.x->'group_id','proof_id',o.x->'proof'->'proof_id','facts_hash',o.x->'proof'->'facts_hash',
      'captured_at',o.x->'proof'->'captured_at','finished_at',o.x->'finished_at')order by o.x->>'group_id')
     from ok o where o.x->>'group_id'in(select g from pl)),'[]'::jsonb)
   into ng,cut,fg,used from pl;
   if ng>=pol.min_groups and cut>=pol.min_cut_pcs then
    k:=cp7_plan_native.wilson_permille(fg::bigint,cut::bigint);
    lv:=lv||jsonb_build_array(jsonb_build_object('level',lvl,'status',case when k>=1 then'SUFFICIENT'else'UNKNOWN'end,
     'reason',case when k<1 then 'LOWER_BOUND_BELOW_ONE_PERMILLE'end,'groups',ng::text,'cut_pcs',cut::text,'fg_pcs',fg::text,
     'raw_numerator',fg::text,'raw_denominator',cut::text,'lower_bound_permille',k::text));
    chosen:=jsonb_build_object('level',lvl,'groups',ng,'cut',cut,'fg',fg,'k',k,'proofs',used);
   else
    lv:=lv||jsonb_build_array(jsonb_build_object('level',lvl,'status','INSUFFICIENT_SAMPLE','reason','HISTORY_SAMPLE_BELOW_POLICY',
     'groups',ng::text,'cut_pcs',cut::text,'fg_pcs',fg::text,'raw_numerator',fg::text,'raw_denominator',cut::text,'lower_bound_permille',null));
   end if;
  end loop;
  if st is null then
   if chosen is not null and(chosen->>'k')::integer>=1 then st:='AVAILABLE';rs:='HISTORY_LOWER_BOUND_AT_POLICY';level:=chosen->>'level';
   elsif chosen is not null then st:='UNKNOWN';rs:='LOWER_BOUND_BELOW_ONE_PERMILLE';level:=chosen->>'level';
   elsif exists(select 1 from jsonb_array_elements(lv)x where x->>'status'='UNKNOWN')then st:='UNKNOWN';
    rs:=(select x->>'reason'from jsonb_array_elements(lv)x where x->>'status'='UNKNOWN'limit 1);
   else st:='INSUFFICIENT_SAMPLE';rs:='HISTORY_SAMPLE_BELOW_POLICY';end if;
  end if;
  stale_or_unverifiable:=unverified;
  select count(*)filter(where x->>'finished_at'is null or((x->>'finished_at')::timestamptz at time zone 'Asia/Jakarta')::date<first_day),
   count(*)filter(where x->>'model_id'is distinct from p_model::text or not x->'qc_models'<@jsonb_build_array(p_model)),
   count(*)filter(where exists(select 1 from jsonb_array_elements(x->'pools')p where p->'spent'<>'true'::jsonb))
   into outside,unattributed,not_spent from jsonb_array_elements(res)x;
 end if;
 if cp7_private.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.history-yield.v2','status',st,'reason',rs,'target_key',p_target,
  'root_id',root,'size_id',size,'model_id',p_model,'checked_at',clk,'window_first_day',first_day,'kernel_version',kernel,
  'basis','PL8_STORED_PROOF_MATCHING_CURRENT_FACTS',
  'policy',jsonb_build_object('id',pol.id,'revision',pol.revision::text,'state',pol.state,'window_days',pol.window_days::text,
   'min_groups',pol.min_groups::text,'min_cut_pcs',pol.min_cut_pcs::text,'confidence',pol.confidence,'actor_role',pol.actor_role,'recorded_at',pol.recorded_at),
  'window_days',pol.window_days::text,'minimum_sample',jsonb_build_object('groups',pol.min_groups::text,'cut_pcs',pol.min_cut_pcs::text),
  'level',level,'levels',lv,
  'groups',case when st='AVAILABLE'then chosen->>'groups'end,'cut_pcs',case when st='AVAILABLE'then chosen->>'cut'end,
  'fg_pcs',case when st='AVAILABLE'then chosen->>'fg'end,'lower_bound_permille',case when st='AVAILABLE'then chosen->>'k'end,
  'lower_bound',case when st='AVAILABLE'then trim_scale((chosen->>'k')::numeric/1000)::text end,
  'numerator',case when st='AVAILABLE'then chosen->>'k'end,'denominator',case when st='AVAILABLE'then '1000'end,
  'proofs',case when st='AVAILABLE'then chosen->'proofs'else'[]'::jsonb end,
  'excluded',case when kernel is null then null else jsonb_build_object('stale_or_unverifiable',coalesce(stale_or_unverifiable,0)::text,
   'outside_window',coalesce(outside,0)::text,'unattributed',coalesce(unattributed,0)::text,'not_spent_now',coalesce(not_spent,0)::text)end);
end $$;
