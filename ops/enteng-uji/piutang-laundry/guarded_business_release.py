"""Render an Enteng Uji addition under its active Global release and row locks."""
from hashlib import sha256
import json
import re

AUTHORITY='87c8a9fdaa5ae9daadbde28f04fdb57127078384b2986e619a4ad6590f34eef7'

def render(*,profile,prior,name,previous_source,migrations,profiles,counts_delta,statements):
    if not all(re.fullmatch(r'[0-9a-f]{64}',s) for s in (profile, previous_source)):
        raise ValueError('An exact reviewed Uji profile and predecessor source are required')
    if not all(re.fullmatch(r'enteng_uji_[a-z0-9_]+',s) for s in (prior,name)):
        raise ValueError('Expected Enteng Uji migration names')
    if not isinstance(migrations,int) or not isinstance(profiles,int) or not counts_delta or not all(
        isinstance(n,int) and re.fullmatch('[a-z_]+',k) for k,n in counts_delta.items()):
        raise ValueError('Expected qualified catalogue group counts')
    if '$business_inner$' in statements or '$business_release$' in statements:
        raise ValueError('Unexpected release delimiter')
    expected=json.dumps(counts_delta,sort_keys=True)
    digest=sha256(statements.encode()).hexdigest()
    return f"""do $business_release$
declare
    previous_ cp7_global_nonpo_envelope.profiles;
    before_ jsonb;
    after_ jsonb;
    changes_ jsonb;
    root_ jsonb;
    next_ text;
begin
    if session_user<>'postgres' or current_user<>'postgres' or current_setting('is_superuser')<>'off'
       or (select count(*) from supabase_migrations.schema_migrations)<>{migrations}
       or (select count(*) from supabase_migrations.schema_migrations where name='{prior}')<>1
       or exists(select from supabase_migrations.schema_migrations where name='{name}') then
        raise exception 'Unexpected Enteng Uji business release predecessor';
    end if;
    perform cp7_global_release_guard.enter_release();
    perform cp7_credit.assert_source_native_trigger_census_v1();
    perform set_config('search_path','',true);
    perform set_config('TimeZone','UTC',true);
    select * into strict previous_ from cp7_global_nonpo_envelope.profiles
       where id=cp7_global_nonpo_envelope.selected_profile_v1();
    if previous_.id<>'{profile}' or previous_.native_authority_sha256<>'{AUTHORITY}'
       or (select count(*) from cp7_global_nonpo_envelope.profiles)<>{profiles}
       or previous_.actual_parent_root_receipt->'managed_enteng_uji' is distinct from 'true'::jsonb
       or previous_.actual_parent_root_receipt->'enteng_uji_release'->>'migration' is distinct from '{prior}'
       or previous_.actual_parent_root_receipt->'enteng_uji_release'->>'source_sha256' is distinct from '{previous_source}' then
        raise exception 'The Enteng Uji Global lineage or financial authority changed';
    end if;
    perform cp7_global_nonpo_envelope.lock_v1(previous_.id);
    before_:=cp7_global_nonpo_envelope.catalogue_fingerprint_v1();
    if before_ is distinct from previous_.actual_parent_root_receipt->'catalogue_fingerprint' then
        raise exception 'Global catalogue verification failed before release';
    end if;
    execute $business_inner$
{statements}$business_inner$;
    perform cp7_credit.assert_source_native_trigger_census_v1();
    perform cp7_global_release_guard.assert_ddl_fence();
    after_:=cp7_global_nonpo_envelope.catalogue_fingerprint_v1();
    select coalesce(jsonb_object_agg(k,delta),'{{}}') into strict changes_ from (
        select coalesce(a.key,b.key) k,a.value::integer-b.value::integer delta from jsonb_each_text(after_->'counts') a
        full join jsonb_each_text(before_->'counts') b on a.key=b.key
        where a.value is distinct from b.value) diff;
    if changes_ is distinct from '{expected}'::jsonb then
        raise exception 'The catalogue differs from the qualified business release';
    end if;
    root_:=previous_.actual_parent_root_receipt||jsonb_build_object('catalogue_fingerprint',after_,
        'supersedes_profile_id',previous_.id,'enteng_uji_release',jsonb_build_object('migration','{name}','source_sha256','{digest}'));
    next_:=encode(sha256(convert_to(jsonb_build_array(root_,previous_.native_authority_sha256,
        previous_.expected_relations,previous_.expected_catalogs)::text,'UTF8')),'hex');
    insert into cp7_global_nonpo_envelope.profiles
        (id,parent_head,parent_tree,actual_parent_root_receipt,expected_catalogs,expected_relations,native_authority_sha256)
    values(next_,previous_.parent_head,previous_.parent_tree,root_,previous_.expected_catalogs,
           previous_.expected_relations,previous_.native_authority_sha256);
    if cp7_global_nonpo_envelope.selected_profile_v1() is distinct from next_ then raise exception 'Successor not selected'; end if;
    perform cp7_global_nonpo_envelope.lock_v1(next_);
end $business_release$;
"""
