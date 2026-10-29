"""Actual local PGlite role/DDL controls. Not Native or vendor acceptance.

Runs frozen report.sql bytes with check_function_bodies=off solely because the
ERP source tables are intentionally absent. No report function is called.
The 22 original catalog queries/data comparator and original atomic function
are source-extracted without importing any runtime or opening another DB.
Parent verification is a labelled local orchestration stub, never qualified.
"""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast
import importlib.util
import json
import os
import subprocess
import unittest
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
COMPONENT = ROOT/'scripts/cp7_accessory_standard_report'
TRACE = []
OBSERVED = {}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


stage = load('s05_local_outer_stage', COMPONENT/'stage.py')


class DatabaseError(Exception):
    def __init__(self, value):
        self.code = value['code']; super().__init__(value['message'])


class Cursor:
    def __init__(self, process):
        self.process = process; self.failed = False; self.rows = []; self.hook = None
        cursor = self
        class Connection:
            autocommit = False
            @property
            def info(self):
                return SimpleNamespace(transaction_status='INERROR' if cursor.failed else 'INTRANS')
            @contextmanager
            def transaction(self):
                cursor.execute('savepoint s05_inherited_atomic')
                try:
                    yield
                except BaseException:
                    cursor.execute('rollback to savepoint s05_inherited_atomic')
                    cursor.execute('release savepoint s05_inherited_atomic')
                    raise
                else:
                    cursor.execute('release savepoint s05_inherited_atomic')
        self.connection = Connection()
    def execute(self, sql, params=None, **_):
        sql = str(sql)
        if self.hook is not None:
            sql = self.hook(sql)
        request = dict(sql=sql)
        if params is not None: request['params'] = list(params)
        started=time.monotonic()
        self.process.stdin.write(json.dumps(request)+'\n'); self.process.stdin.flush()
        response = json.loads(self.process.stdout.readline())
        if 'error' in response:
            self.failed = True
            TRACE.append(dict(sql=sql, params=params, error=response['error'],elapsed=time.monotonic()-started))
            raise DatabaseError(response['error'])
        if sql.lstrip().lower().startswith(('rollback', 'begin')): self.failed = False
        self.rows = [tuple(row) for row in response['rows']]
        TRACE.append(dict(sql=sql, params=params, rows=self.rows,elapsed=time.monotonic()-started))
        return self
    def fetchone(self): return self.rows[0] if self.rows else None
    def fetchall(self): return list(self.rows)
    def __iter__(self): return iter(self.rows)


class SQL(str):
    def format(self, *args): return SQL(str(self).format(*args))


def identifier(*names):
    return '.'.join('"'+name.replace('"','""')+'"' for name in names)


def extracted_catalog():
    path = ROOT/'scripts/cp7_ow04_restore_bundle.py'
    names = {'canonical','digest','_acl','_catalog','_authority','_catalog_rows','_data'}
    variables = {'NAMESPACE','QUERIES'}
    nodes = [node for node in ast.parse(path.read_text()).body
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names
             or isinstance(node, ast.Assign) and any(isinstance(t,ast.Name) and t.id in variables for t in node.targets)]
    values = dict(json=json, sha256=sha256, contextmanager=contextmanager,
                  TransactionStatus=SimpleNamespace(INERROR='INERROR'), sql=SimpleNamespace(SQL=SQL,Identifier=identifier))
    exec(compile(ast.Module(body=nodes,type_ignores=[]), str(path), 'exec'), values)
    return SimpleNamespace(**{name: values[name] for name in names | variables})


def extracted_atomic():
    path = ROOT/'scripts/cp7_consumer_owning_install.py'
    node = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == 'atomic')
    values = dict(contextmanager=contextmanager)
    exec(compile(ast.Module(body=[node],type_ignores=[]), str(path), 'exec'), values)
    return values['atomic']


catalog = extracted_catalog()
atomic = extracted_atomic()


class OuterSuperuserControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.environ.get('S05_PGLITE_MODULE'):
            raise RuntimeError('Installed local PGlite required; no download or Native DB fallback')
        cls.process = subprocess.Popen(['node', str(HERE/'pglite_bridge.mjs')], stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=os.environ.copy())
        cls.cur = Cursor(cls.process)
        OBSERVED['version'] = cls.cur.execute('select version()').fetchone()[0]
        OBSERVED['dependency_version'] = json.loads((Path(os.environ['S05_PGLITE_MODULE'])/'package.json').read_bytes())['version']
        for role in ('anon','authenticated','service_role','cp7_capture','s05_external'):
            cls.cur.execute('create role '+role+' nologin')
        cls.cur.execute('create role supabase_admin nologin superuser')
        cls.cur.execute('set session authorization supabase_admin')
        # PGlite protects bootstrap postgres from attribute changes. The first
        # fixture failure is retained; no product rule depends on its flag.
        cls.cur.execute("set check_function_bodies=off")
        cls.cur.execute('create table public.s05_local_sentinel(id integer primary key,value text)')
        cls.cur.execute("insert into public.s05_local_sentinel values(1,'unchanged')")
        cls.cur.execute('create sequence public.s05_local_sequence start 7')
    @classmethod
    def tearDownClass(cls):
        cls.process.stdin.write('{"close":true}\n'); cls.process.stdin.flush(); cls.process.stdin.close()
        cls.process.wait(timeout=15)
        stderr = cls.process.stderr.read()
        if stderr: OBSERVED['adapter_stderr'] = stderr
    def setUp(self):
        self.cur.hook = None
        self.cur.execute('begin')
        self.addCleanup(self.reset_fixture_identity)
        self.parent = SimpleNamespace(runtime=lambda: (None,None,None,SimpleNamespace(atomic=atomic),catalog),
            sources=lambda: {'LOCAL_ORCHESTRATION_STUB_NOT_VENDOR_PARENT': True},
            verify=lambda *_: {'LOCAL_ORCHESTRATION_STUB_NOT_VENDOR_PARENT': True})
        self.sources_patch = patch.object(stage, 'sources', return_value={'LOCAL_ROLE_DDL_FIXTURE_ONLY': True})
        self.parent_patch = patch.object(stage, 'parent', return_value=self.parent)
        self.verify_patch = patch.object(stage, 'verify', side_effect=self.installed)
        for control in (self.sources_patch,self.parent_patch,self.verify_patch): control.start()
        self.initial = self.snapshot()
    def tearDown(self):
        self.cur.hook = None
        for control in (self.verify_patch,self.parent_patch,self.sources_patch): control.stop()
        self.cur.execute('rollback')
    def reset_fixture_identity(self):
        self.cur.hook=None
        self.cur.execute('rollback')
        self.cur.execute('reset session authorization')
        self.cur.execute('reset role')
        self.cur.execute('set session authorization supabase_admin')
    def snapshot(self):
        return dict(catalog=catalog._catalog_rows(self.cur),data=catalog._data(self.cur),
            raw_public=self.cur.execute("select pg_get_userbyid(nspowner)::text,nspacl::text from pg_namespace where nspname='public'").fetchone(),
            identity=self.cur.execute("select current_user::text,session_user::text,current_setting('createrole_self_grant')").fetchone())
    def installed(self, cur, state):
        # These are actual local catalogs/owners/ACLs, not a vendor proof.
        actual = catalog._catalog_rows(cur)
        self.assertEqual(actual,state['after']); stage.transition(state['before'],actual)
        self.assertEqual(catalog._data(cur),state['data'])
        self.assertEqual(cur.execute('select rolcanlogin,rolinherit,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls from pg_roles where rolname=%s',(stage.ROLE,)).fetchone(),(False,)*7)
        self.assertEqual(cur.execute('select count(*) from pg_auth_members where roleid=%s::regrole or member=%s::regrole',(stage.ROLE,stage.ROLE)).fetchone()[0],0)
        for sig,(definer,volatility) in stage.FUNCTIONS.items():
            row = cur.execute('select pg_get_userbyid(proowner)::text,prosecdef,provolatile::text,proconfig,prosrc from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()
            self.assertEqual(row,(stage.ROLE if sig==stage.PUBLIC else 'postgres',definer,volatility,['search_path=""'],stage.function_sources()[sig.split('(')[0]]))
        stage.installer_function_grants(cur)
        return {'LOCAL_ROLE_DDL_AND_UNCHANGED_FUNCTION_BODIES_ONLY': True}
    def install(self): return stage.install_delta(self.cur,{'LOCAL_STUB':True})
    def uninstall(self,state): return stage.uninstall_delta(self.cur,state,{'LOCAL_STUB':True})
    def assertBaseline(self,expected=None): self.assertEqual(self.snapshot(),self.initial if expected is None else expected)

    def test_outer_su_original_whole_sql_preuse_uninstall_reinstall(self):
        self.cur.execute("select set_config('createrole_self_grant','set, inherit',true)")
        self.initial=self.snapshot()
        one=self.install(); self.installed(self.cur,one)
        self.assertEqual(one['installer_capability']['outer_role'],'supabase_admin')
        self.assertTrue(one['installer_capability']['outer_current_superuser'])
        self.assertEqual(self.cur.execute("select nspacl::text from pg_namespace where nspname='public'").fetchone()[0],self.initial['raw_public'][1])
        self.uninstall(one); self.assertBaseline()
        two=self.install(); self.assertEqual(one['after'],two['after'])
        self.uninstall(two); self.assertBaseline()
        OBSERVED['successful_outer_profile']=one['installer_capability']
        OBSERVED['local_full_catalog_groups']=len(one['after'])

    def test_raw_null_public_acl_preserved_without_grant_revoke(self):
        # Recreate only this disposable schema normally; never update catalogs.
        self.cur.execute('drop schema public cascade;create schema public authorization postgres')
        self.initial=self.snapshot(); self.assertIsNone(self.initial['raw_public'][1])
        state=self.install(); self.assertIsNone(self.snapshot()['raw_public'][1])
        self.uninstall(state); self.assertBaseline()
        OBSERVED['raw_NULL_profile']='PRESERVED_NULL_WITHOUT_SCHEMA_GRANT_REVOKE'

    def test_nonsuper_outer_refused_before_any_ddl(self):
        self.cur.execute('reset session authorization')
        self.cur.execute('alter role supabase_admin nosuperuser')
        before=self.snapshot()
        self.cur.execute('set local role supabase_admin')
        self.assertFalse(self.cur.execute('select rolsuper from pg_roles where rolname=current_user').fetchone()[0])
        index=len(TRACE)
        with self.assertRaisesRegex(ValueError,'SUPERUSER_REQUIRED_BEFORE_DDL'): self.install()
        self.cur.execute('reset role')
        self.assertBaseline(before)
        self.assertFalse(any('create role cp7_accessory_standard_read' in row['sql'] for row in TRACE[index:]))

    def test_existing_role_and_unexpected_default_acl_refused_atomically(self):
        self.cur.execute('create role '+stage.ROLE+' nologin')
        before=self.snapshot()
        with self.assertRaisesRegex(ValueError,'ALREADY_INSTALLED'): self.install()
        self.assertBaseline(before)
        self.cur.execute('drop role '+stage.ROLE)
        self.cur.execute('alter default privileges for role supabase_admin grant execute on functions to s05_external')
        before=self.snapshot()
        with self.assertRaisesRegex(ValueError,'UNEXPECTED_INSTALLER_FUNCTION_GRANT'): self.install()
        self.assertBaseline(before)

    def test_sql_error_after_create_role_or_public_owner_is_atomic(self):
        for label,needle in (('AFTER_CREATE_ROLE', 'create schema cp7_accessory_standard_report'),
                             ('AFTER_PUBLIC_OWNER','revoke all on function public.erp_cp7_get_accessory_standard_report_v1')):
            def inject(sql):
                return sql.replace(needle,'select 1/0;\n'+needle,1) if stage.ROLE in sql and 'create role' in sql else sql
            self.cur.hook=inject
            try:
                with self.assertRaises(DatabaseError) as caught: self.install()
                self.assertEqual(caught.exception.code,'22012')
            finally: self.cur.hook=None
            self.assertBaseline()
            OBSERVED[label]='ERROR_22012_AND_EXACT_RESTORE'

    def test_post_install_validation_error_is_atomic(self):
        with patch.object(stage,'transition',side_effect=ValueError('LOCAL_AFTER_DDL_VALIDATION_ERROR')):
            with self.assertRaisesRegex(ValueError,'AFTER_DDL_VALIDATION'): self.install()
        self.assertBaseline()

    def test_inverse_error_after_drop_owned_is_atomic(self):
        state=self.install(); before=self.snapshot()
        def inject(sql):
            return sql.replace('; drop role','; select 1/0; drop role',1) if sql.startswith('drop owned by ') else sql
        self.cur.hook=inject
        try:
            with self.assertRaises(DatabaseError) as caught: self.uninstall(state)
            self.assertEqual(caught.exception.code,'22012')
        finally: self.cur.hook=None
        self.assertBaseline(before)
        self.uninstall(state); self.assertBaseline()

    def test_outer_su_catalog_equals_original_postgres_su_install(self):
        state=self.install(); current=state['after']; self.uninstall(state); self.assertBaseline()
        baseline=self.snapshot()
        self.cur.execute('set local role postgres')
        self.cur.execute((COMPONENT/'report.sql').read_text())
        original=catalog._catalog_rows(self.cur)
        self.assertEqual(current,original)
        self.cur.execute('reset role')
        self.uninstall({'before':baseline['catalog'],'data':baseline['data'],'after':original})
        self.assertBaseline(baseline)
        OBSERVED['original_postgres_superuser_vs_outer_superuser']='ALL22_EXACTLY_EQUAL'


def main():
    destination=os.environ.get('S05_LOCAL_ROLE_RECEIPT')
    if not destination: raise RuntimeError('S05_LOCAL_ROLE_RECEIPT is required; choose a new path to retain first failures')
    path=Path(destination)
    if path.exists(): raise RuntimeError('Refusing overwrite of retained local role receipt')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(OuterSuperuserControls))
    value=dict(classification='LOCAL_PGLITE_ACTUAL_ROLE_DDL_NOT_NATIVE_NOT_VENDOR_ACCEPTANCE',
        Native_executions=0, ERP_function_calls=0, check_function_bodies='off_LOCAL_ONLY_ERP_ABSENT',
        parent_verification='EXPLICIT_LOCAL_ORCHESTRATION_STUB', production_go=False, independent_acceptance=False,
        tests_run=result.testsRun,failures=[{'test':str(t),'trace':trace}for t,trace in result.failures],
        errors=[{'test':str(t),'trace':trace}for t,trace in result.errors],status='PASS_LOCAL_ONLY'if result.wasSuccessful()else'FAIL_LOCAL_ONLY',
        observed=OBSERVED, trace=TRACE,
        source_sha256={str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest() for p in
            (COMPONENT/'stage.py',COMPONENT/'report.sql',HERE/'pglite_bridge.mjs',Path(__file__),
             ROOT/'scripts/cp7_ow04_restore_bundle.py',ROOT/'scripts/cp7_consumer_owning_install.py')})
    path.write_text(json.dumps(value,indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__=='__main__':main()
