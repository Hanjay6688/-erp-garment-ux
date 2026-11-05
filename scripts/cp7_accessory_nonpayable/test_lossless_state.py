"""Byte equivalence, independent containers and bounded cold-state controls."""
from datetime import datetime,timezone
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import io,json,tempfile,unittest,copy
from . import complete_original_io,lossless_state as state


class LosslessStateControls(unittest.TestCase):
    def sample(self):
        shared=dict(sql='CREATE FUNCTION € ' * 40000,rows=[{'id':1,'amount':Decimal('0.014')}])
        return dict(before=shared,after=copy.deepcopy(shared),retained_parent=shared,integer=2**80,float=-0.0,flags=[True,False,None],
            date=datetime(2026,11,5,tzinfo=timezone.utc),text='"\\\n→é')

    def test_every_canonical_byte_and_non_json_default_str_value_survives(self):
        value=self.sample();document=state.encode(value);decoded=state.decode(document)
        expected=(json.dumps(value,sort_keys=True,default=str)+'\n').encode()
        self.assertEqual(state.canonical_pin(decoded),dict(bytes=len(expected),sha256=sha256(expected).hexdigest()))
        self.assertEqual(decoded,json.loads(expected))

    def test_all_containers_are_independent_but_immutable_text_is_shared(self):
        value=state.decode(state.encode(self.sample()))
        self.assertIsNot(value['before'],value['after'])
        self.assertIsNot(value['before']['rows'],value['after']['rows'])
        self.assertIs(value['before'],value['retained_parent'])
        self.assertIs(value['before']['sql'],value['after']['sql'])
        value['before']['rows'][0]['amount']='changed'
        self.assertEqual(value['after']['rows'][0]['amount'],'0.014')

    def test_cache_is_bound_to_both_exact_files_and_first_original_is_preserved(self):
        with tempfile.TemporaryDirectory()as td:
            original=Path(td)/'AFUI_BROWSER_SETTINGS_STATE.json';cache=Path(td)/'cache.json'
            reference=complete_original_io.save_sorted(original,self.sample(),'CONFLICT')
            receipt=state.save(cache,self.sample(),reference)
            actual=state.read(cache,receipt['sha256'],original,reference['sha256'])
            self.assertEqual(actual,json.loads(original.read_text()))
            original.write_text('{}\n')
            with self.assertRaisesRegex(ValueError,'COMPLETE_ORIGINAL_CHANGED'):
                state.read(cache,receipt['sha256'],original,reference['sha256'])

    def test_incomplete_source_pin_cannot_publish_cache(self):
        with tempfile.TemporaryDirectory()as td:
            cache=Path(td)/'cache.json'
            with self.assertRaisesRegex(ValueError,'EVERY_CANONICAL_ORIGINAL_BYTE'):
                state.save(cache,{'all_fields':[1,2]},dict(name='original.json',bytes=1,sha256='0'*64))
            self.assertFalse(cache.exists())

    def test_changed_cache_is_refused_before_decoding(self):
        with tempfile.TemporaryDirectory()as td:
            original=Path(td)/'original.json';cache=Path(td)/'cache.json'
            reference=complete_original_io.save_sorted(original,{'all':True},'CONFLICT')
            receipt=state.save(cache,{'all':True},reference);cache.write_text('{}\n')
            with self.assertRaisesRegex(ValueError,'CACHE_CHANGED'):
                state.read(cache,receipt['sha256'],original,reference['sha256'])

    def test_reference_unknown_tags_duplicate_keys_and_nonfinite_numbers_refuse(self):
        for document in (
            dict(format=state.FORMAT,strings=['k'],nodes=[],root=[1,-1]),
            dict(format=state.FORMAT,strings=['k'],nodes=[],root=[4,[]]),
            dict(format=state.FORMAT,strings=['k'],nodes=[[3,[[0,[0,1]],[0,[0,2]]]]],root=[2,0]),
            dict(format=state.FORMAT,strings=['k','k'],nodes=[],root=[0,None]),
            dict(format=state.FORMAT,strings=[],nodes=[],root=[0,float('nan')]),
            dict(format=state.FORMAT,strings=[],nodes=[[2,[[2,0]]]],root=[2,0]),
        ):
            with self.assertRaises(ValueError):state.decode(document)
        cycle=[];cycle.append(cycle)
        with self.assertRaisesRegex(ValueError,'CIRCULAR'):state.encode(cycle)

    def test_stream_reads_every_token_across_small_chunks_with_exact_number_types(self):
        raw=json.dumps(dict(keys=['a\\b','→',True,False,None],integer=2**100,float=-0.000000123,empty={},list=[]))
        for block in (1,2,3,7,64):
            reader=state.CompleteStream(io.StringIO(raw),block);actual=reader.value()
            self.assertEqual(actual,json.loads(raw));self.assertEqual(reader.peek(),'')
            self.assertTrue(reader.ended)

    def test_stream_does_not_alias_containers_and_deduplicates_long_strings(self):
        raw=json.dumps([{'body':'SELECT € '*10000}]*3)
        reader=state.CompleteStream(io.StringIO(raw),4096);actual=reader.value()
        self.assertIsNot(actual[0],actual[1]);self.assertIs(actual[0]['body'],actual[1]['body'])
        self.assertEqual(actual,json.loads(raw))
        reconstructed=state.CompleteStream(io.StringIO(raw),4096,deduplicate_equal_containers=True).value()
        self.assertEqual(reconstructed,actual)
        self.assertEqual(state.canonical_pin(reconstructed),state.canonical_pin(actual))

    def test_stream_refuses_duplicate_nonfinite_truncated_and_trailing_json(self):
        with tempfile.TemporaryDirectory()as td:
            target=Path(td)/'original.json'
            for raw in ('{"x":1,"x":2}','{"x":NaN}','[1,]','{"x":1e999}','{} false'):
                target.write_text(raw)
                with self.assertRaises((ValueError,json.JSONDecodeError)):state.read_complete_original(target)


if __name__=='__main__':unittest.main()
