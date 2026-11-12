"""Actual derived product interface and full catalogue census controls, without ERP."""

import builtins
from contextlib import chdir
from hashlib import sha256
import inspect
import json
from pathlib import Path
import re
import socket
from tempfile import TemporaryDirectory
from types import CodeType, FunctionType, ModuleType, SimpleNamespace
from unittest import TestCase, main
from unittest.mock import patch

import browser_binding as binding
import psycopg


HERE = Path(__file__).resolve().parent


def forbidden(*args, **kwargs):
    raise AssertionError('The browser census source control may not use a database or network')


def current_product(catalog):
    assembly = binding.entry.assembly
    reference = json.loads((HERE / 'SOURCE_REFERENCE.json').read_bytes())
    name = 'scripts/cp7_sku_automatic_pending/composition.py'
    raw = assembly.git('show', reference['automatic_source']['tree'] + ':' + name)
    expected = reference['automatic_files'][name]
    if assembly.admission.pin(raw) != {key: expected[key] for key in ('bytes', 'sha256')}:
        raise AssertionError('Actual current automatic composition source changed')
    text, _ = assembly.derivation.derive(raw)
    if reference.get('automatic_source', {}).get('public_head') is None:
        raise AssertionError('Exact reviewed automatic donor is required')
    # Execute the entire exact derived module. The catalogue and import-only
    # dependencies model only this read contract, never the product's data.
    product = ModuleType('current_automatic_browser_census_control')
    product.__file__ = str(assembly.FROZEN_AUTO / name)
    product.__package__ = 'cp7_sku_automatic_pending'
    dependencies = {
        ('cp7_laundry_unknown_wash.composition', 0): SimpleNamespace(as_owner=forbidden),
        ('cp7_sku_cost_components', 0): SimpleNamespace(prepared_product=SimpleNamespace()),
        ('', 1): SimpleNamespace(catalog_additions=SimpleNamespace(), installation_product=SimpleNamespace()),
    }

    def import_for_control(name, globals=None, locals=None, fromlist=(), level=0):
        if (name, level) in dependencies:
            return dependencies[name, level]
        if name not in ('hashlib', 'pathlib', 'psycopg') or level:
            raise AssertionError('Unexpected automatic composition import: ' + name)
        return builtins.__import__(name, globals, locals, fromlist, level)

    product.__dict__.update(__builtins__=dict(vars(builtins), __import__=import_for_control),
                            _CURRENT_MONEY_PARENT=SimpleNamespace(runtime=lambda: (None, None, None, None, catalog)),
                            _BRIDGE_SOURCES=forbidden)
    exec(compile(text, product.__file__ + '::current_money_parent', 'exec', dont_inherit=True), product.__dict__)
    if product.runtime()[-1] is not catalog or tuple(inspect.signature(product.verify).parameters) != ('cur', 'state'):
        raise AssertionError('Actual current automatic runtime or verifier interface changed')
    return product


def function(source, namespace):
    complete = compile(source, 'actual_retained_browser_fixture_compiler_control', 'exec', dont_inherit=True)
    code, = [value for value in complete.co_consts if isinstance(value, CodeType) and value.co_name == 'census']
    return FunctionType(code, namespace)


