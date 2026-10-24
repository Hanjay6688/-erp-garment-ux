"""Call frozen AI phase cases unchanged; preserve their IDs and three-day clock.

This is Native SQL qualification: the retained strict harness supplies its
explicit temporary ERP schema usage, seeded identity, rollback and leak checks.
No table/function grant, facade substitution, expected value or case body changes.
"""
from datetime import timedelta
import cp6_v2620ai_family as original

PHASES=('focused','detector')
PHASE_IDS={phase:tuple(name for name,_ in original.phase_cases(phase))for phase in PHASES}
IDS=tuple(name for phase in PHASES for name in PHASE_IDS[phase])
assert len(IDS)==len(set(IDS))==135
assert {phase:len(ids)for phase,ids in PHASE_IDS.items()}=={'focused':99,'detector':36}

def cases(cur,today):
    day=today-timedelta(days=3)
    original.actors.admin(cur)
    original.prior.set_open_period(cur,day-timedelta(days=5))
    result=[]
    for phase in PHASES:
        found=original.phase_cases(phase)
        assert tuple(name for name,_ in found)==PHASE_IDS[phase]
        for name,operation in found:
            def run(fn=operation,p=phase,n=name):
                row=fn(cur,day)
                return dict(row,retained_phase=p,retained_case_id=n,fixture_day=str(day))
            result.append((name,run))
    return result
