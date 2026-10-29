"""Actual-byte admission with semantic tampering controls, never a DB rerun."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import gzip
import json
import unittest

from admit import admit, IDS

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


class ActualSourceAdmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((HERE / 'CONFIG.json').read_bytes())
        cls.money = json.loads((ROOT / 'scripts/current-vendor-integration-source/CONFIG.json').read_bytes())
        cls.pin = cls.cfg['qualified_source6']
        cls.raw = gzip.decompress((ROOT / cls.pin['original']['path']).read_bytes())
        cls.package = gzip.decompress((ROOT / cls.pin['package']['path']).read_bytes())
        cls.actual = json.loads(cls.raw)
        cls.declaration = json.loads((HERE / 'QUALIFIED_SOURCE_DECLARATION.json').read_bytes())
        cls.runtime = {p: sha256((ROOT / p).read_bytes()).hexdigest() for p in (
            'scripts/cp7_vendor_receivable/receivable.sql',
            'scripts/cp7_vendor_receivable/native_delta.py',
            'scripts/cp7_vendor_receivable/composition.py')}

    def call(self, *, pin=None, actual=None, package=None):
        selected = deepcopy(self.pin) if pin is None else pin
        raw = self.raw
        pkg = self.package
        if actual is not None:
            raw = json.dumps(actual).encode()
            selected['original'].update(bytes=len(raw), sha256=sha256(raw).hexdigest())
        if package is not None:
            pkg = json.dumps(package).encode()
            selected['package'].update(bytes=len(pkg), sha256=sha256(pkg).hexdigest())
        return admit(selected, raw, pkg, self.declaration, self.runtime,
                     self.money['parent_backend_sha256'], self.money['qualified_combined11']['head'],
                     self.money['qualified_money_browser2']['head'], self.cfg['scoped_paint_overlays'],
                     self.money['current_installation_entrypoint'])

    def test_exact_actual_bytes_and_all_six_semantics_pass(self):
        self.assertEqual(self.call()['fresh_browser'], 6)

    def test_closed_or_changed_bytes_are_refused(self):
        with self.assertRaises(ValueError):
            admit(None, b'', b'', {}, {}, '', '', '', [], {})
        wrong = deepcopy(self.pin)
        wrong['original']['sha256'] = '0' * 64
        with self.assertRaises(AssertionError):
            self.call(pin=wrong)

    def test_semantic_tampering_is_refused_even_with_matching_new_byte_hashes(self):
        def row(a):
            return a['committed']['OW08_SOURCE_BROWSER6']['browser']['cases'][IDS[-1]]

        controls = {
            'restoration': lambda a: a.update(cp6_restored=False),
            'used_inverse_guard': lambda a: a.update(used_guard_refused_before_DDL=False),
            'other_head': lambda a: a.update(qualification_commit='0' * 40),
            'money_reexecuted': lambda a: a['source_declaration'].update(retained_money_browser_repeated=True),
            'real_auth': lambda a: a['committed']['OW08_SOURCE_BROWSER6']['browser'].update(real_auth=False),
            'physical_stock_changed': lambda a: row(a).update(all_business_rows_and_sequences_unchanged=False),
            'wrong_actor': lambda a: row(a).update(positive_actor_role='ADMIN'),
            'not_denied': lambda a: row(a)['admin_denial'].update(http_status=200),
            'wrong_server_code': lambda a: row(a)['admin_denial']['body'].update(code='P0001'),
            'leaked_document': lambda a: row(a)['admin_denial']['body'].update(document={}),
            'wrong_ui_message': lambda a: row(a)['admin_denial'].update(display_message='ok'),
            'denied_DML': lambda a: row(a)['admin_denial'].update(business_unchanged=False),
            'page_overflow': lambda a: row(a)['width'].update(page=391),
            'missing_case': lambda a: a['committed']['OW08_SOURCE_BROWSER6']['browser']['cases'].pop(IDS[0]),
        }
        for name, mutate in controls.items():
            with self.subTest(name=name):
                changed = deepcopy(self.actual)
                mutate(changed)
                with self.assertRaises((AssertionError, KeyError)):
                    self.call(actual=changed)

    def test_package_gate_failure_is_refused_with_matching_byte_hash(self):
        changed = json.loads(self.package)
        changed['gate']['writer_runtime'] = False
        with self.assertRaises(AssertionError):
            self.call(package=changed)


if __name__ == '__main__':
    unittest.main()
