"""Explicit source/interface models only; zero actual ERP qualification."""
import ast
from contextlib import nullcontext, ExitStack
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import sku_current_parent_admission as admission
import sku_current_parent_assembly as assembly
import sku_current_parent_derive as derive

RAW = (Path(__file__).resolve().parent / "original_composition.py.txt").read_bytes()


def functions(*names):
    code, _ = derive.derive(RAW)
    nodes = [n for n in ast.parse(code).body if isinstance(n, ast.FunctionDef) and n.name in names]
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "explicit-interface-model", "exec"), namespace)
    return namespace


class CurrentParentBridge(unittest.TestCase):
    def test_only_complete_six_case_child_receipt_can_pass_modeled_gate(self):
        # Explicit receipt-interface model. This is not a Root receipt or ERP
        # qualification, and every module gate is restored after this control.
        parent = dict(status="ROOT_VERIFIED_CURRENT_MANDOR17_ALL5", head="modeled-parent", tree="modeled-parent-tree",
            actual_Native_cases=9, actual_Native_session_cases=4, actual_Auth_HTTP_cases=2,
            actual_browser_cases=2, actual_business_cases=17, complete17_qualified=True,
            package_all_five=True, prior_runs_aggregated=False, assembly_source={"model": True},
            production_go=False, independent_acceptance=False)
        sku = dict(status="ROOT_VERIFIED_CURRENT_SKU_MOVAVG_NATIVE6_ALL5", head="modeled-child", tree="modeled-child-tree",
            actual_Native_cases=6, complete6_qualified=True, package_all_five=True,
            prior_runs_aggregated=False, production_go=False, independent_acceptance=False)
        parent_raw, sku_raw = admission.canonical(parent), admission.canonical(sku)
        values = dict(PARENT_HEAD=parent['head'], PARENT_TREE=parent['tree'],
            PARENT_ROOT_PIN=admission.pin(parent_raw), PARENT_SOURCE_PIN={"model": True},
            PARENT_MODULE_PIN=parent['assembly_source'], SKU_HEAD=sku['head'], SKU_TREE=sku['tree'],
            SKU_ROOT_PIN=admission.pin(sku_raw), SKU_SOURCE_PIN={"model": True}, RUNTIME_ENTRY="modeled-entry")
        with ExitStack() as stack:
            for name, value in values.items(): stack.enter_context(patch.object(admission, name, value))
            self.assertEqual(admission.admitted(parent_raw, sku_raw)['actual_composite_cases'], 0)
            old = dict(sku, status="ROOT_VERIFIED_CURRENT_SKU_MOVAVG_NATIVE5_ALL5", actual_Native_cases=5)
            old.pop('complete6_qualified'); old['complete5_qualified'] = True
            old_raw = admission.canonical(old)
            with patch.object(admission, 'SKU_ROOT_PIN', admission.pin(old_raw)):
                with self.assertRaisesRegex(ValueError, 'ACTUAL_COMPLETE_PARENT_OR_CHILD_REQUIRED'):
                    admission.admitted(parent_raw, old_raw)
            for key, value in [('actual_Native_cases', 5), ('complete6_qualified', False), ('package_all_five', False), ('prior_runs_aggregated', True)]:
                changed_raw = admission.canonical(dict(sku, **{key: value}))
                with patch.object(admission, 'SKU_ROOT_PIN', admission.pin(changed_raw)):
                    with self.assertRaisesRegex(ValueError, 'ACTUAL_COMPLETE_PARENT_OR_CHILD_REQUIRED'):
                        admission.admitted(parent_raw, changed_raw)
        self.assertTrue(all(getattr(admission, name) is None for name in values))

    def test_closed_gate_does_not_inspect_modules_or_open_files(self):
        class Untouchable:
            def __getattribute__(self, name):
                raise AssertionError("module inspected before Root acceptance")
        with self.assertRaisesRegex(ValueError, "ROOT_AND_OWNING_ENTRY_PENDING"):
            assembly.load_prepared(Untouchable(), Untouchable(), b"not accepted", b"not accepted")

    def test_exact_derivation_recovers_every_original_byte(self):
        _, proof = derive.derive(RAW)
        self.assertEqual(proof["counted_changes"], 6)
        self.assertTrue(proof["original_recovered_exactly"])
        with self.assertRaisesRegex(ValueError, "EXACT_ORIGINAL"):
            derive.derive(RAW + b"\n")

    def test_entire_nested_parent_state_and_raw_authority_are_bound(self):
        binding = functions("binding")["binding"]
        catalog = SimpleNamespace(digest=lambda value: sha256(admission.canonical(value)).hexdigest())
        parent = {"contract": "explicit-modeled-current-Mandor", "sources": {"current": True},
                  "parent": {"before_raw_schemas": {"public": ["owner", "exact raw acl"]},
                             "preinstall_data_and_sequences": {"sequence": 14}},
                  "Mandor": {"data": {"rows": "digest"}}, "before": {"all22": "original"},
                  "after": {"all22": "current"}}
        proof = {"verified": True}
        baseline = binding(catalog, parent, proof)
        variants = [deepcopy(parent) for _ in range(3)]
        variants[0]["parent"]["before_raw_schemas"]["public"][1] = "changed"
        variants[1]["Mandor"]["data"]["rows"] = "changed"
        variants[2]["parent"]["preinstall_data_and_sequences"]["sequence"] = 15
        for changed in variants:
            self.assertNotEqual(binding(catalog, changed, proof), baseline)
        self.assertNotEqual(binding(catalog, parent, {"verified": False}), baseline)

    def test_parent_verifier_refuses_before_first_child_write(self):
        env = functions("install_delta")
        predecessor = SimpleNamespace(atomic=lambda cur: nullcontext(),
            predecessor=SimpleNamespace(predecessor=SimpleNamespace(_locks=lambda cur: None)))
        parent = SimpleNamespace(verify=Mock(side_effect=ValueError("actual parent refused")))
        env.update(runtime=lambda: (None, None, None, predecessor, None), parent=lambda: parent)
        cursor = Mock()
        with self.assertRaisesRegex(ValueError, "actual parent refused"):
            env["install_delta"](cursor, {"complete_current_parent": True})
        cursor.execute.assert_not_called()

    def test_full_current_catalogue_mismatch_refuses_before_child_sql(self):
        env = functions("install_delta")
        predecessor = SimpleNamespace(atomic=lambda cur: nullcontext(),
            predecessor=SimpleNamespace(predecessor=SimpleNamespace(_locks=lambda cur: None)))
        catalog = SimpleNamespace(_catalog_rows=lambda cur: {"full22": "actual"}, _data=lambda cur: {})
        parent = SimpleNamespace(verify=Mock(return_value={"verified": True}))
        env.update(runtime=lambda: (None, None, None, predecessor, catalog), parent=lambda: parent)
        cursor = Mock()
        with self.assertRaisesRegex(ValueError, "FULL_CURRENT_PARENT_CATALOGUE"):
            env["install_delta"](cursor, {"after": {"full22": "stale"}})
        parent.verify.assert_called_once()
        cursor.execute.assert_not_called()

    def test_financial_transition_and_both_inverse_bodies_stay_unchanged(self):
        original = {n.name: ast.dump(n) for n in ast.parse(RAW).body if isinstance(n, ast.FunctionDef)}
        code, _ = derive.derive(RAW)
        current = {n.name: ast.dump(n) for n in ast.parse(code).body if isinstance(n, ast.FunctionDef)}
        for name in ("transition", "verify", "rollback_delta_preuse", "rollback_preuse",
                     "reader_handover", "reader_function_ddl"):
            self.assertEqual(original[name], current[name], name)
        self.assertIn("parent_verified=parent().verify(cur,state['predecessor'])", code)
        self.assertIn("preinstall_data_and_sequences=prior['parent']['preinstall_data_and_sequences']", code)


if __name__ == "__main__":
    unittest.main()