class BrowserCensusControls(TestCase):
    def setUp(self):
        deriver = binding.load('current_browser_exact_census_fixture_control',
            HERE.parent / 'current-sku-managed-recovery-native27-qualification/derive.py')
        self.original, _ = deriver.derive('browser_fixture')
        output, _ = binding.derive_fixture(self.original.encode())
        self.derived, self.proof = binding.derive_census(output)
        self.relations = {name: ['postgres', 'r'] for name in binding.PAIR_CENSUS_TABLES}
        self.relations.update({'erp.partitioned': ['postgres', 'p'], 'erp.summary_cache': ['postgres', 'm'],
                               'cp7_sku_conversion.automatic_context_v5': ['postgres', 'r'],
                               'cp7_sku_conversion.automatic_admissions_v5': ['postgres', 'r'],
                               'erp.MixedCaseSequence': ['postgres', 'S'], 'erp.excluded_view': ['postgres', 'v']})
        self.rows = {str(index): {} for index in range(20)} | {'relations': self.relations, 'sequences': {}}
        self.data = {name: [1, 'verified-row-digest'] for name, row in self.relations.items() if row[1] in ('r', 'p', 'm')}
        self.data['sequence:erp.MixedCaseSequence'] = ['12', True]
        self.catalog = SimpleNamespace(_catalog_rows=lambda _: self.rows, _data=lambda _: self.data)
        self.product = current_product(self.catalog)
        self.context = dict(product=self.product, Path=Path, f=SimpleNamespace(admin=lambda _: None),
                            json=json, re=re, sha256=sha256, digest=lambda _: 'catalogue-digest',
                            _BROWSER_REQUIRE_COMPLETE_CENSUS=lambda rows, data: binding.require_complete_census(
                                rows, data, binding.PAIR_CENSUS_TABLES))

    def test_actual_product_lacks_legacy_tables_and_new_census_keeps_complete_output(self):
        self.assertNotIn('TABLES', self.product.__dict__)
        original = function(self.original, self.context)
        with patch.object(psycopg, 'connect', forbidden), patch.object(socket.socket, 'connect', forbidden):
            with self.assertRaisesRegex(AttributeError, 'TABLES'):
                original(object(), 'SKU29_DESKTOP_CONTROL')
        self.assertTrue(self.proof['previous_source_recovered'])
        self.assertEqual(self.proof['exact_assertion_routes'], 1)
        self.assertEqual(self.proof['pair_product_table_scope'], binding.PAIR_CENSUS_TABLES)
        helper_source = binding.entry.report_io
        helper_path = 'scripts/cp7_accessory_nonpayable/complete_original_io.py'
        raw = binding.entry.assembly.git('show', helper_source.COMPLETE_ORIGINALS_HEAD + ':' + helper_path)
        self.assertEqual((len(raw), sha256(raw).hexdigest()), helper_source.COMPLETE_ORIGINALS_PIN)
        helper = ModuleType('actual_retained_complete_browser_original_io')
        helper.__file__ = helper_path
        exec(compile(raw, helper_path, 'exec', dont_inherit=True), helper.__dict__)
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            writer, auditor, reference = [root / name for name in ('writer', 'auditor', 'reference')]
            for path in (writer, auditor, reference):
                path.mkdir()
            old_product = SimpleNamespace(runtime=self.product.runtime, TABLES=binding.PAIR_CENSUS_TABLES)
            legacy = function(self.original, dict(self.context, product=old_product))
            updated = function(self.derived, dict(self.context, _BROWSER_PROOF_ROOT=auditor,
                                                  _COMPLETE_IO=binding.pretty_originals(helper)))
            with chdir(reference):
                expected = legacy(object(), 'SKU29_DESKTOP_CONTROL')
            with patch.object(psycopg, 'connect', forbidden), patch.object(socket.socket, 'connect', forbidden), chdir(writer):
                result = updated(object(), 'SKU29_DESKTOP_CONTROL')
            path = Path(result['raw_evidence']['path'])
            self.assertFalse((writer / path).exists())
            self.assertEqual((reference / path).read_bytes(), (auditor / path).read_bytes())
            self.assertEqual(result, expected)
            self.assertIs(result['data_and_sequences'], self.data)

    def test_missing_or_extra_current_data_or_sequence_is_refused(self):
        for name in ('cp7_sku_conversion.automatic_context_v5', 'erp.partitioned', 'erp.summary_cache', 'sequence:erp.MixedCaseSequence'):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'SKU29_FULL_CURRENT_CENSUS_REQUIRED'):
                binding.require_complete_census(self.rows, {key: value for key, value in self.data.items() if key != name},
                                                binding.PAIR_CENSUS_TABLES)
        with self.assertRaisesRegex(ValueError, 'SKU29_FULL_CURRENT_CENSUS_REQUIRED'):
            binding.require_complete_census(self.rows, self.data | {'erp.excluded_view': []}, binding.PAIR_CENSUS_TABLES)

    def test_original_pair_table_and_all22_group_are_still_required(self):
        missing = binding.PAIR_CENSUS_TABLES[-1]
        with self.assertRaisesRegex(ValueError, 'SKU29_FULL_CURRENT_CENSUS_REQUIRED'):
            binding.require_complete_census(
                dict(self.rows, relations={name: row for name, row in self.relations.items() if name != missing}),
                {name: row for name, row in self.data.items() if name != missing}, binding.PAIR_CENSUS_TABLES)
        with self.assertRaisesRegex(ValueError, 'SKU29_FULL_CURRENT_CENSUS_REQUIRED'):
            binding.require_complete_census({name: row for name, row in self.rows.items() if name != '0'}, self.data,
                                            binding.PAIR_CENSUS_TABLES)


if __name__ == '__main__':
    main()
