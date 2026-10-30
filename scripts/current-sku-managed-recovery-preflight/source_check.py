"""Bounded PREPARED product admission, not the future full Native27 runner."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def admitted(root=ROOT,manifest=None):
    root=Path(root).resolve();manifest=manifest or json.loads((HERE/'SOURCE.json').read_bytes())
    if manifest.get('status')!='PREPARED_LOCAL_ONLY_NATIVE_FINANCIAL_0':
        raise ValueError('SKU_RECOVERY_PREPARED_SOURCE_REQUIRED')
    base=manifest['base_head']
    tree=subprocess.check_output(['git','rev-parse',base+'^{tree}'],cwd=root,text=True).strip()
    if tree!=manifest['base_tree']:raise ValueError('SKU_RECOVERY_BASE_TREE_CHANGED')
    changed=subprocess.check_output(['git','diff','--name-status','--no-renames',base,'--'],cwd=root,text=True).splitlines()
    own_manifest=str(HERE.relative_to(ROOT)/'SOURCE.json')
    for change in changed:
        status,name=change.split('\t',1)
        if status=='M'and name in manifest['allowed_modified_base_files']:continue
        if status=='A'and name in(set(manifest['files'])|{own_manifest}):continue
        raise ValueError('SKU_RECOVERY_UNDECLARED_OLD_FILE_CHANGED:'+name)
    for name,pin in manifest['files'].items():
        path=root/name
        if path.is_symlink()or any(p.is_symlink()for p in path.parents if p!=root.parent):raise ValueError('SKU_RECOVERY_SOURCE_SYMLINK')
        raw=path.read_bytes()
        if len(raw)!=pin['bytes']or sha256(raw).hexdigest()!=pin['sha256']:raise ValueError('SKU_RECOVERY_SOURCE_CHANGED:'+name)
    for prefix in manifest['closed_owned_prefixes']:
        actual={str(p.relative_to(root))for p in(root/prefix).rglob('*')if p.is_file()and'__pycache__'not in p.parts and p.suffix!='.pyc'}
        expected={p for p in manifest['files']if p.startswith(prefix)}|({own_manifest}if own_manifest.startswith(prefix)else set())
        if actual!=expected:raise ValueError('SKU_RECOVERY_UNDECLARED_OWN_SOURCE')
    # This gate deliberately scopes its own source prefixes. The future outer
    # runner must still use the retained complete source/generated-artifact
    # validators; this helper is not an untracked-source waiver for that runner.
    return dict(status='PASS',files=len(manifest['files']),old_tree_exact_except_declared=True,
        prepared_product_only=True,actual_Native_financial=0,production_go=False,independent_acceptance=False)

if __name__=='__main__':print(json.dumps(admitted(),sort_keys=True))
