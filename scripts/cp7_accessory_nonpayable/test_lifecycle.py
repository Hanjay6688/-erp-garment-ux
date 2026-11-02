"""Synthetic admission/lifecycle refusal controls, not ERP execution."""
from contextlib import nullcontext
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import builtins
import json
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from cp7_accessory_nonpayable import admission as a, composition as c

GROUPS = ('schemas', 'relations', 'columns', 'constraints', 'indexes', 'triggers', 'functions',
    'aggregates', 'types', 'enums', 'sequences', 'policies', 'extensions', 'roles', 'memberships',
    'event_triggers', 'rules', 'inheritance', 'default_privileges', 'database_authority',
    'type_implementation', 'sequence_ownership')


class Catalog:
    @staticmethod
    def digest(value):
        return sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

    @staticmethod
    def _authority(cur):
        cur.events.append('MODEL_AUTHORITY_CHECK')

    @staticmethod
    def _catalog_rows(cur):
        return deepcopy(cur.catalog)

    @staticmethod
    def _data(cur):
        return deepcopy(cur.data)

    @staticmethod
    def _lock_tables(cur):
        cur.events.append('MODEL_ALL_TABLE_LOCK')


class AdmissionAndLifecycle(unittest.TestCase):
    def fixture(self):
        originals = c.native_derivation.originals()
        definitions, _ = c.native_derivation.derive(originals)
        origin = json.loads((HERE / 'NATIVE_ORIGIN.json').read_bytes())
        before = {group: {} for group in GROUPS}
        before['functions'] = {name: [body] + origin['functions'][name]['metadata']
            for name, body in originals.items()}
        before['roles']['MODEL_OLD_ROLE'] = [False]
        after = deepcopy(before)
        for name, body in definitions.items():
            after['functions'][name][0] = body
        after['functions'].update({name: ['MODEL_PRIVATE_DEFINITION'] for name in c.FUNCTIONS})
        after['schemas'][c.SCHEMA] = ['MODEL_PRIVATE_SCHEMA']
        after['relations'].update({name: ['MODEL_PRIVATE_RELATION'] for name in c.RELATIONS})
        after['constraints'].update(c.ri_catalog.expected_constraints())
        after['triggers'].update(c.ri_catalog.expected_external_triggers(after['constraints']))
        data = {'erp.MODEL_business_row': [1, 'MODEL_ROW_DIGEST'], 'sequence:erp.MODEL_sequence': ['7', True]}
        preinstall = {'MODEL_BEFORE_PARENT': True}
        prior = dict(sources={'MODEL': 'accepted-free-parent', 'lower': {'version': 1}},
            after=deepcopy(before), preuse_data_and_sequences=deepcopy(data),
            preinstall_data_and_sequences=deepcopy(preinstall))
        catalog = Catalog()

        def parent_binding(cat, state):
            return cat.digest({key: state[key] for key in ('sources', 'after',
                'preuse_data_and_sequences', 'preinstall_data_and_sequences')})

        prior['component_binding'] = parent_binding(catalog, prior)
        receipt = {'qualified_complete_DE_FREE_date_sources': a.pin(json.dumps(
            prior['sources'], sort_keys=True, separators=(',', ':')).encode())}
        cur = SimpleNamespace(catalog=deepcopy(before), data=deepcopy(data), events=[],
            authority={name: [str(i), 'postgres', None if i % 2 else '{MODEL_EXPLICIT_ACL}']
                for i, name in enumerate(originals, 1)})

        def execute(sql, args=None, *, prepare=None):
            # Native definitions are multi-statement-mode explicit. The exact
            # single constant DROP uses psycopg's ordinary default, as do the
            # existing admitted components. Do not impose a false model rule.
            self.assertIs(prepare, None if sql == 'drop schema ' + c.SCHEMA + ' cascade' else False)
            if sql == (HERE / 'policy.sql').read_text():
                cur.events.append('MODEL_POLICY_DDL')
            elif sql == (HERE / 'basis.sql').read_text():
                cur.events.append('MODEL_BASIS_DDL')
                cur.catalog = deepcopy(after)
                cur.data = dict(deepcopy(data), **{table: deepcopy(c.EMPTY) for table in c.TABLES})
            elif sql in definitions.values():
                cur.events.append('MODEL_NATIVE_DDL')
            elif sql in originals.values():
                cur.events.append('MODEL_NATIVE_INVERSE_DDL')
            elif sql == 'drop schema ' + c.SCHEMA + ' cascade':
                cur.events.append('MODEL_SCHEMA_INVERSE_DDL')
                cur.catalog = deepcopy(before)
                cur.data = deepcopy(data)
            else:
                raise AssertionError('UNDECLARED_MODEL_DDL:' + sql[:80])

        cur.execute = execute

        def parent_verify(cursor, state):
            self.assertEqual(cursor.catalog, state['after'], 'OLD_PARENT_VERIFIER_CALLED_ON_CHANGED_CATALOGUE')
            cursor.events.append('MODEL_PARENT_VERIFY')
            return {'MODEL_PARENT_VERIFIED': True}

        def parent_remove(cursor, state):
            parent_verify(cursor, state)
            cursor.events.append('MODEL_PARENT_INVERSE')
            cursor.data = deepcopy(preinstall)
            return {'MODEL_PARENT_REMOVED': True}

        parent = SimpleNamespace(sources=lambda: prior['sources'], binding=parent_binding,
            verify=parent_verify, rollback_preuse=parent_remove)
        base = SimpleNamespace(atomic=lambda _: nullcontext(), predecessor=SimpleNamespace(
            predecessor=SimpleNamespace(_locks=lambda cursor: cursor.events.append('MODEL_PARENT_LOCK'))))
        return cur, prior, parent, receipt, (None, None, None, base, catalog)

    def invoke(self, fixture, operation, state=None):
        cur, prior, parent, receipt, runtime = fixture
        with patch.object(c, 'qualification', return_value=receipt), patch.object(c, 'parent', return_value=parent), \
            patch.object(c, 'runtime', return_value=runtime), patch.object(c, 'sources', return_value={'MODEL': 'nonpayable'}), \
            patch.object(c, 'owner_scope', return_value=nullcontext()), \
            patch.object(c, 'raw_authority', side_effect=lambda cursor: deepcopy(cursor.authority)), \
            patch.object(c, 'private_authority', side_effect=lambda cursor: cursor.events.append('MODEL_PRIVATE_AUTHORITY_CHECK')):
            return getattr(c, operation)(cur, prior if operation == 'install_delta' else state)

    def test_unarmed_install_verify_and_inverse_refuse_before_ERP_import_or_SQL(self):
        old_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name.startswith(('psycopg', 'cp7_current_de_free_date', 'cp7_laundry_unknown_wash')):
                raise AssertionError('ERP_IMPORT_BEFORE_ACTUAL_PARENT_RECEIPT')
            return old_import(name, *args, **kwargs)

        class NoSQL:
            def execute(self, *args, **kwargs):
                raise AssertionError('SQL_BEFORE_ACTUAL_PARENT_RECEIPT')

        with patch.object(builtins, '__import__', guarded_import):
            for operation, args in ((c.install, (NoSQL(),)), (c.install_delta, (NoSQL(), {})),
                (c.verify, (NoSQL(), {})), (c.rollback_delta_preuse, (NoSQL(), {})),
                (c.rollback_preuse, (NoSQL(), {})), (c.sources, ()), (c.runtime, ())):
                with self.assertRaisesRegex(ValueError, 'ACTUAL_FREE3_ROOT_INTAKE_PENDING'):
                    operation(*args)

    def test_duplicate_and_nonfinite_receipts_refuse(self):
        for raw in ('{"same":1,"same":2}', '{"n":NaN}', '{"n":1e999}'):
            with self.assertRaises(ValueError):
                a.strict(raw)

    def test_boolean_source_byte_count_refuses(self):
        with self.assertRaisesRegex(ValueError, 'TYPED_SOURCE_PIN'):
            a.require_pin({'bytes': True, 'sha256': 'a' * 64})

    def test_entire_lower_parent_source_change_refuses(self):
        cur, prior, parent, receipt, runtime = self.fixture()
        prior['sources']['lower']['version'] = 2
        with self.assertRaisesRegex(ValueError, 'ENTIRE_ACCEPTED_FREE3'):
            a.qualified_parent_sources(receipt, prior['sources'])
        self.assertEqual(cur.events, [])

    def test_install_verifies_parent_before_any_DDL_and_preserves_rows_sequences(self):
        fixture = self.fixture()
        state = self.invoke(fixture, 'install_delta')
        cur, prior, _, _, _ = fixture
        self.assertLess(cur.events.index('MODEL_PARENT_VERIFY'), cur.events.index('MODEL_POLICY_DDL'))
        self.assertEqual(state['before_data'], prior['preuse_data_and_sequences'])
        self.assertEqual(state['preuse_data_and_sequences'], dict(state['before_data'],
            **{table: c.EMPTY for table in c.TABLES}))
        self.assertEqual(cur.events.count('MODEL_NATIVE_DDL'), 4)

    def test_preuse_delta_inverse_restores_parent_before_parent_verification(self):
        fixture = self.fixture()
        state = self.invoke(fixture, 'install_delta')
        fixture[0].events.clear()
        result = self.invoke(fixture, 'rollback_delta_preuse', state)
        self.assertTrue(result['used_guard_before_DDL'])
        self.assertLess(fixture[0].events.index('MODEL_SCHEMA_INVERSE_DDL'), fixture[0].events.index('MODEL_PARENT_VERIFY'))
        self.assertEqual(fixture[0].data, state['before_data'])

    def test_used_native_row_or_sequence_or_private_basis_refuses_before_inverse_DDL(self):
        for key, value in (('erp.MODEL_business_row', [2, 'CHANGED']),
            ('sequence:erp.MODEL_sequence', ['8', True]), (c.TABLES[1], [1, 'FROZEN_GOOD_BASIS'])):
            fixture = self.fixture()
            state = self.invoke(fixture, 'install_delta')
            cur = fixture[0]
            cur.events.clear()
            cur.data[key] = value
            before = deepcopy(cur.catalog)
            with self.assertRaisesRegex(ValueError, c.USED_ERROR):
                self.invoke(fixture, 'rollback_delta_preuse', state)
            self.assertFalse(any('DDL' in event for event in cur.events))
            self.assertEqual(cur.catalog, before)

    def test_raw_NULL_to_explicit_ACL_change_refuses_before_DDL(self):
        fixture = self.fixture()
        state = self.invoke(fixture, 'install_delta')
        fixture[0].events.clear()
        name = next(name for name, row in fixture[0].authority.items() if row[2] is None)
        fixture[0].authority[name][2] = '{}'
        with self.assertRaisesRegex(ValueError, 'RAW_NATIVE_OID_OWNER_OR_ACL'):
            self.invoke(fixture, 'rollback_delta_preuse', state)
        self.assertFalse(any('DDL' in event for event in fixture[0].events))

    def test_native_metadata_change_refuses_before_install_DDL(self):
        fixture = self.fixture()
        fixture[0].catalog['functions'][c.native_derivation.SNAPSHOT][1] = 'MODEL_OTHER_OWNER'
        # The actual parent's verifier rejects before the new derivation runs.
        with self.assertRaisesRegex(AssertionError, 'OLD_PARENT_VERIFIER'):
            self.invoke(fixture, 'install_delta')
        self.assertFalse(any('DDL' in event for event in fixture[0].events))

    def test_undeclared_old_role_grant_or_extra_parent_trigger_refuses(self):
        for group, key, value in (('roles', 'MODEL_OLD_ROLE', [True]),
            ('functions', c.native_derivation.SNAPSHOT, ['MODEL_UNREVIEWED_BODY']),
            ('triggers', 'erp.MODEL_parent:extra', ['MODEL_EXTRA_TRIGGER'])):
            fixture = self.fixture()
            state = self.invoke(fixture, 'install_delta')
            after = deepcopy(state['after'])
            after[group][key] = value
            with self.assertRaises(ValueError):
                c.transition(state['before'], after, state['definitions'])

    def test_coordinated_preuse_rebinding_does_not_rewrite_accepted_parent(self):
        fixture = self.fixture()
        state = self.invoke(fixture, 'install_delta')
        state['before_data']['erp.MODEL_business_row'] = [9, 'REBOUND']
        state['preuse_data_and_sequences']['erp.MODEL_business_row'] = [9, 'REBOUND']
        fixture[0].events.clear()
        with self.assertRaisesRegex(ValueError, 'EXACT_ACCEPTED_PARENT_STATE'):
            self.invoke(fixture, 'rollback_delta_preuse', state)
        self.assertFalse(any('DDL' in event for event in fixture[0].events))

    def test_full_inverse_removes_delta_before_parent(self):
        fixture = self.fixture()
        state = self.invoke(fixture, 'install_delta')
        fixture[0].events.clear()
        self.invoke(fixture, 'rollback_preuse', state)
        self.assertLess(fixture[0].events.index('MODEL_SCHEMA_INVERSE_DDL'), fixture[0].events.index('MODEL_PARENT_INVERSE'))
        self.assertEqual(fixture[0].data, state['preinstall_data_and_sequences'])


if __name__ == '__main__':
    unittest.main()
