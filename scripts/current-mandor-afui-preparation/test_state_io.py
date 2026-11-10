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
                cache=state.save(value,reference)
                with patch.object(state.json,'load',side_effect=AssertionError('whole streamed cache load')):
                    self.assertEqual(state.reference(reference),cache)
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

    def test_cold_observer_uses_exact_catalogue_and_hashes_without_decoding_full_graph(self):
        codec=state.codec()
        with TemporaryDirectory()as td:
            root,out,value,reference=self.fixture(td)
            value['after']={f'group{i}':[['exact',i]]for i in range(22)}
            (out/state.ORIGINAL).write_text(json.dumps(value,sort_keys=True,default=str)+'\n')
            reference=dict(name=state.ORIGINAL,**state.pin(out/state.ORIGINAL))
            with patch.object(state,'codec',return_value=codec):
                cache=state.save(value,reference,directory=out)
                final=state.verified(SimpleNamespace(exact=self.exact),out,reference,cache)
            catalogue=state.observer_catalogue(value,reference,cache)
            self.assertEqual(catalogue,state.observer_catalogue(final,reference,cache))
            fixture=dict(observer_catalogue=catalogue)
            with patch.object(state,'codec',side_effect=AssertionError('cold full graph decoder')):
                expected=dict(contract=state.CONTRACT,after=final['after'])
                self.assertEqual(state.observer_state(fixture,out,reference['sha256'],cache['sha256']),expected)
                with self.assertRaisesRegex(ValueError,'EXACT_BOUND_STATE_ORIGINAL_REQUIRED:cache'):
                    state.observer_state(fixture,out,reference['sha256'],'0'*64)
                for key,file in (('original',reference),('cache',cache)):
                    path=out/file['name'];raw=path.read_bytes()
                    path.write_bytes(b'!'+raw[1:])
                    with self.assertRaisesRegex(ValueError,'EXACT_BOUND_STATE_ORIGINAL_REQUIRED:'+key):
                        state.observer_state(fixture,out,reference['sha256'],cache['sha256'])
                    path.write_bytes(raw)
                catalogue['after'].pop('group21')
                with self.assertRaisesRegex(ValueError,'COMPLETE_OBSERVER_CATALOGUE_REQUIRED'):
                    state.observer_state(fixture,out,reference['sha256'],cache['sha256'])


if __name__=='__main__':unittest.main()
