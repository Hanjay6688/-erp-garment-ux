"""Adversarial admission and actual installer guard controls, never ERP credit."""
import ast
from contextlib import nullcontext
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from cp7_sku_automatic_pending import catalog_additions


class CatalogueAdmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(Path(os.environ['CP7_AUTO_CATALOG_REPORT']).read_bytes())
        cls.product = json.loads(Path(os.environ['CP7_AUTO_CATALOG_INPUT']).read_bytes())['product']
        cls.profile = json.loads((HERE / 'CATALOG_ADDITIONS.json').read_bytes())
        if cls.report['status'] != 'POSTGRES17_AUTOMATIC_DDL_ALL22_ACL_UNUSED_INVERSE_PASS_NOT_ERP':
            raise ValueError('REAL_PG17_DDL_CAPTURE_REQUIRED')
        if cls.report['before'] != cls.report['restored']:
            raise ValueError('REAL_EXPLICIT_INVERSE_MUST_BE_EXACT')

    def test_exact_install_and_unused_inverse(self):
        catalog_additions.expected(self.product)
        catalog_additions.transition(self.report['before'], self.report['after'], self.profile)
        self.assertEqual(self.report['before'], self.report['restored'])

    def test_undeclared_metadata_and_privileges_refuse(self):
        helper = 'cp7_sku_conversion.automatic_enter_v5(uuid,text,uuid)'
        table = 'cp7_sku_conversion.automatic_context_v5'
        old = 'erp.be_complete_rework_target_v1(uuid)'
        def private_grant(b, a): a['functions'][helper][18].append(['authenticated', 'postgres', 'EXECUTE', False])
        def old_grant(b, a): a['functions'][old][18].append(['anon', 'postgres', 'EXECUTE', False])
        def old_body(b, a): b['functions'][old][0] += '\n-- another source'
        def new_body(b, a): a['functions'][helper][0] += '\n-- another helper'
        def search_path(b, a): a['functions'][helper][12] = ['search_path=public']
        def rls(b, a): a['relations'][table][3] = False
        def column(b, a): a['columns'].pop(table + ':native_request_id')
        def constraint(b, a): a['constraints'].pop(next(iter(self.profile['groups']['constraints'])))
        def index(b, a): a['indexes'][next(iter(self.profile['groups']['indexes']))][1] = False
        def trigger(b, a): a['triggers'].pop(next(iter(self.profile['groups']['triggers'])))
        def new_helper(b, a): a['functions']['cp7_sku_conversion.allow_everything()'] = deepcopy(a['functions'][helper])
        def role(b, a): a['roles']['authenticated'][0] = True
        def member(b, a): a['memberships']['postgres:authenticated:postgres'] = [False, True, True]
        def policy(b, a): a['policies'][table + ':allow_all'] = ['*', True, ['PUBLIC'], 'true', 'true']
        def group(b, a): a.pop('database_authority')
        def schema(b, a): a['schemas']['cp7_sku_conversion'][1].append(['authenticated', 'postgres', 'CREATE', False])
        for mutate in (private_grant, old_grant, old_body, new_body, search_path, rls, column,
                       constraint, index, trigger, new_helper, role, member, policy, group, schema):
            with self.subTest(counter=mutate.__name__):
                before, after = deepcopy(self.report['before']), deepcopy(self.report['after'])
                mutate(before, after)
                with self.assertRaises(ValueError):
                    catalog_additions.transition(before, after, self.profile)

    def test_profile_itself_cannot_admit_authority_changes(self):
        original_read = Path.read_bytes
        def run(profile):
            def read(path):
                return json.dumps(profile).encode() if path == HERE / 'CATALOG_ADDITIONS.json' else original_read(path)
            with patch.object(Path, 'read_bytes', read), self.assertRaises(ValueError):
                catalog_additions.expected(self.product)
        helper = 'cp7_sku_conversion.automatic_valid_v5()'
        for field, value in ((1, 'authenticated'), (4, False), (12, ['search_path=public']),
                             (18, [['authenticated', 'postgres', 'EXECUTE', False]])):
            forged = deepcopy(self.profile)
            forged['groups']['functions'][helper][field] = value
            run(forged)
        forged = deepcopy(self.profile)
        forged['groups']['relations']['cp7_sku_conversion.automatic_context_v5'][3] = False
        run(forged)
        forged = deepcopy(self.profile)
        forged['groups']['roles']['unapproved'] = []
        run(forged)
        forged = deepcopy(self.profile)
        forged['replacement_functions']['erp.be_complete_rework_target_v1(uuid)'][18].append(['PUBLIC', 'postgres', 'EXECUTE', False])
        run(forged)


class InstallerUsedGuard(unittest.TestCase):
    def test_actual_inverse_body_refuses_changed_rows_or_sequence_before_DDL(self):
        # Compile the actual unmodified owning function. Only dependency I/O is
        # modeled; SQL execution itself is covered by the separate PG17 capture.
        path = HERE / 'composition.py'
        tree = ast.parse(path.read_bytes())
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'rollback_delta_preuse'
                 or isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'USED_ERROR' for t in n.targets)]
        self.assertEqual(len(nodes), 2)
        for actual in ({'rows': {'admission': 1}, 'sequences': {'seq': 1}},
                       {'rows': {}, 'sequences': {'seq': 2}}):
            with self.subTest(actual=actual):
                calls = []
                prior = SimpleNamespace(predecessor=SimpleNamespace(_locks=lambda cur: calls.append('global_lock')))
                predecessor = SimpleNamespace(atomic=lambda cur: nullcontext(), predecessor=prior)
                catalog = SimpleNamespace(_lock_tables=lambda cur: calls.append('tables_locked'), _data=lambda cur: actual)
                def unexpected(*args, **kwargs): raise AssertionError('No DDL/preparation/owner switch is allowed after use')
                ns = dict(runtime=lambda: (None, None, None, predecessor, catalog),
                          verify=lambda cur, state: calls.append('exact_verify'), prepared=unexpected, as_owner=unexpected)
                exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), ns)
                cur = SimpleNamespace(execute=unexpected)
                state = dict(preuse_data_and_sequences={'rows': {}, 'sequences': {'seq': 1}})
                with self.assertRaisesRegex(ValueError, 'AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'):
                    ns['rollback_delta_preuse'](cur, state)
                self.assertEqual(calls, ['global_lock', 'exact_verify', 'tables_locked'])


if __name__ == '__main__':
    unittest.main()
