"""Clock boundary/source controls only; no product clock or Native case."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
from hashlib import sha256
import importlib.util,json,subprocess,unittest,yaml

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('permanent_own_real_window_control',HERE/'attempt_policy.py')
policy=importlib.util.module_from_spec(spec);spec.loader.exec_module(policy)


class OwnWindow(unittest.TestCase):
    def test_job_guard_and_exact_one_constant_derivation_match(self):
        d=json.loads((HERE/'ATTEMPT_POLICY_DERIVATION.json').read_bytes())
        raw=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',d['source_commit']+':'+d['source_path']])
        self.assertEqual(sha256(raw).hexdigest(),d['original_sha256'])
        text=raw.decode()
        for change in d['changes']:
            self.assertEqual(text.count(change['before']),change['count'])
            text=text.replace(change['before'],change['after'],change['count'])
        self.assertEqual(text.encode(),(HERE/'attempt_policy.py').read_bytes())
        for change in reversed(d['changes']):text=text.replace(change['after'],change['before'],change['count'])
        self.assertEqual(text.encode(),raw)
        job=yaml.safe_load((ROOT/'.github/workflows/cp7-final-s03-sku-s05.yml').read_bytes())['jobs']['p21']
        self.assertEqual(policy.JOB_BUDGET_SECONDS,job['timeout-minutes']*60)
        self.assertEqual(policy.JOB_BUDGET_SECONDS,7200)
        self.assertTrue(any('current-final-s03-sku-s05-preparation/attempt_policy.py'in s.get('run','')
            for s in job['steps']))

    def test_real_aware_WIB_window_refuses_boundary_in_all_clock_zones(self):
        before=datetime(2026,10,31,14,59,59,tzinfo=timezone.utc)
        boundary=before+timedelta(seconds=1)
        for hours in (-12,0,7,14):
            tz=timezone(timedelta(hours=hours))
            with self.subTest(hours=hours):
                result=policy.require_window(before.astimezone(tz))
                self.assertEqual(result['business_day'],'2026-10-31')
                self.assertEqual(result['seconds_to_midnight'],7201)
                self.assertIs(result['product_clock_changed'],False)
                self.assertIs(result['automatic_group_retry'],False)
                with self.assertRaisesRegex(ValueError,'INSUFFICIENT_WIB_DAY_WINDOW'):
                    policy.require_window(boundary.astimezone(tz))
        with self.assertRaisesRegex(ValueError,'AWARE_REAL_CLOCK_REQUIRED'):
            policy.require_window(datetime(2026,10,31,21,0))


if __name__=='__main__':unittest.main()
