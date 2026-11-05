"""Complete state pins and original graph identity; no ERP command."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import importlib.util,json,copy,unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('mandor_complete_state_control',HERE/'state_io.py')
state=importlib.util.module_from_spec(spec);spec.loader.exec_module(state)


class CurrentStateIO(unittest.TestCase):
    def fixture(self,directory):
        root=Path(directory);out=root/'cp6-proof/t3';out.mkdir(parents=True)
        before={'all_fields':{'SQL':'SELECT € '*3000},'rows':[1,2,3]}
        value=dict(contract='cp7.mandor-shop-on-accepted-afui.v1',before=before,after=copy.deepcopy(before),parent=before)
        original=out/state.ORIGINAL;original.write_text(json.dumps(value,sort_keys=True,default=str)+'\n')
        reference=dict(name=state.ORIGINAL,**state.pin(original))
        return root,out,value,reference

    def exact(self,left,right,message):
        if type(left)is not type(right)or left!=right:raise ValueError(message)

    def test_full_cache_and_every_original_byte_preserve_snapshot_and_parent_identity(self):
        codec=state.codec()
        with TemporaryDirectory()as td:
            root,out,value,reference=self.fixture(td)
            with patch.object(state,'ROOT',root),patch.object(state,'codec',return_value=codec):
                cache=state.save(value,reference);self.assertEqual(state.reference(reference),cache)
                actual=state.verified(SimpleNamespace(exact=self.exact),out,reference,cache)
                self.assertEqual(actual,value);self.assertIsNot(actual['before'],actual['after'])
                self.assertIs(actual['before'],actual['parent'])
                self.assertEqual(codec.canonical_pin(actual),{k:reference[k]for k in('bytes','sha256')})

    def test_changed_original_or_cache_cannot_reach_decoder(self):
        codec=state.codec()
        for changed in('original','cache'):
            with self.subTest(changed=changed),TemporaryDirectory()as td:
                root,out,value,reference=self.fixture(td)
                with patch.object(state,'ROOT',root),patch.object(state,'codec',return_value=codec):
                    cache=state.save(value,reference)
                    (out/(state.ORIGINAL if changed=='original'else state.CACHE)).write_text('{}\n')
                    with self.assertRaises(ValueError):state.read(out/state.ORIGINAL,reference['sha256'],cache['sha256'])

    def test_forged_cache_reference_and_wrong_name_refuse(self):
        codec=state.codec()
        with TemporaryDirectory()as td:
            root,out,value,reference=self.fixture(td)
            with patch.object(state,'ROOT',root),patch.object(state,'codec',return_value=codec):
                state.save(value,reference)
                with self.assertRaisesRegex(ValueError,'EXACT_ORIGINAL_REFERENCE'):
                    state.reference(dict(reference,sha256='0'*64))
                with self.assertRaisesRegex(ValueError,'FIXED_ORIGINAL_NAME'):
                    state.save(value,dict(reference,name='other.json'))

    def test_complete_file_pin_rejects_symlink(self):
        with TemporaryDirectory()as td:
            root,out,value,reference=self.fixture(td);link=out/'linked.json';link.symlink_to(out/state.ORIGINAL)
            with self.assertRaisesRegex(ValueError,'REGULAR_ORIGINAL'):state.pin(link)


if __name__=='__main__':unittest.main()
