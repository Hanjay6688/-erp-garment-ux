-- Private source-only review for the future counted owning adapters. No public
-- fields, permissions, seed or runtime admission are introduced here.
create function cp7_global_nonpo_envelope.selected_profile_v1()returns text
language plpgsql stable security definer set search_path=''as $$
declare id_ text;count_ bigint;
begin
 select count(*),min(id)into count_,id_ from cp7_global_nonpo_envelope.profiles;
 if count_<>1 then raise exception 'CP7_GLOBAL_ONE_ACTUAL_FINAL_PARENT_PROFILE_REQUIRED';end if;
 return id_;
end $$;

create function cp7_global_nonpo_envelope.review_v1(p_roots uuid[])returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare profile_ cp7_global_nonpo_envelope.profiles;seen_ jsonb;authority_ jsonb;hash_ text;
begin
 if p_roots is null or cardinality(p_roots)=0 or array_position(p_roots,null)is not null
  or cardinality(p_roots)<>(select count(distinct x)from unnest(p_roots)x)then
  raise exception 'CP7_GLOBAL_EXPLICIT_DISTINCT_ROOTS_REQUIRED';end if;
 select *into strict profile_ from cp7_global_nonpo_envelope.profiles
  where id=cp7_global_nonpo_envelope.selected_profile_v1();
 seen_:=cp7_global_nonpo_native_graph.inspect_v1(p_roots);authority_:=seen_->'authority';
 if authority_->'known_functions_exact'is distinct from'true'::jsonb
  or authority_#>'{view,exact_known_source}'is distinct from'true'::jsonb
  or authority_->'new_private_acl_closed'is distinct from'true'::jsonb then
  raise exception 'CP7_GLOBAL_EXACT_CURRENT_NATIVE_AUTHORITY_REQUIRED';end if;
 hash_:=encode(sha256(convert_to((authority_-array['session_user','current_user',
  'runtime_entry','required_final_parent','actual_Native_qualification_credit','production_go'])::text,'UTF8')),'hex');
 if hash_ is distinct from profile_.native_authority_sha256 then
  raise exception 'CP7_GLOBAL_FINAL_NATIVE_AUTHORITY_PROFILE_CHANGED';end if;
 if seen_->>'contract'is distinct from'cp7.global-nonpo-native-graph.readonly-inspector.v1'
  or coalesce(seen_->>'status','')not in('OBSERVED_QUIESCENT_SOURCE_ONLY','OBSERVED_REFUSAL_SOURCE_ONLY')
  or coalesce(seen_->>'basis_sha256','')!~'^[0-9a-f]{64}$'
  or jsonb_typeof(seen_->'issues')is distinct from'array'
  or(seen_->>'status'='OBSERVED_QUIESCENT_SOURCE_ONLY'and seen_->'issues'<>'[]'::jsonb)then
  raise exception 'CP7_GLOBAL_EXACT_READONLY_INSPECTION_REQUIRED';end if;
 return jsonb_build_object('contract','cp7.global-nonpo-envelope-review.v1',
  'profile',profile_.id,'basis_sha256',seen_->'basis_sha256','status',seen_->'status',
  'native_authority_sha256',hash_,'read_only',true,'runtime_acceptance_claimed',false);
end $$;
alter function cp7_global_nonpo_envelope.selected_profile_v1()owner to postgres;
alter function cp7_global_nonpo_envelope.review_v1(uuid[])owner to postgres;
revoke all on function cp7_global_nonpo_envelope.selected_profile_v1(),
 cp7_global_nonpo_envelope.review_v1(uuid[])from public,anon,authenticated,service_role;
