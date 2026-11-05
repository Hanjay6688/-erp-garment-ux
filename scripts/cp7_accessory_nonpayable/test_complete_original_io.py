"""Exact file/encoder and memory controls; no ERP command is executed."""
import ast
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import gzip
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('afui_complete_original_storage_control', HERE / 'complete_original_io.py')
io = importlib.util.module_from_spec(spec)
spec.loader.exec_module(io)


class CompleteOriginalStorage(unittest.TestCase):
    def value(self):
        return dict(catalogue=['SELECT ' * 90000] * 3, integer=2**70, decimal=Decimal('40.000001'),
                    text='Harga → é €', date=datetime(2026, 11, 4, tzinfo=timezone.utc), nan=float('nan'))

    def test_sorted_complete_original_matches_all_original_encoder_options(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'state.json'
            value = self.value()
            receipt = io.save_sorted(target, value, 'ORIGINAL_CONFLICT')
            expected = (json.dumps(value, sort_keys=True, default=str) + '\n').encode()
            self.assertEqual(target.read_bytes(), expected)
            self.assertEqual(receipt, dict(name=target.name, bytes=len(expected), sha256=sha256(expected).hexdigest()))
            before = target.stat().st_mtime_ns
            self.assertEqual(io.save_sorted(target, value, 'ORIGINAL_CONFLICT'), receipt)
            self.assertEqual(target.stat().st_mtime_ns, before)
            with self.assertRaisesRegex(ValueError, 'ORIGINAL_CONFLICT'):
                io.save_sorted(target, dict(changed=True), 'ORIGINAL_CONFLICT')
            self.assertEqual(target.read_bytes(), expected)

    def test_failed_encoder_preserves_the_previous_complete_original(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'state.json'
            target.write_bytes(b'previous complete original\n')
            cyclic = []
            cyclic.append(cyclic)
            with self.assertRaisesRegex(ValueError, 'Circular reference'):
                io.save_sorted(target, cyclic, 'CONFLICT')
            self.assertEqual(target.read_bytes(), b'previous complete original\n')
            self.assertEqual(len(list(Path(directory).glob('*.partial'))), 1)

    def test_gzip_bytes_and_raw_metadata_match_the_original_compressor(self):
        with tempfile.TemporaryDirectory() as directory:
            for number, value in enumerate(({}, self.value(), ['simple', 1, 2.5, False, None])):
                target = Path(directory) / (str(number) + '.json.gz')
                raw = (json.dumps(value, sort_keys=True, default=str) + '\n').encode()
                expected = gzip.compress(raw, mtime=0)
                result = io.save_gzip_sorted(target, value)
                self.assertEqual(target.read_bytes(), expected)
                self.assertEqual(result, dict(name=target.name, bytes=len(raw), sha256=sha256(raw).hexdigest(),
                    gzip_bytes=len(expected), gzip_sha256=sha256(expected).hexdigest()))
                with self.assertRaises(FileExistsError):
                    io.save_gzip_sorted(target, value)
                self.assertEqual(target.read_bytes(), expected)

    def test_native_group_copy_compares_complete_bytes_and_refuses_conflicting_original(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source.json'
            target = Path(directory) / 'target.json'
            source.write_bytes(b'complete Native group ' * 200000)
            original = source.read_bytes()
            receipt = io.copy_exact(source, target, 'STRICT_ORIGINAL_CHANGED')
            self.assertEqual(target.read_bytes(), original)
            self.assertEqual(receipt, dict(name=target.name, **io.pin(source)))
            self.assertEqual(io.copy_exact(source, target, 'STRICT_ORIGINAL_CHANGED'), receipt)
            self.assertEqual(io.copy_exact(source, source, 'STRICT_ORIGINAL_CHANGED'), dict(name=source.name, **io.pin(source)))
            source.write_bytes(b'changed source')
            with self.assertRaisesRegex(ValueError, 'STRICT_ORIGINAL_CHANGED'):
                io.copy_exact(source, target, 'STRICT_ORIGINAL_CHANGED')
            self.assertEqual(target.read_bytes(), original)

    def test_only_complete_named_outputs_are_published_without_renaming(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(io, 'OUT', Path(directory)):
            name = 'AFUI_BROWSER_SETTINGS_STATE.json'
            target = Path(directory) / name
            io.save_sorted(target, dict(all_fields=['preserved']), 'CONFLICT')
            io.publish(target)
            linked = Path(directory) / 'AFUI_CASE_STDOUT' / name
            self.assertEqual(target.stat().st_ino, linked.stat().st_ino)
            self.assertEqual(linked.read_bytes(), target.read_bytes())
            io.publish(target)
            other = Path(directory) / 'unrelated.json'
            other.write_text('{}\n')
            io.publish(other)
            self.assertFalse((linked.parent / other.name).exists())

    def test_verified_reader_refuses_changed_bytes_before_json_parsing(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'state.json'
            target.write_bytes(b'{"whole": [1, 2, "retained"]}\n')
            actual = io.pin(target)
            self.assertEqual(io.read_verified_json(target, actual['sha256'], 'ORIGINAL_REQUIRED'),
                             json.loads(target.read_bytes()))
            target.write_bytes(b'not JSON and not the required original')
            with self.assertRaisesRegex(ValueError, 'ORIGINAL_REQUIRED'):
                io.read_verified_json(target, actual['sha256'], 'ORIGINAL_REQUIRED')

    def test_symlink_output_is_refused_before_any_original_is_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / 'original.json'
            original.write_bytes(b'original\n')
            link = Path(directory) / 'link.json'
            link.symlink_to(original)
            with self.assertRaisesRegex(ValueError, 'REGULAR_ABSOLUTE_PATH'):
                io.save_sorted(link, dict(changed=True), 'CONFLICT')
            self.assertEqual(original.read_bytes(), b'original\n')

    def test_all_financial_functions_assertions_and_declared_SQL_remain_exact(self):
        allowed = {'qualification_component.py': {'save', 'retain'}, 'access_cases.py': {'retain'},
                   'browser_fixture.py': {'main'}}
        for name, changed in allowed.items():
            old = subprocess.check_output(['git', '-C', str(ROOT), 'show',
                'e0cfa98382e977933d63e9f828de17a0faba9ef9:scripts/cp7_accessory_nonpayable/' + name])
            raw=(HERE / name).read_text()
            if name=='qualification_component.py':
                routes={
                    'case_output,progress,report_io,state_prepare': 'case_output,progress,report_io',
                    "    with progress.phase('COMPLETE_STATE_PREREQUISITE'):\n"
                    "        prepared_state=state_prepare.prepare(state,ROOT/'cp6-proof/t3',save)\n"
                    "    report.update({key:prepared_state[key]for key in('browser_settings_state_original','browser_settings_cache_original')})\n":'',
                    "    state_prepare.verify_unchanged(state,prepared_state)\n":'',
                    "        report['browser_fixture_original']=save('AFUI_BROWSER_NATIVE_PREREQUISITE.json',prepared)\n":
                    "        report['browser_fixture_original']=save('AFUI_BROWSER_NATIVE_PREREQUISITE.json',prepared)\n"
                    "        report['browser_settings_state_original']=save('AFUI_BROWSER_SETTINGS_STATE.json',state)\n",
                    "        AFUI_BROWSER_STATE_CACHE_SHA256=report['browser_settings_cache_original']['sha256'],\n":'',
                }
                for route,original_route in routes.items():
                    self.assertEqual(raw.count(route),1)
                    raw=raw.replace(route,original_route,1)
            before, after = ast.parse(old), ast.parse(raw)
            original = {n.name: n for n in before.body if isinstance(n, ast.FunctionDef)}
            current = {n.name: n for n in after.body if isinstance(n, ast.FunctionDef)}
            self.assertEqual(set(original), set(current))
            self.assertEqual({key for key in original if ast.dump(original[key]) != ast.dump(current[key])}, changed)
            self.assertEqual([ast.dump(n) for n in ast.walk(before) if isinstance(n, ast.Assert)],
                             [ast.dump(n) for n in ast.walk(after) if isinstance(n, ast.Assert)])
            def sql(tree):
                return [ast.dump(n) for n in ast.walk(tree) if isinstance(n, ast.Call)
                        and isinstance(n.func, ast.Attribute) and n.func.attr == 'execute']
            self.assertEqual(sql(before), sql(after))

    def test_large_state_and_gzip_fit_the_bounded_memory_control(self):
        script = '''import importlib.util,json,resource,sys,hashlib
from pathlib import Path
spec=importlib.util.spec_from_file_location('isolated_original_io',sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
resource.setrlimit(resource.RLIMIT_AS,(160*1024*1024,160*1024*1024))
sql='SQL'*350000
value={'catalogues':[sql]*80}
target=Path(sys.argv[3])/'state.json'
if sys.argv[2]=='old':
 try:raw=(json.dumps(value,sort_keys=True,default=str)+'\\n').encode()
 except MemoryError:sys.exit(0)
 raise AssertionError('Original whole-buffer writer unexpectedly fitted this memory counterexample')
receipt=m.save_sorted(target,value,'CONFLICT')
packed=m.save_gzip_sorted(target.with_suffix('.json.gz'),value)
h=hashlib.sha256();h.update(b'{"catalogues": [')
for n in range(80):h.update(json.dumps(sql).encode()+(b', 'if n<79 else b''))
h.update(b']}\\n')
assert receipt['sha256']==h.hexdigest() and packed['sha256']==receipt['sha256']
assert receipt['bytes']==packed['bytes'] and receipt['bytes']>80*1024*1024
print(json.dumps({'complete_bytes':receipt['bytes'],'raw_sha256':receipt['sha256'],'peak_RSS_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'actual_ERP_cases':0}))
'''
        with tempfile.TemporaryDirectory() as directory:
            for mode in ('old', 'new'):
                result = subprocess.run([sys.executable, '-B', '-c', script, str(HERE / 'complete_original_io.py'), mode, directory],
                                        text=True, capture_output=True, timeout=60)
                self.assertEqual(result.returncode, 0, (mode, result.stdout, result.stderr))
                if mode == 'new':
                    print(result.stdout.strip())


if __name__ == '__main__':
    unittest.main()
