"""Pure/source controls only. No files called Originals are manufactured."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import ModuleType
import ast
import importlib.util
import json
import subprocess
import unittest
from unittest.mock import patch
import midnight_common as common
import midnight_gate as gate
import parent_binding as binding
import provenance


def future_metadata_model():
    cfg = deepcopy(common.document((common.HERE / 'CONFIG.json').read_bytes()))
    cfg['state'] = 'ROOT_BOUND_ACTUAL_SUCCESSOR14'
    original_pin = dict(encoding='raw', stored=dict(bytes=1, sha256='a' * 64), raw=dict(bytes=1, sha256='a' * 64))
    cfg['accepted_parent14'] = dict(status='ROOT_VERIFIED_NATIVE14_SIX_ORIGINALS_ALL5',
        head=binding.HEAD, tree=binding.TREE, run_id=binding.RUN, job_id=binding.JOB,
        workflow=binding.WORKFLOW, outer_case_id='S03_ATTENDANCE_NATIVE14_AND_USED_INVERSE',
        original11_ids=cfg['expected_parent11_ids'], reader3_ids=cfg['expected_parent3_ids'],
        originals={key: dict(original_pin, path=common.NS + 'accepted-parent14/' + key + '.json') for key in gate.SIX})
    cfg['backend_binding'] = dict(head=binding.HEAD, tree=binding.TREE,
        runtime_files=cfg['prepared_backend_runtime7'], product_sources_sha256='a' * 64,
        source_manifest=dict(path=binding.SOURCE, **binding.SOURCE_PIN), files=binding.source()[1])
    return cfg


class BindingControls(unittest.TestCase):
    def test_actual_NULL_remains_closed_before_Originals_or_ERP_processes(self):
        import probe
        with patch.object(subprocess, 'check_output', side_effect=AssertionError('PROCESS_BEFORE_NULL_GATE')):
            with self.assertRaisesRegex(ValueError, gate.CLOSED):
                probe.runtime()

    def test_exact_future_metadata_is_only_a_model_and_reads_no_Original(self):
        cfg = future_metadata_model()
        with patch.object(common, 'read_original', side_effect=AssertionError('ORIGINAL_READ')):
            parent, backend = gate.selected(cfg)
        self.assertEqual(parent['job_id'], binding.JOB)
        self.assertEqual(len(backend['files']), 475)

    def test_old425_binding_refuses_named_counter(self):
        cfg = future_metadata_model()
        old = 'scripts/current-attendance-choice-reader-native14-qualification/SOURCE.json'
        raw = (common.ROOT / old).read_bytes()
        cfg['backend_binding'].update(source_manifest=dict(path=old, **common.pin(raw)), files=json.loads(raw)['files'])
        self.assertEqual(len(cfg['backend_binding']['files']), 425)
        with self.assertRaisesRegex(ValueError, 'SOURCE475_PIN_REQUIRED_NOT_HISTORICAL425'):
            gate.selected(cfg)

    def test_missing_member_cannot_project_current475(self):
        cfg = future_metadata_model(); cfg['backend_binding']['files'].pop('scripts/current-s03-lawful-fixture-successor-qualification/lawful_fixture.py')
        with self.assertRaisesRegex(ValueError, 'COMPLETE_CURRENT_SOURCE475_MAP'):
            gate.selected(cfg)

    def test_rogue_map_and_sha_are_rejected(self):
        cfg = future_metadata_model(); cfg['backend_binding']['files']['scripts/rogue.py'] = dict(bytes=0, sha256='a' * 64)
        with self.assertRaisesRegex(ValueError, 'COMPLETE_CURRENT_SOURCE475_MAP'): gate.selected(cfg)
        cfg = future_metadata_model(); cfg['backend_binding']['source_manifest']['sha256'] = 'f' * 64
        with self.assertRaisesRegex(ValueError, 'SOURCE475_PIN_REQUIRED'): gate.selected(cfg)

    def test_exact_public_head_tree_run_job_workflow(self):
        for field, wrong in (('head', 'f' * 40), ('tree', 'f' * 40), ('run_id', '40983410166'),
                             ('job_id', '123828634301'), ('workflow', 'FOREIGN_WORKFLOW')):
            cfg = future_metadata_model(); cfg['accepted_parent14'][field] = wrong
            if field in ('head', 'tree'): cfg['backend_binding'][field] = wrong
            with self.assertRaisesRegex(ValueError, 'EXACT_PUBLIC3C0_RUN'): gate.selected(cfg)

    def test_five_raw_pins_and_changed_runtime_still_reject(self):
        cfg = future_metadata_model(); cfg['accepted_parent14']['originals'].pop('reader3')
        with self.assertRaisesRegex(ValueError, 'SUCCESSOR14_IDENTITY'): gate.selected(cfg)
        cfg = future_metadata_model(); cfg['backend_binding']['runtime_files'] = {}
        with self.assertRaisesRegex(ValueError, 'CURRENT_ACTUAL_RUNTIME7'): gate.selected(cfg)

    def test_closed_declaration_is_exact475_plus_its_manifest_not_old425(self):
        cfg = common.document((common.HERE / 'CONFIG.json').read_bytes())
        head, tree, files = binding.current_declaration(common.ROOT, cfg)
        self.assertEqual((head, tree), (binding.HEAD, binding.TREE))
        self.assertEqual(len(files), 476)
        self.assertEqual(files[binding.SOURCE], binding.SOURCE_PIN)
        self.assertIn('scripts/current-s03-lawful-fixture-successor-qualification/lawful_fixture.py', files)

    def test_actual_source475_bytes_and_all_runtime7_members(self):
        raw, files = binding.source()
        self.assertEqual(sha256(raw).hexdigest(), binding.SOURCE_PIN['sha256'])
        cfg = common.document((common.HERE / 'CONFIG.json').read_bytes())
        for name, digest in cfg['prepared_backend_runtime7'].items():
            self.assertEqual(sha256((common.ROOT / name).read_bytes()).hexdigest(), digest)
            self.assertEqual(files[name], common.pin((common.ROOT / name).read_bytes()))

    def test_all41_c097_bytes_and_active_routes_are_lossless(self):
        self.assertEqual(provenance.check()['retained_c097_files'], 41)

    def test_missing_derivation_anchor_refuses(self):
        with self.assertRaisesRegex(ValueError, 'ONE_EXACT_ROUTING_ANCHOR'):
            provenance.substitute(b'original', [dict(before='absent', after='replacement', count=1)])

    def test_original_callback_oracle_remain_exact_and_once(self):
        case = common.HERE / 'historical-midnight-c0/cases.py'
        oracle = common.HERE / 'historical-midnight-c0/oracle.py'
        self.assertEqual(sha256(case.read_bytes()).hexdigest(), '7cdfd006c4dfb2f3c35dc9557366f601fd2d0a6748505c40f2ee8b66373b2506')
        self.assertEqual(sha256(oracle.read_bytes()).hexdigest(), '9f866f07083477ea338649fed88d9f92a71559c173bbbce88885ebf906b77a1d')
        tree = ast.parse((common.HERE / 'midnight_group.py').read_bytes())
        calls = [n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
        self.assertEqual(calls.count('_strict_group_once'), 1)
        self.assertNotIn('strict_group', calls); self.assertNotIn('with_retry', calls)

    def test_committed_used_block_and_complete_six_engine_selections(self):
        import midnight_derive
        code, proof = midnight_derive.witness((midnight_derive.OLD / 'native_runner.py').read_bytes())
        self.assertEqual(proof['counted_body_changes'], 1)
        self.assertIn('connection.commit()', code)
        self.assertIn('after_catalog != before_catalog or after_data != before_data', code)
        _, proof = midnight_derive.engine((common.ROOT / 'scripts/current-vendor-receivable-qualification/probe.py').read_bytes())
        self.assertEqual(proof['counted_changes'], 6)

    def test_current_Original_intake_is_exactly_one_reversible_metadata_anchor(self):
        import current_originals
        raw = (common.ROOT / current_originals.INTAKE).read_bytes()
        self.assertEqual(raw.decode().count(current_originals.ANCHOR), 1)
        changed = raw.decode().replace(current_originals.ANCHOR, current_originals.REPLACEMENT, 1)
        self.assertEqual(changed.replace(current_originals.REPLACEMENT, current_originals.ANCHOR, 1).encode(), raw)

    def test_workflow_is_only_owned_successor_and_shell_parses(self):
        import workflow, yaml
        actual = yaml.safe_load((common.ROOT / common.WORKFLOW).read_bytes())
        expected = workflow.derive(yaml.safe_load((common.ROOT / workflow.OLD).read_bytes()))
        self.assertEqual(actual, expected)
        self.assertEqual(actual['jobs']['p21']['steps'][1]['working-directory'], 'auditor')
        for step in actual['jobs']['p21']['steps']:
            if 'run' in step:
                result = subprocess.run(['bash', '-n'], input=step['run'], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
