"""Exact SKU private authority over the unchanged accepted Mandor reviewer.

Only eleven named default-deny INFOs can be classified. All 23 new SKU table
authorities, including twelve original deny policies, are checked together.
No privilege, policy, owner or product SQL is changed by this observer.
"""
from pathlib import Path
from types import SimpleNamespace
import importlib.util
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ROLES = ('anon', 'authenticated', 'service_role', 'cp7_alert', 'cp7_finance_read')
PRIVILEGES = ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER')
SCHEMA = 'cp7_sku_conversion'
PARENT = 'scripts/current-mandor-shop-native-qualification/advisor_review.py'
PARENT_PIN = dict(bytes=8140, sha256='4bfe15aedd3d61228f7f59b8b863b6109b8c8d6779797ccf0e9b9f4fe9da17e8')

# One read-only statement captures all tables, all raw nonowner ACLs (including
# roles outside the five public-facing probes), full policies and effective
# public-facing privileges. The owning package separately retains all22 roles,
# memberships, default privileges and the complete actual catalogue.
CAPTURE_SQL = r"""
with wanted as(select unnest(%s::text[])qualified), probes as(select unnest(%s::text[])role_name)
select w.qualified,jsonb_build_object(
 'object',jsonb_build_array(n.nspname,c.relname),'owner',pg_get_userbyid(c.relowner),
 'rls',c.relrowsecurity,'force_rls',c.relforcerowsecurity,
 'schema_owner',pg_get_userbyid(n.nspowner),
 'nonowner_schema_acl',coalesce((select jsonb_agg(jsonb_build_array(
  case a.grantee when 0 then 'PUBLIC'else pg_get_userbyid(a.grantee)end,a.privilege_type,a.is_grantable)
  order by a.grantee,a.privilege_type,a.is_grantable)
  from aclexplode(coalesce(n.nspacl,acldefault('n',n.nspowner)))a where a.grantee<>n.nspowner),'[]'),
 'nonowner_table_acl',coalesce((select jsonb_agg(jsonb_build_array(
  case a.grantee when 0 then 'PUBLIC'else pg_get_userbyid(a.grantee)end,a.privilege_type,a.is_grantable)
  order by a.grantee,a.privilege_type,a.is_grantable)
  from aclexplode(coalesce(c.relacl,acldefault('r',c.relowner)))a where a.grantee<>c.relowner),'[]'),
 'nonowner_column_acl',coalesce((select jsonb_agg(jsonb_build_array(t.attname,
  case a.grantee when 0 then 'PUBLIC'else pg_get_userbyid(a.grantee)end,a.privilege_type,a.is_grantable)
  order by t.attname,a.grantee,a.privilege_type,a.is_grantable)
  from pg_attribute t cross join lateral aclexplode(t.attacl)a
  where t.attrelid=c.oid and a.grantee<>c.relowner),'[]'),
 'policies',coalesce((select jsonb_agg(jsonb_build_array(p.polname,p.polcmd,p.polpermissive,
   (select jsonb_agg(case x when 0 then 'PUBLIC'else pg_get_userbyid(x)end order by x)from unnest(p.polroles)x),
   pg_get_expr(p.polqual,p.polrelid),pg_get_expr(p.polwithcheck,p.polrelid))order by p.polname)
   from pg_policy p where p.polrelid=c.oid),'[]'),
 'schema_usage',(select jsonb_object_agg(role_name,has_schema_privilege(role_name,n.oid,'USAGE'))from probes),
 'table_privileges',(select jsonb_object_agg(role_name,
    (select jsonb_object_agg(priv,has_table_privilege(role_name,c.oid,priv))
     from unnest(array['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER'])priv))from probes)
 )authority
from wanted w join pg_class c on c.oid=to_regclass(w.qualified)
join pg_namespace n on n.oid=c.relnamespace order by w.qualified
"""


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


assembly = load('automatic_authority_exact_source_assembly', HERE / 'assembly.py')


