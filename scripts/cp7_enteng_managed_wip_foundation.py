"""Reproduce the reviewed Enteng Uji WIP foundation rehearsal from the CP7 source.

Running this module prints a rollback-only SQL transaction for the restored BF
test database. It does not connect to a database. The production installer has
its own package identity and admission.
"""
import argparse
from hashlib import sha256
import json
import re

import cp7_wip_bundle


SOURCE_SHA256 = '045e443cf22b831c78c8b05a8d4a1f225592eb070132077d2184ac034328e2c6'
BODY_SHA256 = '4befa473c7c8f7ab3373c749f824e588da183fa0744ce32612dff13325366cc9'
REHEARSAL_SHA256 = 'a51cd1f548efd199fec27ad3309e5bb2fe2a4567ea783a4e5a52ec3a62d36f8b'
CONTEXT = """SET LOCAL createrole_self_grant='set,inherit';
CREATE SCHEMA cp7_request_context AUTHORIZATION postgres;
REVOKE ALL ON SCHEMA cp7_request_context FROM PUBLIC,anon,authenticated,service_role;
CREATE FUNCTION cp7_request_context.jwt() RETURNS jsonb
LANGUAGE sql STABLE SECURITY INVOKER SET search_path='' AS $enteng_auth_value$
  select 
    coalesce(
        nullif(current_setting('request.jwt.claim', true), ''),
        nullif(current_setting('request.jwt.claims', true), '')
    )::jsonb
$enteng_auth_value$;
CREATE FUNCTION cp7_request_context.uid() RETURNS uuid
LANGUAGE sql STABLE SECURITY INVOKER SET search_path='' AS $enteng_auth_value$
  select 
  coalesce(
    nullif(current_setting('request.jwt.claim.sub', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')
  )::uuid
$enteng_auth_value$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA cp7_request_context FROM PUBLIC,anon,authenticated,service_role;
"""
VERIFY = """DO $prove_portability_scope$
BEGIN
  IF to_regprocedure('public.erp_cp7_capture_production_wip_v1(jsonb,uuid)') IS NULL
    OR (SELECT pg_get_userbyid(proowner) FROM pg_proc WHERE oid='public.erp_cp7_capture_production_wip_v1(jsonb,uuid)'::regprocedure)<>'cp7_capture'
    OR has_schema_privilege('cp7_capture','auth','USAGE')
    OR has_schema_privilege('cp7_capture','public','CREATE')
    OR NOT has_schema_privilege('cp7_capture','cp7_request_context','USAGE')
    OR NOT has_function_privilege('cp7_capture','cp7_request_context.uid()','EXECUTE')
    OR has_function_privilege('authenticated','cp7_request_context.uid()','EXECUTE') THEN
    RAISE EXCEPTION 'Managed CP7 WIP role boundary mismatch';
  END IF;
END $prove_portability_scope$;"""
READBACK = """SELECT to_regnamespace('cp7_request_context') IS NULL AND to_regnamespace('cp7_wip') IS NULL
   AND (SELECT count(*) FROM supabase_migrations.schema_migrations)=138;
"""
PUBLIC_OWNER = re.compile(
    r'^alter function public\.[a-z0-9_]+\([a-z0-9_,\[\]]*\) owner to (?P<role>cp7_capture|cp7_policy);$',
    flags=re.MULTILINE,
)


def checked(text, expected):
    if sha256(text.encode('utf-8')).hexdigest() != expected:
        raise ValueError("The ERP WIP source differs from the reviewed managed rehearsal")
    return text


def transfer_owner(match):
    # PostgreSQL requires the receiving owner to have CREATE in the schema.
    # Both the ownership transfer and returning the schema privilege happen
    # inside the caller's transaction. Preserve any pre-existing grant.
    role = match['role']
    return f"""DO $cp7_local_public_transfer$
DECLARE keep_create boolean:=has_schema_privilege('{role}','public','CREATE');
BEGIN
  IF NOT keep_create THEN GRANT CREATE ON SCHEMA public TO {role}; END IF;
  {match.group()}
  IF NOT keep_create THEN REVOKE CREATE ON SCHEMA public FROM {role}; END IF;
END;
$cp7_local_public_transfer$;"""


def body():
    canonical = checked(cp7_wip_bundle.bundle(), SOURCE_SHA256)
    adapted = canonical.replace('schema erp,auth,extensions', 'schema erp,cp7_request_context,extensions')
    for name in ('uid','jwt'):
        adapted = adapted.replace(f'auth.{name}()', f'cp7_request_context.{name}()')
    adapted, changes = PUBLIC_OWNER.subn(transfer_owner, adapted)
    if changes != 9:
        raise ValueError("Expected nine public WIP ownership transfers")
    return checked(CONTEXT + adapted + VERIFY, BODY_SHA256)


def rehearsal():
    return checked('BEGIN;\n' + body() + '\nROLLBACK;\n' + READBACK, REHEARSAL_SHA256)


def predecessor_manifest():
    """Bind this single change to the original full predecessor from the repo root."""
    import cp7_full_owning_install as original

    canonical = original.source_manifest()
    expected = 'e7701eaada592cfd74a8555cf4cdcb7df8d180448213d3bbf5698c3bfa025127'
    if canonical['predecessor_sql_sha256'] != expected:
        raise ValueError("Unexpected full predecessor")
    text = original.f03.procurement.bundle() + '\n' + original.predecessor_extension()
    checked(text, expected)
    foundation = checked(cp7_wip_bundle.bundle(), SOURCE_SHA256)
    if not text.startswith(foundation) or text.count(foundation) != 1:
        raise ValueError("The qualified WIP foundation must occur exactly once at the start")
    rest = text[len(foundation):]
    managed = body() + rest
    managed_digest = 'c4c54061dea165a968b3db6b07870cd0a1ea9a9b5b5768789cbff12175c4f11f'
    checked(managed, managed_digest)
    return {
        'canonical_predecessor_sha256': expected,
        'managed_predecessor_sha256': managed_digest,
        'managed_predecessor_bytes': len(managed.encode()),
        'unchanged_tail_sha256': sha256(rest.encode()).hexdigest(),
        'managed_wip_body_sha256': BODY_SHA256,
        'qualified_full_installation': False,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predecessor-manifest', action='store_true',
                        help='Report the source identity of the complete predecessor with this WIP change')
    if parser.parse_args().predecessor_manifest:
        print(json.dumps(predecessor_manifest(), indent=2))
    else:
        print(rehearsal(), end='')
