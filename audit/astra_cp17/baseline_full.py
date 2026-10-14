"""Run the original 326+AS34, AR174, AT16/AU15 and races on CP7 FULL bodies.

The original T2 orchestration normally installs AU/AV and later dev layers.
Here ONLY those install calls become explicit already-installed verification.
The frozen factories, expected maps, approved supplements and race operations
are unchanged. No verdict is accepted solely because the job is green.
"""
from pathlib import Path
import json,os,sys,traceback,types

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
PRODUCT=Path.cwd().parent/'auditor'
sys.path.insert(0,str(PRODUCT/'scripts'))
import cp6_av_trial as avt
import legacy_group
import full_stack
avt.group=legacy_group.group  # T2 captures this as its ORIGINAL_GROUP.
import cp6_t2_regression as t2
from cp7_catalog_state import exact_public_catalog
import cp6_auditor_runner as native

PHASE=sys.argv[1]
assert PHASE in ('ar','regression','temporal')
OUT=full_stack.OUT
avt.OUT=OUT
native.r1.OUT=OUT

def already_installed(*args,**kwargs):
    with avt.psycopg.connect(avt.ADMIN) as conn,conn.cursor() as cur:
        checked=full_stack.composition.verify(cur);conn.rollback()
    return dict(status='PASS',install_operation='NOT_REPLAYED_ALREADY_FULL_COMPOSITION',verified=checked)

def run():
    report=dict(label='ASTRA_CP17_BASELINE_'+PHASE.upper(),status='INCOMPLETE',phase=PHASE,
                oracle_origin='FROZEN_LEGACY_UNCHANGED',fixture_origin='CANDIDATE_T2_REVIEWED_ADAPTER',
                evidence_origin='INDEPENDENT_NATIVE_RERUN',production_go=False)
    try:
        with full_stack.installed(report):
            avt.install_au=lambda:already_installed()['status']
            t2.change=already_installed
            avt.runtime=types.SimpleNamespace(change=already_installed,verified=full_stack.composition.verify,
                pins=t2.av_runtime.pins,qualify=None,refuse_post_use=None)
            with exact_public_catalog(native,retain_raw=True,retain_locations=True) as catalog:
                if PHASE=='ar':t2.ar_phase(report)
                elif PHASE=='regression':t2.regression_phase(report)
                else:avt.temporal_phase(report)
                report['candidate_catalog_adapter']=catalog
    except Exception as exc:
        report.update(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
    finally:
        full_stack.save('CP17_BASELINE_'+PHASE.upper(),report)
        print(json.dumps({k:report.get(k) for k in ('label','status','phase','case_count','cp6_restored','advisor_gate','error','traceback')},default=str),flush=True)
    # DISPOSITION_REQUIRED / COUNTEREXAMPLE retain their original meaning.
    # A moved result stays unresolved/red pending its per-case disposition.
    assert not report.get('error') and report.get('cp6_restored') and report.get('advisor_gate'),report
    return dict(status='PASS' if report['status'] in ('WRITER_PASS','WRITER_PASS_WITH_12_PRESERVED_HISTORICAL_HOLD') else 'INCOMPLETE',
                legacy_status=report['status'],production_go=False,
                scope='LEGACY_VERDICT_RETAINED_BUSINESS_DISPOSITIONS_STILL_REQUIRED')

if __name__=='__main__':
    full_stack.package._writer_runtime=lambda browser_mode=False:run()
    full_stack.package.run('install')
