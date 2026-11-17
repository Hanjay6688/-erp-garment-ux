"""Preseal foundation on the existing, trusted Global installation transaction."""

import ast
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
from types import SimpleNamespace


WRITER_HEAD = 'ca7f09556397801c50a2277bdb65b1bf019f9a05'
WRITER_TREE = '5b5f12c5ef50b646c84a5e41cf8e02b394912325'
API = 'scripts/cp6_ao_ap_installed.py'
ACTORS = 'scripts/cp6_x_independent_audit.py'
SESSION = 'scripts/cp6_v2620x_internal_role_regression.py'
BASE = 'scripts/cp6_v2620e_counterexample_regression.py'
CP3 = 'supabase/tests/cp3_r4_full_schema_seed.sql'
CP3_INCLUDE = 'supabase/tests/cp3_r3_full_schema_seed.sql'
CP6 = 'supabase/tests/cp6_laundry_qc_concurrency_seed.sql'
WRITER_BLOBS = {
    API: 'bf6d37db7054ec4fb9a56b0eaf2f6c30171168ed',
    ACTORS: '9087482c997a03859c57bc2da3fd2a4b883e0265',
    SESSION: '98c87aef79bbbd20438efd778713d2dc51c58b98',
    BASE: 'a110e0ef51e28b6b20997bffe40de3978883089f',
    CP3: 'd3898f73c3e15e9b4aaf57cb9c03c2e5f8274929',
    CP3_INCLUDE: 'd74fcd12c3263aaec01f7fef4c226559104f43fa',
    CP6: 'cd8eaf14a7123de8d4490dc060351ed518079b35',
}
LOGIN = 'cp6_maintenance_admission'
AUTHORITY = ('current_user', 'session_user', 'role', 'session_authorization')
GUC = ('TimeZone', 'search_path', 'request.jwt.claims', 'request.jwt.claim.sub', 'app.change_reason')
# The retained CP3 worker and attendance writers also set these guarded switches.
CP3_SWITCHES = ('app.worker_rate_write', 'app.worker_employment_write', 'app.attendance_period_lifecycle')
# The retained writer trace reaches both SKU HPP synchronization functions.
SKU_SWITCHES = ('cp7.sku_nonpo_sync_expanding', 'cp7.sku_po_sync_expanding')
SETTINGS = GUC + CP3_SWITCHES + SKU_SWITCHES
SESSION_SQL = ('select pg_backend_pid(), current_database(), pg_my_temp_schema(), '
               'current_user::text, session_user::text, current_setting(\'role\'), '
               "current_setting('session_authorization'), "
               + ', '.join('current_setting(%s, true)' for _ in SETTINGS))
SET_GUC = 'select set_config(%s, %s, false)'
SCRATCH = 'cp7_global_fixture_foundation_scratch'
SCRATCH_SQL = 'select to_regnamespace(%s) is null'
TEMP_DDL = ('create temp table if not exists cp3_r3_ids(\n'
            '  key text primary key,\n  id uuid,\n  value jsonb\n) on commit preserve rows;')
SCRATCH_TABLE = SCRATCH + '.cp3_r3_ids'
SCRATCH_DDL = f'create schema {SCRATCH} authorization supabase_admin;\n' + (
    TEMP_DDL.replace('create temp table if not exists cp3_r3_ids', 'create table ' + SCRATCH_TABLE)
    .replace(' on commit preserve rows', ''))
