#!/usr/bin/env python3
"""H-01: compare regression outcomes case by case, not by status counts.

The AV trial compared per-group status counts; a PASS turning into HOLD while a HOLD turned into PASS kept the counts
and hid both moves (GPT audit 757b79a, H-01). This comparator takes the expected map case_id -> status recorded by
the AU qualification (run 35822980561) and reports, per group, every added, removed and moved case, whether the case
order is unchanged, and the exact identity of the historical HOLD cases. Counts stay only as a summary.

Usage:
  python3 scripts/cp6_regression_identity.py selftest
  python3 scripts/cp6_regression_identity.py compare OBSERVED_RECORDS.json [EXPECTED.json]
OBSERVED_RECORDS.json holds {"records":[{"group":..,"case":..,"status":..},...]} as printed by the trial runners.
"""
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
EXPECTED=ROOT/'docs/evidence/cp6-regression-expected-au-run35822980561.json'
HOLD='DATE_POLICY_REVIEW_REQUIRED'
GROUPS=('BUSINESS','IMPORTS','VALUES','NEW_CASES')


def from_records(records,groups=GROUPS):
    """Ordered {group: {case: status}}; a case seen twice in one group is an error, never silently merged."""
    out={g:{} for g in groups}
    for r in records:
        g=r.get('group')
        if g not in out or 'case' not in r:continue
        assert r['case'] not in out[g],('DUPLICATE_CASE',g,r['case'])
        out[g][r['case']]=r.get('status')
    return out


def compare(expected,observed,hold_count=12):
    report={'groups':{},'holds':{}}
    for g in expected:
        e=expected[g];o=observed.get(g,{})
        moved=[dict(case=k,expected=e[k],observed=o[k]) for k in e if k in o and o[k]!=e[k]]
        report['groups'][g]=dict(expected=len(e),observed=len(o),added=[k for k in o if k not in e],
            removed=[k for k in e if k not in o],moved=moved,order_unchanged=[k for k in o if k in e]==[k for k in e if k in o])
    exp_hold=[(g,k) for g in expected for k,s in expected[g].items() if s==HOLD]
    obs_hold=[(g,k) for g in observed for k,s in observed[g].items() if s==HOLD]
    report['holds']=dict(expected=len(exp_hold),observed=len(obs_hold),identical=exp_hold==obs_hold,
        expected_count_is_recorded=len(exp_hold)==hold_count,
        left_hold=[list(x) for x in exp_hold if x not in obs_hold],entered_hold=[list(x) for x in obs_hold if x not in exp_hold])
    clean=all(not v['added'] and not v['removed'] and not v['moved'] and v['order_unchanged'] for v in report['groups'].values())
    clean=clean and report['holds']['identical'] and report['holds']['expected_count_is_recorded']
    report['status']='IDENTICAL_PER_CASE' if clean else 'DISPOSITION_REQUIRED'
    return report


def load_expected(path=EXPECTED):
    return json.loads(Path(path).read_text())['expected']


def selftest():
    """The H-01 counterexample: swap one PASS with one HOLD, keep ids, order and counts. Must be caught."""
    expected=load_expected()
    observed={g:dict(v) for g,v in expected.items()}
    b=observed['BUSINESS'];first_pass=next(k for k,s in b.items() if s=='PASS');first_hold=next(k for k,s in b.items() if s==HOLD)
    b[first_pass],b[first_hold]=HOLD,'PASS'
    swapped=compare(expected,observed)
    same=compare(expected,{g:dict(v) for g,v in expected.items()})
    ok=(swapped['status']=='DISPOSITION_REQUIRED' and len(swapped['groups']['BUSINESS']['moved'])==2
        and swapped['holds']['left_hold']==[['BUSINESS',first_hold]] and swapped['holds']['entered_hold']==[['BUSINESS',first_pass]]
        and same['status']=='IDENTICAL_PER_CASE')
    return dict(status='PASS' if ok else 'FAIL',swap=[first_pass,first_hold],swapped=swapped,unchanged_control=same['status'])


if __name__=='__main__':
    if sys.argv[1]=='selftest':
        r=selftest();print(json.dumps(r,indent=1));assert r['status']=='PASS'
    elif sys.argv[1]=='compare':
        exp=load_expected(sys.argv[3] if len(sys.argv)>3 else EXPECTED)
        obs=from_records(json.loads(Path(sys.argv[2]).read_text())['records'])
        print(json.dumps(compare(exp,obs),indent=1))
