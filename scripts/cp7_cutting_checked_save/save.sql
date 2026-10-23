-- Same retained plan engine, with a stricter SAVE for the cutting form only.
-- The old archive-plan save and its dated-snapshot contract remain unchanged.
create function cp7_cutting_checked.source_now(p_run uuid,p_target text)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;s jsonb;c jsonb;
begin
 a:=cp7_private.access_now();
 s:=cp7_plan_native.staged_source(p_run,p_target);
 c:=cp7_analysis_stage.check_source(p_run);
 if c->>'source_state'is distinct from'UNCHANGED'then
  raise exception using errcode='40001',message='CP7_CUTTING_SUGGESTION_SOURCE_CHANGED',
   hint='Ambil analisis terbaru sebelum menyimpan saran Potongan.';
 end if;
 if cp7_private.access_now()is distinct from a then
  raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';
 end if;
 return jsonb_build_object('run_id',p_run,'target_key',p_target,'identity_hash',s->'identity_hash',
  'source_hash',s->'source_hash','data_as_of',s->'data_as_of','checked_at',c->'checked_at');
end $$;
alter function cp7_cutting_checked.source_now(uuid,text)owner to cp7_capture;
revoke all on function cp7_cutting_checked.source_now(uuid,text)from public,anon,authenticated,service_role;
grant execute on function cp7_cutting_checked.source_now(uuid,text)to cp7_plan_writer;

create function cp7_cutting_checked.save(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;old cp7_cutting_checked.receipts%rowtype;prior cp7_plan_native.drafts%rowtype;
 body jsonb;checked jsonb;again jsonb;preview jsonb;native jsonb;result jsonb;k uuid;first_code text;
begin
 a:=cp7_plan_native.access_now('DRAFT');
 if p_request is null or jsonb_typeof(p)is distinct from'object'
  or p->>'cutting_save_contract'is distinct from'cp7.cutting-checked-save.v1' then
  raise exception 'CP7_CUTTING_SUGGESTION_REQUEST';
 end if;
 body:=p-'cutting_save_contract';
 -- The same request lock as the old save prevents cross-route UUID reuse.
 perform pg_advisory_xact_lock(hashtextextended('CP7:PLAN_SAVE:'||(a->>'actor')||':'||p_request::text,0));
 if cp7_plan_native.access_now('DRAFT')is distinct from a then
  raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';
 end if;
 select *into old from cp7_cutting_checked.receipts where actor=(a->>'actor')::uuid and request_id=p_request;
 if found then
  if old.payload<>p then raise exception 'CP7_PLAN_REQUEST_CHANGED';end if;
  if cp7_plan_native.access_now('DRAFT')is distinct from a then
   raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';
  end if;
  return old.result;
 end if;
 if exists(select 1 from cp7_plan_native.drafts where actor=(a->>'actor')::uuid and request_id=p_request)then
  raise exception 'CP7_PLAN_REQUEST_CHANGED';
 end if;
 -- Same ordering as apply: request, sorted rolls, shared capacity, target,
 -- plan version. A saved plan creates no stock reservation or physical fact.
 for k in select distinct(x->>'roll_id')::uuid from jsonb_array_elements(body#>'{cutting,rolls}')x order by 1 loop
  perform pg_advisory_xact_lock(hashtextextended('CP7:PLAN_MATERIAL_POOL:'||k::text,0));
 end loop;
 perform pg_advisory_xact_lock(hashtextextended('CP7:PLAN_CAPACITY',0));
 perform pg_advisory_xact_lock(hashtextextended('CP7:PLAN_TARGET:'||(body->>'target_key'),0));
 if body->>'plan_id'is not null then
  perform pg_advisory_xact_lock(hashtextextended('CP7:PLAN_VERSION:'||(body->>'plan_id'),0));
  select *into prior from cp7_plan_native.drafts where plan_id=(body->>'plan_id')::uuid
   and actor=(a->>'actor')::uuid order by revision desc limit 1;
 end if;
 if cp7_plan_native.access_now('DRAFT')is distinct from a then
  raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';
 end if;
 checked:=cp7_cutting_checked.source_now((body->>'run_id')::uuid,body->>'target_key');
 if checked->>'identity_hash'is distinct from body->>'identity_hash'then raise exception 'CP7_PLAN_REVIEW';end if;
 preview:=cp7_plan_native.preflight_v2(body,'PREVIEW',prior.id);
 if preview#>'{live,apply_ready}'is distinct from'true'::jsonb then
  select x->>'code'into first_code from jsonb_array_elements(preview#>'{live,verdicts}')x
   where x->>'status'<>'OK'and x->>'code'is not null limit 1;
  raise exception using errcode='40001',message=coalesce(first_code,'CP7_CUTTING_SUGGESTION_NOT_FEASIBLE');
 end if;
 if cp7_plan_native.access_now('DRAFT')is distinct from a then
  raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';
 end if;
 native:=cp7_plan_native.save_v2(body,p_request);
 -- Recheck after the delegated writer's last possible lock wait. Any refusal
 -- rolls its draft, its revision and our receipt back together.
 again:=cp7_cutting_checked.source_now((body->>'run_id')::uuid,body->>'target_key');
 if(again-'checked_at')is distinct from(checked-'checked_at')then
  raise exception using errcode='40001',message='CP7_CUTTING_SUGGESTION_SOURCE_CHANGED';
 end if;
 preview:=cp7_plan_native.preflight_v2(body,'PREVIEW',(native->>'draft_id')::uuid);
 if preview#>'{live,apply_ready}'is distinct from'true'::jsonb then
  raise exception using errcode='40001',message='CP7_CUTTING_SUGGESTION_NOT_FEASIBLE';
 end if;
 if cp7_plan_native.access_now('DRAFT')is distinct from a then
  raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';
 end if;
 result:=native||jsonb_build_object('cutting_save_guard',jsonb_build_object(
  'contract_version','cp7.cutting-checked-save.v1','run_id',body->'run_id','target_key',body->'target_key',
  'identity_hash',body->'identity_hash','checked_at',again->'checked_at','feasible',true));
 insert into cp7_cutting_checked.receipts(actor,request_id,payload,result,draft_id)
 values((a->>'actor')::uuid,p_request,p,result,(native->>'draft_id')::uuid);
 return result;
end $$;
alter function cp7_cutting_checked.save(jsonb,uuid)owner to cp7_plan_writer;
revoke all on function cp7_cutting_checked.save(jsonb,uuid)from public,anon,authenticated,service_role,cp7_capture;
create function public.erp_cp7_save_cutting_suggestion_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'as $$
 select cp7_cutting_checked.save(p_payload,p_request)
$$;
grant create on schema public to cp7_plan_writer;
alter function public.erp_cp7_save_cutting_suggestion_v1(jsonb,uuid)owner to cp7_plan_writer;
revoke create on schema public from cp7_plan_writer;
revoke all on function public.erp_cp7_save_cutting_suggestion_v1(jsonb,uuid)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_save_cutting_suggestion_v1(jsonb,uuid)to authenticated;
