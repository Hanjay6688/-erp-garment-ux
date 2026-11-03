"""Materialize only the exact accepted Afui parent, with no fetch or rewrite."""
from pathlib import Path
import json,os,subprocess
import admission,qualification

ROOT=Path(__file__).resolve().parents[2]
FROZEN=ROOT.parent/'qualified-afui-parent'


def require(value,message):
    if not value:raise ValueError(message)


def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],
        env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_OPTIONAL_LOCKS='0'),stderr=subprocess.PIPE)


def materialize():
    _,receipt=qualification.actual_parent()  # Before even Git/worktree inspection.
    require(FROZEN==ROOT.parent/'qualified-afui-parent'and not FROZEN.is_symlink(),
        'MANDOR_PARENT_FIXED_REGULAR_WORKTREE_PATH')
    require(git(ROOT,'rev-parse',admission.PARENT_HEAD+'^{commit}').decode().strip()==admission.PARENT_HEAD,
        'MANDOR_PARENT_EXACT_COMMIT_MISSING_FROM_COMPLETE_CHECKOUT')
    require(git(ROOT,'rev-parse',admission.PARENT_HEAD+'^{tree}').decode().strip()==admission.PARENT_TREE,
        'MANDOR_PARENT_EXACT_TREE_MISMATCH')
    created=False
    if not FROZEN.exists():
        git(ROOT,'worktree','add','--detach',str(FROZEN),admission.PARENT_HEAD);created=True
    require(FROZEN.is_dir()and not FROZEN.is_symlink(),'MANDOR_PARENT_REGULAR_WORKTREE_REQUIRED')
    require(git(FROZEN,'rev-parse','HEAD').decode().strip()==admission.PARENT_HEAD
        and git(FROZEN,'rev-parse','HEAD^{tree}').decode().strip()==admission.PARENT_TREE,
        'MANDOR_PARENT_EXISTING_WORKTREE_IDENTITY_CHANGED')
    require(not git(FROZEN,'status','--porcelain').strip(),'MANDOR_PARENT_EXISTING_WORKTREE_CHANGED')
    return dict(status='EXACT_ACCEPTED_AFUI_PARENT_WORKTREE_READY',head=receipt['head'],tree=receipt['tree'],
        created=created,git_fetches=0,existing_files_rewritten=False,actual_Native_cases=0,
        production_go=False,independent_acceptance=False)


if __name__=='__main__':print(json.dumps(materialize(),sort_keys=True))
