-- OW-01: one coherent current observation, not an authorization to buy.
-- No ERP mutation privilege is given to the capture/reminder roles.
create function cp7_reminder_native.accessory_category_locks(p_run uuid,p_target text)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare j uuid;root uuid;
begin
 perform cp7_schedule_native.access_now(false);
 if p_target!~'^[0-9a-f-]{36}:[0-9a-f-]{36}$'then raise exception 'CP7_REMINDER_V2_PAYLOAD';end if;
 select x.id into j from cp7_analysis_stage.jobs x where x.run_id=p_run and x.actor=auth.uid()and x.state='DONE';
 perform cp7_analysis_stage.require_kept(j);
 if j is null or(select count(*)from cp7_analysis_stage.plan_targets t where t.job_id=j and t.target_key=p_target)<>1 then
  raise exception using errcode='42501',message='CP7_REMINDER_V2_CONDITION_UNAVAILABLE';end if;
 root:=split_part(p_target,':',1)::uuid;
 -- Include future versions: a category wait can cross an effective boundary.
 perform c.id from erp.accessory_categories c where exists(
  select 1 from erp.accessory_bom_items i join erp.accessory_bom_versions v on v.id=i.bom_version_id
  where v.product_id=root and i.category_id=c.id)order by c.id for share of c;
end $$;
alter function cp7_reminder_native.accessory_category_locks(uuid,text)owner to postgres;
revoke all on function cp7_reminder_native.accessory_category_locks(uuid,text)from public,anon,authenticated,service_role,cp7_reminder;
grant execute on function cp7_reminder_native.accessory_category_locks(uuid,text)to cp7_capture;

create function cp7_reminder_native.accessory_capture(p_job uuid,p_target text,p_material text,p_index integer,p_at timestamptz)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare j cp7_analysis_stage.jobs%rowtype;mark cp7_analysis_stage.capture_marks%rowtype;r jsonb;sc jsonb;product jsonb;products jsonb;before_products jsonb;
 root uuid:=split_part(p_target,':',1)::uuid;size uuid:=split_part(p_target,':',2)::uuid;model uuid;skus uuid[];policy jsonb;
 fg numeric;ids uuid[];n integer;bi integer:=1;part jsonb;norm jsonb;wip numeric:=0;wip_status text:='COMPLETE';wip_reason text;
 profiles jsonb;before_profiles jsonb;schedule jsonb;ms jsonb;before_ms jsonb;binding_same boolean;plans bigint;original jsonb;originals jsonb;pg cp7_analysis_stage.pages%rowtype;target_ord integer;
 selected jsonb;category jsonb;review_reason text;wip_snap text;
