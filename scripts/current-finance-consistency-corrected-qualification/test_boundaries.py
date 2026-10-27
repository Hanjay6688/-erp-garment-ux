from hashlib import sha256
from pathlib import Path
import unittest
import evidence,source_guard,workflow_guard

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]


class FocusedEvidenceBoundaries(unittest.TestCase):
    def test_first_whole_failure_cannot_be_relabelled_PASS(self):
        for config in ({},{'allow_database_execution':False,'retained64':{'status':'INCOMPLETE'}},
            {'allow_database_execution':True,'retained64':{'status':'PASS'}}):
            with self.subTest(config=config),self.assertRaisesRegex(ValueError,'ACTUAL64_REQUIRED'):evidence.gate(config)

    def test_both_raw_original_and_package_bytes_are_bound(self):
        raw=b'{}';package=b'{}';proof=dict(bytes=2,sha256=sha256(raw).hexdigest(),package_bytes=2,package_sha256=sha256(package).hexdigest())
        for key in proof:
            changed=dict(proof);changed[key]='tampered'
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'ACTUAL64_BYTES_CHANGED'):
                evidence.retained(changed,raw,package,{})

    def test_full_restore_probe_assertions_are_retained(self):
        result=source_guard.check(ROOT,HERE)
        self.assertEqual(result['probe.py']['assertions_retained'],9)
        self.assertEqual(result['runner.py']['assertions_retained'],14)
        text=(HERE/'probe.py').read_text().replace("assert restored['only_pg_cron_errors']","pass",1)
        with self.assertRaisesRegex(AssertionError,'UNDECLARED_PROBE_OR_RESTORE_CHANGE'):
            source_guard.check(ROOT,HERE,overrides={'probe.py':text})

    def test_skipping_actual_focused_runtime_is_refused(self):
        value=workflow_guard.expected(ROOT,HERE)
        step=[s for s in value['jobs']['p21']['steps']if s.get('name')=='Run corrected unchanged Native20 and actual minute cron with full restoration']
        self.assertEqual(len(step),1);step[0]['run']='true'
        with self.assertRaisesRegex(AssertionError,'FOCUSED_UNDECLARED_WORKFLOW_CHANGE'):
            workflow_guard.check(ROOT,HERE,actual=value)


if __name__=='__main__':unittest.main()
