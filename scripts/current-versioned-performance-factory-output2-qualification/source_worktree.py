"""Keep committed source exact and admit only generated non-code proof outputs."""
from pathlib import Path
import subprocess

ALLOWED_SUFFIXES={'.json','.jsonl','.sql','.txt','.log'}


def validate(repo,tracked_status,untracked):
    if tracked_status.strip():
        raise ValueError('FACTORY_COMMITTED_SOURCE_WORKTREE_CHANGED')
    root=Path(repo).resolve();proof_root=root/'cp6-proof/t3'
    for name in untracked:
        relative=Path(name);path=root/relative
        if (relative.is_absolute()or '..'in relative.parts
                or not name.startswith('cp6-proof/t3/')or relative.suffix not in ALLOWED_SUFFIXES
                or not path.is_file()or path.is_symlink()
                or not path.resolve().is_relative_to(proof_root)):
            raise ValueError('FACTORY_UNDECLARED_UNTRACKED_INPUT:'+name)
    return dict(tracked_sources_clean=True,generated_evidence_only=True,
        allowed_generated_evidence_paths=sorted(untracked),ignored_source_paths=[])


def admit(repo):
    tracked=subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],text=True)
    raw=subprocess.check_output(['git','-C',str(repo),'ls-files','--others','--exclude-standard','-z'])
    names=[name.decode()for name in raw.split(b'\0')if name]
    return validate(repo,tracked,names)
