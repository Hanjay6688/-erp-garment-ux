"""Three bounded routes to platform fences and a catalogue profile; no executor.

The old lock source and all old controls remain exact. Trusted capability
bootstrap, final accepted parent and global runtime qualification remain gates.
"""
from pathlib import Path
from hashlib import sha256
import json

HERE=Path(__file__).resolve().parent
ORIGINAL=dict(bytes=7185,sha256='2446da79ce58c29bbaaef9b126897322b29ff1504ed4d65f16be5d0150482c13')
AFTER=""" -- The platform helper has no input arguments and can lock only actual
 -- pg_catalog tables. Its locks remain on this backend/transaction after the
 -- SECURITY DEFINER call returns to the ordinary postgres owner.
 catalogs_:=cp7_global_catalog_fence.lock_v1();
 if catalogs_ is distinct from profile_.expected_catalogs then
  raise exception 'CP7_GLOBAL_SYSTEM_CATALOG_IDENTITY_OR_AUTHORITY_CHANGED';end if;
"""


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def derive():
    raw=(HERE/'lock.sql').read_bytes()
    if pin(raw)!=ORIGINAL:raise ValueError('GLOBAL_CATALOG_BRIDGE_ORIGINAL_LOCK_CHANGED')
    text=raw.decode();start=text.index(' -- First freeze the identity universe')
    end=text.index('\n -- EXCLUSIVE also conflicts',start)
    before=text[start:end]
    # Catalog tuple writers may commit after the old observation but before the
    # old later XID check. Drain before a fresh metadata read; keep that later
    # original check as a second conservative boundary.
    xid_start=text.index(' select coalesce(jsonb_agg(jsonb_build_array(pid,transactionid::text')
    xid_end=text.index('\n -- Preserve the exact Native',xid_start)
    early_xid=text[xid_start:xid_end]
    read_start=before.index(' select coalesce(jsonb_agg(jsonb_build_array(n.nspname')
    read_end=before.index(' if catalogs_ is distinct from profile_.expected_catalogs')
    fresh=before[read_start:read_end]
    after=AFTER[:AFTER.index(' if catalogs_ is distinct')]+early_xid+'\n'+fresh+AFTER[AFTER.index(' if catalogs_ is distinct'):]
    derived=text[:start]+after+text[end:]
    data_start=text.index(' -- EXCLUSIVE also conflicts')
    data_end=text.index('\n -- Snapshot xip is NOT',data_start)
    data_before=text[data_start:data_end]
    data_after=" -- A fixed platform capability locks only the one sealed profile's\n -- declared application relations, including private internal-role tables.\n actual_:=cp7_global_catalog_fence.lock_relations_v1(p_profile);\n if actual_ is distinct from profile_.expected_relations then\n  raise exception 'CP7_GLOBAL_RELATION_IDENTITY_OR_AUTHORITY_CHANGED';end if;\n"
    if derived.count(data_before)!=1:raise ValueError('GLOBAL_RELATION_BRIDGE_EXACT_ORIGINAL_BLOCK_REQUIRED')
    derived=derived.replace(data_before,data_after,1)
    catalogue_check=""" -- Full current catalogue authority is sealed separately from the nineteen
 -- known financial functions. Its fixed25 groups include all original22 plus
 -- operator/cast/language dispatch. It changes neither data nor sequence state.
 if pg_my_temp_schema()<>0 then
  raise exception 'CP7_GLOBAL_TEMPORARY_NAMESPACE_REQUIRES_FRESH_CONNECTION';end if;
 if profile_.actual_parent_root_receipt->>'contract'is distinct from'cp7.global-parent-and-catalogue-profile.v1'
  or profile_.actual_parent_root_receipt#>>'{accepted_parent,head}'is distinct from profile_.parent_head
  or profile_.actual_parent_root_receipt#>>'{accepted_parent,tree}'is distinct from profile_.parent_tree
  or coalesce(profile_.actual_parent_root_receipt#>>'{accepted_parent,root_receipt_pin,sha256}','')!~'^[0-9a-f]{64}$'then
  raise exception 'CP7_GLOBAL_ACTUAL_PARENT_AND_CATALOGUE_PROFILE_REQUIRED';end if;
 actual_:=cp7_global_nonpo_envelope.catalogue_fingerprint_v1();
 if actual_ is distinct from profile_.actual_parent_root_receipt->'catalogue_fingerprint'then
  raise exception 'CP7_GLOBAL_COMPLETE_CURRENT_CATALOGUE_AUTHORITY_CHANGED';end if;

"""
    if derived.count(data_after)!=1:raise ValueError('GLOBAL_CATALOGUE_PROFILE_ONE_INSERTION_SITE_REQUIRED')
    derived=derived.replace(data_after,catalogue_check+data_after,1)
    restored=derived.replace(catalogue_check+data_after,data_before,1).replace(after,before,1)
    if restored.encode()!=raw:raise ValueError('GLOBAL_CATALOG_BRIDGE_COMPLETE_ORIGINAL_NOT_RECOVERED')
    platform=(HERE/'platform_catalog_fence.sql').read_bytes()
    if platform.count(b'create function ')!=1 or b'create function cp7_global_catalog_fence.lock_v1()'not in platform:
        raise ValueError('GLOBAL_CATALOG_BRIDGE_SINGLE_ZERO_ARGUMENT_CAPABILITY_REQUIRED')
    if b"execute format('lock table pg_catalog.%I in share mode nowait',entry_->>1)"not in platform:
        raise ValueError('GLOBAL_CATALOG_BRIDGE_FIXED_CATALOG_SCHEMA_ONLY')
    return derived,dict(status='EXACT_THREE_ROUTE_PLATFORM_FENCES_AND_CATALOGUE_PROFILE_SOURCE_NOT_GLOBAL_RUNTIME',
        original_lock=ORIGINAL,derived_lock=pin(derived.encode()),platform_source=pin(platform),
        route=dict(before=before,after=after,count=1),
        relation_route=dict(before=data_before,after=data_after,count=1),
        catalogue_profile_route=dict(before=data_after,after=catalogue_check+data_after,count=1),source_routes=3,
        catalogue_fingerprint_source=pin((HERE/'catalogue_fingerprint.sql').read_bytes()),
        original_all22_plus_operator_cast_language_groups=25,
        full_current_catalogue_checked_before_post_fence_source_graph_reads=True,
        nonempty_current_backend_temporary_namespace_refused=True,
        fresh_catalog_metadata_after_early_XID_drain=True,original_later_XID_check_retained=True,
        complete_original_recovered=True,
        platform_helper='cp7_global_catalog_fence.lock_v1()',platform_helper_owner='supabase_admin',
        allowed_external_invoker='postgres',new_roles=0,new_browser_or_service_grants=0,
        postgres_catalog_DML_or_MAINTAIN_grants=0,new_owning_or_financial_function_changes=0,
        old_scope21_and_review13_and_catalog_and_relation_controls_NOT_rerun=True,
        trusted_bootstrap_and_final_parent_and_global_qualification_pending=True,
        relation_platform_source=pin((HERE/'platform_relation_fence.sql').read_bytes()),
        actual_SQL_executed=0,actual_Native_cases=0,production_go=False,independent_acceptance=False)


def inverse_sql():
    """Exact unused removal after owning routes/full restore; no CASCADE."""
    return ('set local role supabase_admin;\n'
        'drop function cp7_global_catalog_fence.lock_relations_v1(text);\n'
        'drop function cp7_global_catalog_fence.lock_v1();\n'
        'drop schema cp7_global_catalog_fence;\nreset role;\n')


if __name__=='__main__':print(json.dumps(derive()[1],indent=2))
