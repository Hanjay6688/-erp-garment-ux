"""Pure/source/in-memory controls: Native0, DB0, Auth0, browser0, remote0."""
from copy import deepcopy
from contextlib import contextmanager
from datetime import date, datetime
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace, ModuleType
from unittest import TestCase
from unittest.mock import patch
import ast
import builtins
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import yaml
from midnight_common import HERE, ROOT, ID, GROUP, document, regular, pin
import midnight_gate as gate
import midnight_admission as admission
import midnight_factory as factory
import midnight_derive as derive
import midnight_group as single
import local_models as models
import result_gate


class SourceContract(TestCase):
    def test_null_gate_before_ERP_subprocess_or_original_read(self):
        import probe
        original = builtins.__import__
        def guard(name, *args, **kwargs):
            if name.startswith(('psycopg', 'cp6_', 'cp7_')):
                raise AssertionError('ERP_IMPORTED_BEFORE_CLOSED_GATE:' + name)
            return original(name, *args, **kwargs)
        with patch.object(builtins, '__import__', guard), patch.object(subprocess, 'check_output',
                side_effect=AssertionError('PROCESS_OR_GET_BEFORE_GATE')):
            with self.assertRaisesRegex(ValueError, 'CLOSED_ACTUAL_SUCCESSOR14'):
                probe.runtime()

    def test_null_parent_before_product_sources_or_Original_reads(self):
        with patch.object(admission, 'read_original', side_effect=AssertionError('ORIGINAL_READ')):
            with self.assertRaisesRegex(ValueError, 'CLOSED_ACTUAL_SUCCESSOR14'):
                admission.admitted(SimpleNamespace(sources=lambda: (_ for _ in ()).throw(AssertionError('ERP'))))

    def test_failed9ac_cannot_be_bound_as_parent(self):
        cfg, _, _ = models.parent()
        cfg['accepted_parent14']['head'] = gate.FAILED
        cfg['backend_binding']['head'] = gate.FAILED
        with self.assertRaisesRegex(ValueError, 'SUCCESSOR14_IDENTITY'):
            gate.selected(cfg)

    def test_all_six_pin_classes_are_mandatory(self):
        cfg, _, _ = models.parent()
        for key in gate.SIX:
            bad = deepcopy(cfg); bad['accepted_parent14']['originals'].pop(key)
            with self.assertRaises(ValueError):
                gate.selected(bad)

    def test_exact_original_case_oracle_and_callback_AST_bytes(self):
        module = factory.historical()
        raw = (HERE / 'historical-midnight-c0/cases.py').read_bytes()
        self.assertEqual(sha256(raw).hexdigest(), '7cdfd006c4dfb2f3c35dc9557366f601fd2d0a6748505c40f2ee8b66373b2506')
        self.assertEqual(sha256((HERE/'historical-midnight-c0/oracle.py').read_bytes()).hexdigest(),
                         '9f866f07083477ea338649fed88d9f92a71559c173bbbce88885ebf906b77a1d')
        node = next(n for n in ast.parse(raw).body if isinstance(n, ast.FunctionDef) and n.name == 'run_boundary')
        self.assertEqual((node.lineno, node.end_lineno), (144, 208))
        self.assertEqual(module.ROOT, ROOT)

    def test_original_fixed_aware_microsecond_and_calendar_axes(self):
        o = factory.historical().oracle
        for day in (date(2026, 10, 30), date(2024, 3, 3), date(2026, 1, 2)):
            p = o.fixed_plan(day)
            self.assertEqual(p['after_us'] - p['before_us'], 1)
            self.assertEqual(p['before'].date(), p['after'].date())
            self.assertNotEqual(p['before'].astimezone(o.WIB).date(), p['after'].astimezone(o.WIB).date())
        with self.assertRaisesRegex(ValueError, 'AWARE_INSTANT'):
            o.epoch_us(datetime(2026, 10, 30))

    def test_new_owned_factory_never_invokes_old_fresh11_factory(self):
        cfg, sources, docs = models.parent()
        calls = []
        exact = factory.historical()
        exact.cases = lambda *a, **k: (_ for _ in ()).throw(AssertionError('OLD_FRESH11_FACTORY'))
        exact.originals = lambda: 'ACTUAL_CURRENT_HELPER_DOUBLE'
        exact.run_boundary = lambda cur, today, original: calls.append((cur, today, original)) or {'Native_credit': 0}
        state = {'LOCAL_DOUBLE': True}
        product = SimpleNamespace(sources=lambda: sources, verify=lambda cur, value: calls.append(value))
        with patch.object(factory, 'historical', return_value=exact), patch.object(factory, 'installed'):
            plan = factory.cases('CURSOR_DOUBLE', date(2026,10,30), state=state, evidence={},
                accepted_parent14={'documents': docs}, product=product, cfg=cfg)
            self.assertEqual([key for key, _ in plan], [ID])
            self.assertEqual(calls, [state])
            self.assertEqual(plan[0][1](), {'Native_credit': 0})
        self.assertEqual(calls[-1], ('CURSOR_DOUBLE', date(2026,10,30), 'ACTUAL_CURRENT_HELPER_DOUBLE'))

    def test_used_helper_has_one_reversible_metadata_change_only(self):
        raw = (derive.OLD/'native_runner.py').read_bytes()
        code, proof = derive.witness(raw)
        self.assertEqual(proof['counted_body_changes'], 1)
        self.assertNotIn('native.strict_group(', code)
        self.assertNotIn('business.cases(', code)
        self.assertIn("connection.commit()  # A real choice and Native cost allocation", code)
        self.assertIn("after_catalog != before_catalog or after_data != before_data", code)
        self.assertIn("actual_Native_cases=1", code)
        with self.assertRaisesRegex(ValueError, 'ONE_EXACT_USED'):
            derive.witness(raw.replace(derive.ANCHOR.encode(), b'', 1))

    def test_complete_outer_engine_retains_six_exact_selections(self):
        raw = (ROOT/'scripts/current-vendor-receivable-qualification/probe.py').read_bytes()
        code, proof = derive.engine(raw)
        self.assertEqual(proof['counted_changes'], 6)
        self.assertIn('baseline_full22_all_rows_all_sequences_equal', code)
        self.assertIn("role_cleanup.restore_roles", code)
        self.assertIn("BASELINE_RESTORE", code)

    def test_single_attempt_source_keeps_original_day_guard(self):
        source = (ROOT/'scripts/cp6_auditor_runner.py').read_text()
        self.assertIn("business_day.guard(row,today,day_before,business_day.wib_day(cur))", source)
        own = ast.parse((HERE/'midnight_group.py').read_text())
        calls = [n for n in ast.walk(own) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
        self.assertEqual(sum(n.func.attr == '_strict_group_once' for n in calls), 1)
        self.assertFalse(any(n.func.attr in ('strict_group', 'with_retry') for n in calls))

    def test_single_attempt_calls_once_and_rejects_rollover_retry(self):
        cfg, sources, docs = models.parent()
        observations = []
        @contextmanager
        def physical(cursor): observations.append('physical'); yield
        @contextmanager
        def public(*args, **kwargs): yield {'LOCAL_DOUBLE': True}
        def once(label, fn, verify):
            observations.append(label)
            self.assertEqual(fn('CURSOR', date(2026,10,30))[0][0], ID)
            return models.group([ID])
        native = SimpleNamespace(_strict_group_once=once,
            strict_group=lambda *a: (_ for _ in ()).throw(AssertionError('RETRY_WRAPPER')))
        module = ModuleType('cp7_catalog_state'); module.exact_public_catalog = public
        with patch.dict(sys.modules, {'cp7_catalog_state': module}), patch.object(single, 'retain'), \
             patch.object(factory, 'cases', return_value=[(ID, lambda: None)]):
            value = single.run(native, SimpleNamespace(product_catalog=physical), {}, {}, None,
                               {'documents':docs}, None, cfg)
        self.assertEqual(value['counts'], {'PASS':1})
        self.assertEqual(observations.count(GROUP), 1)

    def test_strict_count_boolean_cannot_be_one_case(self):
        value = models.group([ID]); value['counts']['PASS'] = True
        with self.assertRaises(ValueError):
            admission.exact_group(value, [ID])

    def test_duplicate_json_and_source_symlinks_refuse(self):
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_JSON_KEY'):
            document('{"same":1,"same":2}')
        with tempfile.TemporaryDirectory(prefix='midnight-source-control-') as folder:
            root=Path(folder); (root/'real').write_text('same')
            (root/'link').symlink_to(root/'real')
            with self.assertRaisesRegex(ValueError, 'SYMLINK'):
                regular(root, 'link')
            with self.assertRaisesRegex(ValueError, 'UNSAFE'):
                regular(root, '../real')

    def test_workflow_is_exact_bounded_full_parent_derivative_and_shell_parses(self):
        import workflow
        cfg = document((HERE/'CONFIG.json').read_bytes())
        before=yaml.safe_load((ROOT/workflow.OLD).read_bytes())
        after=yaml.safe_load((ROOT/'.github/workflows/cp7-attendance-midnight-native1.yml').read_bytes())
        self.assertEqual(after, workflow.derive(before, cfg['root_execution_branch']))
        self.assertEqual(after['jobs']['p21']['steps'][1]['name'], workflow.EARLY)
        for step in after['jobs']['p21']['steps']:
            if 'run' in step:
                value=subprocess.run(['bash','-n'], input=step['run'], capture_output=True, text=True)
                self.assertEqual(value.returncode,0,(step.get('name'),value.stderr))

    def test_frozen_output_validators_and_only_producer_identity_delta(self):
        for name, digest in (('generated_receipts.py','a569138a5b6d4c0d1ce542ab45af98ee156f47e6d772766c214bbae3366ffc7e'),
                             ('generated_later.py','7bf35d85d9f7ec19da34c5626f24af908f3691a4e3ed7251dbc4958e59b4bea3')):
            self.assertEqual(sha256((HERE/name).read_bytes()).hexdigest(), digest)
        for name in ('GENERATED_RECEIPTS.json','LATER_GENERATED_RECEIPTS.json'):
            old=document((ROOT/'scripts/current-attendance-choice-reader-native14-qualification'/name).read_bytes())
            new=document((HERE/name).read_bytes())
            for key in old:
                if key not in ('producer_files','package_workflow_name','S03_contract_derivation'):
                    self.assertEqual(new[key],old[key])
            expected=dict(old['producer_files']);expected.pop('.github/workflows/cp7-s03-choice-reader-native14.yml')
            expected['.github/workflows/cp7-attendance-midnight-native1.yml']=pin((ROOT/'.github/workflows/cp7-attendance-midnight-native1.yml').read_bytes())
            self.assertEqual(new['producer_files'],expected)

    def test_CI_cannot_reseal_and_unknown_flags_refuse(self):
        import freeze
        with patch.dict(os.environ, {'CI':'true'}):
            with self.assertRaisesRegex(ValueError,'REGENERATION_IN_CI'):
                freeze.freeze()
        result=subprocess.run([sys.executable,'-B',str(HERE/'probe.py'),'--unknown'],capture_output=True,text=True)
        self.assertEqual(result.returncode,2)


class ParentAndResultControls(TestCase):
    def test_labelled_six_document_model_pass_is_not_runtime_evidence(self):
        cfg, sources, docs=models.parent()
        value=admission.checked(docs,cfg,sources)
        self.assertEqual(value['fresh_Native_cases_before_execution'],0)
        self.assertFalse(value['retained_parent_reexecuted'])

    def test_parent_failures_raw_group_projection_and_runtime_source_refuse(self):
        mutations=[
            lambda d:d['strict11']['counts'].update(PASS=8,INCOMPLETE=3),
            lambda d:d['reader3'].update(status='INCOMPLETE'),
            lambda d:d['outer14']['committed']['LOCAL_PARENT14'].update(reader_native3={}),
            lambda d:d['outer14']['committed']['LOCAL_PARENT14']['used_inverse_refusal_after'].update(changed=True),
            lambda d:d['package']['gate'].update(writer_runtime=False),
            lambda d:d['package'].update(auth_users_after=1),
            lambda d:d['files']['files'].pop(),
            lambda d:d['drill']['data'].update(differ={'LOCAL':'DIFFER'}),
        ]
        for mutate in mutations:
            cfg,sources,docs=models.parent();mutate(docs)
            with self.assertRaises(ValueError):admission.checked(docs,cfg,sources)
        cfg,sources,docs=models.parent()
        with self.assertRaisesRegex(ValueError,'ACTUAL_PRODUCT_SOURCES'):
            admission.checked(docs,cfg,{'files':cfg['prepared_backend_runtime7']})

    def test_labelled_new1_model_keeps_only_one_fresh_case(self):
        value=result_gate.checked(*models.new_result())
        self.assertEqual(value['actual_Native_cases'],1)
        self.assertFalse(value['fresh_original11_or14_reexecuted'])
        self.assertFalse(value['production_go'])

    def test_new1_retries_counts_capture_witness_and_all5_refuse(self):
        mutations=[
            lambda v:v[1].update(business_day_retried=True),
            lambda v:v[0].update(actual_Native_cases=15),
            lambda v:v[0]['committed']['S03_MIDNIGHT_NATIVE1_AND_UNCHANGED_USED_WITNESS'].update(fresh_original11_or14_reexecuted=True),
            lambda v:v[0]['committed']['S03_MIDNIGHT_NATIVE1_AND_UNCHANGED_USED_WITNESS']['actual_installed_capture']['originals'].pop('14'),
            lambda v:v[0]['committed']['S03_MIDNIGHT_NATIVE1_AND_UNCHANGED_USED_WITNESS']['used_inverse_refusal_after'].update(sequence_changed=True),
            lambda v:v[0].update(baseline_full22_all_rows_all_sequences_equal=False),
            lambda v:v[2]['gate'].update(writer_runtime=False),
            lambda v:v[2]['run_identity'].update(tool_head='e'*40),
            lambda v:v[4]['catalog'].update(differ={'LOCAL':'DIFFER'}),
            lambda v:v[1]['cases'][ID]['previews']['AFTER'].update(denominator=10),
        ]
        for mutate in mutations:
            values=list(deepcopy(models.new_result()));mutate(values)
            with self.assertRaises(ValueError):result_gate.checked(*values)
