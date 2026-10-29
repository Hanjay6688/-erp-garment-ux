"""Offline workflow/receipt checks; no Actions, shell steps or runtime run."""
from hashlib import sha256
from pathlib import Path
import base64
import gzip
import importlib.util
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


workflow = load('s05_test_workflow_source', HERE/'workflow_source.py')
receipts = load('s05_test_byte_receipts', HERE/'retain_reports.py')


class WorkflowControls(unittest.TestCase):
    def test_generated_root_leaf_workflow_and_all_unchanged_phase_steps(self):
        text = (ROOT/workflow.PATH).read_text(); proof = workflow.checked(text)
        self.assertEqual(proof['original_sha256'], workflow.PARENT_SHA256)
        self.assertEqual(proof['generated_sha256'], sha256(text.encode()).hexdigest())
        original = workflow.yaml.load((HERE/'frozen_vendor/workflow.yml').read_bytes(), Loader=workflow.UniqueLoader)
        child = workflow.yaml.load(text, Loader=workflow.UniqueLoader)
        changed = {row['parent_step'] for row in proof['replacements']}
        old = [s for s in original['jobs']['p21']['steps'] if (s.get('name') or s.get('uses')) not in changed]
        new = child['jobs']['p21']['steps']
        self.assertEqual([s for s in new if s in old], old)
        self.assertEqual(child['on']['push'], {'branches': [workflow.ROOT_PUBLISH_BRANCH], 'paths': [workflow.PATH, 'scripts/current-s05-native10-qualification/**']})
        self.assertEqual(child['on']['workflow_dispatch'], {})
        self.assertFalse(proof['automatic_on_default_or_other_branches'])
        self.assertEqual(child['permissions'], {'contents': 'read', 'actions': 'read'})

    def test_any_workflow_drift_or_malformed_keys_are_refused(self):
        text = (ROOT/workflow.PATH).read_text()
        for bad in (text+'\n', text.replace('working-directory:', 'working_directory:', 1), text.replace("if: always()", 'if: false', 1), text.replace('writer_runtime', 'weakened', 1)+'\n'):
            with self.assertRaises(ValueError): workflow.checked(bad)
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_WORKFLOW_KEY'):
            workflow.yaml.load('name: first\nname: duplicate\n', Loader=workflow.UniqueLoader)

    def test_failed_original_bytes_are_preserved_without_relabel_or_json_reserialize(self):
        with tempfile.TemporaryDirectory(prefix='s05-offline-receipt-') as temp:
            raw = b'{ "status" : "INCOMPLETE", "SYNTHETIC_RECEIPT_CONTROL" : true }\n'
            (Path(temp)/receipts.NAMES[0]).write_bytes(raw)
            result = list(receipts.preserve(temp)); self.assertEqual(len(result), 1)
            row = result[0]; compressed = base64.b64decode(row['gzip_base64'])
            self.assertEqual(gzip.decompress(compressed), raw)
            self.assertEqual(row['raw_sha256'], sha256(raw).hexdigest())
            self.assertEqual(list(receipts.preserve(temp)), result)


if __name__ == '__main__':
    unittest.main()
