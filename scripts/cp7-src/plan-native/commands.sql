create function cp7_plan_native.save(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r cp7_plan_native.drafts%rowtype;preview jsonb;plan uuid;revision bigint;expected bigint;
begin
 a:=cp7_plan_native.access_now('DRAFT');if p_request is null then raise exception 'CP7_PLAN_REQUEST';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:PLAN_SAVE:'||(a->>'actor')||':'||p_request::text,0));
 if cp7_plan_native.access_now('DRAFT')is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
 select *into r from cp7_plan_native.drafts where actor=(a->>'actor')::uuid and request_id=p_request;
 if found then if r.payload<>p then raise exception 'CP7_PLAN_REQUEST_CHANGED';end if;return jsonb_build_object('contract_version','cp7.plan-draft.v1','actor_scope_id',a->>'actor','draft_id',r.id,'plan_id',r.plan_id,'revision',r.revision::text,'run_id',r.run_id,'target_key',r.target_key,'request_id',p_request,'state','SAVED','reservation_created',false,'production_go',false);end if;
 perform cp7_plan_native.fields(p,array['run_id','target_key','plan_id','expected_revision','source_hash','cutting','reviewed_assumption_ids','reason']
  ||case when p?'new_start_yield'then array['new_start_yield']else'{}'::text[]end);
 if p->'plan_id'='null'::jsonb then
  if p->'expected_revision'<>'null'::jsonb then raise exception 'CP7_PLAN_REVISION';end if;plan:=gen_random_uuid();revision:=1;
 else
  if jsonb_typeof(p->'plan_id')<>'string'or jsonb_typeof(p->'expected_revision')<>'string'or p->>'expected_revision'!~'^[1-9][0-9]{0,14}$'then raise exception 'CP7_PLAN_REVISION';end if;
  plan:=(p->>'plan_id')::uuid;expected:=(p->>'expected_revision')::bigint;
  perform pg_advisory_xact_lock(hashtextextended('CP7:PLAN_VERSION:'||plan::text,0));
  if cp7_plan_native.access_now('DRAFT')is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
  select *into r from cp7_plan_native.drafts where plan_id=plan and actor=(a->>'actor')::uuid order by revision desc limit 1;
  if r.id is null or r.revision<>expected or r.target_key<>p->>'target_key'then raise exception using errcode='40001',message='CP7_PLAN_REVISION_CHANGED';end if;
  if exists(select 1 from cp7_plan_native.intents where draft_id in(select id from cp7_plan_native.drafts where plan_id=plan))then raise exception 'CP7_PLAN_ALREADY_APPLIED';end if;revision:=expected+1;
 end if;
 preview:=cp7_plan_native.preflight(p);
 if cp7_plan_native.access_now('DRAFT')is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
 insert into cp7_plan_native.drafts(plan_id,revision,actor,request_id,payload,run_id,target_key,source_hash,core_hash,composition_hash)
 values(plan,revision,(a->>'actor')::uuid,p_request,p,(p->>'run_id')::uuid,p->>'target_key',preview->>'source_hash',preview->>'core_hash',preview->>'composition_hash')returning *into r;
 return jsonb_build_object('contract_version','cp7.plan-draft.v1','actor_scope_id',a->>'actor','draft_id',r.id,'plan_id',r.plan_id,'revision',r.revision::text,'run_id',r.run_id,'target_key',r.target_key,'request_id',p_request,'state','SAVED','reservation_created',false,'production_go',false);
end $$;
create function cp7_plan_native.preview(p_draft uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r cp7_plan_native.drafts%rowtype;outcome jsonb;
begin
 a:=cp7_plan_native.access_now('READ');select *into r from cp7_plan_native.drafts where id=p_draft and actor=(a->>'actor')::uuid;
 if r.id is null then raise exception using errcode='42501',message='CP7_PLAN_DRAFT_UNAVAILABLE';end if;
 if r.revision<>(select max(revision)from cp7_plan_native.drafts where plan_id=r.plan_id)then raise exception using errcode='40001',message='CP7_PLAN_REVISION_CHANGED';end if;
 outcome:=cp7_plan_native.preflight(r.payload)-'native_payload';
 if outcome->>'composition_hash'<>r.composition_hash then raise exception using errcode='40001',message='CP7_PLAN_NATIVE_SELECTION_CHANGED';end if;
 if cp7_plan_native.access_now('READ')is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
 return outcome||jsonb_build_object('draft_id',r.id,'plan_id',r.plan_id,'revision',r.revision::text,'actor_scope_id',a->>'actor');
end $$;
create function cp7_plan_native.apply(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;old cp7_plan_native.commands%rowtype;r cp7_plan_native.drafts%rowtype;preview jsonb;native jsonb;outcome jsonb;k uuid;used numeric;
begin
 a:=cp7_plan_native.access_now('APPLY');perform cp7_plan_native.fields(p,array['draft_id','expected_revision','explicit_review','reason']);
 if p_request is null or jsonb_typeof(p->'draft_id')<>'string'or jsonb_typeof(p->'expected_revision')<>'string'
  or p->>'expected_revision'!~'^[1-9][0-9]{0,14}$'or p->'explicit_review'is distinct from'true'::jsonb
  or jsonb_typeof(p->'reason')<>'string'or length(btrim(p->>'reason'))not between 1 and 1000 then raise exception 'CP7_PLAN_EXPLICIT_REVIEW';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:PLAN_APPLY_REQUEST:'||(a->>'actor')||':'||p_request::text,0));
 if cp7_plan_native.access_now('APPLY')is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
 select *into old from cp7_plan_native.commands where actor=(a->>'actor')::uuid and request_id=p_request;
 if found then if old.payload<>p then raise exception 'CP7_PLAN_REQUEST_CHANGED';end if;return old.result;end if;
 select *into r from cp7_plan_native.drafts where id=(p->>'draft_id')::uuid and actor=(a->>'actor')::uuid;
 if r.id is null then raise exception using errcode='42501',message='CP7_PLAN_DRAFT_UNAVAILABLE';end if;
  -- Acquire shared physical-roll budgets in one order before target/version
  -- locks. Distinct targets cannot both offer the same remaining roll in full.
  for k in select distinct(x->>'roll_id')::uuid from jsonb_array_elements(r.payload->'cutting'->'rolls')x order by 1 loop
   perform pg_advisory_xact_lock(hashtextextended('CP7:PLAN_MATERIAL_POOL:'||k::text,0));
  end loop;
  if cp7_plan_native.access_now('APPLY')is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
 -- P20 F01: the one shared capacity centre, under the same lock and in the same
 -- order as apply_v2 (request, rolls, capacity, target, version). A v1 or v2
 -- apply that is still uncommitted holds it, so the other version waits and
 -- then counts that plan's committed intent below.
 perform pg_advisory_xact_lock(hashtextextended('CP7:PLAN_CAPACITY',0));
 if cp7_plan_native.access_now('APPLY')is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
  -- Same canonical target lock for every actor, draft, run and UUID. The Native
 -- roll locks retain their own unchanged ordering inside the domain command.
 perform pg_advisory_xact_lock(hashtextextended('CP7:PLAN_TARGET:'||r.target_key,0));
 perform pg_advisory_xact_lock(hashtextextended('CP7:PLAN_VERSION:'||r.plan_id::text,0));
 if cp7_plan_native.access_now('APPLY')is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
 if r.revision::text<>p->>'expected_revision'or r.revision<>(select max(revision)from cp7_plan_native.drafts where plan_id=r.plan_id)then raise exception using errcode='40001',message='CP7_PLAN_REVISION_CHANGED';end if;
 if exists(select 1 from cp7_plan_native.intents where draft_id=r.id)then raise exception 'CP7_PLAN_ALREADY_APPLIED';end if;
 -- Bound Native PO/pattern/location/current roll lifecycle and ledger amount are
 -- re-read after every potentially blocking canonical lock and before writing.
 preview:=cp7_plan_native.preflight(r.payload);
 if preview->>'composition_hash'<>r.composition_hash then raise exception using errcode='40001',message='CP7_PLAN_NATIVE_SELECTION_CHANGED';end if;
 if cp7_plan_native.access_now('APPLY')is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
 -- P20 F01: capacity left after every other plan (v1 or v2) whose Native cutting
 -- group is still an unposted draft: such cuts are not in any Original's load.
 -- A posted group was in this Original's load or changed its source (refused
 -- above); a deleted Native draft uses none.
 select coalesce(sum((yy.value->>'qty_pcs')::numeric),0)into used from cp7_plan_native.intents i
  join erp.cutting_groups g on g.id=i.cutting_group_id join cp7_plan_native.drafts d on d.id=i.draft_id
  cross join lateral jsonb_array_elements(d.payload#>'{cutting,rolls}')rr(value)cross join lateral jsonb_array_elements(rr.value->'yields')yy(value)
  where i.draft_id<>r.id and not g.material_issue_posted;
 if(preview->>'selected_new_pcs')::numeric>(preview->>'free_capacity_pcs')::numeric-used then raise exception using errcode='40001',message='CP7_PLAN_CAPACITY_USED',
  detail=jsonb_build_object('capacity_pcs',preview->'free_capacity_pcs','capacity_used_by_other_plans_pcs',used::text,
   'capacity_now_pcs',((preview->>'free_capacity_pcs')::numeric-used)::text,'selected_new_pcs',preview->'selected_new_pcs')::text;end if;
 native:=public.erp_save_cutting_group_before_sewing_v2(preview->'native_payload',p_request,null);
 if native->'material_issue_posted'is distinct from'false'::jsonb then raise exception 'CP7_PLAN_DOMAIN_DRAFT_ONLY';end if;
 -- The Native writer can wait on real roll locks. Recheck its own Original
 -- after that wait, before recording an intent. A refusal rolls the Native
 -- draft back too; there is no domain commit without an atomic receipt.
 -- P08: the fabric physical source must not count this command's own new
 -- draft as a foreign change; everything else is still compared.
 insert into cp7_plan_native.apply_own_drafts(cutting_group_id)values((native->>'cutting_group_id')::uuid);
 preview:=cp7_plan_native.preflight(r.payload);
 delete from cp7_plan_native.apply_own_drafts where cutting_group_id=(native->>'cutting_group_id')::uuid;
 if preview->>'composition_hash'<>r.composition_hash then raise exception using errcode='40001',message='CP7_PLAN_NATIVE_SELECTION_CHANGED';end if;
 if cp7_plan_native.access_now('APPLY')is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
 -- P20 F01: the same capacity check again after the Native writer (it may wait on row locks).
 select coalesce(sum((yy.value->>'qty_pcs')::numeric),0)into used from cp7_plan_native.intents i
  join erp.cutting_groups g on g.id=i.cutting_group_id join cp7_plan_native.drafts d on d.id=i.draft_id
  cross join lateral jsonb_array_elements(d.payload#>'{cutting,rolls}')rr(value)cross join lateral jsonb_array_elements(rr.value->'yields')yy(value)
  where i.draft_id<>r.id and not g.material_issue_posted;
 if(preview->>'selected_new_pcs')::numeric>(preview->>'free_capacity_pcs')::numeric-used then raise exception using errcode='40001',message='CP7_PLAN_CAPACITY_USED',
  detail=jsonb_build_object('capacity_pcs',preview->'free_capacity_pcs','capacity_used_by_other_plans_pcs',used::text,
   'capacity_now_pcs',((preview->>'free_capacity_pcs')::numeric-used)::text,'selected_new_pcs',preview->'selected_new_pcs')::text;end if;
 insert into cp7_plan_native.intents(draft_id,actor,target_key,core_hash,cutting_group_id,request_id)
 values(r.id,(a->>'actor')::uuid,r.target_key,preview->>'core_hash',(native->>'cutting_group_id')::uuid,p_request)returning id into k;
 outcome:=jsonb_build_object('contract_version','cp7.plan-apply-outcome.v1','kind','COMMITTED_OUTCOME','actor_scope_id',a->>'actor',
  'request_id',p_request,'draft_id',r.id,'revision',r.revision::text,'intent_id',k,'target_key',r.target_key,'native',native,
  'state','NATIVE_DRAFT_CREATED','reservation_created',false,'physical_production_confirmed',false,'production_go',false);
 insert into cp7_plan_native.commands(actor,request_id,payload,result)values((a->>'actor')::uuid,p_request,p,outcome);return outcome;
end $$;
