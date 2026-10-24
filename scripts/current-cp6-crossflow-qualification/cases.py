"""Call frozen AI crossflow cases unchanged; preserve their IDs and three-day clock.

This is Native SQL qualification: the retained strict harness supplies its
explicit temporary ERP schema usage, seeded identity, rollback and leak checks.
No table/function grant, facade substitution, expected value or case body changes.
"""
from datetime import date,timedelta
import cp6_v2620ai_family as original
import cp7_retained_cp6_fixture as fixture

PHASES=('crossflow',)
PHASE_IDS={phase:tuple(name for name,_ in original.phase_cases(phase))for phase in PHASES}
IDS=tuple(name for phase in PHASES for name in PHASE_IDS[phase])
assert len(IDS)==len(set(IDS))==142
assert {phase:len(ids)for phase,ids in PHASE_IDS.items()}=={'crossflow':142}

def cases(cur,today,*,current,evidence):
    day=today-timedelta(days=3)
    original.actors.admin(cur)
    original.prior.set_open_period(cur,date(2026,8,31))
    fixture.prepare(cur,today,current=current,closed_through=date(2026,8,31),evidence=evidence)
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