def source():
    reference = assembly.prepared_sources()[0]
    tree = reference['automatic_source']['tree']
    tables, eligible, profiles = {}, [], {}
    for name, count in (('cp7_sku_moving_average', 12), ('cp7_sku_cost_components', 9), ('cp7_sku_automatic_pending', 2)):
        path = 'scripts/' + name + '/CATALOG_ADDITIONS.json'
        raw = assembly.git('show', tree + ':' + path)
        profile = json.loads(raw)
        profiles[name] = assembly.admission.pin(raw)
        additions = {key: row for key, row in profile['groups']['relations'].items() if row[1] in ('r', 'p')}
        assembly.require(len(additions) == count and not set(additions) & set(tables), 'SKU_ADVISOR_EXACT_DISJOINT_SOURCE_TABLES')
        for qualified, row in additions.items():
            assembly.require(qualified.startswith(SCHEMA + '.') and row[0] == 'postgres'
                             and row[3] is True and row[4] is False
                             and all(acl[1] == 'postgres' for acl in row[12]), 'SKU_ADVISOR_EXACT_PRIVATE_SOURCE_AUTHORITY')
            policies = [[identity.split(':', 1)[1]] + value for identity, value in profile['groups'].get('policies', {}).items()
                        if identity.split(':', 1)[0] == qualified]
            assembly.require((name == 'cp7_sku_moving_average' and len(policies) == 1
                              and policies[0][1:] == ['*', True, ['PUBLIC'], 'false', 'false'])
                             or (name != 'cp7_sku_moving_average' and not policies), 'SKU_ADVISOR_EXACT_DENY_POLICY_SOURCE')
            if not policies:
                eligible.append(qualified)
            tables[qualified] = dict(object=qualified.split('.'), owner='postgres', rls=True, force_rls=False,
                                    schema_owner='postgres', nonowner_schema_acl=[], nonowner_table_acl=[], nonowner_column_acl=[],
                                    policies=policies, schema_usage={role: False for role in ROLES},
                                    table_privileges={role: {priv: False for priv in PRIVILEGES} for role in ROLES})
    assembly.require(len(tables) == 23 and len(eligible) == 11, 'SKU_ADVISOR_EXACT_TWENTY_THREE_TABLES_ELEVEN_INFOS')
    return dict(tables=tables, eligible=sorted(eligible), exact_profiles=profiles,
                classification='SOURCE_AUTHORITY_EXPECTATIONS_NOT_LIVE_PROOF', actual_ERP_cases=0, production_go=False)


def compose(parent, expected):
    """Private reviewer construction; the owning entry admits the frozen parent."""
    def require_closed(proof):
        assembly.require(type(proof) is dict and set(proof) == {'parent', 'SKU'}, 'SKU_ADVISOR_COMPLETE_PARENT_AND_CHILD_PROOF')
        parent.require_closed(proof['parent'])
        assembly.require(json.dumps(proof['SKU'], sort_keys=True, allow_nan=False)
                         == json.dumps(expected['tables'], sort_keys=True, allow_nan=False),
                         'SKU_ADVISOR_EXACT_PRIVATE_LIVE_AUTHORITY_REQUIRED')
        return proof

    def capture(cur):
        inherited = parent.capture(cur)
        rows = cur.execute(CAPTURE_SQL, (sorted(expected['tables']), list(ROLES))).fetchall()
        assembly.require(len(rows) == 23 and len(dict(rows)) == 23, 'SKU_ADVISOR_COMPLETE_LIVE_AUTHORITY_ROWS_REQUIRED')
        return require_closed(dict(parent=inherited, SKU=dict(rows)))

    def review(delta, manifest, proof, predecessor_review):
        require_closed(proof)
        original = parent.review(delta, manifest, proof['parent'], predecessor_review)
        reviewed, unexplained = [], []
        for finding in original['unexplained']:
            meta = finding.get('metadata') or {}
            qualified = str(meta.get('schema')) + '.' + str(meta.get('name'))
            exact = (finding.get('name') == 'rls_enabled_no_policy' and finding.get('level') == 'INFO'
                     and meta.get('type') == 'table' and qualified in expected['eligible'])
            (reviewed if exact else unexplained).append(finding)
        keys = [json.dumps(row, sort_keys=True, allow_nan=False) for row in reviewed]
        remaining = dict(delta, added=[row for row in delta.get('added', [])
                                      if json.dumps(row, sort_keys=True, allow_nan=False) not in keys])
        remainder = parent.review(remaining, manifest, proof['parent'], predecessor_review)
        identities = [(row.get('name'), row.get('level'), (row.get('metadata') or {}).get('type'),
                       (row.get('metadata') or {}).get('schema'), (row.get('metadata') or {}).get('name'))
                      for row in delta.get('added', [])]
        passed = (delta.get('status') in ('NO_NEW_FINDINGS', 'REVIEW_REQUIRED') and not unexplained
                  and len(keys) == len(set(keys)) and len(identities) == len(set(identities)) and remainder['gate'] is True)
        return dict(status='VERIFIED_PARENT_AND_SKU_PRIVATE_DEFAULT_DENY_INFO' if passed else 'UNEXPLAINED_FINDINGS',
                    predecessor_disposition=original, unchanged_parent_remainder_disposition=remainder,
                    reviewed_SKU_private_info=reviewed, unexplained=unexplained, current_private_authority=proof,
                    complete_original_delta=delta, gate=bool(passed))
    return SimpleNamespace(require_closed=require_closed, capture=capture, review=review)


def bind(parent_reviewer, frozen_parent):
    assembly.admission.require_ready()  # Before caller, file, Git or ERP inspection.
    path = Path(frozen_parent) / PARENT
    assembly.require(Path(parent_reviewer.__file__).resolve() == path.resolve()
                     and path.is_file() and not path.is_symlink() and assembly.admission.pin(path.read_bytes()) == PARENT_PIN,
                     'SKU_ADVISOR_EXACT_ACCEPTED_FROZEN_MANDOR_REVIEWER_REQUIRED')
    return compose(parent_reviewer, source())
