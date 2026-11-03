"""Closed UI reader derivation on the exact completed theme; no database gate."""
from pathlib import Path
from hashlib import sha256
import json,os,subprocess
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
ENV=dict(os.environ,GIT_NO_LAZY_FETCH='1')
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args],env=ENV)
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def main():
    m=json.loads((HERE/'SOURCE.json').read_bytes())
    assert m['contract']=='cp7.A.themed-SKU-reader-preparation.v1'
    assert m['unified_runtime_admission']is False and m['production_go']is False
    assert git('rev-parse',m['theme_base_commit']+'^{tree}').decode().strip()==m['theme_base_tree']
    readers=set(m['reader_files'])
    assert readers=={'src/ConnectedFgStockPage.tsx','src/fgContract.ts','src/ConnectedFgStockPage.dom.test.tsx','src/fgMovingAverageContract.test.ts','tests/fixtures/skuMovingAverageReaderPg17.json'}
    expected=readers|set(m['preparation_files'])|{str((HERE/'SOURCE.json').relative_to(ROOT))}
    changed=set(git('diff','--name-only',m['theme_base_commit']).decode().splitlines())
    changed.update(git('ls-files','--others','--exclude-standard').decode().splitlines())
    assert changed==expected,sorted(changed^expected)
    for group in ['reader_files','preparation_files']:
        for name,value in m[group].items():assert pin((ROOT/name).read_bytes())==value,name
    original=json.loads((ROOT/'docs/cp7/d17-14/ui-a-integration-20261103/SOURCE.json').read_bytes())
    for name,value in original['presentation_derivations'].items():assert pin((ROOT/name).read_bytes())==value['after'],name
    preserved=0
    for entry in git('ls-tree','-r',m['theme_base_commit'],'--','src').decode().splitlines():
        meta,name=entry.split('\t',1)
        if name in readers:continue
        assert git('hash-object',str(ROOT/name)).decode().strip()==meta.split()[2],name
        preserved+=1
    print(json.dumps(dict(status='EXACT_SKU_READER_ON_COMPLETED_B_THEME_PREPARED',reader_paths=len(readers),
        all_75_theme_paths_unchanged=len(original['presentation_derivations'])==75,
        other_src_files_identical=preserved,actual_ERP_cases=0,unified_runtime_admission=False,production_go=False)))
if __name__=='__main__':main()
