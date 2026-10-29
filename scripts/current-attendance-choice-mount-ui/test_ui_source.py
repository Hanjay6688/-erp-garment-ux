"""Local exact source boundaries; Git object reads only, never DB/remote execution."""
from pathlib import Path
import os
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = 'a5774f59ce67fd18427a9aa700ee5e34fdece5b3'
UI = 'abdbc3060b02e69c0ed8476ec6a23f5cb98892ea'
COPIED = (
    'src/AttendancePeriodChoicePanel.tsx', 'src/attendancePeriodChoiceContract.ts', 'src/attendance-period-choice.css',
    'src/AttendancePeriodChoicePanel.dom.test.tsx', 'src/attendancePeriodChoiceContract.test.ts',
    'tests/fixtures/attendancePeriodChoice.ts', 'src/productionRecovery.ts', 'src/productionRecovery.test.ts',
)
RPCS = (
    'src/attendancePeriodChoiceContract.ts:erp_cp7_get_attendance_choice_v1',
    'src/attendancePeriodChoiceContract.ts:erp_cp7_preview_attendance_choice_v1',
    'src/attendancePeriodChoiceContract.ts:erp_cp7_save_attendance_choice_v1',
)


def original(commit, path):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', commit + ':' + path],
        env=dict(os.environ, GIT_NO_LAZY_FETCH='1'))


class SourceBoundaries(unittest.TestCase):
    def test_all_eight_previously_frozen_ui_and_test_files_are_exact(self):
        for path in COPIED:
            with self.subTest(path=path):
                self.assertEqual((ROOT / path).read_bytes(), original(UI, path))

    def test_no_app_menu_hook_dependency_backend_or_s05_edit(self):
        paths = ['src/App.tsx', 'src/useProductionMutation.ts', 'package.json', 'package-lock.json', 'src/hpp-pool.css',
            'scripts/cp7_attendance_period_choice/choice.sql', 'scripts/cp7_attendance_period_choice/native_delta.py',
            'scripts/cp7_attendance_period_choice/composition.py', 'scripts/cp7_attendance_period_choice/catalog_contract.py',
            'scripts/cp7_attendance_period_choice/NEW_CATALOG_IDENTITIES.json']
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual((ROOT / path).read_bytes(), original(BASE, path))
        env = dict(os.environ, GIT_NO_LAZY_FETCH='1')
        changed = subprocess.check_output(['git', '-C', str(ROOT), 'diff', BASE, '--name-only'], env=env).decode().splitlines()
        changed += subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '--others', '--exclude-standard'], env=env).decode().splitlines()
        allowed = set(COPIED) | {'src/hppPoolContract.ts', 'src/AttendanceHppPoolPanel.tsx', 'src/AttendanceHppPoolPanel.dom.test.tsx',
            'src/ConnectedSkuHppPage.tsx', 'src/ConnectedSkuHppPage.attendance.dom.test.tsx',
            'src/ConnectedSkuHppPage.attendance.integration.dom.test.tsx',
            'scripts/check-source-ownership.mjs', 'scripts/check-access-catalog.mjs'}
        self.assertEqual([path for path in changed if path not in allowed and not path.startswith('scripts/current-attendance-choice-mount-ui/')], [])

    def test_literal_rpc_registry_has_exactly_three_insertions_and_no_old_change(self):
        path = 'scripts/check-source-ownership.mjs'
        current = (ROOT / path).read_text()
        for rpc in RPCS:
            line = "  '" + rpc + "',\n"
            self.assertEqual(current.count(line), 1)
            current = current.replace(line, '', 1)
        self.assertEqual(current.encode(), original(BASE, path))

    def test_access_census_preserves_every_old_assertion_and_declares_each_new_member(self):
        path = 'scripts/check-access-catalog.mjs'
        current = (ROOT / path).read_text()
        block = re.search(r'// S03 adds only its three existing exact-wire RPC boundaries; frozen evidence and every older boundary stay unchanged\.\nconst cp7AttendanceChoiceBoundaries=\[\n.*?\nfor\(const name of cp7AttendanceChoiceBoundaries\)assert.ok\(rpcBoundaries.has\(name\),name\)\n', current, re.S)
        self.assertIsNotNone(block)
        for rpc in RPCS:
            self.assertEqual(block.group().count("  '" + rpc + "',\n"), 1)
        self.assertIn('assert.equal(new Set(cp7AttendanceChoiceBoundaries).size,3)', block.group())
        current = current.replace(block.group(), '', 1)
        self.assertEqual(current.count('rpcBoundaries.size, cp7AttendanceChoiceBoundaries.length + '), 1)
        current = current.replace('rpcBoundaries.size, cp7AttendanceChoiceBoundaries.length + ', 'rpcBoundaries.size, ', 1)
        self.assertEqual(current.encode(), original(BASE, path))


if __name__ == '__main__':
    unittest.main(verbosity=2)
