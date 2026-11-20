"""Materialize the auditor's pinned, full product tree in a separate Git index."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
PRODUCT = 'ffda5cfceb7ebc196656baa650dffd18dd425047'
TREE = '760f38cc80ee9ca15e62a86ba358dfd8e858d895'
BASE = '7a17d348ea5831454c770586eff4270627003be0'
BASE_TREE = '85b9e0b0dd6cde60ff33a231c3605f23677a2321'
AUDIT = 'eafbbde103c3d0fd716ebf559ea3f24022b071df'
FILES = (('source-chain.json',''), ('source-deltas.json.gz.b64',''))

def check(ok, detail):
    if not ok:
        raise ValueError(detail)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def git(repo,*args,env=None,data=None):
    return subprocess.run(['git','-C',str(repo),*args],input=data,capture_output=True,check=True,env=env).stdout

def materialize(work):
    import base64, gzip
    base=work/'s06-product'
    audit=work/'close11-audit-input'
    check(git(audit,'rev-parse','HEAD').decode().strip()==AUDIT,'AUDITOR_SOURCE_COMMIT')
    def read(name):
        return git(audit,'show',AUDIT+':qualification/astra-public/installer/'+name)
    manifest=json.loads(read('source-chain.json'))
    patches=json.loads(gzip.decompress(base64.b64decode(read('source-deltas.json.gz.b64'),validate=True)))
    check((manifest['baseline'],manifest['baseline_tree'],manifest['candidate'],manifest['all_touched_paths'])==(BASE,BASE_TREE,PRODUCT,94),'AUDITOR_CHAIN_IDENTITY')
    check(git(base,'rev-parse','HEAD').decode().strip()==BASE and git(base,'rev-parse','HEAD^{tree}').decode().strip()==BASE_TREE,'BASE_CHECKOUT')
    dest=work/'close11-product'
    dest.mkdir()
    with tempfile.TemporaryDirectory() as td:
        env=dict(os.environ,GIT_INDEX_FILE=str(Path(td)/'index'))
        git(base,'read-tree',BASE_TREE,env=env)
        parent=BASE
        for row in manifest['steps']:
            patch=patches[row['patch']].encode()
            check(row['parent']==parent and sha(patch)==row['sha256'] and len(patch)==row['bytes'],'SOURCE_PATCH_'+row['commit'])
            git(base,'apply','--cached','--whitespace=nowarn','-',data=patch,env=env)
            check(git(base,'write-tree',env=env).decode().strip()==row['tree'],'FULL_TREE_'+row['commit'])
            parent=row['commit']
        check(len(manifest['steps'])==8 and parent==PRODUCT and row['tree']==TREE,'CANDIDATE_TREE')
        # This exports tracked candidate files, including frontend and manifests, without
        # inventing a commit header or changing the certified predecessor checkout.
        for folder in ('src','public','contracts','scripts','supabase'):
            names=git(base,'ls-tree','-r','--name-only','-z',TREE,'--',folder)
            git(base,'checkout-index','--ignore-skip-worktree-bits','--stdin','-z','--prefix='+str(dest)+'/',env=env,data=names)
        roots=git(base,'ls-tree','--name-only','-z',TREE).split(b'\0')
        top=[n for n in roots if n and git(base,'cat-file','-t',TREE+':'+n.decode()).strip()==b'blob']
        git(base,'checkout-index','--stdin','-z','--prefix='+str(dest)+'/',env=env,data=b'\0'.join(top)+b'\0')
    out=work/'close11-evidence';out.mkdir(exist_ok=True)
    (out/'product.json').write_text(json.dumps(dict(product=PRODUCT,tree=TREE,baseline=BASE,baseline_tree=BASE_TREE,audit_source=AUDIT,steps=[r['tree'] for r in manifest['steps']],changed_paths=94,production_go=False),indent=2)+'\n')

if __name__=='__main__':
    materialize(Path(os.environ['GITHUB_WORKSPACE']))
