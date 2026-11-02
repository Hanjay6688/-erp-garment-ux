-- Pure metadata projection. Observed OIDs remain in the raw authority receipt;
-- only these three explicit paths are absent from its portable semantic hash.
-- Complete current metadata is independently bound by the fixed25 fingerprint.
create function cp7_global_nonpo_envelope.semantic_authority_v1(p_authority jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''as $$
declare projected_ jsonb;field_key_ text;entries_ jsonb;
begin
 if jsonb_typeof(p_authority)is distinct from'object'
  or p_authority->'known_function_count'is distinct from'19'::jsonb
  or jsonb_typeof(p_authority->'functions')is distinct from'array'
  or jsonb_typeof(p_authority->'new_private_functions')is distinct from'array'
  or jsonb_typeof(p_authority->'view')is distinct from'object'then
  raise exception 'CP7_GLOBAL_COMPLETE_TYPED_AUTHORITY_REQUIRED';end if;
 if jsonb_array_length(p_authority->'functions')<>19
  or jsonb_array_length(p_authority->'new_private_functions')<>4
  or jsonb_typeof(p_authority#>'{view,oid}')is distinct from'number'
  or jsonb_typeof(p_authority#>'{view,actual_catalog_row}')is distinct from'array'then
  raise exception 'CP7_GLOBAL_COMPLETE_TYPED_AUTHORITY_REQUIRED';end if;
 if jsonb_array_length(p_authority#>'{view,actual_catalog_row}')<>13 then
  raise exception 'CP7_GLOBAL_COMPLETE_TYPED_AUTHORITY_REQUIRED';end if;
 projected_:=p_authority-array['session_user','current_user','runtime_entry',
  'required_final_parent','actual_Native_qualification_credit','production_go'];
 foreach field_key_ in array array['functions','new_private_functions']loop
  if exists(select 1 from jsonb_array_elements(p_authority->field_key_)as element_(value)
   where jsonb_typeof(element_.value)is distinct from'object'
    or jsonb_typeof(element_.value->'oid')is distinct from'number'
    or jsonb_typeof(element_.value->'signature')is distinct from'string'
    or coalesce(element_.value->>'signature','')='')
   or jsonb_array_length(p_authority->field_key_)<>(select count(distinct element_.value->>'signature')
    from jsonb_array_elements(p_authority->field_key_)as element_(value))then
   raise exception 'CP7_GLOBAL_COMPLETE_TYPED_AUTHORITY_REQUIRED';end if;
  select jsonb_agg(element_.value-'oid'order by element_.ordinality)into entries_
   from jsonb_array_elements(p_authority->field_key_)with ordinality as element_(value,ordinality);
  projected_:=jsonb_set(projected_,array[field_key_],entries_,false);
 end loop;
 if exists(select 1 from jsonb_array_elements(p_authority->'functions')as element_(value)
  where jsonb_typeof(element_.value->'actual_catalog_row')is distinct from'array')then
  raise exception 'CP7_GLOBAL_COMPLETE_TYPED_AUTHORITY_REQUIRED';end if;
 if exists(select 1 from jsonb_array_elements(p_authority->'functions')as element_(value)
  where jsonb_array_length(element_.value->'actual_catalog_row')<>19)then
  raise exception 'CP7_GLOBAL_COMPLETE_TYPED_AUTHORITY_REQUIRED';end if;
 return jsonb_set(projected_,array['view'],(p_authority->'view')-'oid',false);
end $$;
alter function cp7_global_nonpo_envelope.semantic_authority_v1(jsonb)owner to postgres;
revoke all on function cp7_global_nonpo_envelope.semantic_authority_v1(jsonb)from public,anon,authenticated,service_role;
