-- Current authorization and own unchanged analysis Original, rechecked after
-- actual per-target serialization. Only private recipe metadata is written.
create function cp7_fabric_native.workspace(q jsonb)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;e jsonb;r jsonb;recipes jsonb;materials jsonb;patterns jsonb;n integer;mo integer;po integer;
 mc bigint;pc bigint;term text;latest bigint;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 perform cp7_wip.fields(q,array['run_id','target_key','material_query','material_offset','pattern_offset','limit']);
 if jsonb_typeof(q->'material_query')is distinct from'string'or length(q->>'material_query')>200 then raise exception 'CP7_FABRIC_QUERY';end if;
 n:=cp7_wip.pcs(q->'limit');mo:=cp7_wip.pcs(q->'material_offset');po:=cp7_wip.pcs(q->'pattern_offset');
 if n not between 1 and 50 or greatest(mo,po)>1000000 then raise exception 'CP7_FABRIC_QUERY';end if;
 e:=cp7_analysis_native.serve((q->>'run_id')::uuid);
 if e->>'source_state'<>'UNCHANGED'then raise exception using errcode='40001',message='CP7_FABRIC_ANALYSIS_CHANGED';end if;
 select x into r from jsonb_array_elements(e->'analysis'->'recommendations')x where x->'target'->>'key'=q->>'target_key';
 if r is null or r->'target'->>'kind'<>'PRODUCT'then raise exception 'CP7_FABRIC_TARGET';end if;
 term:=lower(btrim(q->>'material_query'));
 select count(*)into mc from erp.materials m where m.is_active and m.material_type='FABRIC'
  and(term=''or strpos(lower(m.material_sku||' '||m.material_name),term)>0);
 select coalesce(jsonb_agg(jsonb_build_object('id',x.id,'sku',x.material_sku,'name',x.material_name,'unit',x.unit_code,
  'source_hash',cp7_fabric_native.material_hash(to_jsonb(x)))order by x.material_sku,x.id),'[]')into materials
  from(select *from erp.materials m where m.is_active and m.material_type='FABRIC'
   and(term=''or strpos(lower(m.material_sku||' '||m.material_name),term)>0)order by m.material_sku,m.id limit n offset mo)x;
 select count(*)into pc from erp.production_patterns where is_active;
 select coalesce(jsonb_agg(jsonb_build_object('id',x.id,'code',x.pattern_code,'name',x.pattern_name,'revision',x.revision::text,
  'source_hash',encode(extensions.digest(convert_to(to_jsonb(x)::text,'UTF8'),'sha256'),'hex'))order by x.pattern_code,x.revision,x.id),'[]')into patterns
  from(select *from erp.production_patterns where is_active order by pattern_code,revision,id limit n offset po)x;
 select coalesce(max(revision),0)into latest from cp7_fabric_native.recipes where target_key=q->>'target_key';
 select coalesce(jsonb_agg(jsonb_build_object('id',x.id,'revision',x.revision::text,'config',x.config,'reason',x.reason,
  'recorded_at',x.recorded_at)order by x.revision desc),'[]')into recipes
  from(select *from cp7_fabric_native.recipes where target_key=q->>'target_key'order by revision desc limit 50)x;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_FABRIC_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.fabric-workspace.v1','actor_scope_id',a->>'actor',
  'run_id',q->'run_id','target_key',q->'target_key','source_hash',e->'analysis'->'snapshot'->'source_hash',
  'revision',latest::text,'analysis',e,'materials',materials,'patterns',patterns,'recipes',recipes,
  'page',jsonb_build_object('limit',n,'material_offset',mo,'material_total',mc::text,'pattern_offset',po,'pattern_total',pc::text,
   'recipe_total',latest::text,'recipe_history_scope','LATEST_50_REVISIONS'),
  'apply_enabled',false,'production_go',false);
end $$;

