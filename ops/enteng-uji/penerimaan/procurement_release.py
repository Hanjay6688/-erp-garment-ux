"""Render the reviewed Enteng Uji procurement change for one verified predecessor."""
import argparse
from hashlib import sha256
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
PREDECESSOR='enteng_uji_cp7_sales_series_snapshot'
PREDECESSOR_SOURCE='b7f0f003f6b2a1db28a2a104e9dd280bfa285cca87533a6ae90816610cf1233a'
MIGRATION='enteng_uji_cp7_procurement_operator_context'
AUTHORITY='87c8a9fdaa5ae9daadbde28f04fdb57127078384b2986e619a4ad6590f34eef7'

def render(profile):
    if not re.fullmatch(r'[0-9a-f]{64}',profile):
        raise ValueError('Expected a verified Enteng Uji Global predecessor')
    body=(HERE/'procurement-context.sql').read_text()
    digest=sha256(body.encode()).hexdigest()
    return f"""do $release$
declare
    previous_ cp7_global_nonpo_envelope.profiles;
    before_ jsonb;
    after_ jsonb;
    root_ jsonb;
    next_ text;
begin
    if session_user<>'postgres' or current_user<>'postgres' or current_setting('is_superuser')<>'off'
       or (select count(*) from supabase_migrations.schema_migrations)<>154
       or (select count(*) from supabase_migrations.schema_migrations where name='{PREDECESSOR}')<>1
       or exists(select from supabase_migrations.schema_migrations where name='{MIGRATION}') then
        raise exception 'Unexpected Enteng Uji release predecessor';
    end if;
    perform cp7_global_release_guard.enter_release();
    perform cp7_credit.assert_source_native_trigger_census_v1();
    perform set_config('search_path','',true);
    perform set_config('TimeZone','UTC',true);
    select * into strict previous_ from cp7_global_nonpo_envelope.profiles
      where id=cp7_global_nonpo_envelope.selected_profile_v1();
    if previous_.id<>'{profile}' or previous_.native_authority_sha256<>'{AUTHORITY}'
       or (select count(*) from cp7_global_nonpo_envelope.profiles)<>2
       or previous_.actual_parent_root_receipt->'managed_enteng_uji' is distinct from 'true'::jsonb
       or previous_.actual_parent_root_receipt->'enteng_uji_release'->>'source_sha256' is distinct from '{PREDECESSOR_SOURCE}' then
        raise exception 'The Uji series predecessor or its authority changed';
    end if;
    perform cp7_global_nonpo_envelope.lock_v1(previous_.id);
    before_:=cp7_global_nonpo_envelope.catalogue_fingerprint_v1();
    if before_ is distinct from previous_.actual_parent_root_receipt->'catalogue_fingerprint' then
        raise exception 'The installed catalogue differs from the active Uji profile';
    end if;
    execute $reviewed_context$
{body}$reviewed_context$;
    perform cp7_global_release_guard.assert_ddl_fence();
    perform cp7_credit.assert_source_native_trigger_census_v1();
    after_:=cp7_global_nonpo_envelope.catalogue_fingerprint_v1();
    if after_=before_ or (after_->'counts') is distinct from (before_->'counts') then
        raise exception 'Unexpected purchasing release catalogue shape';
    end if;
    root_:=previous_.actual_parent_root_receipt || jsonb_build_object(
        'catalogue_fingerprint',after_, 'supersedes_profile_id',previous_.id,
        'enteng_uji_release',jsonb_build_object('migration','{MIGRATION}','source_sha256','{digest}'));
    next_:=encode(sha256(convert_to(jsonb_build_array(root_,previous_.native_authority_sha256,
             previous_.expected_relations,previous_.expected_catalogs)::text,'UTF8')),'hex');
    insert into cp7_global_nonpo_envelope.profiles
        (id,parent_head,parent_tree,actual_parent_root_receipt,expected_catalogs,expected_relations,native_authority_sha256)
    values(next_,previous_.parent_head,previous_.parent_tree,root_,previous_.expected_catalogs,
           previous_.expected_relations,previous_.native_authority_sha256);
    if cp7_global_nonpo_envelope.selected_profile_v1() is distinct from next_ then
        raise exception 'The procurement successor was not selected';
    end if;
    perform cp7_global_nonpo_envelope.lock_v1(next_);
end $release$;
"""
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile')
    print(render(parser.parse_args().profile),end='')
