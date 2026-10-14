"""Execute the exact candidate probe; retain its first outcome without case retries.

Audit harness adaptation: Pro Max 1.9 forbids retrying a group after cases ran.
The candidate guard/oracle still records rollover as INCOMPLETE. No expected,
fixture, product clock, comparator or case function is changed.
"""
from pathlib import Path
import sys,runpy,json
product=Path.cwd().parent/'auditor'
probe=sys.argv[1]
assert '/' not in probe and probe.endswith('.py')
sys.path.insert(0,str(product/'scripts'))
import cp6_auditor_business_day as business_day

def first_only(group,run_once,rows_of,keep_first=None):
    first=run_once()
    rows=rows_of(first) or {}
    rolled=sorted(k for k,r in rows.items() if r.get('business_day_rollover'))
    if rolled:
        if keep_first:keep_first(first)
        print(json.dumps(dict(group=group,business_day_rollover='KEPT_FIRST_RESULT',
                              reason='AUDIT_PRO_MAX_1_9_NO_CASE_RERUN',rolled_cases=rolled,
                              final={k:r.get('status') for k,r in rows.items()})),flush=True)
        business_day.annotate('KEPT_FIRST_RESULT',group,rolled)
    return first

business_day.with_retry=first_only
sys.argv=[str(product/'scripts'/probe),*sys.argv[2:]]
runpy.run_path(sys.argv[0],run_name='__main__')
