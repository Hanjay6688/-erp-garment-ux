"""Frozen S05 ACL refusal reproduced only in the declared local PGlite fixture.

The inherited fixture disables body compilation because it has no ERP tables.
No report function, Native command, hosted target or remote service is called.
The fixture's parent proof is explicitly an orchestration stub.
"""
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
spec = importlib.util.spec_from_file_location('s05_public_default_acl_retained_harness', HARNESS_PATH)
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)
# The first run used the current, still-frozen b0 files. Preserve that exact
# runner as retained/repro_FIRST.py, and bind subsequent historical repros to
# the retained b0 source instead of reading the repaired product accidentally.
for filename, digest in (
        ('stage.py', 'a30e254ddf5cba7f3f74524b2be98ce4a34c5008b4e775c25d79849f5eaa7d87'),
        ('report.sql', '44e26f9144cff011bf2fb9935d1a448955f8179a9ffaa6884557d8391651c5ab')):
    if sha256((HERE/'retained'/filename).read_bytes()).hexdigest() != digest:
        raise ValueError('S05_FROZEN_B0_REPRO_SOURCE_CHANGED: '+filename)
spec = importlib.util.spec_from_file_location('s05_public_default_acl_frozen_b0_stage', HERE/'retained/stage.py')
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)
harness.stage = stage  # Isolated local test module only, never a product runtime.
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


class PublicDefaultAclRepro(harness.OuterSuperuserControls):
    def faithful_defaults(self, extra=False):
        grantees = 'postgres,anon,authenticated,service_role'
        if extra:
            grantees += ',s05_external'
        self.cur.execute('alter default privileges for role supabase_admin in schema public '
                         'grant execute on functions to '+grantees)

    def refusal(self, label, extra=False):
        self.faithful_defaults(extra)
        before = self.snapshot()
        defaults = default_rows(self.cur)
        checker = stage.installer_function_grants
        seen = {}

        def observe_before_frozen_refusal(cur):
            seen.update(actual_function_grants=function_rows(cur),
                        default_acl=default_rows(cur), raw_public=self.snapshot()['raw_public'])
            return checker(cur)

        with patch.object(stage, 'installer_function_grants', side_effect=observe_before_frozen_refusal):
            with self.assertRaisesRegex(ValueError, 'S05_UNEXPECTED_INSTALLER_FUNCTION_GRANT: public\\.') as caught:
                self.install()
        self.assertBaseline(before)
        self.assertEqual(default_rows(self.cur), defaults)
        self.assertEqual(seen['default_acl'], defaults)
        self.assertEqual(seen['raw_public'], before['raw_public'])

        private = {signature: rows for signature, rows in seen['actual_function_grants'].items()
                   if signature != stage.PUBLIC}
        self.assertEqual(len(private), 4)
        for signature, rows in private.items():
            expected = {('postgres', 'postgres', 'EXECUTE', False)}
            if signature == stage.SCHEMA+'.workspace(date,date,uuid,uuid,text,integer,integer)':
                expected.add(('postgres', stage.ROLE, 'EXECUTE', False))
            self.assertEqual(set(rows), expected)
            self.assertEqual(len(rows), len(expected))

        expected_public = {(stage.ROLE, stage.ROLE, 'EXECUTE', False),
                           (stage.ROLE, 'authenticated', 'EXECUTE', False)}
        unexpected = {(stage.ROLE, 'postgres', 'EXECUTE', False)}
        if extra:
            unexpected.add((stage.ROLE, 's05_external', 'EXECUTE', False))
        actual_public = seen['actual_function_grants'][stage.PUBLIC]
        self.assertEqual(set(actual_public), expected_public | unexpected)
        self.assertEqual(len(actual_public), len(expected_public | unexpected))
        OBSERVED[label] = dict(expected_refusal=str(caught.exception),
            actual_before_refusal=seen, final_expected_public_acl=sorted(expected_public),
            local_unexpected_public_acl=sorted(unexpected),
            all_four_private_function_acl_checks_match=True,
            complete22_rows_sequences_raw_public_default_acl_identity_restored=True,
            actual_CI_extra_tuple_identity_proven=False)

    def test_frozen_public_default_postgres_reproduces(self):
        self.refusal('FAITHFUL_PUBLIC_DEFAULT_POSTGRES')

    def test_unexpected_external_default_remains_refused(self):
        self.refusal('UNEXPECTED_EXTERNAL_DEFAULT', extra=True)


def main():
    assert sys.argv[1:] == ['--repro']
    destination = Path(os.environ['S05_PUBLIC_DEFAULT_ACL_REPRO_RECEIPT'])
    if destination.exists():
        raise RuntimeError('S05_REPRO_RECEIPT_ALREADY_EXISTS_PRESERVE_FIRST_FAILURE')
    suite = unittest.TestSuite(PublicDefaultAclRepro(name) for name in (
        'test_frozen_public_default_postgres_reproduces',
        'test_unexpected_external_default_remains_refused'))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    pins = {}
    for path in (Path(__file__), HARNESS_PATH,
                 HARNESS_PATH.parent/'pglite_bridge.mjs',
                 HERE/'retained/stage.py', HERE/'retained/report.sql',
                 ROOT/'scripts/cp7_ow04_restore_bundle.py',
                 ROOT/'scripts/cp7_consumer_owning_install.py'):
        raw = path.read_bytes()
        pins[str(path.relative_to(ROOT))] = dict(bytes=len(raw), sha256=sha256(raw).hexdigest())
    receipt = dict(status='PASS_LOCAL_REFUSAL_REPRO_ONLY' if result.wasSuccessful() else 'FAIL_LOCAL_REPRO',
        command=dict(argv=sys.argv, S05_PGLITE_MODULE=os.environ.get('S05_PGLITE_MODULE'),
                     S05_PUBLIC_DEFAULT_ACL_REPRO_RECEIPT=str(destination), PYTHONDONTWRITEBYTECODE='1'),
        tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        unittest_output=stream.getvalue(), source_pins=pins,
        runtime=harness.OBSERVED, observed=OBSERVED, trace=harness.TRACE,
        local_fixture_only=True, ERP_body_compilation=False, ERP_function_calls=0,
        parent_verification='LOCAL_ORCHESTRATION_STUB_NOT_VENDOR_PARENT',
        Native_executions=0, actual_CI_extra_tuple_identity_proven=False,
        actual_CI_failure='S05_UNEXPECTED_INSTALLER_FUNCTION_GRANT_PUBLIC_WRAPPER',
        independent_acceptance=False, production_go=False)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('x') as out:
        json.dump(receipt, out, indent=2, default=str)
        out.write('\n')
    print(json.dumps({k: receipt[k] for k in ('status','tests_run','failures','errors','Native_executions')}))
    print(stream.getvalue())
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
