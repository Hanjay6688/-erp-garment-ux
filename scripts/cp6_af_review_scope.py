#!/usr/bin/env python3
"""Only route an AF review harness when all original AF source is unchanged."""
from pathlib import Path
import json,subprocess

HEAD='f46699865501b03f9fba3a8b188f3fd01eedf404'
TREE='f4dad6a6bccfffa1ba01f542cac36ac1d100c63f'
FULL='.github/workflows/cp6-full-schema-validation.yml'
NATIVE='.github/workflows/cp6-ad-roll-opening-check.yml'
ALLOWED={FULL,NATIVE,'.github/workflows/cp6-af-independent-review.yml',
    'scripts/cp6_af_review_scope.py','scripts/cp6_af_independent_review.py',
    'docs/cp6-af-independent-review.md'}

def strip_block(text,start,end):
    assert text.count(start)==text.count(end)==1
    a=text.index(start);b=text.index(end,a)+len(end)
    return text[:a]+text[b:]

def verify():
    git=lambda *args:subprocess.check_output(['git',*args],text=True).strip()
    assert git('rev-parse',HEAD+'^{tree}')==TREE and git('merge-base',HEAD,'HEAD')==HEAD
    assert not git('rev-list','--merges',HEAD+'..HEAD')
    changed=set(git('diff','--name-only',HEAD,'HEAD').splitlines())
    assert changed and changed<=ALLOWED,sorted(changed)
    for path in (FULL,NATIVE):
        source=Path(path).read_text()
        if path==FULL:
            source=strip_block(source,'          # BEGIN AF INDEPENDENT ROUTE\n','          # END AF INDEPENDENT ROUTE\n')
            old='              reuse=audit_only or ad_exact or ad_round or ae_exact or ae_independent or af_exact\n'
            new=old.rstrip('\n')+' or af_review\n'
            assert source.count(new)==1;source=source.replace(new,old,1)
        else:
            source=strip_block(source,'  # BEGIN AF INDEPENDENT ROUTE\n','  # END AF INDEPENDENT ROUTE\n')
            added="    needs: review-scope\n    if: needs.review-scope.outputs.reused != 'true'\n"
            assert source.count(added)==1;source=source.replace(added,'',1)
        original=subprocess.check_output(['git','show',HEAD+':'+path],text=True)
        assert source==original,'ORIGINAL_WORKFLOW_BODY_DRIFT:'+path
    return {'status':'REUSED_VERIFIED_AF_WRITER_SOURCE','candidate_head':HEAD,'candidate_tree':TREE,
      'harness_head':git('rev-parse','HEAD'),'harness_tree':git('rev-parse','HEAD^{tree}'),
      'changed_harness_paths':sorted(changed),'all_business_runtime_and_old_tests_unchanged':True,
      'native_writer_run':35051574342,'separate_independent_review_required':True,
      'large_matrix_reexecuted':False,'production_go':False}

if __name__=='__main__':print(json.dumps(verify()))
