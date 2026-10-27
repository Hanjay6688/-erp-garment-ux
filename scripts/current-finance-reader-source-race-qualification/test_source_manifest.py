"""Nested Native source pins remain exact even outside the flattened map."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,tempfile,unittest
spec=importlib.util.spec_from_file_location('race_evidence',Path(__file__).with_name('evidence.py'))
evidence=importlib.util.module_from_spec(spec);spec.loader.exec_module(evidence)

class SourceManifestTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.path='supabase/dev/cp6_ba_t1_family.sql'
        p=self.root/self.path;p.parent.mkdir(parents=True);p.write_bytes(b'exact Native source')
        self.manifest={'sources':{self.path:sha256(p.read_bytes()).hexdigest()}}
        marker='scripts/current-finance-check-reuse-diagnostic/INSTALLED_REPORT_SOURCE.json'
        self.marker=self.root/marker;self.marker.parent.mkdir(parents=True)
        self.marker.write_text(json.dumps(self.manifest))
        self.source={'files':{marker:sha256(self.marker.read_bytes()).hexdigest()}}
    def check(self):evidence.verify_installed_sources(self.root,self.source,self.manifest)
    def test_nested_native_pin_without_flat_entry_is_checked(self):self.check()
    def test_native_byte_drift_refused(self):
        (self.root/self.path).write_bytes(b'changed Native source')
        with self.assertRaises(AssertionError):self.check()
    def test_conflicting_flat_pin_refused(self):
        self.source['files'][self.path]='0'*64
        with self.assertRaises(AssertionError):self.check()
    def test_manifest_byte_drift_refused(self):
        self.marker.write_text(self.marker.read_text()+' ')
        with self.assertRaises(AssertionError):self.check()
    def test_missing_native_file_refused(self):
        (self.root/self.path).unlink()
        with self.assertRaises(FileNotFoundError):self.check()

if __name__=='__main__':unittest.main()
