"""Physical, immutable qualified SKU backend; the current App is a separate input."""
from pathlib import Path
from hashlib import sha256
import json,os,subprocess

HEAD='090b85d3fcb738d3e694d4329d306f199a686eb8'
TREE='e04831b441bed987cd72ff738cf2a06a7c0ef0ae'

def admitted():
    root=Path(os.environ['JOIN_QUALIFIED_SKU_ROOT'])
    if not root.is_absolute()or any(path.is_symlink()for path in(root,*root.parents)):
        raise ValueError('JOIN_PHYSICAL_QUALIFIED_SKU_ROOT_REQUIRED')
    root=root.resolve()
    def git(*args):return subprocess.check_output(['/usr/bin/git','-C',str(root),*args],env=dict(os.environ,GIT_OPTIONAL_LOCKS='0',GIT_NO_LAZY_FETCH='1')).decode().strip()
    if git('rev-parse','HEAD')!=HEAD or git('rev-parse','HEAD^{tree}')!=TREE:
        raise ValueError('JOIN_EXACT_QUALIFIED_SKU_CHECKOUT_REQUIRED')
    if git('diff','--name-only','--no-ext-diff','HEAD','--')or git('diff','--cached','--name-only','--no-ext-diff','--'):
        raise ValueError('JOIN_QUALIFIED_SKU_TRACKED_SOURCE_CHANGED')
    archive=json.loads((root/'scripts/current-workflow-history-isolation/ARCHIVE.json').read_bytes())
    history={row['path']:row for row in archive['files']}
    executable={'.py','.pyc','.mjs','.cjs','.js','.ts','.tsx','.sql','.yml','.yaml','.sh'}
    for name in git('ls-files','--others','--exclude-standard').splitlines():
        path=root/name
        if name in history:
            row=history[name];raw=path.read_bytes()
            if path.is_symlink()or len(raw)!=row['bytes']or sha256(raw).hexdigest()!=row['sha256']:
                raise ValueError('JOIN_QUALIFIED_SKU_HISTORY_PROOF_CHANGED')
        elif path.suffix in executable and not name.startswith('cp6-ui-build/'):
            raise ValueError('JOIN_QUALIFIED_SKU_UNDECLARED_EXECUTABLE:'+name)
    return dict(path=str(root),head=HEAD,tree=TREE,physical_tracked_sources_unchanged=True,
        historical_Originals_are_not_current_UI_qualification=True,ROOT_or_method_override=False)
