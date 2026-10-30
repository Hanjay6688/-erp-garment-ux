"""Local filesystem-only fault-construction controls; no product/DB action."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase,main
from unittest.mock import patch
import importlib.util

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('s03_lawful_fault_restore_controls',HERE/'whole_caller_matrix.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class Restore(TestCase):
    def fixture(self,root,directory):
        p=root/'source'
        if directory:p.mkdir();target=p/'file';target.write_bytes(b'LOCAL_RAW_SOURCE_DOUBLE');target.chmod(0o640)
        else:p.write_bytes(b'LOCAL_RAW_SOURCE_DOUBLE');p.chmod(0o640)
        return p

    def test_leaf_and_ancestor_symlink_creation_failure_restore_original_bytes_modes(self):
        for directory in (False,True):
            with self.subTest(directory=directory),TemporaryDirectory()as temp:
                root=Path(temp);target=self.fixture(root,directory);before=m.snapshot(target)
                with patch.object(Path,'symlink_to',side_effect=OSError('LOCAL_CREATION_FAILURE')):
                    with self.assertRaisesRegex(OSError,'LOCAL_CREATION_FAILURE'):
                        with m.source_link_fault(target,root/'held'):raise AssertionError('MUST_NOT_ENTER')
                self.assertEqual(m.snapshot(target),before);self.assertFalse(target.is_symlink())

    def test_caller_exception_during_both_link_faults_restores_and_retains_no_source_link(self):
        for directory in (False,True):
            with self.subTest(directory=directory),TemporaryDirectory()as temp:
                root=Path(temp);target=self.fixture(root,directory);before=m.snapshot(target)
                with self.assertRaisesRegex(ValueError,'LOCAL_CALLER_REFUSAL'):
                    with m.source_link_fault(target,root/'held'):
                        self.assertTrue(target.is_symlink());raise ValueError('LOCAL_CALLER_REFUSAL')
                self.assertEqual(m.snapshot(target),before);self.assertFalse(target.is_symlink())

    def test_snapshot_refuses_a_descendant_link_instead_of_following_it(self):
        with TemporaryDirectory()as temp:
            root=Path(temp);target=self.fixture(root,True)
            (target/'link').symlink_to(target/'file')
            with self.assertRaisesRegex(AssertionError,'DESCENDANT_LINK'):m.snapshot(target)


if __name__=='__main__':main(verbosity=2)
