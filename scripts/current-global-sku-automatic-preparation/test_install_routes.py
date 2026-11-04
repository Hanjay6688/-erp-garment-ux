"""Critical source and closed-install checks; no ERP/cursor is executed."""
from pathlib import Path
from unittest.mock import patch
import importlib.util
import json
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('global_automatic_installer_control_subject', HERE / 'install_routes.py')
install = importlib.util.module_from_spec(spec)
spec.loader.exec_module(install)


class Forbidden:
    def __getattribute__(self, name):
        raise AssertionError('Closed preparation inspected a database cursor: ' + name)


class ClosedAutomaticInstaller(unittest.TestCase):
    def test_only_two_observer_bodies_change_in_the_complete_original_plan(self):
        before = json.loads(install.parent.PLAN.read_bytes())
        after = json.loads(install.PLAN.read_bytes())
        self.assertEqual(set(before), set(after))
        self.assertEqual({key for key in before if before[key] != after[key]}, {'source_sql', 'functions'})
        changed = {signature for signature in before['functions'] if before['functions'][signature] != after['functions'][signature]}
        self.assertEqual(changed, {'cp7_global_nonpo_native_graph.scope_v1(uuid[])',
                                   'cp7_global_nonpo_native_graph.capture_v1(jsonb,boolean)'})
        for signature in changed:
            self.assertEqual({key: value for key, value in before['functions'][signature].items() if key != 'body_sha256'},
                             {key: value for key, value in after['functions'][signature].items() if key != 'body_sha256'})
        self.assertEqual((len(after['functions']), len(after['tables']), after['Native_adapters']), (16, 3, 8))

    def test_exact_plan_manifest_and_private_providers_keep_original_installer_unchanged(self):
        before = dict(install.original.__dict__)
        admission = dict(install.admission.__dict__)
        module, proof = install.load_prepared()
        self.assertEqual(proof['additional_installer_body_changes'], 0)
        self.assertEqual(module.sql_sources(), install.sql_sources())
        self.assertIs(module._money_compare_current, install.routes.current_reference)
        self.assertIs(module._money_input_relations, install.require_input_relations)
        source = module.sources()
        self.assertEqual(source['plan'], install.base.pin(install.PLAN.read_bytes()))
        self.assertEqual(source['manifest'], install.manifest_pin())
        self.assertIsNone(source['runtime_entry'])
        self.assertTrue(all(install.original.__dict__[key] is value for key, value in before.items()))
        self.assertEqual(admission, install.admission.__dict__)

    def test_each_unaccepted_gate_refuses_before_any_cursor_or_receipt_access(self):
        for name in install.GATES:
            with self.subTest(gate=name), patch.object(install.admission, name, 'FORGED'):
                with self.assertRaisesRegex(ValueError, 'ACTUAL_PARENT_AND_COMPLETE_INPUT_ADOPTION_PENDING'):
                    install.load_prepared()
        module, _ = install.load_prepared()
        with self.assertRaisesRegex(ValueError, 'ACTUAL_FINAL_PARENT_AND_OWNING_SCOPE_PENDING'):
            module.install(Forbidden(), b'not a Root', b'not an input profile')

    def test_all_new_relation_omissions_refuse_and_count_cannot_adopt_a_parent(self):
        names = install.parent.callbacks.requirements()['required_relation_lower_bound']
        all_names = install.callbacks.requirements()['required_relation_lower_bound']
        added = sorted(set(all_names) - set(names))
        self.assertEqual(len(names), 244)
        self.assertEqual(len(added), 32)
        for missing in added:
            with self.subTest(missing=missing), self.assertRaisesRegex(ValueError, 'AUTOMATIC_INPUT_RELATIONS_MISSING'):
                install.require_input_relations(dict(relations=sorted(names + [name for name in added if name != missing])))
        proof = install.require_input_relations(dict(relations=sorted(names + added + ['erp.future_actual_source'])))
        self.assertEqual(proof['required_relation_lower_bound'], 276)
        self.assertFalse(proof['complete_input_review'])
        self.assertFalse(proof['actual_final_parent_adopted'])

    def test_removed_provider_or_changed_plan_refuses_before_cursor(self):
        read = Path.read_bytes
        def changed(path):
            return read(path) + (b'\n' if path == install.PLAN else b'')
        with patch.object(Path, 'read_bytes', changed), self.assertRaisesRegex(ValueError, 'DECLARED_SOURCE_CHANGED'):
            install.load_prepared()
        path = HERE / 'SOURCE.json'
        manifest = json.loads(read(path))
        manifest['files'].pop(str((HERE / 'SOURCE_REFERENCE.json').relative_to(install.ROOT)))
        def missing(target):
            return json.dumps(manifest).encode() if target == path else read(target)
        with patch.object(Path, 'read_bytes', missing), self.assertRaisesRegex(ValueError, 'COMPLETE_OWN_PROVIDER_MANIFEST'):
            install.load_prepared()


if __name__ == '__main__':
    unittest.main()
