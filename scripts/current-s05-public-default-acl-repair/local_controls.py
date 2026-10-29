"""Actual local role/DDL controls; no Native SQL/body/business qualification."""
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import importlib.util
import io
import json
import os
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
HARNESS_PATH = ROOT/'scripts/current-s05-native10-qualification/owner_transfer/test_outer_superuser.py'
spec = importlib.util.spec_from_file_location('s05_default_acl_current_local_harness', HARNESS_PATH)
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)
stage = harness.stage
OBSERVED = {}


def default_rows(cur):
    return cur.execute("select pg_get_userbyid(d.defaclrole)::text,"
        "coalesce(n.nspname::text,'GLOBAL'),d.defaclobjtype::text,d.defaclacl::text "
        "from pg_default_acl d left join pg_namespace n on n.oid=d.defaclnamespace "
        "order by 1,2,3").fetchall()


def function_rows(cur):
    return {signature: cur.execute(
        "select pg_get_userbyid(a.grantor)::text,case when a.grantee=0 then 'PUBLIC' "
        "else pg_get_userbyid(a.grantee)::text end,a.privilege_type,a.is_grantable "
        "from pg_proc p cross join lateral aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a "
        "where p.oid=%s::regprocedure order by 1,2,3,4", (signature,)).fetchall()
        for signature in stage.FUNCTIONS}


class DefaultAclControls(harness.OuterSuperuserControls):
    def defaults(self, *, global_scope=False, extra=(), installer='supabase_admin'):
        grantees = ('postgres', 'anon', 'authenticated', 'service_role')+tuple(extra)
        self.cur.execute('alter default privileges for role '+installer+
                         ('' if global_scope else ' in schema public')+
                         ' grant execute on functions to '+','.join(grantees))

    def cycle(self, label):
        before = self.snapshot()
        defaults = default_rows(self.cur)
        cycles = []
        for phase in ('INSTALL_INVERSE', 'REINSTALL_INVERSE'):
            state = self.install()
            grants = stage.installer_function_grants(self.cur)
            self.assertEqual(len(grants), 5)
            self.assertEqual(set(map(tuple, grants[stage.PUBLIC])),
                {(stage.ROLE, stage.ROLE, 'EXECUTE', False),
                 (stage.ROLE, 'authenticated', 'EXECUTE', False)})
            self.assertEqual(self.snapshot()['raw_public'], before['raw_public'])
            self.assertEqual(default_rows(self.cur), defaults)
            self.installed(self.cur, state)
            cycles.append(dict(phase=phase, actual_function_grants=grants,
                installer=state['installer_capability'], default_acl=defaults,
                raw_public=self.snapshot()['raw_public']))
            self.uninstall(state)
            self.assertBaseline(before)
            self.assertEqual(default_rows(self.cur), defaults)
        OBSERVED[label] = dict(cycles=cycles,
            strict_public_two_and_private_four_unchanged=True,
            complete22_rows_sequences_raw_public_default_acl_identity_restored=True)

    def test_schema_defaults_explicit_public_acl(self):
        self.defaults()
        self.cycle('SCHEMA_DEFAULTS_EXPLICIT_PUBLIC_ACL')

    def test_schema_defaults_raw_null_public_acl(self):
        self.cur.execute('drop schema public cascade;create schema public authorization postgres')
        self.assertIsNone(self.snapshot()['raw_public'][1])
        self.defaults()
        self.cycle('SCHEMA_DEFAULTS_RAW_NULL_PUBLIC_ACL')

    def test_global_and_schema_defaults(self):
        self.defaults(global_scope=True)
        self.defaults()
        self.cycle('GLOBAL_AND_SCHEMA_DEFAULTS')

    def test_supported_postgres_outer_profile(self):
        self.cur.execute('set local role postgres')
        self.defaults(installer='postgres')
        self.cycle('POSTGRES_OUTER_SUPERUSER_PROFILE')

    def refused(self, label, *, global_scope=False, extra=('s05_external',)):
        self.defaults(global_scope=global_scope, extra=extra)
        before = self.snapshot()
        defaults = default_rows(self.cur)
        with self.assertRaisesRegex(ValueError, 'S05_UNEXPECTED_INSTALLER_FUNCTION_GRANT: ') as caught:
            self.install()
        message = str(caught.exception)
        signature, raw = message.removeprefix('S05_UNEXPECTED_INSTALLER_FUNCTION_GRANT: ').split('; ', 1)
        diagnostic = json.loads(raw)
        self.assertEqual(diagnostic['installer'], 'supabase_admin')
        self.assertEqual(diagnostic['row_limit'], 16)
        self.assertLessEqual(len(diagnostic['actual_acl_rows']), 16)
        self.assertLessEqual(len(diagnostic['installer_function_default_acl_rows']), 16)
        self.assertEqual(diagnostic['actual_acl_total']-len(diagnostic['actual_acl_rows']), diagnostic['actual_acl_omitted'])
        self.assertEqual(diagnostic['installer_function_default_acl_total']-
                         len(diagnostic['installer_function_default_acl_rows']),
                         diagnostic['installer_function_default_acl_omitted'])
        self.assertLess(len(message.encode()), 10000)
        self.assertBaseline(before)
        self.assertEqual(default_rows(self.cur), defaults)
        OBSERVED[label] = dict(signature=signature, actual_failure_diagnostic=diagnostic,
            raw_message=message, default_acl=defaults,
            complete22_rows_sequences_raw_public_default_acl_identity_restored=True)
        return signature, diagnostic

    def test_unknown_public_default_refused_with_actual_diagnostic(self):
        signature, diagnostic = self.refused('UNKNOWN_PUBLIC_DEFAULT')
        self.assertEqual(signature, stage.PUBLIC)
        self.assertEqual(set(map(tuple, diagnostic['actual_acl_rows'])),
            {(stage.ROLE, stage.ROLE, 'EXECUTE', False),
             (stage.ROLE, 'authenticated', 'EXECUTE', False),
             (stage.ROLE, 's05_external', 'EXECUTE', False)})
        self.assertEqual(diagnostic['actual_acl_omitted'], 0)
        self.assertEqual(diagnostic['installer_function_default_acl_omitted'], 0)
        self.assertTrue(any(row[1]=='public' and row[4]=='postgres'
                            for row in diagnostic['installer_function_default_acl_rows']))

    def test_unknown_global_default_refused_on_private_function(self):
        signature, diagnostic = self.refused('UNKNOWN_GLOBAL_DEFAULT', global_scope=True)
        self.assertEqual(signature, stage.SCHEMA+'.iso(timestamp with time zone)')
        self.assertIn(['postgres', 's05_external', 'EXECUTE', False], diagnostic['actual_acl_rows'])
        self.assertTrue(all(row[1]=='GLOBAL' for row in diagnostic['installer_function_default_acl_rows']))

    def test_diagnostics_bounded_without_hiding_omitted_counts(self):
        roles = tuple('s05_unexpected_'+str(i).zfill(2) for i in range(24))
        for role in roles:
            self.cur.execute('create role '+role+' nologin')
        signature, diagnostic = self.refused('BOUNDED_UNKNOWN_DEFAULT', extra=roles)
        self.assertEqual(signature, stage.PUBLIC)
        self.assertEqual(diagnostic['actual_acl_total'], 26)
        self.assertEqual(diagnostic['actual_acl_omitted'], 10)
        self.assertEqual(diagnostic['installer_function_default_acl_total'], 28)
        self.assertEqual(diagnostic['installer_function_default_acl_omitted'], 12)

    def test_failure_after_new_revoke_is_atomic(self):
        self.defaults()
        before = self.snapshot()
        defaults = default_rows(self.cur)
        needle = 'grant execute on function '+stage.PUBLIC+'to authenticated;'
        sql = (ROOT/'scripts/cp7_accessory_standard_report/report.sql').read_text()
        self.assertEqual(sql.count(needle), 1)
        self.assertIn('from public,anon,service_role,cp7_capture,postgres;', sql)
        def inject(text):
            return text.replace(needle, 'select 1/0;\n'+needle, 1) if needle in text else text
        self.cur.hook = inject
        try:
            with self.assertRaises(harness.DatabaseError) as caught:
                self.install()
            self.assertEqual(caught.exception.code, '22012')
        finally:
            self.cur.hook = None
        self.assertBaseline(before)
        self.assertEqual(default_rows(self.cur), defaults)
        OBSERVED['AFTER_NEW_REVOKE_BEFORE_AUTHENTICATED_GRANT'] = dict(sqlstate='22012',
            complete22_rows_sequences_raw_public_default_acl_identity_restored=True)


