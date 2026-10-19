"""Run the unchanged writer345 cases once; retain any business-day failure."""
from pathlib import Path
import sys

PRODUCT = Path(__file__).resolve().parent.parents[2] / 'auditor'
sys.path.insert(0, str(PRODUCT / 'scripts'))
import cp6_auditor_business_day as business_day
import cp7_cp17_fix_probe as cp17

def first_only(group, run_once, rows_of, keep_first=None):
    result = run_once()
    result['sol_retry_policy'] = 'FIRST_RESULT_ONLY_NO_BUSINESS_DAY_RERUN'
    return result

if __name__ == '__main__':
    business_day.with_retry = first_only
    cp17.package._writer_runtime = lambda browser_mode=False: cp17.run()
    cp17.package.run('install')