begin
 select *into j from cp7_analysis_stage.jobs x where x.id=p_job and x.actor=auth.uid()and x.state='DONE';
 if j.id is null then raise exception using errcode='42501',message='CP7_REMINDER_V2_SNAPSHOT_UNAVAILABLE';end if;
 if(select count(*)from cp7_analysis_stage.plan_targets t where t.job_id=j.id and t.target_key=p_target)<>1 then
  raise exception using errcode='42501',message='CP7_REMINDER_V2_CONDITION_UNAVAILABLE';end if;
 select t.row,t.ord into r,target_ord from cp7_analysis_stage.plan_targets t where t.job_id=j.id and t.target_key=p_target;
 select t.scope into sc from cp7_analysis_stage.plan_scope t where t.job_id=j.id;
 select *into mark from cp7_analysis_stage.capture_marks x where x.job_id=j.id;
 if sc is null or mark.job_id is null then raise exception 'CP7_REMINDER_V2_SNAPSHOT_INDEX_MISSING';end if;
 select coalesce(jsonb_agg(x order by x->>'id'),'[]')into before_products from jsonb_array_elements(r->'products')x
  where x->>'root_id'=root::text and x->>'size_id'=size::text;
 if jsonb_array_length(before_products)=1 then product:=before_products->0;model:=(product->>'model_id')::uuid;end if;
 select coalesce(jsonb_agg(to_jsonb(q)order by q.id),'[]')into products from(
  select p.id,coalesce(p.identity_root_id,p.id)root_id,p.size_id,p.model_id,p.brand_id,p.sku,p.product_name,p.is_active,
   p.effective_from,p.effective_to,p.created_at,
   (select min(p0.created_at)from erp.products p0 where coalesce(p0.identity_root_id,p0.id)=root)established_at,
   coalesce((select jsonb_agg(jsonb_build_object('sku_id',s.id,'sku',s.sku,'version_id',v.id,'revision',v.revision::text)order by v.id)
    from erp.bf_sku_members_v1 m join erp.bf_sku_versions_v1 v on v.id=m.version_id join erp.bf_skus_v1 s on s.id=v.sku_id
    where m.product_root=root and v.effective_from<=p_at and(v.effective_to is null or v.effective_to>p_at)),'[]')commercial
  from erp.products p where coalesce(p.identity_root_id,p.id)=root and p.effective_from<=p_at and(p.effective_to is null or p.effective_to>p_at))q;
 select coalesce(array_agg(distinct v.sku_id order by v.sku_id),'{}')into skus from erp.bf_sku_members_v1 m join erp.bf_sku_versions_v1 v on v.id=m.version_id
  where m.product_root=root and v.effective_from<=p_at and(v.effective_to is null or v.effective_to>p_at);
 select x.v into policy from jsonb_array_elements(cp7_identity.workspace_data(skus,p_at)->'rows')with ordinality x(v,o)
  where jsonb_typeof(x.v->'members')='array'and(x.v->'members')?root::text order by x.o limit 1;
 profiles:=cp7_profile.source(array[root],p_at);
 select coalesce(jsonb_agg(x order by x->>'root_id',x->>'product_version_id'),'[]')into before_profiles
  from jsonb_array_elements(j.reference->'profiles')x where x->>'root_id'=root::text;
 schedule:=cp7_schedule_native.source_at(p_at);
 ms:=(cp7_analysis_stage.material_scope(jsonb_build_object('material_source',cp7_analysis_native.material_source(products,p_at)),array[p_target])->'material_source')-'captured_at';
 before_ms:=(cp7_analysis_stage.material_scope(j.reference,array[p_target])->'material_source')-'captured_at';
 binding_same:=products=before_products and policy is not distinct from r->'production_policy'
  and profiles=before_profiles and schedule is not distinct from j.reference->'schedule'and ms=before_ms;
 select coalesce(sum(m.qty_signed),0)into fg from erp.fg_stock_movements m join erp.products p on p.id=m.product_id
  where coalesce(p.identity_root_id,p.id)=root and m.quality_grade in('GRADE_A','GRADE_B')and m.physical_at<=p_at and m.system_created_at<=p_at;
 if model is null then wip_status:='UNKNOWN';wip_reason:='SNAPSHOT_MODEL_UNKNOWN';
 else
  select coalesce(array_agg(x.id order by x.id),'{}'),count(*)into ids,n from(
   select g.id from erp.cutting_groups g join erp.production_orders po on po.id=g.po_id
   where po.model_id=model and g.material_issue_posted and g.cut_at<=p_at
    and not exists(select 1 from cp7_analysis_stage.plan_groups x where x.job_id=j.id and x.group_id=g.id::text and x.scope='EXHAUSTED')
   order by g.id limit 201)x;
  if n>200 then wip_status:='UNKNOWN';wip_reason:='MODEL_WIP_GROUP_LIMIT';end if;
  while wip_status='COMPLETE'and bi<=n loop
   part:=cp7_wip.capture_cutting_sources(ids[bi:least(bi+49,n)],p_at);
   if part->>'status'is distinct from'COMPLETE'then wip_status:='UNKNOWN';wip_reason:='WIP_SOURCE_INCOMPLETE';exit;end if;
   begin norm:=cp7_wip.normalize_cutting(part);
   exception when others then norm:=jsonb_build_object('status','UNKNOWN','reason','WIP_NORMALIZATION_REFUSED');end;
   if norm->>'status'is distinct from'COMPLETE'then wip_status:='UNKNOWN';wip_reason:=coalesce(norm->>'reason','WIP_NOT_COMPLETE');exit;end if;
   wip:=wip+(select coalesce(sum((x->>'wip_pcs')::numeric),0)from jsonb_array_elements(norm->'totals')x
    where x->>'pool_key'like'CUT:%'and x->>'ownership'='COMPANY'and x->>'size_id'=size::text);
   bi:=bi+50;
  end loop;
 end if;
 select count(*)into plans from cp7_plan_native.intents i where i.target_key=p_target
  and cp7_plan_native.after_snapshot(i.xmin,i.recorded_at,j.captured_at,mark.source_snapshot);
 select *into pg from cp7_analysis_stage.pages x where x.run_id=j.run_id and x.idx=p_index;
 if pg.run_id is null or target_ord not between pg.target_lo and pg.target_hi
  or((pg.body::jsonb)->>'target_lo')::integer is distinct from pg.target_lo
  or((pg.body::jsonb)->>'target_hi')::integer is distinct from pg.target_hi or(pg.body::jsonb)->>'run_id'is distinct from j.run_id::text or((pg.body::jsonb)->>'index')::integer is distinct from pg.idx
  or jsonb_array_length((pg.body::jsonb)#>'{items,material_needs}')is distinct from(pg.counts->>'material_needs')::integer then
  raise exception 'CP7_REMINDER_V2_SNAPSHOT_INVARIANT';end if;
 select coalesce(jsonb_agg(x),'[]')into originals from jsonb_array_elements((pg.body::jsonb)#>'{items,material_needs}')x
  where x->>'target_key'=p_target and x->>'material_key'is not distinct from p_material;
 if jsonb_array_length(originals)<>1 then raise exception 'CP7_REMINDER_V2_SNAPSHOT_INVARIANT';end if;original:=originals->0;
 select x into selected from jsonb_array_elements(ms->'selected')x where x->>'root_id'=root::text;
 select x into category from jsonb_array_elements(ms->'categories')x where 'ACCESSORY_CATEGORY:'||(x->>'id')=p_material;
 review_reason:=case when selected is null or(selected->>'effective_version_count')::integer=0 then'BOM_NOT_RECORDED'
  when(selected->>'effective_version_count')::integer>1 then'BOM_AMBIGUOUS'
  when p_material like'ACCESSORY_CATEGORY:%'and(category is null or category->'is_active'is distinct from'true'::jsonb)then'CATEGORY_UNAVAILABLE'
  else'INSTALLATION_AND_ELIGIBLE_UNUSED_SUPPLY_NOT_PROVEN'end;
 wip_snap:=case when sc->>'wip_status'='COMPLETE'and product is not null then
  coalesce(sc->'wip_by_model_size'->>((product->>'model_id')||':'||(product->>'size_id')),'0')end;
 return jsonb_build_object('checked_at',p_at,'data_as_of',j.captured_at,'binding_unchanged',coalesce(binding_same,false),
  'original',original,'category',category,'review_reason',review_reason,'target_plans_after',plans,
  'snapshot',jsonb_build_object('need_pcs',r->'conditional_gap_pcs','available_fg_pcs',r->'available_fg_pcs','wip_status',sc->'wip_status',
   'wip_model_size_pcs',wip_snap,'product',product,'production_state',r->'production_policy'->'policy'->'state'),
  'live',jsonb_build_object('products',products,'policy_state',policy->'policy'->'state','policy_quality',policy->'policy'->'quality',
   'fg_pcs',fg::text,'wip',jsonb_build_object('status',wip_status,'reason',wip_reason,'pcs',case when wip_status='COMPLETE'then wip::text end)));
end $$;
alter function cp7_reminder_native.accessory_capture(uuid,text,text,integer,timestamptz)owner to cp7_capture;
revoke all on function cp7_reminder_native.accessory_capture(uuid,text,text,integer,timestamptz)from public,anon,authenticated,service_role,cp7_reminder;

create function cp7_reminder_native.accessory_target_now(p_run uuid,p_target text,p_material text,p_index integer)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;j uuid;r jsonb;root uuid;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 if p_target!~'^[0-9a-f-]{36}:[0-9a-f-]{36}$'or p_material is not null and p_material!~'^[A-Za-z0-9_:-]{1,200}$'then raise exception 'CP7_REMINDER_V2_PAYLOAD';end if;
 select x.id into j from cp7_analysis_stage.jobs x where x.run_id=p_run and x.actor=auth.uid()and x.state='DONE';
 perform cp7_analysis_stage.require_kept(j);
 if j is null or(select count(*)from cp7_analysis_stage.plan_targets t where t.job_id=j and t.target_key=p_target)<>1 then
  raise exception using errcode='42501',message='CP7_REMINDER_V2_CONDITION_UNAVAILABLE';end if;
 root:=split_part(p_target,':',1)::uuid;
 perform pg_advisory_xact_lock_shared(hashtextextended('FG_HPP_SALES_V2620C',0));
 perform pg_advisory_xact_lock_shared(hashtextextended('BF:COMMERCIAL_SKUS',0));
 perform pg_advisory_xact_lock_shared(hashtextextended('CP7:PROFILE:ROOT:'||root::text,0));
 perform pg_advisory_xact_lock_shared(hashtextextended('CP7:SCHEDULE:GLOBAL',0));
 perform pg_advisory_xact_lock_shared(hashtextextended('CP7:RULE_POLICY:ACCESSORY_NEED:GLOBAL:*',0));
 perform pg_advisory_xact_lock_shared(hashtextextended('CP7:RULE_POLICY:ACCESSORY_NEED:TARGET:'||p_target,0));
 perform cp7_reminder_native.accessory_category_locks(p_run,p_target);
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_CHANGED';end if;
 select cp7_reminder_native.accessory_capture(j,p_target,p_material,p_index,clock_timestamp())into r;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_CHANGED';end if;
 return r;
end $$;
alter function cp7_reminder_native.accessory_target_now(uuid,text,text,integer)owner to cp7_capture;
revoke all on function cp7_reminder_native.accessory_target_now(uuid,text,text,integer)from public,anon,authenticated,service_role;
grant execute on function cp7_reminder_native.accessory_target_now(uuid,text,text,integer)to cp7_reminder;