NAMES = (
    'test_schema_defaults_explicit_public_acl', 'test_schema_defaults_raw_null_public_acl',
    'test_global_and_schema_defaults', 'test_supported_postgres_outer_profile',
    'test_unknown_public_default_refused_with_actual_diagnostic',
    'test_unknown_global_default_refused_on_private_function',
    'test_diagnostics_bounded_without_hiding_omitted_counts',
    'test_failure_after_new_revoke_is_atomic')


def main():
    assert sys.argv[1:] == ['--local-controls']
    destination = Path(os.environ['S05_PUBLIC_DEFAULT_ACL_CONTROLS_RECEIPT'])
    if destination.exists():
        raise RuntimeError('S05_LOCAL_RECEIPT_EXISTS_PRESERVE_FIRST_FAILURE')
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.TestSuite(DefaultAclControls(name) for name in NAMES))
    pins = {}
    for path in (Path(__file__), HARNESS_PATH, HARNESS_PATH.parent/'pglite_bridge.mjs',
                 ROOT/'scripts/cp7_accessory_standard_report/stage.py',
                 ROOT/'scripts/cp7_accessory_standard_report/report.sql',
                 ROOT/'scripts/cp7_ow04_restore_bundle.py', ROOT/'scripts/cp7_consumer_owning_install.py'):
        raw = path.read_bytes()
        pins[str(path.relative_to(ROOT))] = dict(bytes=len(raw), sha256=sha256(raw).hexdigest())
    receipt = dict(status='PASS_LOCAL_ROLE_DDL_ONLY' if result.wasSuccessful() else 'FAIL_LOCAL_ROLE_DDL',
        tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        unittest_output=stream.getvalue(), runtime=harness.OBSERVED, observed=OBSERVED,
        source_pins=pins, trace=harness.TRACE,
        command=dict(argv=sys.argv, S05_PGLITE_MODULE=os.environ.get('S05_PGLITE_MODULE'),
                     S05_PUBLIC_DEFAULT_ACL_CONTROLS_RECEIPT=str(destination), PYTHONDONTWRITEBYTECODE='1'),
        local_fixture_only=True, ERP_body_compilation=False, ERP_function_calls=0,
        parent_verification='LOCAL_ORCHESTRATION_STUB_NOT_VENDOR_PARENT',
        Native_executions=0, actual_CI_extra_tuple_identity_proven=False,
        independent_acceptance=False, production_go=False)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('x') as out:
        json.dump(receipt, out, indent=2, default=str)
        out.write('\n')
    print(json.dumps({k:receipt[k] for k in ('status','tests_run','failures','errors','Native_executions')}))
    print(stream.getvalue())
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
