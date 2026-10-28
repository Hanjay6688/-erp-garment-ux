"""One full authenticated checkout; exact detached worktrees for frozen inputs.

Uses only stdlib and git, before installing the disposable runtime. Every
commit must already exist in the full checkout. No replacement/fallback ref,
network fetch or source modification is allowed.
"""
from pathlib import Path
import json,os,re,subprocess

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]


def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()


def plan(repo,heads):
    repo=Path(repo).resolve();workspace=repo.parent
    result=[]
    assert git(repo,'rev-parse','--is-shallow-repository')=='false','FULL_SOURCE_HISTORY_REQUIRED'
    for name,head in heads.items():
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*',name)or name==repo.name:
            raise ValueError('FROZEN_SOURCE_DIRECTORY_INVALID')
        if not isinstance(head,str)or not re.fullmatch('[0-9a-f]{40}',head):
            raise ValueError('EXACT_FROZEN_SOURCE_HEAD_REQUIRED')
        assert git(repo,'cat-file','-t',head)=='commit','FROZEN_SOURCE_COMMIT_REQUIRED'
        destination=workspace/name
        if destination.exists():raise ValueError('FROZEN_SOURCE_DESTINATION_ALREADY_EXISTS')
        result.append(dict(path=name,head=head,tree=git(repo,'rev-parse',head+'^{tree}')))
    assert result,'FROZEN_SOURCE_HEADS_REQUIRED'
    return result


def materialize(repo,heads):
    repo=Path(repo).resolve();entries=plan(repo,heads)  # Preflight every input first.
    original=git(repo,'rev-parse','HEAD');original_tree=git(repo,'rev-parse','HEAD^{tree}')
    for entry in entries:
        destination=repo.parent/entry['path']
        subprocess.run(['git','-C',str(repo),'worktree','add','--detach',str(destination),entry['head']],check=True)
        assert git(destination,'rev-parse','HEAD')==entry['head']
        assert git(destination,'rev-parse','HEAD^{tree}')==entry['tree']
        assert Path(git(destination,'rev-parse','--show-toplevel')).resolve()==destination
        assert not git(destination,'status','--porcelain')
        detached=subprocess.run(['git','-C',str(destination),'symbolic-ref','-q','HEAD'],capture_output=True,check=False)
        assert detached.returncode==1,'FROZEN_SOURCE_MUST_BE_DETACHED'
    assert git(repo,'rev-parse','HEAD')==original and git(repo,'rev-parse','HEAD^{tree}')==original_tree
    return dict(status='EXACT_FROZEN_SOURCE_WORKTREES',single_full_history=True,
        network_fetches=0,source_refs_substituted=False,auditor_head_unchanged=True,
        inputs=entries,source_worktree_count=len(entries))


def qualified_heads():
    heads=json.loads((HERE/'FROZEN_SOURCE_ROOTS.json').read_bytes())
    selected=json.loads((ROOT/'scripts/current-versioned-performance-native-qualification/SOURCE.json').read_bytes())
    dynamic={'${{ steps.qualified_heads.outputs.native }}':selected['frozen_declaration']['head'],
        '${{ steps.qualified_heads.outputs.B }}':selected['B_frozen_head']}
    assert os.environ['QUALIFIED_NATIVE_HEAD']==dynamic['${{ steps.qualified_heads.outputs.native }}']
    assert os.environ['QUALIFIED_B_HEAD']==dynamic['${{ steps.qualified_heads.outputs.B }}']
    return {name:dynamic.get(head,head)for name,head in heads.items()}


if __name__=='__main__':
    proof=materialize(ROOT,qualified_heads())
    output=ROOT/'cp6-proof/t3/FROZEN_SOURCE_WORKTREES.json';output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps(proof),flush=True)
