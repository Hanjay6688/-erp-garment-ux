"""Actual local Git provenance controls; no ERP imports, database or workflow."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import importlib.util,json,subprocess,sys,unittest
import package_identity


class PackageIdentityControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=TemporaryDirectory(prefix='mandor-package-identity-')
        cls.own=Path(cls.tmp.name)/'candidate';cls.parent=Path(cls.tmp.name)/'qualified-afui-parent'
        raw=(package_identity.ROOT/package_identity.PATH).read_bytes()
        cls.heads={}
        for root in(cls.own,cls.parent):
            (root/'scripts').mkdir(parents=True);(root/'src').mkdir()
            (root/package_identity.PATH).write_bytes(raw)
            (root/'src/fixture.txt').write_text(root.name+'\n')
            for args in [('init','--quiet'),('add','scripts','src'),
                ('-c','user.name=ERP prerequisite control','-c','user.email=prerequisite@example.invalid','commit','--quiet','-m','Isolated provenance fixture')]:
                subprocess.run(['git','-C',str(root),*args],check=True,capture_output=True)
            cls.heads[root]=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
        assert cls.heads[cls.own]!=cls.heads[cls.parent]

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def setUp(self):
        self.roots=patch.multiple(package_identity,ROOT=self.own,FROZEN=self.parent);self.roots.start()
        self.previous=sys.modules.get('cp6_run_identity');sys.modules.pop('cp6_run_identity',None)

    def tearDown(self):
        self.roots.stop();sys.modules.pop('cp6_run_identity',None)
        if self.previous is not None:sys.modules['cp6_run_identity']=self.previous

    def inherited(self):
        spec=importlib.util.spec_from_file_location('cp6_run_identity',self.parent/package_identity.PATH)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        sys.modules['cp6_run_identity']=module;return module

    def test_reproduces_frozen_identity_then_selects_actual_owning_checkout(self):
        inherited=self.inherited()
        self.assertEqual(inherited.identity('T3_PREP')['tool_head'],self.heads[self.parent])
        self.assertNotEqual(inherited.identity('T3_PREP')['tool_head'],self.heads[self.own])
        with patch.dict('os.environ',GITHUB_SHA=self.heads[self.own],GITHUB_RUN_ID='123',GITHUB_RUN_ATTEMPT='1'):
            with package_identity.scope():
                import cp6_run_identity
                actual=cp6_run_identity.identity('T3_PREP',mode='install')
                self.assertEqual(actual['tool_head'],self.heads[self.own]);self.assertEqual(actual['github_sha'],self.heads[self.own])
                self.assertEqual(actual['run_id'],'123');self.assertEqual(actual['run_attempt'],'1')
                self.assertEqual(actual['product_ref'],self.heads[self.own]);self.assertEqual(actual['mode'],'install')
        self.assertIs(sys.modules['cp6_run_identity'],inherited)

    def test_fresh_process_import_is_restored_to_absence(self):
        with package_identity.scope():self.assertIn('cp6_run_identity',sys.modules)
        self.assertNotIn('cp6_run_identity',sys.modules)

    def test_package_error_restores_prior_module_without_replacing_error(self):
        inherited=self.inherited();original=RuntimeError('ORIGINAL_PACKAGE_FAILURE')
        with self.assertRaises(RuntimeError)as caught:
            with package_identity.scope():raise original
        self.assertIs(caught.exception,original);self.assertIs(sys.modules['cp6_run_identity'],inherited)

    def test_changed_inherited_identity_source_refused_before_replacement(self):
        inherited=self.inherited();path=self.parent/package_identity.PATH;raw=path.read_bytes()
        try:
            path.write_bytes(raw+b'\n# unexpected change\n')
            with self.assertRaisesRegex(ValueError,'MANDOR_IDENTITY_UNCHANGED_RECORDER_REQUIRED'):
                with package_identity.scope():self.fail('must not enter package')
            self.assertIs(sys.modules['cp6_run_identity'],inherited)
        finally:path.write_bytes(raw)


if __name__=='__main__':unittest.main()
