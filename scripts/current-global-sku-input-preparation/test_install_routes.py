"""New exact installer bindings only; no Native, DDL or old graph tests."""
from pathlib import Path
from unittest.mock import patch
import ast,json,sys,unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import install_routes as routes


class ForbiddenCursor:
    def __getattribute__(self,name):
        raise AssertionError('closed admission reached cursor: '+name)


class InstallationBinding(unittest.TestCase):
    def test_only_three_helper_bodies_change_in_the_complete_plan(self):
        plan=json.loads(routes.PLAN.read_bytes())
        prior=json.loads((routes.base.GLOBAL/'INSTALL_PLAN.json').read_bytes())
        self.assertEqual(set(plan),set(prior))
        self.assertEqual({k for k in plan if plan[k]!=prior[k]},{'source_sql','functions'})
        changed={s for s in plan['functions']if plan['functions'][s]!=prior['functions'][s]}
        self.assertEqual(changed,{'cp7_global_nonpo_native_graph.authority_v1()',
            'cp7_global_nonpo_native_graph.scope_v1(uuid[])','cp7_global_nonpo_native_graph.capture_v1(jsonb,boolean)'})
        for sig in changed:
            self.assertEqual({k:v for k,v in plan['functions'][sig].items()if k!='body_sha256'},
                {k:v for k,v in prior['functions'][sig].items()if k!='body_sha256'})

    def test_seven_routes_preserve_every_signature_and_all_other_function_bodies(self):
        source,proof=routes.derive();self.assertEqual(proof['counted_replacements'],7)
        before={n.name:n for n in ast.parse(routes.exact_original()).body if isinstance(n,ast.FunctionDef)}
        after={n.name:n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)}
        self.assertEqual(set(before),set(after))
        for name in before:
            self.assertEqual(ast.dump(before[name].args),ast.dump(after[name].args),name)
            if name not in ('sql_sources','sources','install'):self.assertEqual(ast.dump(before[name]),ast.dump(after[name]),name)

    def test_prepared_sources_bind_the_new_plan_and_both_manifests(self):
        module,_=routes.load_prepared();proof=module.sources()
        self.assertEqual(module.sql_sources(),routes.sql_sources())
        self.assertEqual(proof['plan'],routes.base.pin(routes.PLAN.read_bytes()))
        self.assertEqual(proof['manifest'],routes.manifest_pin())
        for name in ('runtime_entry','final_parent_head','complete_input_profile_pin'):self.assertIsNone(proof[name])

    def test_actual_install_refuses_before_any_cursor_attribute(self):
        module,_=routes.load_prepared()
        with self.assertRaisesRegex(ValueError,'CP7_GLOBAL_ENVELOPE_ACTUAL_FINAL_PARENT_AND_OWNING_SCOPE_PENDING'):
            module.install(ForbiddenCursor(),b'not an accepted parent',b'not an accepted input profile')

    def test_preparation_cannot_silently_promote_an_admission_constant(self):
        with patch.object(routes.admission,'RUNTIME_ENTRY','forged-entry'):
            with self.assertRaisesRegex(ValueError,'GLOBAL_PO_INSTALL_FINAL_ADOPTION_REQUIRES_SEPARATE_REVIEW'):
                routes.load_prepared()

    def test_changed_plan_bytes_refuse_even_when_json_semantics_are_unchanged(self):
        read=Path.read_bytes
        def changed(path):return read(path)+(b'\n'if path==routes.PLAN else b'')
        with patch.object(Path,'read_bytes',changed):
            with self.assertRaisesRegex(ValueError,'GLOBAL_PO_INSTALL_PREPARED_SOURCE_CHANGED:'):
                routes.load_prepared()

    def test_loading_does_not_replace_original_module_functions_or_globals(self):
        before=dict(routes.original.__dict__);admission=dict(routes.admission.__dict__)
        module,_=routes.load_prepared()
        self.assertIsNot(module,routes.original)
        self.assertEqual(set(before),set(routes.original.__dict__))
        self.assertTrue(all(routes.original.__dict__[k]is v for k,v in before.items()))
        self.assertEqual(admission,routes.admission.__dict__)
        self.assertNotIn(module.__name__,sys.modules)


if __name__=='__main__':unittest.main()