create function cp7_fabric_native.save(p_payload jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;old cp7_fabric_native.commands%rowtype;recipe cp7_fabric_native.recipes%rowtype;
 e jsonb;target jsonb;cfg jsonb;catalog jsonb;revision bigint;expected numeric;reason text;outcome jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(true);if p_request is null then raise exception 'CP7_FABRIC_REQUEST_REQUIRED';end if;
 perform cp7_wip.fields(p_payload,array['run_id','target_key','source_hash','expected_revision','config','reason']);
 perform cp7_wip.key(p_payload->'target_key');
 perform pg_advisory_xact_lock(hashtextextended('CP7:FABRIC:REQUEST:'||(a->>'actor')||':'||p_request::text,0));
 if cp7_schedule_native.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_FABRIC_ACCESS_CHANGED';end if;
 select *into old from cp7_fabric_native.commands where actor=(a->>'actor')::uuid and request_id=p_request;
 if found then
  if old.payload<>p_payload then raise exception 'CP7_FABRIC_REQUEST_CHANGED';end if;return old.result;
 end if;
 expected:=cp7_wip.pcs(p_payload->'expected_revision');
 if expected>=9223372036854775807 or jsonb_typeof(p_payload->'source_hash')is distinct from'string'
  or p_payload->>'source_hash'!~'^[0-9a-f]{64}$'then raise exception 'CP7_FABRIC_REVIEW';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:FABRIC:TARGET:'||(p_payload->>'target_key'),0));
 if cp7_schedule_native.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_FABRIC_ACCESS_CHANGED';end if;
 select coalesce(max(x.revision),0)into revision from cp7_fabric_native.recipes x where x.target_key=p_payload->>'target_key';
 if revision<>expected then raise exception using errcode='40001',message='CP7_FABRIC_REVISION_CHANGED';end if;
 e:=cp7_analysis_native.serve((p_payload->>'run_id')::uuid);
 if e->>'source_state'<>'UNCHANGED'or e->'analysis'->'snapshot'->>'source_hash'<>p_payload->>'source_hash'
  or e->'analysis'->'snapshot'->'capture_complete'<>'true'::jsonb then
  raise exception using errcode='40001',message='CP7_FABRIC_ANALYSIS_CHANGED';end if;
 if e->'analysis'->'versions'->>'access_epoch'is distinct from encode(extensions.digest(convert_to(a::text,'UTF8'),'sha256'),'hex')then
  raise exception using errcode='42501',message='CP7_FABRIC_ORIGINAL_ACCESS_CHANGED';end if;
 select x into target from jsonb_array_elements(e->'analysis'->'recommendations')x where x->'target'->>'key'=p_payload->>'target_key';
 if target is null or target->'target'->>'kind'<>'PRODUCT'then raise exception 'CP7_FABRIC_TARGET';end if;
 -- Read every field of each selected Native master after the real lock wait.
 select jsonb_build_object('materials',coalesce((select jsonb_agg(to_jsonb(m))from erp.materials m
  where m.id::text=p_payload->'config'->>'material_id'),'[]'),
  'patterns',coalesce((select jsonb_agg(to_jsonb(p))from erp.production_patterns p
  where p.id::text=p_payload->'config'->>'pattern_id'),'[]'))into catalog;
 cfg:=cp7_fabric_native.validate(p_payload->'config',catalog);
 if(cfg->>'effective_from')::timestamptz<clock_timestamp()-interval'1 year'then raise exception 'CP7_FABRIC_BACKDATE_LIMIT';end if;
 reason:=btrim(p_payload->>'reason');
 if jsonb_typeof(p_payload->'reason')is distinct from'string'or reason is null or length(reason)not between 1 and 1000 then raise exception 'CP7_FABRIC_REASON';end if;
 insert into cp7_fabric_native.recipes(target_key,revision,source_run,source_hash,config,reason,actor,request_id)
  values(p_payload->>'target_key',revision+1,(p_payload->>'run_id')::uuid,p_payload->>'source_hash',cfg,reason,(a->>'actor')::uuid,p_request)returning *into recipe;
 outcome:=jsonb_build_object('contract_version','cp7.fabric-outcome.v1','actor_scope_id',a->>'actor','request_id',p_request,
  'recipe_id',recipe.id,'target_key',recipe.target_key,'revision',recipe.revision::text,
  'quality','SELECTED_ASSUMPTIONS','apply_enabled',false,'production_go',false);
 insert into cp7_fabric_native.commands(actor,request_id,payload,result)values((a->>'actor')::uuid,p_request,p_payload,outcome);
 if cp7_schedule_native.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_FABRIC_ACCESS_CHANGED';end if;
 return outcome;
end $$;
alter function cp7_fabric_native.workspace(jsonb)owner to cp7_capture;
alter function cp7_fabric_native.save(jsonb,uuid)owner to cp7_capture;
revoke all on all functions in schema cp7_fabric_native from public,anon,authenticated,service_role;
grant create on schema public to cp7_capture;
create function public.erp_cp7_get_fabric_recipe_v1(p_query jsonb)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_fabric_native.workspace(p_query)$$;
create function public.erp_cp7_save_fabric_recipe_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_fabric_native.save(p_payload,p_request)$$;
alter function public.erp_cp7_get_fabric_recipe_v1(jsonb)owner to cp7_capture;
alter function public.erp_cp7_save_fabric_recipe_v1(jsonb,uuid)owner to cp7_capture;
revoke create on schema public from cp7_capture;
revoke all on function public.erp_cp7_get_fabric_recipe_v1(jsonb),public.erp_cp7_save_fabric_recipe_v1(jsonb,uuid)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_fabric_recipe_v1(jsonb),public.erp_cp7_save_fabric_recipe_v1(jsonb,uuid)to authenticated;
