from pathlib import Path
from types import CodeType, FunctionType, ModuleType
from unittest.mock import patch
import gzip
import hashlib
import importlib.util
import json
import os
import re
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('tested_catalogue_decode', HERE / 'catalogue_decode.py')
cache = importlib.util.module_from_spec(spec); spec.loader.exec_module(cache)


class CatalogueControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.catalogue = self.root / 'docs/cp7/evidence/p00/CP7_P00_CATALOGUE.json.gz'
        self.catalogue.parent.mkdir(parents=True)
        self.modules = {}
        for name in cache.PINS:
            source = HERE.parents[1] / 'scripts' / (name + '.py')
            path = self.root / 'scripts' / source.name
            path.parent.mkdir(exist_ok=True); path.write_bytes(source.read_bytes())
            module = ModuleType(name)
            module.__file__ = str(path)
            module.ROOT, module.CATALOGUE = self.root, self.catalogue
            module.gzip, module.json, module.hashlib = gzip, json, hashlib
            code = next(c for c in compile(path.read_bytes(), str(path), 'exec', dont_inherit=True).co_consts
                        if isinstance(c, CodeType) and c.co_name == 'accepted')
            module.accepted = FunctionType(code, module.__dict__)
            self.modules[name] = module
        self.write('first')

    def regex_modules(self):
        result = {}
        for name, (relative, function, _, _) in cache.REGEX_PINS.items():
            source = HERE.parents[1] / 'scripts' / relative
            path = self.root / 'scripts' / relative
            path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(source.read_bytes())
            module = ModuleType(name); module.__file__ = str(path); module.re = re
            module.NATIVE = self.root / 'scripts/cp7-src/planning'
            module.SCRIPTS = self.root / 'scripts'
            module.NATIVE.mkdir(parents=True, exist_ok=True)
            code = next(c for c in compile(path.read_bytes(), str(path), 'exec', dont_inherit=True).co_consts
                        if isinstance(c, CodeType) and c.co_name == function)
            setattr(module, function, FunctionType(code, module.__dict__))
            result[name] = module
        return result

    def write(self, definition, valid_hash=True):
        row = dict(schema='erp', name='example', definition=definition,
                   definition_sha256=hashlib.sha256(definition.encode()).hexdigest() if valid_hash else '0' * 64)
        self.catalogue.write_bytes(gzip.compress(json.dumps(dict(functions=[row])).encode(), mtime=0))

    def calls(self):
        return (self.modules['cp7_supplier_credit_guard'].accepted('erp.example(uuid)'),
                self.modules['cp7_settlement_bundle'].accepted('example'))

    def test_original_code_and_sha_assertions_run_with_one_decode(self):
        original = {name: module.accepted for name, module in self.modules.items()}
        self.assertEqual(self.calls(), ('first', 'first'))
        with patch.dict(sys.modules, self.modules), cache.scope(self.root) as decoder:
            for _ in range(4):
                self.assertEqual(self.calls(), ('first', 'first'))
            self.assertEqual((decoder.decompressions, decoder.decodes, decoder.gzip_hits, decoder.json_hits), (1, 1, 7, 7))
            for name, module in self.modules.items():
                self.assertIs(module.accepted, original[name])
            self.write('tampered', valid_hash=False)
            for module, name in ((self.modules['cp7_supplier_credit_guard'], 'erp.example(uuid)'),
                                 (self.modules['cp7_settlement_bundle'], 'example')):
                with self.assertRaises(AssertionError):
                    module.accepted(name)
        for module in self.modules.values():
            self.assertIs(module.json, json); self.assertIs(module.gzip, gzip)
        self.assertIsNone(decoder.parsed)

    def test_same_size_same_time_changed_bytes_are_never_a_hit(self):
        with patch.dict(sys.modules, self.modules), cache.scope(self.root) as decoder:
            self.assertEqual(self.calls(), ('first', 'first'))
            before = self.catalogue.stat()
            raw = self.catalogue.read_bytes()
            # gzip's timestamp changes while its length and decoded text do not.
            self.catalogue.write_bytes(raw[:4] + b'\x01\x00\x00\x00' + raw[8:])
            os.utime(self.catalogue, ns=(before.st_atime_ns, before.st_mtime_ns))
            self.assertEqual(self.catalogue.stat().st_size, before.st_size)
            self.assertEqual(self.calls(), ('first', 'first'))
            self.assertEqual(decoder.decompressions, 2)
            self.write('fresh')
            self.assertEqual(self.calls(), ('fresh', 'fresh'))

    def test_parsed_cache_is_immutable(self):
        decoder = cache.Decoder()
        value = decoder.loads(decoder.decompress(self.catalogue.read_bytes()))
        with self.assertRaises(TypeError): value['functions'][0]['definition'] = 'forged'
        with self.assertRaises(TypeError): value['functions'] = []
        self.assertIsInstance(value['functions'], tuple)

    def test_corrupt_input_is_not_hidden_by_previous_success(self):
        with patch.dict(sys.modules, self.modules), cache.scope(self.root):
            self.assertEqual(self.calls(), ('first', 'first'))
            self.catalogue.write_bytes(b'broken gzip')
            with self.assertRaises(gzip.BadGzipFile): self.calls()
            self.catalogue.write_bytes(gzip.compress(b'{bad json'))
            with self.assertRaises(json.JSONDecodeError): self.calls()
            self.write('fixed')
            self.assertEqual(self.calls(), ('fixed', 'fixed'))

    def test_consumer_source_change_is_refused(self):
        module = next(iter(self.modules.values()))
        path = Path(module.__file__); path.write_bytes(path.read_bytes() + b'\n')
        with patch.dict(sys.modules, self.modules), self.assertRaisesRegex(ValueError, 'EXACT_CONSUMER_BYTES'):
            with cache.scope(self.root): pass

    def test_changed_function_or_origin_is_refused(self):
        module = self.modules['cp7_settlement_bundle']; original = module.accepted
        module.accepted = lambda name: 'forged'
        with patch.dict(sys.modules, self.modules), self.assertRaisesRegex(ValueError, 'UNCHANGED_ACCEPTED_FUNCTION'):
            with cache.scope(self.root): pass
        module.accepted = original; module.ROOT = self.root.parent
        with patch.dict(sys.modules, self.modules), self.assertRaisesRegex(ValueError, 'EXACT_CONSUMER_ORIGIN'):
            with cache.scope(self.root): pass

    def test_nested_scope_and_exception_restore_bindings(self):
        before = list(sys.meta_path)
        with patch.dict(sys.modules, self.modules), self.assertRaisesRegex(RuntimeError, 'deliberate'):
            with cache.scope(self.root) as outer:
                with cache.scope(self.root) as inner:
                    self.assertIs(outer, inner); self.assertEqual(self.calls(), ('first', 'first'))
                raise RuntimeError('deliberate')
        self.assertEqual(sys.meta_path, before)
        self.assertEqual(cache._active, [])
        for module in self.modules.values():
            self.assertIs(module.json, json); self.assertIs(module.gzip, gzip)

    def test_regex_real_source_functions_and_changed_file_input(self):
        modules = self.regex_modules()
        sql = 'create function example.f() returns text as $$begin return 1; end $$;'
        path = self.root / 'scripts/cp7-src/planning/example.sql'; path.write_text(sql)
        analog = modules['cp7_product_analog_consumer_stage.render']
        bounded = modules['cp7_bounded_analysis_stage.source']
        body = modules['cp7_production_stage']
        before = (analog.block('cp7-src/planning/example.sql', 'example.f'),
                  bounded.block('example.sql', 'example.f'), body._body(sql))
        with patch.dict(sys.modules, modules), cache.scope(self.root) as decoder:
            for _ in range(3):
                self.assertEqual((analog.block('cp7-src/planning/example.sql', 'example.f'),
                                  bounded.block('example.sql', 'example.f'), body._body(sql)), before)
            self.assertGreater(decoder.regex_search.cache_info().hits, 0)
            self.assertGreater(decoder.regex_findall.cache_info().hits, 0)
            path.write_text(sql.replace('return 1', 'return 2'))
            self.assertIn('return 2', bounded.block('example.sql', 'example.f'))
            self.assertIn('return 2', analog.block('cp7-src/planning/example.sql', 'example.f'))
        for module in modules.values(): self.assertIs(module.re, re)
        self.assertEqual(decoder.regex_search.cache_info().currsize, 0)

    def test_missing_and_duplicate_sql_keep_original_failures(self):
        modules = self.regex_modules(); path = self.root / 'scripts/cp7-src/planning/example.sql'
        sql = 'create function example.f() returns text as $$begin return 1; end $$;'
        path.write_text(sql)
        with patch.dict(sys.modules, modules), cache.scope(self.root):
            analog = modules['cp7_product_analog_consumer_stage.render']
            self.assertIn('return 1', analog.block('cp7-src/planning/example.sql', 'example.f'))
            path.write_text(sql + '\n' + sql)
            with self.assertRaisesRegex(ValueError, 'PREDECESSOR_NOT_UNIQUE'):
                analog.block('cp7-src/planning/example.sql', 'example.f')
            path.write_text('')
            with self.assertRaisesRegex(ValueError, 'NATIVE_MISSING'):
                modules['cp7_bounded_analysis_stage.source'].block('example.sql', 'example.f')

    def test_regex_flags_patterns_and_mutable_results_are_separate(self):
        decoder = cache.Decoder()
        self.assertIsNone(decoder.regex_search('ABC', 'abc'))
        self.assertEqual(decoder.regex_search('ABC', 'abc', re.I)[0], 'abc')
        found = decoder.findall('(a)(b)', 'ab ab'); found.clear()
        self.assertEqual(decoder.findall('(a)(b)', 'ab ab'), [('a', 'b'), ('a', 'b')])
        self.assertEqual(decoder.findall('x', 'ab ab'), [])

    def test_regex_cache_is_bounded_and_corrupt_expression_still_raises(self):
        decoder = cache.Decoder()
        for n in range(300): decoder.regex_search(str(n), str(n))
        self.assertLessEqual(decoder.regex_search.cache_info().currsize, 256)
        with self.assertRaises(re.error): decoder.regex_search('(', 'abc')

    def test_regex_consumer_bytes_cannot_change(self):
        modules = self.regex_modules()
        path = Path(modules['cp7_production_stage'].__file__)
        path.write_text(path.read_text() + '\n')
        with patch.dict(sys.modules, modules), self.assertRaisesRegex(ValueError, 'EXACT_CONSUMER'):
            with cache.scope(self.root): pass


if __name__ == '__main__':
    unittest.main()
