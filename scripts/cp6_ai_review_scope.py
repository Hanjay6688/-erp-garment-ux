#!/usr/bin/env python3
"""Route only independent additions; every original AI-R2 source stays exact."""
from pathlib import Path
import json,subprocess
HEAD='25fa4736329e5148dfdb3572bc169952cba23251'
TREE='a5cb1e43d776a9ffc058f99c8d5c96ac7f6a9c0d'
PATCHES={'.github/workflows/cp6-full-schema-validation.yml': [('          # BEGIN AI QUALIFIED ROUTE\n', "          # BEGIN AI INDEPENDENT ROUTE\n          ai_independent=False\n          if Path('scripts/cp6_ai_review_scope.py').exists():\n              ai_independent=subprocess.run(['python','scripts/cp6_ai_review_scope.py'],capture_output=True).returncode==0\n          # END AI INDEPENDENT ROUTE\n          # BEGIN AI QUALIFIED ROUTE\n"), ('              reuse=audit_only or ad_exact or ad_round or ae_exact or ae_independent or af_exact or af_review or ag_review or ag_residual or ah_review or ah_independent or ai_review\n', '              reuse=audit_only or ad_exact or ad_round or ae_exact or ae_independent or af_exact or af_review or ag_review or ag_residual or ah_review or ah_independent or ai_review or ai_independent\n')], '.github/workflows/cp6-ad-roll-opening-check.yml': [(' || python scripts/cp6_ai_gate_scope.py; then\n', ' || python scripts/cp6_ai_gate_scope.py || python scripts/cp6_ai_review_scope.py; then\n')]}
NEW=['.github/workflows/cp6-ai-independent-review.yml', 'scripts/cp6_ai_independent_review.py', 'scripts/cp6_ai_review_scope.py']

def verify():
 git=lambda *a:subprocess.check_output(['git',*a],text=True).strip()
 assert git('rev-parse',HEAD+'^{tree}')==TREE and git('merge-base',HEAD,'HEAD')==HEAD
 assert not git('rev-list','--merges',HEAD+'..HEAD')
 changed=set(git('diff','--name-only',HEAD,'HEAD').splitlines())
 assert changed==set(PATCHES)|set(NEW),sorted(changed)
 assert not git('diff','--name-only','HEAD'),'Uncommitted tracked source'
 for path,edits in PATCHES.items():
  s=Path(path).read_text()
  for old,new in reversed(edits):
   assert s.count(new)==1,(path,'route missing or repeated')
   s=s.replace(new,old,1)
  assert s==subprocess.check_output(['git','show',HEAD+':'+path],text=True),'ORIGINAL_AI_BODY_CHANGED:'+path
 return dict(status='ROUTED_TO_INDEPENDENT_AI',candidate_head=HEAD,candidate_tree=TREE,
  harness_head=git('rev-parse','HEAD'),historical_460_matrix_reexecuted=False,
  independent_result_required=True,production_go=False)
if __name__=='__main__':print(json.dumps(verify()))
