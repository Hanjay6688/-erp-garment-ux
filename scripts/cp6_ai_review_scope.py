#!/usr/bin/env python3
"""Route only independent additions; every original AI-R2 source stays exact."""
from pathlib import Path
import json,subprocess,textwrap
HEAD='25fa4736329e5148dfdb3572bc169952cba23251'
TREE='a5cb1e43d776a9ffc058f99c8d5c96ac7f6a9c0d'
PATCHES={'.github/workflows/cp6-ad-roll-opening-check.yml': [(' || python scripts/cp6_ai_gate_scope.py; then\n', ' || python scripts/cp6_ai_gate_scope.py || python scripts/cp6_ai_review_scope.py; then\n')]}
NEW=['.github/workflows/cp6-ai-independent-review.yml', 'scripts/cp6_ai_audit_router.py', 'scripts/cp6_ai_independent_review.py', 'scripts/cp6_ai_review_scope.py']
NEW += ['.github/workflows/cp6-final-boundary-audit.yml', 'scripts/cp6_final_crossflow_review.py',
        'docs/cp6-final-audit-checkpoint.md', 'docs/evidence/cp6-final-audit-reconciliation.json']

def verify():
 git=lambda *a:subprocess.check_output(['git',*a],text=True).strip()
 assert git('rev-parse',HEAD+'^{tree}')==TREE and git('merge-base',HEAD,'HEAD')==HEAD
 assert not git('rev-list','--merges',HEAD+'..HEAD')
 changed=set(git('diff','--name-only',HEAD,'HEAD').splitlines())
 assert changed==set(PATCHES)|set(NEW)|{'.github/workflows/cp6-full-schema-validation.yml'},sorted(changed)
 assert not git('diff','--name-only','HEAD'),'Uncommitted tracked source'
 for path,edits in PATCHES.items():
  s=Path(path).read_text()
  for old,new in reversed(edits):
   assert s.count(new)==1,(path,'route missing or repeated')
   s=s.replace(new,old,1)
  assert s==subprocess.check_output(['git','show',HEAD+':'+path],text=True),'ORIGINAL_AI_BODY_CHANGED:'+path
 full='.github/workflows/cp6-full-schema-validation.yml'
 original=subprocess.check_output(['git','show',HEAD+':'+full],text=True)
 start="          python - <<'PYROUTE'\n";end='          PYROUTE\n'
 a=original.index(start);b=original.index(end,a)+len(end)
 block=original[a:b]
 assert Path(full).read_text()==original[:a]+'          python scripts/cp6_ai_audit_router.py\n'+original[b:],'ORIGINAL_FULL_WORKFLOW_CHANGED'
 expected=textwrap.dedent(block[len(start):-len(end)])
 anchor='# BEGIN AI QUALIFIED ROUTE\n'
 prefix="""# BEGIN AI INDEPENDENT ROUTE
ai_independent=False
if Path('scripts/cp6_ai_review_scope.py').exists():
    ai_independent=subprocess.run(['python','scripts/cp6_ai_review_scope.py'],capture_output=True).returncode==0
# END AI INDEPENDENT ROUTE
"""
 assert expected.count(anchor)==1
 expected=expected.replace(anchor,prefix+anchor,1)
 line=next(x+'\n' for x in expected.splitlines() if x.strip().startswith('reuse=audit_only'))
 expected=expected.replace(line,line.rstrip()+' or ai_independent\n',1)
 assert Path('scripts/cp6_ai_audit_router.py').read_text()==expected,'ORIGINAL_ROUTER_CHANGED'
 return dict(status='ROUTED_TO_INDEPENDENT_AI',candidate_head=HEAD,candidate_tree=TREE,
  harness_head=git('rev-parse','HEAD'),historical_460_matrix_reexecuted=False,
  independent_result_required=True,production_go=False)
if __name__=='__main__':print(json.dumps(verify()))
