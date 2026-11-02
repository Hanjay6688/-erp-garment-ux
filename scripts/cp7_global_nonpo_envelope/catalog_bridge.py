"""One bounded source route to a fixed platform catalog fence; no SQL executor.

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
    before=text[start:end];derived=text[:start]+AFTER+text[end:]
    if derived.count(AFTER)!=1 or derived.replace(AFTER,before,1).encode()!=raw:
        raise ValueError('GLOBAL_CATALOG_BRIDGE_COMPLETE_ORIGINAL_NOT_RECOVERED')
    platform=(HERE/'platform_catalog_fence.sql').read_bytes()
    if platform.count(b'create function ')!=1 or b'create function cp7_global_catalog_fence.lock_v1()'not in platform:
        raise ValueError('GLOBAL_CATALOG_BRIDGE_SINGLE_ZERO_ARGUMENT_CAPABILITY_REQUIRED')
    if b"execute format('lock table pg_catalog.%I in share mode nowait',entry_->>1)"not in platform:
        raise ValueError('GLOBAL_CATALOG_BRIDGE_FIXED_CATALOG_SCHEMA_ONLY')
    return derived,dict(status='EXACT_ONE_ROUTE_PLATFORM_CATALOG_CAPABILITY_SOURCE_NOT_GLOBAL_RUNTIME',
        original_lock=ORIGINAL,derived_lock=pin(derived.encode()),platform_source=pin(platform),
        route=dict(before=before,after=AFTER,count=1),complete_original_recovered=True,
        platform_helper='cp7_global_catalog_fence.lock_v1()',platform_helper_owner='supabase_admin',
        allowed_external_invoker='postgres',new_roles=0,new_browser_or_service_grants=0,
        postgres_catalog_DML_or_MAINTAIN_grants=0,new_owning_or_financial_function_changes=0,
        old_scope21_and_review13_and_catalog_and_relation_controls_NOT_rerun=True,
        trusted_bootstrap_and_final_parent_and_global_qualification_pending=True,
        actual_SQL_executed=0,actual_Native_cases=0,production_go=False,independent_acceptance=False)


def inverse_sql():
    """Exact unused removal after owning routes/full restore; no CASCADE."""
    return ('set local role supabase_admin;\n'
        'drop function cp7_global_catalog_fence.lock_v1();\n'
        'drop schema cp7_global_catalog_fence;\nreset role;\n')


if __name__=='__main__':print(json.dumps(derive()[1],indent=2))
