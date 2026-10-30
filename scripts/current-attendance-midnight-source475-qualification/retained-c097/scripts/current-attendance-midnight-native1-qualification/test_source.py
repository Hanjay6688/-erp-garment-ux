"""Whole-caller source controls within the owned namespace; Native0/DB0."""
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from types import SimpleNamespace
import tempfile
import source_check
from midnight_common import HERE, ROOT, document, NS


class WholeCallerControls(TestCase):
    def test_changed_actual_runtime_source_closes_whole_caller_without_product_edit(self):
        # File-read double only; actual product bytes are never changed.
        real=source_check.regular
        name='scripts/cp7_attendance_period_choice/readers.sql'
        before=(ROOT/name).read_bytes()
        def altered(root,relative):
            path=real(root,relative)
            if relative==name:
                return SimpleNamespace(read_bytes=lambda:before+b'\n-- LOCAL SOURCE READ DOUBLE\n')
            return path
        with patch.object(source_check,'regular',altered):
            with self.assertRaisesRegex(ValueError,'EXACT_BYTES_REQUIRED'):
                source_check.check()
        self.assertEqual((ROOT/name).read_bytes(),before)

    def test_historical_SOURCE_is_pinned_while_only_outer_self_is_excluded(self):
        manifest=document((HERE/'SOURCE.json').read_bytes())
        self.assertIn(NS+'historical-midnight-c0/SOURCE.json',manifest['files'])
        self.assertNotIn(NS+'SOURCE.json',manifest['files'])

    def test_unknown_source_is_refused_by_actual_whole_caller(self):
        target=HERE/'UNDECLARED_LOCAL_CONTROL.py'
        self.assertFalse(target.exists())
        try:
            with target.open('x') as stream:stream.write('raise AssertionError("must not import")\n')
            with self.assertRaisesRegex(ValueError,'UNKNOWN_SOURCE_OR_RECEIPT'):
                source_check.check()
        finally:target.unlink(missing_ok=True)

    def test_same_byte_known_leaf_symlink_refuses_then_exact_bytes_restore(self):
        target=HERE/'CONFIG.json';raw=target.read_bytes();mode=target.stat().st_mode
        with tempfile.TemporaryDirectory(prefix='midnight-known-leaf-') as folder:
            donor=Path(folder)/'config.json';donor.write_bytes(raw)
            try:
                target.unlink();target.symlink_to(donor)
                with self.assertRaisesRegex(ValueError,'SOURCE_SYMLINK'):
                    source_check.check()
            finally:
                target.unlink(missing_ok=True);target.write_bytes(raw);target.chmod(mode)
        self.assertEqual(target.read_bytes(),raw)

    def test_whole_caller_ancestor_symlink_refuses_without_source_copy(self):
        target=HERE/'historical-midnight-c0'
        with tempfile.TemporaryDirectory(prefix='midnight-known-parent-',dir=ROOT.parent) as folder:
            donor=Path(folder)/'historical'
            target.rename(donor)
            try:
                target.symlink_to(donor,target_is_directory=True)
                with self.assertRaisesRegex(ValueError,'SOURCE_SYMLINK|UNKNOWN_SOURCE_OR_RECEIPT'):
                    source_check.check()
            finally:
                target.unlink(missing_ok=True);donor.rename(target)