SCRATCH_DROP = f'\ndrop table {SCRATCH_TABLE} restrict;\ndrop schema {SCRATCH} restrict;\n'
MODEL = 'a2000000-0000-0000-0000-000000000001'
CP3_SIZE = 'a2100000-0000-0000-0000-000000000001'
LEDGER = ('AR_CUSTOMER', 'COGS', 'FG_INVENTORY', 'SALES_REVENUE')


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def checked_writer(writer):
    root = Path(writer).absolute()
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update(GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0', GIT_NO_REPLACE_OBJECTS='1')

    def git(*args, **options):
        return subprocess.run(['git', '-C', str(root), *args], env=env, capture_output=True, **options)

    require(root.is_dir() and not any(path.is_symlink() for path in (root, *root.parents)),
            'GLOBAL_FOUNDATION_EXACT_REGULAR_WRITER_CHECKOUT_REQUIRED')
    refs = git('rev-parse', '--show-toplevel', 'HEAD', 'HEAD^{tree}', check=True).stdout.decode().splitlines()
    require(refs == [str(root), WRITER_HEAD, WRITER_TREE] and git('symbolic-ref', '-q', 'HEAD').returncode == 1,
            'GLOBAL_FOUNDATION_EXACT_DETACHED_CI_WRITER_REQUIRED')
    require(not git('status', '--porcelain=v1', '--untracked-files=all', check=True).stdout,
            'GLOBAL_FOUNDATION_CLEAN_CI_WRITER_REQUIRED')
    sources = {}
    for relative, expected in WRITER_BLOBS.items():
        path = root / relative
        require(path.is_file() and not any(part.is_symlink() for part in (path, *path.parents)),
                'GLOBAL_FOUNDATION_EXACT_REGULAR_WRITER_SOURCE_REQUIRED:' + relative)
        raw = path.read_bytes()
        oid = git('hash-object', '--stdin', input=raw, check=True).stdout.decode().strip()
        tracked = git('rev-parse', WRITER_TREE + ':' + relative, check=True).stdout.decode().strip()
        require(oid == tracked == expected, 'GLOBAL_FOUNDATION_EXACT_WRITER_SOURCE_REQUIRED:' + relative)
        sources[relative] = raw
    return root, sources


def donor_functions(root, sources, path, names, **bindings):
    """Compile the original definitions with only their exact required globals."""
    tree = ast.parse(sources[path])
    definitions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    future = [node for node in tree.body if isinstance(node, ast.ImportFrom) and node.module == '__future__']
    require(len(definitions) == len(names) and {node.name for node in definitions} == set(names),
            'GLOBAL_FOUNDATION_EXACT_WRITER_DEFINITIONS_REQUIRED:' + path)
    exec(compile(ast.Module(body=future + definitions, type_ignores=[]), str(root / path), 'exec',
                 dont_inherit=True), bindings)
    return SimpleNamespace(**{name: bindings[name] for name in names})


def route_scratch(original):
    require(original.count(TEMP_DDL) == 1 and original.count('cp3_r3_ids') == 35 and SCRATCH not in original,
            'GLOBAL_FOUNDATION_EXACT_CP3_SCRATCH_ANCHORS_REQUIRED')
    qualified = TEMP_DDL.replace('cp3_r3_ids', SCRATCH_TABLE)
    derived = original.replace('cp3_r3_ids', SCRATCH_TABLE).replace(qualified, SCRATCH_DDL, 1) + SCRATCH_DROP
    restored = derived.removesuffix(SCRATCH_DROP).replace(SCRATCH_DDL, qualified, 1).replace(SCRATCH_TABLE, 'cp3_r3_ids')
    require(derived.count(SCRATCH_TABLE) == 36 and restored == original,
            'GLOBAL_FOUNDATION_COMPLETE_CP3_SCRATCH_INVERSE_REQUIRED')
    return derived


def bind_seed(writer):
    root, sources = checked_writer(writer)
    base_tree = ast.parse(sources[BASE])
    names = ('OPERATOR_AUTH', 'OPERATOR_APP', 'BASE_PRODUCT', 'SIZE', 'LOCATION')
    constants = {node.targets[0].id: ast.literal_eval(node.value) for node in base_tree.body
                 if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                 and node.targets[0].id in names}
    require(set(constants) == set(names), 'GLOBAL_FOUNDATION_EXACT_WRITER_FOUNDATION_IDENTITIES_REQUIRED')
    reader = donor_functions(root, sources, BASE, ('read_psql_seed',), Path=Path, re=re).read_psql_seed
    cp3, cp6 = (reader(root / name) for name in (CP3, CP6))
    require(all((root / name).read_bytes() == sources[name] for name in (CP3, CP3_INCLUDE, CP6)),
            'GLOBAL_FOUNDATION_WRITER_SEED_INPUT_CHANGED_DURING_BIND')
    routed = route_scratch(cp3)
    prepared = {Path(CP3): routed, Path(CP6): cp6}
    base = donor_functions(root, sources, BASE, ('load_fixture_foundation',),
                           Path=Path, read_psql_seed=prepared.__getitem__)
    base.__dict__.update(constants)
    sessions = donor_functions(root, sources, SESSION, ('claims', 'session'), json=json)
    actors = donor_functions(root, sources, ACTORS, ('admin',), actors=sessions)
    actors.actors = sessions
    api = donor_functions(root, sources, API, ('admin', 'seed'), actors=actors, base=base)
    return api.seed, base, dict(writer_head=WRITER_HEAD, writer_tree=WRITER_TREE,
                                sources={name: pin(raw) for name, raw in sources.items()},
                                CP3_expanded=pin(cp3.encode()), CP3_without_temporary_namespace=pin(routed.encode()),
                                CP6_expanded=pin(cp6.encode()), CP3_scratch_references=35)


FACTS_SQL = """
select jsonb_build_object(
 'app_users', (select count(*) from erp.app_users),
 'owner', (select jsonb_build_array(u.id,u.auth_user_id,u.role::text,u.is_active,r.id,r.role_code,r.is_active)
   from erp.app_users u join erp.app_roles r on r.id=u.role_id where u.id=%s::uuid and u.auth_user_id=%s::uuid),
 'product', (select jsonb_build_array(id,model_id,size_id,sku,is_active) from erp.products where id=%s::uuid),
 'model', (select jsonb_build_array(id,model_code,is_active) from erp.product_models where id=%s::uuid),
 'sizes', (select coalesce(jsonb_agg(jsonb_build_array(s.id,s.size_code,s.is_active) order by s.id),'[]')
   from erp.product_model_sizes p join erp.sizes s on s.id=p.size_id where p.model_id=%s::uuid and s.id=any(%s::uuid[])),
 'location', (select jsonb_build_array(id,location_code,location_type::text,is_active) from erp.locations where id=%s::uuid),
 'ledger', (select coalesce(jsonb_object_agg(m.mapping_key,jsonb_build_array(a.id,a.account_code,a.is_active,a.is_postable)), 'null')
   from erp.accounting_account_mappings m join erp.chart_accounts a on a.id=m.account_id where m.mapping_key=any(%s::text[])),
 'period', (select jsonb_build_array(closed_through, closed_through is null or closed_through < %s::date)
   from erp.accounting_period_control where singleton_id=1),
 'erp_usage', has_schema_privilege('authenticated','erp','USAGE'))
"""


def session(cur):
    row = cur.execute(SESSION_SQL, SETTINGS).fetchone()
    return dict(zip(('pid', 'database', 'temporary_namespace') + AUTHORITY + SETTINGS, row, strict=True))



def exact_preseed_session(cur, expected, report):
    """Return the original session after removing only a redundant local self-role."""
    observed = session(cur)
    changed = sorted(key for key in expected if observed[key] != expected[key])
    report['preseed_session_changed_fields'] = changed
    report['preseed_local_self_role_reset'] = False
    if (changed == ['role'] and expected['role'] == 'none' and observed['role'] == LOGIN
            and all(expected[key] == observed[key] == LOGIN
                    for key in ('current_user', 'session_user', 'session_authorization'))):
        cur.execute('set local role none')
        observed = session(cur)
        report['preseed_local_self_role_reset'] = observed == expected
    return observed


def present_facts(cur, base, day):
    args = (base.OPERATOR_APP, base.OPERATOR_AUTH, base.BASE_PRODUCT, MODEL, MODEL,
            [CP3_SIZE, base.SIZE], base.LOCATION, list(LEDGER), day)
    facts, = cur.execute(FACTS_SQL, args).fetchone()
    require(facts['erp_usage'] is True and facts['period'] is not None and facts['period'][1] is True,
            'GLOBAL_FOUNDATION_EXISTING_USAGE_AND_ACTUAL_OPEN_PERIOD_REQUIRED')
    ledger = facts['ledger']
    require(type(ledger) is dict and set(ledger) == set(LEDGER)
            and all(len(row) == 4 and all(row[:2]) and row[2:] == [True, True] for row in ledger.values()),
            'GLOBAL_FOUNDATION_ACTIVE_POSTABLE_LEDGER_MAPPINGS_REQUIRED')
    return facts


def require_present(facts, base):
    owner = facts['owner']
    require(facts['app_users'] > 0 and owner is not None and owner[:4] == [base.OPERATOR_APP, base.OPERATOR_AUTH, 'OWNER', True]
            and owner[4] and owner[5:] == ['OWNER', True], 'GLOBAL_FOUNDATION_EXACT_ACTIVE_OWNER_REQUIRED')
    require(facts['product'] == [base.BASE_PRODUCT, MODEL, base.SIZE, 'CP6-RACE-SKU', True]
            and facts['model'] == [MODEL, 'CP3R3-MODEL', True]
            and facts['sizes'] == [[CP3_SIZE, 'CP3R3-SIZE', True], [base.SIZE, 'CP6-RACE-S', True]]
            and facts['location'] == [base.LOCATION, 'CP6-RACE-FG', 'FG_WAREHOUSE', True],
            'GLOBAL_FOUNDATION_EXACT_ACTIVE_PRODUCT_MODEL_SIZES_LOCATION_REQUIRED')
    return facts


class Foundation:
    def __init__(self, seed, identities, source, provider, actual_day):
        self.seed, self.identities, self.source = seed, identities, source
        self.provider, self.actual_day = provider, actual_day
        self.cursor = self.baseline = self.day = None

    def initialize(self, cur, report):
        require(self.cursor is None, 'GLOBAL_FOUNDATION_SINGLE_OWNING_INSTALLER_REQUIRED')
        conn = cur.connection
        require(not conn.autocommit and conn.info.host == '127.0.0.1' and conn.info.port == 54322
                and conn.info.dbname == 'cp6_rollback' and conn.info.user == LOGIN
                and conn.info.transaction_status.name == 'INTRANS', 'GLOBAL_FOUNDATION_FIXED_TRUSTED_INSTALLER_REQUIRED')
        initial = session(cur)
        proof = report['preseal_foundation'] = dict(status='INCOMPLETE', source=self.source, fresh_session=initial)
        require(initial['database'] == 'cp6_rollback' and initial['temporary_namespace'] == 0
                and tuple(initial[key] for key in AUTHORITY) == (LOGIN, LOGIN, 'none', LOGIN)
                and cur.execute('select pg_current_xact_id_if_assigned() is null').fetchone() == (True,),
                'GLOBAL_FOUNDATION_FRESH_FIXED_TRUSTED_LOGIN_REQUIRED')
        neutral = {key: (None, '') for key in GUC[2:]}
        neutral['request.jwt.claims'] += ('{}',)
        neutral.update({key: (None, '', 'off') for key in CP3_SWITCHES + SKU_SWITCHES})
        require(all(initial[key] in values for key, values in neutral.items()),
                'GLOBAL_FOUNDATION_NONNEUTRAL_INSTALLER_CONTEXT')
        initialized = [key for key in neutral if initial[key] is None]
        for key in initialized:
            cur.execute(SET_GUC, (key, ''))
        baseline = session(cur)
        require(baseline == dict(initial, **dict.fromkeys(initialized, '')),
                'GLOBAL_FOUNDATION_EXACT_NEUTRAL_BASELINE_REQUIRED')
        proof.update(initialized_neutral_GUCs=initialized, baseline=baseline)
        self.cursor, self.baseline = cur, baseline

    def verify(self, cur):
        require(self.day is not None and self.actual_day(cur) == self.day, 'GLOBAL_FOUNDATION_ACTUAL_WIB_DAY_CHANGED')
        return require_present(present_facts(cur, self.identities, self.day), self.identities)

    def bootstrap(self, cur, report):
        proof = report['preseal_foundation']
        require(cur is self.cursor and self.baseline is not None and 'before_seed_session' not in proof,
                'GLOBAL_FOUNDATION_ONE_PRESEAL_BOOTSTRAP_REQUIRED')
        proof['before_seed_session'] = exact_preseed_session(cur, self.baseline, proof)
        require(proof['before_seed_session'] == self.baseline, 'GLOBAL_FOUNDATION_PRESEED_SESSION_CHANGED')
        require(cur.execute(SCRATCH_SQL, (SCRATCH,)).fetchone() == (True,), 'GLOBAL_FOUNDATION_SCRATCH_COLLISION')
        day = self.actual_day(cur)
        before = self.provider.capture(cur)
        groups = self.provider.catalogue_profile.queries()
        require(len(groups) == 25 and before.keys() == groups.keys(), 'GLOBAL_FOUNDATION_COMPLETE_FULL25_REQUIRED')
        proof['full25_before'] = self.provider.fingerprint(cur, before)
        proof['before_rows_and_sequences'] = self.provider._timezone_snapshot(cur, lock=False)
        facts = proof['foundation_before'] = present_facts(cur, self.identities, day)
        proof['seed_invoked'] = facts['app_users'] == 0
        if proof['seed_invoked']:
            self.seed(cur)
            proof['seed_tail_session'] = tail = session(cur)
            require(tuple(tail[key] for key in AUTHORITY) == ('supabase_admin', 'supabase_admin', 'none', 'supabase_admin'),
                    'GLOBAL_FOUNDATION_EXACT_RETAINED_SEED_TAIL_AUTHORITY_REQUIRED')
            cur.execute('reset session authorization')
            for key in SETTINGS:
                if tail[key] != self.baseline[key]:
                    cur.execute(SET_GUC, (key, self.baseline[key]))
        require(cur.execute(SCRATCH_SQL, (SCRATCH,)).fetchone() == (True,), 'GLOBAL_FOUNDATION_SCRATCH_RESIDUE')
        proof['after_seed_session'] = session(cur)
        require(proof['after_seed_session'] == self.baseline, 'GLOBAL_FOUNDATION_SEED_SESSION_NOT_EXACTLY_RESTORED')
        after = self.provider.capture(cur)
        proof['full25_after'] = self.provider.fingerprint(cur, after)
        require(before == after and proof['full25_before'] == proof['full25_after'],
                'GLOBAL_FOUNDATION_SEED_CHANGED_FULL25')
        proof['after_rows_and_sequences'] = self.provider._timezone_snapshot(cur, lock=False)
        self.day = day
        proof['foundation_after'] = self.verify(cur)
        proof['status'] = 'VERIFIED_BEFORE_FIRST_GLOBAL_INSTALL'

    def after_commit(self, cur, report):
        conn = cur.connection
        proof = report['preseal_foundation']
        require(cur is self.cursor and conn.info.transaction_status.name == 'IDLE'
                and proof['status'] == 'VERIFIED_BEFORE_FIRST_GLOBAL_INSTALL',
                'GLOBAL_FOUNDATION_EXISTING_OWNING_COMMIT_REQUIRED')
        try:
            proof['after_commit_session'] = session(cur)
            require(proof['after_commit_session'] == self.baseline, 'GLOBAL_FOUNDATION_POSTCOMMIT_SESSION_CHANGED')
            proof['foundation_after_commit'] = self.verify(cur)
            require(proof['foundation_after_commit'] == proof['foundation_after'],
                    'GLOBAL_FOUNDATION_POSTCOMMIT_FOUNDATION_CHANGED')
            proof['status'] = 'VERIFIED_ON_EXISTING_INSTALLER_AFTER_COMMIT'
        finally:
            conn.rollback()
