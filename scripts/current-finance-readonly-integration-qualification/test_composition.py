from copy import deepcopy
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
import composition as product


class CompositionBoundary(unittest.TestCase):
    def setUp(self):
        self.before = {'functions': {k: ['old', 'owner', 'same-authority'] for k in product.REPLACED}}
        self.before.update({str(i): {'member': ['unchanged']} for i in range(21)})
        self.after = deepcopy(self.before)
        for key in product.REPLACED:
            self.after['functions'][key][0] = 'exact-new-definition'
        for key in product.ADDED:
            self.after['functions'][key] = ['new-private-function']

    def test_only_four_function_delta_admitted(self):
        product.admit_delta(self.before, self.after)

    def test_unrelated_schema_change_refused(self):
        self.after['0']['member'] = ['changed']
        with self.assertRaisesRegex(ValueError, 'UNDECLARED_DELTA'):
            product.admit_delta(self.before, self.after)

    def test_existing_function_grant_or_owner_change_refused(self):
        for offset in (1, 2):
            after = deepcopy(self.after)
            after['functions'][sorted(product.REPLACED)[0]][offset] = 'changed'
            with self.subTest(offset=offset), self.assertRaisesRegex(ValueError, 'UNDECLARED_DELTA'):
                product.admit_delta(self.before, after)

    def test_extra_private_function_refused(self):
        self.after['functions']['cp7_finance.extra()'] = ['unexpected']
        with self.assertRaisesRegex(ValueError, 'UNDECLARED_DELTA'):
            product.admit_delta(self.before, self.after)

    def test_incomplete_install_refused(self):
        del self.after['functions'][sorted(product.ADDED)[0]]
        with self.assertRaisesRegex(ValueError, 'INCOMPLETE_DELTA'):
            product.admit_delta(self.before, self.after)

    def test_missing_catalog_group_refused(self):
        del self.after['0']
        with self.assertRaisesRegex(ValueError, 'ALL22_REQUIRED'):
            product.admit_delta(self.before, self.after)

    def test_pending_race_refuses_before_database_access(self):
        class NoDatabase:
            def __getattr__(self, name):
                raise AssertionError('DATABASE_TOUCHED_BEFORE_RACE_ACCEPTANCE:' + name)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'PREREQUISITES.json').write_text(json.dumps({'source_race': None}))
            with patch.object(product, 'HERE', root), self.assertRaisesRegex(ValueError, 'ACCEPTED_ORIGINAL_REQUIRED'):
                product.install(NoDatabase())
            with patch.object(product, 'HERE', root), self.assertRaisesRegex(ValueError, 'ACCEPTED_ORIGINAL_REQUIRED'):
                product.install_delta(NoDatabase(), {})

    def test_incomplete_or_empty_package_gates_refused(self):
        for gate in ({}, {'writer_runtime': True}, {k: k != 'security_advisors' for k in ('installed', 'primary_unchanged', 'backup_restore_drill', 'security_advisors', 'writer_runtime')}):
            race = dict(head='bd3505f624fb4e821ea9ef2ea039313abd850fd5', status='PASS',
                        source_change_race_qualification=True, package_gate=gate,
                        cp6_restored=True, advisor_gate=True)
            with self.subTest(gate=gate), self.assertRaisesRegex(ValueError, 'ACCEPTANCE_CHANGED'):
                product.accepted_prerequisites({'source_race': race})


if __name__ == '__main__':
    unittest.main()
