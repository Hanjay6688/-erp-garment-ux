"""Actual immutable input plus admission mutations, not new runtime cases."""
from pathlib import Path
from hashlib import sha256
import gzip,importlib.util,json,unittest,copy
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('actual_vendor_backend_admission',HERE/'check.py');check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)
CFG=json.loads((HERE/'CONFIG.json').read_bytes());PIN=CFG['qualified_combined11']
RAW={k:gzip.decompress((ROOT/PIN[k]['path']).read_bytes())for k in ('original','package')}
RUNTIME={p:sha256((ROOT/p).read_bytes()).hexdigest()for p in check.RUNTIME}

class ActualBackendAdmission(unittest.TestCase):
    def test_exact_complete_actual_backend_is_admitted(self):
        result=check.admit(PIN,RAW['original'],RAW['package'],RUNTIME,CFG['parent_backend_sha256'])
        self.assertEqual(result['fresh_Native']+result['fresh_races']+result['fresh_Auth_HTTP'],11)
        self.assertEqual(result['head'],PIN['head'])
    def test_partial_or_different_evidence_stays_closed_even_with_matching_digest(self):
        edits=[('no CP6 restore','original',lambda x:x.update(cp6_restored=False)),
          ('missing race','original',lambda x:x['committed']['VENDOR_RECEIVABLE_NATIVE7_RACES3_AUTH1']['followup4']['races'].update(counts={'PASS':2})),
          ('Auth not restored','original',lambda x:x['committed']['VENDOR_RECEIVABLE_NATIVE7_RACES3_AUTH1']['followup4']['http']['auth_counts'].update(restored=False)),
          ('package runtime failed','package',lambda x:x['gate'].update(writer_runtime=False)),
          ('other SQL','original',lambda x:x['source_declaration']['current_installation']['files'].update({'scripts/cp7_vendor_receivable/receivable.sql':'0'*64})),
          ('other candidate','original',lambda x:x.update(qualification_commit='0'*40))]
        for label,kind,mutate in edits:
            with self.subTest(label=label):
                raw=dict(RAW);data=json.loads(raw[kind]);mutate(data);raw[kind]=json.dumps(data).encode();pin=copy.deepcopy(PIN)
                pin[kind].update(bytes=len(raw[kind]),sha256=sha256(raw[kind]).hexdigest())
                with self.assertRaises((AssertionError,ValueError)):
                    check.admit(pin,raw['original'],raw['package'],RUNTIME,CFG['parent_backend_sha256'])

if __name__=='__main__':unittest.main()
