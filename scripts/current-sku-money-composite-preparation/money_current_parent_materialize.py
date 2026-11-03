"""Materialize the exact accepted Mandor/SKU trees and their actual Afui parent."""
from pathlib import Path
import json,os,subprocess,sys
from money_execution_bindings import admission
import money_current_parent_runtime as runtime

ROOT=Path(__file__).resolve().parents[2]


def require(value,message):
    if not value:raise ValueError(message)


def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.PIPE,
        env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_OPTIONAL_LOCKS='0'))


def one(folder,head,tree):
    path=ROOT.parent/folder
    require(folder in('qualified-mandor-parent','qualified-sku-money')and not path.is_symlink(),
        'SKU_COMPOSITE_FIXED_REGULAR_WORKTREE_PATH')
    require(git(ROOT,'rev-parse',head+'^{commit}').decode().strip()==head
        and git(ROOT,'rev-parse',head+'^{tree}').decode().strip()==tree,
        'SKU_COMPOSITE_EXACT_ACCEPTED_COMMIT_AND_TREE_REQUIRED')
    created=False
    if not path.exists():git(ROOT,'worktree','add','--detach',str(path),head);created=True
    runtime.frozen(path,head,tree)
    require(not git(path,'status','--porcelain').strip(),'SKU_COMPOSITE_EXISTING_WORKTREE_CHANGED')
    return dict(folder=folder,head=head,tree=tree,created=created,git_fetches=0,existing_files_rewritten=False)


def materialize():
    runtime.actual_inputs()  # No Git, filesystem inspection or ERP import before all ten gates.
    results=[one('qualified-mandor-parent',admission.PARENT_HEAD,admission.PARENT_TREE),
             one('qualified-sku-money',admission.SKU_HEAD,admission.SKU_TREE)]
    parent=ROOT.parent/'qualified-mandor-parent'
    raw=subprocess.check_output([sys.executable,'-B',str(parent/'scripts/current-mandor-shop-native-qualification/materialize_parent.py')],
        cwd=parent,env=dict(os.environ,GIT_NO_LAZY_FETCH='1',PYTHONDONTWRITEBYTECODE='1'))
    return dict(status='EXACT_ACCEPTED_MANDOR_SKU_AND_AFUI_WORKTREES_READY',sources=results,
        actual_Afui_parent=json.loads(raw),actual_composite_cases=0,production_go=False)


if __name__=='__main__':print(json.dumps(materialize(),sort_keys=True))
