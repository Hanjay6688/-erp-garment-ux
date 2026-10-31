"""A newly sealed file pin cannot waive the frozen financial/body contracts."""
from hashlib import sha256
from pathlib import Path
import importlib.util,json,shutil,tempfile,unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


binding=load('join_native14_source_guard_subject',HERE/'prepare.py')


class FrozenOracleControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _,proof=binding.prepare()
        if proof['separate_strict_groups']!=[11,3]or proof['complete_compiled_modules']!=6:
            raise AssertionError('THE_UNALTERED_BASELINE_MUST_PASS_FIRST')

    def changed_reference(self,name,before,after):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        directory=Path(temporary.name);shutil.copytree(HERE/'retained-s03-f42e',directory/'retained-s03-f42e')
        shutil.copyfile(HERE/'RETAINED.json',directory/'RETAINED.json')
        path=directory/'retained-s03-f42e'/name;text=path.read_text()
        self.assertEqual(text.count(before),1)
        raw=text.replace(before,after,1).encode();path.write_bytes(raw)
        manifest=json.loads((directory/'RETAINED.json').read_bytes())
        manifest['retained_sources'][name].update(bytes=len(raw),sha256=sha256(raw).hexdigest())
        (directory/'RETAINED.json').write_text(json.dumps(manifest))
        return directory

    def test_resealed_changed_financial_oracle_still_refuses(self):
        directory=self.changed_reference('cases.py',
            'assert money=={(wip,f.AMOUNT,D(0)),(payable,D(0),f.AMOUNT)},money',
            'assert money=={(wip,D(0),D(0)),(payable,D(0),D(0))},money')
        with self.assertRaisesRegex(ValueError,'S03_LAWFUL_ORIGINAL15FE_REQUIRED'):
            binding.prepare(directory)

    def test_resealed_native_capture_count_drift_still_refuses(self):
        directory=self.changed_reference('native_runner.py',
            "or len(state['originals']) != 13 or len(state['clones']) != 2",
            "or len(state['originals']) != 14 or len(state['clones']) != 2")
        with self.assertRaisesRegex(ValueError,'JOIN_NATIVE14_EXACT_BINDING_ANCHOR_REQUIRED'):
            binding.prepare(directory)

    def test_same_count_references_cannot_omit_verified_helper(self):
        with tempfile.TemporaryDirectory()as temporary:
            directory=Path(temporary);manifest=json.loads((HERE/'RETAINED.json').read_bytes())
            manifest['retained_sources']['unrelated.py']=manifest['retained_sources'].pop('business.py')
            (directory/'RETAINED.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'JOIN_NATIVE14_EXACT_NINE_REFERENCE_NAMES_REQUIRED'):
                binding.prepare(directory)

    def test_retained_directory_symlink_refuses_even_with_exact_bytes(self):
        with tempfile.TemporaryDirectory()as temporary:
            directory=Path(temporary);shutil.copyfile(HERE/'RETAINED.json',directory/'RETAINED.json')
            (directory/'retained-s03-f42e').symlink_to(HERE/'retained-s03-f42e',target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'JOIN_NATIVE14_SOURCE_SYMLINK_FORBIDDEN'):
                binding.prepare(directory)


if __name__=='__main__':
    fence=load('join_native14_source_guard_no_DB',ROOT/'scripts/current-sku-managed-recovery-native27-qualification/source_context.py')
    with fence.fenced_source_read()as guard:
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FrozenOracleControls))
    print(json.dumps(dict(source_DB_guard=guard,tests_run=result.testsRun,
        errors=len(result.errors),failures=len(result.failures),actual_Native_cases=0,actual_browser_cases=0)))
    raise SystemExit(0 if result.wasSuccessful()else 1)
