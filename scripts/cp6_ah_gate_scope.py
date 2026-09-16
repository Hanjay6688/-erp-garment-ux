#!/usr/bin/env python3
"""Route the complete, pinned AH family; preserve every older validation body."""
from pathlib import Path
import hashlib,json,subprocess
BASE='961c592e22b6582ba7c5b07d612e32a9dbbae28b'
MANIFEST='docs/evidence/cp6-ah-gate-pins.json'
FULL='.github/workflows/cp6-full-schema-validation.yml'
AD='.github/workflows/cp6-ad-roll-opening-check.yml'
AC='.github/workflows/cp6-ac-independent-audit.yml'
AG='.github/workflows/cp6-ag-sale-reservation.yml'
OLD='              reuse=audit_only or ad_exact or ad_round or ae_exact or ae_independent or af_exact or af_review or ag_review or ag_residual\n'

def strip(text,indent):
    start=indent+'# BEGIN AH QUALIFIED ROUTE\n';end=indent+'# END AH QUALIFIED ROUTE\n'
    assert text.count(start)==text.count(end)==1
    a=text.index(start);b=text.index(end,a)+len(end)
    return text[:a]+text[b:]

def verify():
    git=lambda *args:subprocess.check_output(['git',*args],text=True).strip()
    assert git('merge-base',BASE,'HEAD')==BASE and not git('rev-list','--merges',BASE+'..HEAD')
    p=json.loads(Path(MANIFEST).read_text());assert p['base']==BASE and p['production_go'] is False
    expected={FULL,AD,AC,AG,'.github/workflows/cp6-ah-return-allocation.yml',
              'scripts/cp6_ah_gate_scope.py','scripts/cp6_preuse_rollback_maintenance.py',
              'docs/cp6-ah-competition-handoff.md',
              'supabase/migrations/20260916070451_erp_v2_6_20ah_cp6_return_allocation_eligibility.sql',
              'supabase/rollbacks/20260916070451_erp_v2_6_20ah_cp6_return_allocation_eligibility.rollback.sql'}
    expected|={'scripts/cp6_v2620ah_'+name+'.py' for name in ('build_sql','runtime','family','concurrency','maintenance_schedules','rollback_guards')}
    expected|={'docs/evidence/cp6-ah-'+name+'.json' for name in ('ag-catalog-pins','predecessor-functions','runtime-pins','family-disposition')}
    assert set(p['source_pins'])==expected,'AH_UNADMITTED_SOURCE_PATH'
    changed=set(git('diff','--name-only',BASE,'HEAD').splitlines())
    assert changed==expected|{MANIFEST},sorted(changed)
    for path,pin in p['source_pins'].items():
        data=Path(path).read_bytes()
        assert len(data)==pin['bytes'] and hashlib.sha256(data).hexdigest()==pin['sha256'],'AH_GATE_SOURCE_DRIFT:'+path
    original=lambda path:subprocess.check_output(['git','show',BASE+':'+path],text=True)
    text=strip(Path(FULL).read_text(),'          ');new=OLD.rstrip('\n')+' or ah_review\n'
    assert text.count(new)==1;text=text.replace(new,OLD,1)
    assert text==original(FULL),'AH_OLD_FULL_BODY_DRIFT'
    text=Path(AD).read_text();new=' || python scripts/cp6_ag_residual_scope.py || python scripts/cp6_ah_gate_scope.py; then\n'
    assert text.count(new)==1;text=text.replace(new,' || python scripts/cp6_ag_residual_scope.py; then\n',1)
    assert text==original(AD),'AH_OLD_AD_BODY_DRIFT'
    assert strip(Path(AC).read_text(),'          ')==original(AC),'AH_OLD_AC_BODY_DRIFT'
    text=strip(Path(AG).read_text(),'  ')
    routing="    needs: review-scope\n    if: needs.review-scope.outputs.ah != 'true'\n"
    assert text.count(routing)==1;text=text.replace(routing,'',1)
    assert text==original(AG),'AH_OLD_AG_BODY_DRIFT'
    return dict(status='ROUTED_TO_AH_QUALIFIED_NATIVE_GATE',head=git('rev-parse','HEAD'),tree=git('rev-parse','HEAD^{tree}'),
                business_predecessor='119f8f133131eaf373f08cc45b7b3d6fc27a3d3e',historical_500_matrix_reexecuted=False,
                ah_native_result_required=True,independent_ah_acceptance=False,production_go=False)

if __name__=='__main__':print(json.dumps(verify()))
