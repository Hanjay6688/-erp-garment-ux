"""Verify Writer A's eight changes against a clean checkout of the certified source."""
import base64,gzip,hashlib,json,sys,subprocess,tempfile
from pathlib import Path

here=Path(__file__).resolve().parent
manifest=json.loads((here/'source-chain.json').read_text())
patches=json.loads(gzip.decompress(base64.b64decode((here/'source-deltas.json.gz.b64').read_bytes(),validate=True)))
assert len(manifest['steps'])==len(patches)==8

def check_inputs():
    prior=manifest['baseline']
    for row in manifest['steps']:
        data=patches[row['patch']].encode();assert row['parent']==prior and len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'];prior=row['commit']
    assert prior==manifest['candidate'];return prior

def git(repo,*args,inp=None):return subprocess.run(['git','-C',str(repo),*args],input=inp,capture_output=True,check=True).stdout.decode().strip()

def verify_existing_checkout(repo):
    with tempfile.TemporaryDirectory(prefix='astra-qualification-index-')as td:
        subprocess.run(['git','clone','--quiet','--local','--shared','--no-checkout',str(repo),td],check=True)
        assert git(td,'rev-parse',manifest['baseline']+'^{tree}')==manifest['baseline_tree']
        git(td,'read-tree',manifest['baseline_tree'])
        for row in manifest['steps']:
            git(td,'apply','--cached','--whitespace=nowarn','-',inp=patches[row['patch']].encode());assert git(td,'write-tree')==row['tree']
        return git(td,'write-tree')

if __name__=='__main__':
    expected=check_inputs()
    if len(sys.argv)==2:print('ASTRA_CANDIDATE_TREE '+verify_existing_checkout(Path(sys.argv[1]).resolve()))
    else:print('ASTRA_CANDIDATE_SOURCE_INPUTS '+json.dumps(dict(commit=expected,patches=len(patches),changed_paths=manifest['all_touched_paths'])))
