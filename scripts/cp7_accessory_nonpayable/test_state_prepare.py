"""Early whole-state readiness, real allocation refusal and first Originals."""
from pathlib import Path
from unittest.mock import patch
import copy
import json
import os
import resource
import subprocess
import sys
import tempfile
import unittest
from . import complete_original_io as io, lossless_state, state_prepare as prepare

HERE = Path(__file__).resolve().parent


class StatePreparationControls(unittest.TestCase):
    def sample(self):
        parent = dict(sql='SELECT € ' * 1000, rows=[dict(amount='0.014', count=2**70)])
        return dict(before=parent, after=copy.deepcopy(parent), retained=parent,
                    flags=[None, True, False, -0.0])

    def test_graph_preserves_values_independent_snapshots_and_intentional_sharing(self):
        original = self.sample()
        pin = lossless_state.graph_pin(original)
        self.assertEqual(pin, lossless_state.graph_pin(copy.deepcopy(original)))
        reordered = dict(reversed(list(original.items())))
        self.assertEqual(pin, lossless_state.graph_pin(reordered))
        self.assertGreater(pin['repeated_container_references'], 0)

    def test_graph_refuses_silent_scalar_column_history_and_alias_changes(self):
        original = self.sample();prepared = dict(graph=lossless_state.graph_pin(original))
        mutations = [lambda v:v['before']['rows'][0].update(amount='0.015'),
                     lambda v:v['after']['rows'][0].update(extra_column=None),
                     lambda v:v.update(retained=copy.deepcopy(v['before'])),
                     lambda v:v.update(after=v['before'])]
        for mutate in mutations:
            changed = copy.deepcopy(original);mutate(changed)
            with self.assertRaisesRegex(ValueError, 'CHANGED_AFTER_EARLY'):
                prepare.verify_unchanged(changed, prepared)

    def test_graph_rejects_cycles_nonfinite_and_nonstring_keys(self):
        cyclic = [];cyclic.append(cyclic)
        for value in (cyclic, dict(amount=float('inf')), {1:'not a JSON key'}):
            with self.assertRaises(ValueError):lossless_state.graph_pin(value)

    def test_real_linux_memory_snapshot_supplies_current_address_space(self):
        snapshot = prepare.memory_snapshot()
        self.assertGreater(snapshot['effective_total_bytes'], 0)
        self.assertGreater(snapshot['virtual_bytes'], snapshot['resident_bytes'])
        self.assertGreaterEqual(snapshot['available_bytes'], 0)

    def test_budget_keeps_recovery_reserve_and_never_raises_existing_limits(self):
        mib = prepare.MiB
        snapshot = dict(effective_total_bytes=4096*mib, available_bytes=2048*mib, virtual_bytes=256*mib)
        budget = prepare.memory_budget(snapshot, (768*mib, 1024*mib))
        self.assertEqual(budget['reserved_available_bytes'], 1024*mib)
        self.assertEqual(budget['temporary_soft_bytes'], 768*mib)
        for available, soft in ((100*mib, resource.RLIM_INFINITY), (2048*mib, 280*mib)):
            with self.assertRaisesRegex(ValueError, 'INSUFFICIENT_RECOVERY_MEMORY_HEADROOM'):
                prepare.memory_budget(dict(snapshot, available_bytes=available), (soft, resource.RLIM_INFINITY))

    def test_cgroup_ancestor_limits_and_usage_bound_host_available_memory(self):
        files = {'/proc/meminfo':'MemTotal: 8388608 kB\nMemAvailable: 7340032 kB\n',
                 '/proc/self/cgroup':'0::/qualification/worker\n', '/proc/self/statm':'1024 512',
                 '/sys/fs/cgroup/memory.current':str(1024*prepare.MiB),
                 '/sys/fs/cgroup/memory.max':str(4096*prepare.MiB),
                 '/sys/fs/cgroup/qualification/memory.current':str(512*prepare.MiB),
                 '/sys/fs/cgroup/qualification/memory.high':str(2048*prepare.MiB)}
        with patch.object(Path, 'read_text', lambda path:files[str(path)]), \
             patch.object(Path, 'is_file', lambda path:str(path) in files):
            snapshot = prepare.memory_snapshot()
        self.assertEqual(snapshot['effective_total_bytes'], 2048*prepare.MiB)
        self.assertEqual(snapshot['available_bytes'], 1536*prepare.MiB)
        self.assertEqual(len(snapshot['cgroup_limits']), 2)

    def test_actual_child_allocation_fails_with_memoryerror_and_exact_limits_restore(self):
        script = '''import resource,sys
sys.path.insert(0,sys.argv[1])
from cp7_accessory_nonpayable import state_prepare as m
original=resource.getrlimit(resource.RLIMIT_AS)
virtual=m.memory_snapshot()['virtual_bytes']
cap=virtual+32*m.MiB
assert all(v==resource.RLIM_INFINITY or v>=cap for v in original)
budget=dict(temporary_soft_bytes=cap,original_soft_bytes=original[0],original_hard_bytes=original[1])
try:
 with m.memory_limit(budget):
  assert resource.getrlimit(resource.RLIMIT_AS)==(cap,original[1])
  value=bytearray(128*m.MiB)
except MemoryError:pass
else:raise AssertionError('Actual bounded allocation was not refused')
assert resource.getrlimit(resource.RLIMIT_AS)==original
try:
 with m.memory_limit(budget):raise ValueError('original-sentinel')
except ValueError as e:assert str(e)=='original-sentinel'
assert resource.getrlimit(resource.RLIMIT_AS)==original
with m.memory_limit(budget):value=bytearray(m.MiB)
assert resource.getrlimit(resource.RLIMIT_AS)==original
print('ACTUAL_ALLOCATION_REFUSAL_AND_EXACT_SOFT_HARD_RESTORATION_PASS')
'''
        result = subprocess.run([sys.executable, '-B', '-c', script, str(HERE.parent)],
            capture_output=True, text=True, timeout=20, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('ACTUAL_ALLOCATION_REFUSAL', result.stdout)

    def saver(self, directory):
        def save(name, value):
            receipt = io.save_sorted(directory / name, value, 'FIRST_ORIGINAL_CONFLICT')
            io.publish(directory / name)
            return receipt
        return save

    def test_early_actual_cache_retains_every_original_byte_and_container_identity(self):
        with tempfile.TemporaryDirectory() as td, patch.object(io, 'OUT', Path(td)):
            directory = Path(td);value = self.sample()
            limits = resource.getrlimit(resource.RLIMIT_AS)
            result = prepare.prepare(value, directory, self.saver(directory))
            self.assertEqual(resource.getrlimit(resource.RLIMIT_AS), limits)
            original = directory / 'AFUI_BROWSER_SETTINGS_STATE.json'
            cache = directory / 'AFUI_BROWSER_SETTINGS_STATE_CACHE.json'
            decoded = lossless_state.read(cache, result['browser_settings_cache_original']['sha256'],
                original, result['browser_settings_state_original']['sha256'])
            self.assertEqual(decoded, json.loads(original.read_text()))
            self.assertIs(decoded['before'], decoded['retained'])
            self.assertIsNot(decoded['before'], decoded['after'])
            self.assertEqual(lossless_state.canonical_pin(decoded), io.pin(original))
            record = json.loads((directory / prepare.RESULT).read_text())
            self.assertEqual(record['status'], 'PASS_COMPLETE_HOT_STATE_PREREQUISITE')
            self.assertEqual(record['actual_case_credit'], 0)
            self.assertFalse(record['previous_runner_shutdown_origin_proven'])
            self.assertEqual({p.name for p in (directory / 'AFUI_CASE_STDOUT').iterdir()},
                {prepare.START, prepare.RESULT, original.name, cache.name})

    def test_bad_complete_source_pin_preserves_first_failure_and_restores_limits(self):
        with tempfile.TemporaryDirectory() as td, patch.object(io, 'OUT', Path(td)):
            directory = Path(td);save = self.saver(directory)
            def wrong_pin(name, value):
                receipt = save(name, value)
                if name == 'AFUI_BROWSER_SETTINGS_STATE.json':receipt['sha256'] = '0'*64
                return receipt
            limits = resource.getrlimit(resource.RLIMIT_AS)
            with self.assertRaisesRegex(ValueError, 'EVERY_CANONICAL_ORIGINAL_BYTE'):
                prepare.prepare(self.sample(), directory, wrong_pin)
            self.assertEqual(resource.getrlimit(resource.RLIMIT_AS), limits)
            record = json.loads((directory / prepare.RESULT).read_text())
            self.assertEqual(record['status'], 'FAILED_COMPLETE_HOT_STATE_PREREQUISITE')
            self.assertEqual(record['stage'], 'COMPLETE_LOSSLESS_CACHE_AND_EVERY_CANONICAL_BYTE')
            self.assertFalse((directory / 'AFUI_BROWSER_SETTINGS_STATE_CACHE.json').exists())

    def test_completed_originals_cannot_be_replaced_by_a_changed_retry(self):
        with tempfile.TemporaryDirectory() as td, patch.object(io, 'OUT', Path(td)):
            directory = Path(td);value = self.sample();save = self.saver(directory)
            prepare.prepare(value, directory, save)
            before = {p.name:p.read_bytes() for p in directory.iterdir() if p.is_file()}
            value['before']['rows'][0]['amount'] = 'changed'
            with self.assertRaisesRegex(ValueError, 'FIRST_ORIGINAL_CONFLICT'):
                prepare.prepare(value, directory, save)
            self.assertEqual({name:(directory/name).read_bytes() for name in before}, before)

    def test_no_memory_headroom_refuses_before_raw_state_or_business_work(self):
        with tempfile.TemporaryDirectory() as td, patch.object(io, 'OUT', Path(td)), \
             patch.object(prepare, 'memory_snapshot', return_value=dict(effective_total_bytes=1024*prepare.MiB,
                available_bytes=0, virtual_bytes=128*prepare.MiB)):
            directory = Path(td)
            with self.assertRaisesRegex(ValueError, 'INSUFFICIENT_RECOVERY_MEMORY_HEADROOM'):
                prepare.prepare(self.sample(), directory, self.saver(directory))
            self.assertFalse((directory / 'AFUI_BROWSER_SETTINGS_STATE.json').exists())
            record = json.loads((directory / prepare.RESULT).read_text())
            self.assertEqual(record['error_type'], 'ValueError')
            self.assertEqual(record['actual_case_credit'], 0)

    def test_early_producer_and_later_graph_guard_enclose_native_group(self):
        import ast
        module = ast.parse((HERE / 'qualification_component.py').read_text())
        exercise = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == 'exercise')
        calls = {ast.unparse(n.func):n.lineno for n in ast.walk(exercise) if isinstance(n, ast.Call)
                 and ast.unparse(n.func) in ('state_prepare.prepare', 'native.strict_group',
                     'state_prepare.verify_unchanged', 'committed_prerequisite')}
        self.assertEqual(len(calls), 4)
        self.assertLess(calls['state_prepare.prepare'], calls['native.strict_group'])
        self.assertLess(calls['native.strict_group'], calls['state_prepare.verify_unchanged'])
        self.assertLess(calls['state_prepare.verify_unchanged'], calls['committed_prerequisite'])


if __name__ == '__main__':unittest.main()
