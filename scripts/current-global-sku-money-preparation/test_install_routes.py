"""Critical closed-install and completeness controls, without ERP calls."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import importlib.util
import json
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('money_install_control_subject',HERE/'install_routes.py')
routes=importlib.util.module_from_spec(spec);spec.loader.exec_module(routes)


class ForbiddenCursor:
    def __getattribute__(self,name):
        raise AssertionError('closed preparation reached database cursor: '+name)


class MoneyInstallation(unittest.TestCase):
    def test_plan_preserves_all_transaction_bodies_and_authority(self):
        plan=json.loads(routes.PLAN.read_bytes())
        old=json.loads((routes.base.GLOBAL/'INSTALL_PLAN.json').read_bytes())
        self.assertEqual(set(plan),set(old))
        self.assertEqual({k for k in plan if plan[k]!=old[k]},{'source_sql','functions'})
        changed={s for s in plan['functions']if plan['functions'][s]!=old['functions'][s]}
        self.assertEqual(changed,{'cp7_global_nonpo_native_graph.authority_v1()',
            'cp7_global_nonpo_native_graph.scope_v1(uuid[])','cp7_global_nonpo_native_graph.capture_v1(jsonb,boolean)'})
        for signature in changed:
            self.assertEqual({k:v for k,v in plan['functions'][signature].items()if k!='body_sha256'},
                {k:v for k,v in old['functions'][signature].items()if k!='body_sha256'})

    def test_one_exact_source_plan_and_seal(self):
        module,proof=routes.load_prepared();source=module.sources()
        self.assertTrue(proof['original_installer_recovered'])
        self.assertEqual(proof['counted_replacements'],8)
        self.assertEqual(module.sql_sources(),routes.sql_sources())
        self.assertEqual(source['plan'],routes.base.pin(routes.PLAN.read_bytes()))
        self.assertEqual(source['manifest'],routes.manifest_pin())
        self.assertIs(module._money_compare_current,routes.routes.current_reference)
        for name in ('runtime_entry','final_parent_head','complete_input_profile_pin'):
            self.assertIsNone(source[name])

    def test_real_admission_refuses_before_any_cursor_use(self):
        module,_=routes.load_prepared()
        with self.assertRaisesRegex(ValueError,'CP7_GLOBAL_ENVELOPE_ACTUAL_FINAL_PARENT_AND_OWNING_SCOPE_PENDING'):
            module.install(ForbiddenCursor(),b'not a receipt',b'not an input profile')

    def test_every_gate_refuses_silent_promotion(self):
        for name in routes.GATES:
            with self.subTest(gate=name),patch.object(routes.admission,name,'forged'):
                with self.assertRaisesRegex(ValueError,'GLOBAL_MONEY_FINAL_ADOPTION_REQUIRES_SEPARATE_REVIEW'):
                    routes.load_prepared()

    def test_old_or_callback_incomplete_profiles_refuse_before_cursor(self):
        module,_=routes.load_prepared()
        prior=routes.routes.PRIOR
        old=json.loads((prior/'INPUT_REVIEW_CONTROLS.json').read_bytes())['physical_relation_candidates']
        composite=json.loads((prior/'CALLBACK_SOURCE_REVIEW.json').read_bytes())['required_relation_lower_bound']
        current=json.loads((HERE/'INPUT_REVIEW_CONTROLS.json').read_bytes())['physical_relation_candidates']
        self.assertEqual([len(v)for v in (old,composite,current)],[209,221,232])
        model=SimpleNamespace(**{name:getattr(routes.admission,name)for name in routes.GATES})
        module.admission=model
        for names in (old,composite,current):
            model.runtime_admission=lambda *args:({},dict(relations=names))
            with self.subTest(count=len(names)),self.assertRaisesRegex(ValueError,'GLOBAL_MONEY_INPUT_RELATIONS_MISSING:'):
                module.install(ForbiddenCursor(),b'modeled admission only',b'modeled input only')

    def test_all_244_omissions_refuse_and_extra_inputs_do_not_adopt_parent(self):
        names=routes.callbacks.requirements()['required_relation_lower_bound']
        self.assertEqual(len(names),244)
        for missing in names:
            with self.subTest(missing=missing),self.assertRaisesRegex(ValueError,'GLOBAL_MONEY_INPUT_RELATIONS_MISSING:'):
                routes.callbacks.require_input_relations(dict(relations=[n for n in names if n!=missing]))
        result=routes.callbacks.require_input_relations(dict(relations=sorted(names+['erp.additional_actual_input'])))
        self.assertFalse(result['complete_input_review']);self.assertFalse(result['actual_final_parent_adopted'])
        for value in ({},{'relations':'erp.journal_entries'},{'relations':[1]},{'relations':['b','a']},{'relations':['a','a']}):
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'GLOBAL_MONEY_DISTINCT_SORTED_INPUT_RELATIONS_REQUIRED'):
                routes.callbacks.require_input_relations(value)

    def test_changed_plan_bytes_and_unpinned_providers_refuse(self):
        read=Path.read_bytes
        def changed(path):return read(path)+(b'\n'if path==routes.PLAN else b'')
        with patch.object(Path,'read_bytes',changed):
            with self.assertRaisesRegex(ValueError,'GLOBAL_MONEY_DECLARED_SOURCE_CHANGED:'):
                routes.load_prepared()
        manifest_path=HERE/'SOURCE.json'
        for filename in ('routes.py','SKU_SOURCE.json','callback_preflight.py','CALLBACK_SOURCE_REVIEW.json','INPUT_REVIEW_CONTROLS.json'):
            manifest=json.loads(read(manifest_path));manifest['files'].pop(str((HERE/filename).relative_to(routes.ROOT)))
            def missing(path):return json.dumps(manifest).encode()if path==manifest_path else read(path)
            with self.subTest(unpinned=filename),patch.object(Path,'read_bytes',missing):
                with self.assertRaisesRegex(ValueError,'GLOBAL_MONEY_ALL_PROVIDERS_MUST_BE_PINNED'):
                    routes.load_prepared()

    def test_original_installation_and_admission_modules_are_unchanged(self):
        before=dict(routes.original.__dict__);admission=dict(routes.admission.__dict__)
        module,_=routes.load_prepared()
        self.assertIsNot(module,routes.original)
        self.assertEqual(set(before),set(routes.original.__dict__))
        self.assertTrue(all(routes.original.__dict__[k]is v for k,v in before.items()))
        self.assertEqual(admission,routes.admission.__dict__)


if __name__=='__main__':unittest.main()
