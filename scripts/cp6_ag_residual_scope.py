#!/usr/bin/env python3
"""Allow only additional proof files while original AG business source is exact."""
from pathlib import Path
import json, subprocess
HEAD='119f8f133131eaf373f08cc45b7b3d6fc27a3d3e'
TREE='bd7dd026d40e64f08f03e122338d8a82ebfd292c'
FULL='.github/workflows/cp6-full-schema-validation.yml'
NATIVE='.github/workflows/cp6-ad-roll-opening-check.yml'
ALLOWED={FULL,NATIVE,'.github/workflows/cp6-ag-residual-review.yml',
         'scripts/cp6_ag_residual_review.py','scripts/cp6_ag_residual_scope.py',
         'docs/cp6-ag-residual-review.md'}
OLD='              reuse=audit_only or ad_exact or ad_round or ae_exact or ae_independent or af_exact or af_review or ag_review\n'
NATIVE_OLD='          if python scripts/cp6_af_review_scope.py || python scripts/cp6_ag_gate_scope.py; then\n'
NATIVE_NEW='          if python scripts/cp6_af_review_scope.py || python scripts/cp6_ag_gate_scope.py || python scripts/cp6_ag_residual_scope.py; then\n'

def verify():
    git=lambda *a:subprocess.check_output(['git',*a],text=True).strip()
    assert git('rev-parse',HEAD+'^{tree}')==TREE and git('merge-base',HEAD,'HEAD')==HEAD
    assert not git('rev-list','--merges',HEAD+'..HEAD')
    changed=set(git('diff','--name-only',HEAD,'HEAD').splitlines())
    assert changed==ALLOWED, sorted(changed)
    s=Path(FULL).read_text()
    start='          # BEGIN AG RESIDUAL ROUTE\n';end='          # END AG RESIDUAL ROUTE\n'
    assert s.count(start)==s.count(end)==1
    a=s.index(start);b=s.index(end,a)+len(end);s=s[:a]+s[b:]
    new=OLD.rstrip('\n')+' or ag_residual\n';assert s.count(new)==1;s=s.replace(new,OLD,1)
    assert s==subprocess.check_output(['git','show',HEAD+':'+FULL],text=True),'ORIGINAL_AG_FULL_BODY_CHANGED'
    s=Path(NATIVE).read_text();assert s.count(NATIVE_NEW)==1;s=s.replace(NATIVE_NEW,NATIVE_OLD,1)
    assert s==subprocess.check_output(['git','show',HEAD+':'+NATIVE],text=True),'ORIGINAL_AG_NATIVE_BODY_CHANGED'
    return dict(status='REUSED_EXACT_AG_SOURCE_ADDITIONAL_WRITER_CHECK_REQUIRED',candidate_head=HEAD,candidate_tree=TREE,
                harness_head=git('rev-parse','HEAD'),harness_tree=git('rev-parse','HEAD^{tree}'),
                native_writer_run=35060285362,large_matrix_reexecuted=False,independent_ag='PENDING',production_go=False)

if __name__=='__main__':print(json.dumps(verify()))
