"""Actual temporary file-copy controls; parent acceptance is explicitly modeled."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json,unittest
import parent_artifacts as artifacts


class ParentArtifacts(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory(prefix='mandor-parent-artifacts-');self.base=Path(self.tmp.name)
        self.own=self.base/'candidate/cp6-proof/t3';self.parent=self.base/'qualified-afui-parent/cp6-proof/t3'
        self.own.mkdir(parents=True);self.parent.mkdir(parents=True)
        self.receipt=self.own/'MANDOR_PARENT_PREREQUISITE_FILES.json';self.retained=self.own/'MANDOR_FROZEN_PARENT_EXECUTION'
        self.paths=patch.multiple(artifacts,OWN=self.own,PARENT=self.parent,MANIFEST=self.receipt,RETAINED=self.retained);self.paths.start()
        self.accepted=patch.object(artifacts.qualification,'actual_parent',return_value=(b'MODELED_ONLY',{'head':'a'*40,'tree':'b'*40}));self.accepted.start()
        self.git=patch.object(artifacts.materialize_parent,'materialize',return_value={'modeled':True});self.git.start()

    def tearDown(self):self.git.stop();self.accepted.stop();self.paths.stop();self.tmp.cleanup()

    def prepare(self):
        (self.own/'proof.json').write_bytes(b'{"integer":9007199254740993,"decimal":"0.000001"}\n')
        (self.own/'nested').mkdir();(self.own/'nested/original.bin').write_bytes(bytes(range(256))*4)
        return artifacts.prepare()

    def test_preparation_preserves_exact_bytes_and_conflicting_parent_is_not_rewritten(self):
        result=self.prepare();self.assertEqual(result['source_files'],2)
        self.assertEqual((self.own/'proof.json').read_bytes(),(self.parent/'proof.json').read_bytes())
        self.assertEqual((self.own/'nested/original.bin').read_bytes(),(self.parent/'nested/original.bin').read_bytes())
        self.assertEqual(json.loads(self.receipt.read_bytes())['original_sources'],artifacts.inventory(self.parent))
        with self.assertRaisesRegex(ValueError,'MANDOR_PARENT_ARTIFACT_SINGLE_PREPARATION'):artifacts.prepare()

    def test_changed_and_new_outputs_retained_in_full_while_unchanged_inputs_are_not_duplicated(self):
        self.prepare();changed=b'{"complete_changed_original":[9007199254740993,"-123.456789"]}\n'
        (self.parent/'proof.json').write_bytes(changed);(self.parent/'failed_case.json').write_bytes(b'{"error":"first failure"}\n')
        value=artifacts.retain();self.assertEqual(value['retained_files'],2)
        self.assertEqual((self.retained/'proof.json').read_bytes(),changed)
        self.assertEqual((self.retained/'failed_case.json').read_bytes(),(self.parent/'failed_case.json').read_bytes())
        self.assertFalse((self.retained/'nested/original.bin').exists())
        self.assertNotEqual((self.own/'proof.json').read_bytes(),changed)
        self.assertEqual(artifacts.retain(),value)

    def test_conflicting_destination_refused_without_overwrite(self):
        (self.own/'proof.json').write_bytes(b'original');(self.parent/'proof.json').write_bytes(b'keep parent bytes')
        with self.assertRaisesRegex(ValueError,'MANDOR_PARENT_ARTIFACT_EXISTING_BYTES_CONFLICT'):artifacts.prepare()
        self.assertEqual((self.parent/'proof.json').read_bytes(),b'keep parent bytes');self.assertFalse(self.receipt.exists())

    def test_symlink_input_and_destination_ancestor_refused(self):
        (self.own/'link').symlink_to(self.parent)
        with self.assertRaisesRegex(ValueError,'MANDOR_PARENT_ARTIFACT_PATH_OR_SYMLINK'):artifacts.prepare()
        (self.own/'link').unlink();(self.base/'outside').mkdir();(self.base/'link').symlink_to(self.base/'outside',target_is_directory=True)
        src=self.own/'proof.json';src.write_bytes(b'full bytes')
        with self.assertRaisesRegex(ValueError,'MANDOR_PARENT_ARTIFACT_PATH_OR_SYMLINK'):
            artifacts.copy_exact(src,self.base/'link/new_root/proof.json',self.own,self.base/'link/new_root',artifacts.pin(src))
        self.assertFalse((self.base/'outside/new_root').exists())

    def test_missing_baseline_is_reported_and_never_recreated(self):
        self.prepare();(self.parent/'proof.json').unlink()
        result=artifacts.retain();self.assertEqual(result['missing_baseline_files'],1)
        self.assertFalse((self.parent/'proof.json').exists())

    def test_no_preparation_has_no_retention_or_qualification_claim(self):
        self.assertEqual(artifacts.retain(),{'status':'PARENT_EXECUTION_NOT_PREPARED','actual_Native_cases':0})
        self.assertFalse(self.retained.exists())


if __name__=='__main__':unittest.main()
