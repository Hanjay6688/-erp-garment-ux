"""Fable probe for the one-off INCOMPLETE of `CP7 Supplier Payment Create` on 7a0b4a90 (all cases PASS, group-end
`complete_boundary_restored` false, no diff recorded). The writer's four native cases run unchanged inside the Fable group,
bracketed by two Fable cases that capture boundary.snapshot() and public_state() and report the differing keys."""
import json
import cp7_supplier_payment_create_cases as spc
import cp6_auditor_runner as native
import cp7_f05_analysis_probe as f05
STATE={}
def _flat(d,prefix=''):
    out={}
    if isinstance(d,dict):
        for k,v in d.items():out.update(_flat(v,prefix+'/'+str(k)))
    else:out[prefix]=json.dumps(d,default=str,sort_keys=True)[:400]
    return out
def cases(cur,today):
    def capture():
        STATE['boundary']=native.boundary.snapshot(cur);STATE['public']=f05.public_state(cur)
        return dict(status='PASS',captured=True,boundary_keys=len(_flat(STATE['boundary'])),public_keys=len(_flat(STATE['public'])))
    def compare():
        b=native.boundary.snapshot(cur);p=f05.public_state(cur)
        fb0,fb1=_flat(STATE['boundary']),_flat(b);fp0,fp1=_flat(STATE['public']),_flat(p)
        db={k:(fb0.get(k),fb1.get(k)) for k in set(fb0)|set(fb1) if fb0.get(k)!=fb1.get(k)}
        dp={k:(fp0.get(k),fp1.get(k)) for k in set(fp0)|set(fp1) if fp0.get(k)!=fp1.get(k)}
        return dict(status='PASS' if not db and not dp else 'COUNTEREXAMPLE',boundary_equal=not db,public_equal=not dp,
                    boundary_diff=dict(list(db.items())[:40]),public_diff=dict(list(dp.items())[:40]))
    inner=list(spc.cases(cur,today))
    return [('FABLE_SPC:CAPTURE_STATE',capture)]+inner+[('FABLE_SPC:COMPARE_STATE_AFTER_WRITER_CASES',compare)]
