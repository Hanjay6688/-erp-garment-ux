#!/usr/bin/env python3
"""Route only the fully pinned AG delta; unknown changes require the full gate."""
from pathlib import Path
import hashlib,json,subprocess
BASE='ed52fa66120f5a6462e79a569c38e28ee3cf1184'
MANIFEST='docs/evidence/cp6-ag-gate-pins.json'
FULL='.github/workflows/cp6-full-schema-validation.yml'
NATIVE='.github/workflows/cp6-ad-roll-opening-check.yml'
START='          # BEGIN AG QUALIFIED ROUTE\n';END='          # END AG QUALIFIED ROUTE\n'
OLD='              reuse=audit_only or ad_exact or ad_round or ae_exact or ae_independent or af_exact or af_review\n'
NATIVE_OLD='          if python scripts/cp6_af_review_scope.py; then\n'
NATIVE_NEW='          if python scripts/cp6_af_review_scope.py || python scripts/cp6_ag_gate_scope.py; then\n'

def verify():
 git=lambda *a:subprocess.check_output(['git',*a],text=True).strip()
 assert git('merge-base',BASE,'HEAD')==BASE and not git('rev-list','--merges',BASE+'..HEAD')
 p=json.loads(Path(MANIFEST).read_text());assert p['base']==BASE and p['production_go'] is False
 changed=set(git('diff','--name-only',BASE,'HEAD').splitlines());assert changed==set(p['source_pins'])|{MANIFEST},sorted(changed)
 for path,pin in p['source_pins'].items():
  b=Path(path).read_bytes();assert hashlib.sha256(b).hexdigest()==pin['sha256'] and len(b)==pin['bytes'],'AG_GATE_SOURCE_DRIFT:'+path
 s=Path(FULL).read_text();assert s.count(START)==s.count(END)==1;a=s.index(START);b=s.index(END,a)+len(END);s=s[:a]+s[b:]
 new=OLD.rstrip('\n')+' or ag_review\n';assert s.count(new)==1;s=s.replace(new,OLD,1)
 assert s==subprocess.check_output(['git','show',BASE+':'+FULL],text=True),'AG_OLD_FULL_BODY_DRIFT'
 s=Path(NATIVE).read_text();assert s.count(NATIVE_NEW)==1;s=s.replace(NATIVE_NEW,NATIVE_OLD,1)
 assert s==subprocess.check_output(['git','show',BASE+':'+NATIVE],text=True),'AG_OLD_NATIVE_BODY_DRIFT'
 path='.github/workflows/cp6-ac-independent-audit.yml'
 s=Path(path).read_text();start='          # BEGIN AG QUALIFIED ROUTE\n';end='          # END AG QUALIFIED ROUTE\n'
 assert s.count(start)==s.count(end)==1;a=s.index(start);b=s.index(end,a)+len(end);s=s[:a]+s[b:]
 assert s==subprocess.check_output(['git','show',BASE+':'+path],text=True),'AG_OLD_AD_BODY_DRIFT'
 return dict(status='ROUTED_TO_AG_QUALIFIED_NATIVE_GATE',head=git('rev-parse','HEAD'),tree=git('rev-parse','HEAD^{tree}'),original_af='f46699865501b03f9fba3a8b188f3fd01eedf404',historical_500_matrix_reexecuted=False,ag_native_result_required=True,production_go=False)

if __name__=='__main__':print(json.dumps(verify()))
