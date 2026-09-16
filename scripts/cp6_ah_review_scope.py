#!/usr/bin/env python3
"""Only audit additions qualify for reusing exact AH writer evidence."""
from pathlib import Path
import json,subprocess
HEAD='965ceac45ef15ddc19c178d87a3606adffcf53a6'
TREE='183a0c2af8ba201e3754e9db77fe47501c196f4d'
PATCHES={'.github/workflows/cp6-full-schema-validation.yml': [['          # BEGIN AH QUALIFIED ROUTE\n', "          # BEGIN AH INDEPENDENT ROUTE\n          ah_independent=False\n          if Path('scripts/cp6_ah_review_scope.py').exists():\n              ah_independent=subprocess.run(['python','scripts/cp6_ah_review_scope.py'],capture_output=True).returncode==0\n          # END AH INDEPENDENT ROUTE\n          # BEGIN AH QUALIFIED ROUTE\n"], ['              reuse=audit_only or ad_exact or ad_round or ae_exact or ae_independent or af_exact or af_review or ag_review or ag_residual or ah_review\n', '              reuse=audit_only or ad_exact or ad_round or ae_exact or ae_independent or af_exact or af_review or ag_review or ag_residual or ah_review or ah_independent\n']], '.github/workflows/cp6-ad-roll-opening-check.yml': [[' || python scripts/cp6_ah_gate_scope.py; then\n', ' || python scripts/cp6_ah_gate_scope.py || python scripts/cp6_ah_review_scope.py; then\n']], '.github/workflows/cp6-ac-independent-audit.yml': [['          # BEGIN AH QUALIFIED ROUTE\n', "          # BEGIN AH INDEPENDENT ROUTE\n          if Path('scripts/cp6_ah_review_scope.py').exists():\n              from cp6_ah_review_scope import verify\n              verify()\n              with open(os.environ['GITHUB_OUTPUT'], 'a') as output:\n                  output.write('ae=true\\n')\n              raise SystemExit(0)\n          # END AH INDEPENDENT ROUTE\n          # BEGIN AH QUALIFIED ROUTE\n"]], '.github/workflows/cp6-ag-sale-reservation.yml': [['        if python scripts/cp6_ah_gate_scope.py; then\n', '        if python scripts/cp6_ah_gate_scope.py || python scripts/cp6_ah_review_scope.py; then\n']]}
NEW={'scripts/cp6_ah_independent_review.py','scripts/cp6_ah_review_scope.py',
     '.github/workflows/cp6-ah-independent-review.yml','docs/cp6-ah-independent-review.md'}
def verify():
 git=lambda *a:subprocess.check_output(['git',*a],text=True).strip()
 assert git('rev-parse',HEAD+'^{tree}')==TREE and git('merge-base',HEAD,'HEAD')==HEAD
 assert not git('rev-list','--merges',HEAD+'..HEAD')
 changed=set(git('diff','--name-only',HEAD,'HEAD').splitlines())
 assert changed==set(PATCHES)|NEW,sorted(changed)
 for path,edits in PATCHES.items():
  s=Path(path).read_text()
  for old,new in reversed(edits):
   assert s.count(new)==1,(path,'route missing or repeated')
   s=s.replace(new,old,1)
  assert s==subprocess.check_output(['git','show',HEAD+':'+path],text=True),'ORIGINAL_AH_BODY_CHANGED:'+path
 return dict(status='ROUTED_TO_INDEPENDENT_AH',candidate_head=HEAD,candidate_tree=TREE,
             harness_head=git('rev-parse','HEAD'),historical_500_matrix_reexecuted=False,
             independent_result_required=True,production_go=False)
if __name__=='__main__':print(json.dumps(verify()))
