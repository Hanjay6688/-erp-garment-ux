"""Mock/source controls only; never a Native, Auth or package result."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import ast
import importlib.util
import json
import subprocess
import sys
import unittest
import yaml

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value
gate = load('sku_unit_gate', HERE / 'gate.py')
plan = load('sku_unit_plan', HERE / 'plan.py')
derive = load('sku_unit_derive', HERE / 'derive.py')
admission = load('sku_unit_admission', HERE / 'admission.py')
workflow = load('sku_unit_workflow', HERE / 'workflow.py')


def sample(mutate=lambda a, p: None):
    sources = {'LOCAL_SYNTHETIC_ONLY': True}
    group = dict(counts={'PASS': 7}, cases={key: dict(status='PASS', full_boundary_restored=True) for key in plan.NATIVE_IDS})
    group['cases'][gate.MIXED_CASE].update(preview_caller_zones_checked=gate.CALLER_ZONES,
      all_preview_fields_equal_across_zones=True,preview_caller_setting_restored=True,posting_function_timezone='UTC')
    a = dict(label='CP7_SKU_PAIR_CONVERSION_NATIVE', status='PASS', qualification_commit=gate.BASE,
      cp6_restored=True, advisor_gate=True, baseline_full22_all_rows_all_sequences_equal=True, baseline_advisors_equal=True,
      used_guard_refused_before_DDL=True, required_case_ids_pass=True, expected_case_count=1, observed_case_count=1,
      required_case_ids=[gate.NATIVE_CASE], focused_preuse_removal={'used_guard_before_DDL': True},
      source_declaration={'current_installation': sources}, committed={gate.NATIVE_CASE: dict(status='PASS', used_guard_refused_before_DDL=True, native=group)})
    p = dict(gate={key: True for key in ('installed', 'primary_unchanged', 'backup_restore_drill', 'security_advisors', 'writer_runtime')},
      run_identity={'tool_head': gate.BASE}, writer_runtime={'status': 'PASS'}, auth_users_before=0, auth_users_after=0)
    mutate(a, p); raw=json.dumps(a).encode(); pkg=json.dumps(p).encode()
    cfg = dict(pending_run_id=40880000000, accepted_native7=dict(head=gate.BASE, tree=gate.TREE, run_id=40880000000,
      original=dict(name='LOCAL_ONLY.json', bytes=len(raw), sha256=sha256(raw).hexdigest()),
      package=dict(name='LOCAL_ONLY_PACKAGE.json', bytes=len(pkg), sha256=sha256(pkg).hexdigest())))
    return cfg, raw, pkg, sources


class Preparation(unittest.TestCase):
    def test_literal_scope_is_7_base_3_cost_3_race_6_admin_wait_4_browser(self):
        self.assertEqual(tuple(map(len,(plan.NATIVE_IDS,plan.COST_IDS,plan.RACE_IDS,plan.WAIT_IDS,plan.BROWSER_IDS))),(7,3,3,6,4))
        cfg=json.loads((HERE/'CONFIG.json').read_bytes());self.assertFalse(cfg['group_recovery_supported'])
        self.assertEqual(cfg['expected_counts']['Auth_HTTP'],0)

    def test_unpinned_prerequisite_refuses_before_runtime_import_or_get(self):
        for script in ('check.py','fetch_prerequisite.py'):
            # The checked-in configuration is deliberately null in preparation.
            if json.loads((HERE/'CONFIG.json').read_bytes())['accepted_native7'] is None:
                run=subprocess.run([sys.executable,'-B',str(HERE/script)],capture_output=True,text=True)
                self.assertNotEqual(run.returncode,0)
                self.assertIn('CLOSED_TERMINAL_21C_NATIVE7',run.stderr)
                self.assertNotIn('ModuleNotFoundError',run.stderr)
        with self.assertRaisesRegex(ValueError,'CLOSED_TERMINAL'):
            gate.selected({'accepted_native7':None})

    def test_exact_mock_bytes_admit_no_new_runtime_credit(self):
        cfg,raw,pkg,source=sample();proof=gate.admitted(cfg,raw,pkg,source,plan.NATIVE_IDS)
        self.assertEqual(proof['fresh_cases_credited'],0)
        with self.assertRaisesRegex(ValueError,'BYTES_CHANGED'):
            gate.admitted(cfg,raw+b' ',pkg,source,plan.NATIVE_IDS)

    def test_partial_native_boundary_package_auth_or_current_source_never_unlocks(self):
        changes=[lambda a,p:a.update(status='INCOMPLETE'),lambda a,p:a.update(cp6_restored=False),
          lambda a,p:a['committed'][gate.NATIVE_CASE]['native'].update(counts={'PASS':6}),
          lambda a,p:a['committed'][gate.NATIVE_CASE]['native']['cases'][plan.NATIVE_IDS[0]].update(full_boundary_restored=False),
          lambda a,p:p['gate'].update(writer_runtime=False),lambda a,p:p.update(auth_users_after=1),lambda a,p:p.pop('auth_users_before')]
        for mutation in changes:
            cfg,raw,pkg,source=sample(mutation)
            with self.assertRaises(ValueError):gate.admitted(cfg,raw,pkg,source,plan.NATIVE_IDS)
        cfg,raw,pkg,source=sample()
        with self.assertRaisesRegex(ValueError,'DIFFERS_FROM_RETAINED'):
            gate.admitted(cfg,raw,pkg,{'OTHER':True},plan.NATIVE_IDS)

    def test_counted_vendor_engine_derivation_retains_all_other_bytes(self):
        raw=(ROOT/'scripts/current-vendor-receivable-qualification/probe.py').read_bytes()
        text,proof=derive.derive(raw);ast.parse(text);self.assertEqual(proof['counted_changes'],5)
        for before,after in reversed(derive.REPLACEMENTS):
            self.assertEqual(text.count(after),1);text=text.replace(after,before,1)
        self.assertEqual(text.encode(),raw)
        with self.assertRaises(ValueError):derive.derive(raw+derive.REPLACEMENTS[0][0].encode())

    def test_historical_source_scope_derivation_keeps_every_hash_oracle(self):
        raw=(ROOT/'scripts/current-sku-pair-native-adapter/admission.py').read_bytes()
        changed,proof=admission.historical_native_admission(raw)
        self.assertEqual(proof['counted_changes'],1)
        self.assertEqual(changed.replace("cfg['base_head'], '"+gate.BASE+"'","cfg['base_head'], 'HEAD'").encode(),raw)

    def test_new_workflow_is_exact_child_and_old_setup_restore_steps_stay(self):
        cfg=json.loads((HERE/'CONFIG.json').read_bytes())
        old=yaml.safe_load((ROOT/workflow.OLD).read_text());new=yaml.safe_load((ROOT/workflow.NEW).read_text())
        self.assertEqual(new,workflow.derive(old,cfg['branch']))
        steps=new['jobs']['p21']['steps'];names=[s.get('name')for s in steps]
        self.assertLess(names.index('Require terminal exact Native21c Original and package before any database'),names.index('Start disposable database'))
        for s in old['jobs']['p21']['steps']:
            if s.get('name') in ('Admit exact vendor parent and declared SKU child before database','Run actual SKU Native cases and complete restoration',
              'Preserve exact original JSON report bytes in a bounded compressed log receipt') or s.get('uses','').startswith('actions/upload-artifact@'):continue
            self.assertIn(s,steps)
        self.assertEqual(new['jobs']['p21']['env']['AUDITOR_UI_MODE'],'DISPOSABLE')
        self.assertTrue(all(s.get('if')=='always()'for s in steps if s.get('name')in('Remove disposable database','Preserve exact original JSON report bytes in a bounded compressed log receipt')))

    def test_source_hash_graph_includes_imports_and_retained_runtime(self):
        source=json.loads((HERE/'SOURCE.json').read_bytes())
        self.assertFalse(source['actual_execution'])
        self.assertGreater(len(source['files']),650)
        for name,pin in source['files'].items():
            raw=(ROOT/name).read_bytes();self.assertEqual(len(raw),pin['bytes'],name);self.assertEqual(sha256(raw).hexdigest(),pin['sha256'],name)


if __name__=='__main__':unittest.main()
