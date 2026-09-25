"""Run identity printed first by every CP6 runner (independent audit B6).

One line per run, before any case:
  {"run_identity": {"label": ..., "tool_head": ..., "product_ref": ..., "run_id": ..., "run_attempt": ..., ...}}

tool_head is the commit of the checkout the runner's scripts come from (the tools). product_ref is the last commit of that
checkout that changed the product itself (migrations, T1 family files, release package and rollbacks, frontend), so a
run of new tools on an unchanged product says so. The label is the runner's own (T1_FAMILY, T2_REGRESSION, T3_PREP,
AUDITOR_SCENARIO); a result keeps the label of the run that produced it and is never relabelled afterwards.
"""
from pathlib import Path
import json,os,subprocess

ROOT=Path(__file__).resolve().parents[1]
PRODUCT_PATHS=('supabase/migrations','supabase/dev','supabase/release','supabase/rollbacks','src')


def _git(*args):
    try:return subprocess.check_output(['git','-C',str(ROOT),*args],text=True,stderr=subprocess.DEVNULL).strip() or None
    except (OSError,subprocess.CalledProcessError):return None


def identity(label,**extra):
    return dict(label=label,tool_head=_git('rev-parse','HEAD'),product_ref=_git('log','-1','--format=%H','--',*PRODUCT_PATHS),
                product_paths=list(PRODUCT_PATHS),run_id=os.environ.get('GITHUB_RUN_ID'),run_attempt=os.environ.get('GITHUB_RUN_ATTEMPT'),
                workflow=os.environ.get('GITHUB_WORKFLOW'),job=os.environ.get('GITHUB_JOB'),event=os.environ.get('GITHUB_EVENT_NAME'),
                github_sha=os.environ.get('GITHUB_SHA'),release_evidence=False,production_go=False,**extra)


def announce(label,**extra):
    """Print the identity line and return it (runners also keep it in their report)."""
    value=identity(label,**extra)
    print(json.dumps(dict(run_identity=value),default=str),flush=True)
    return value
