"""One real WIB day with a matching hard two-hour owning job budget."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import importlib.util,json,sys

JOB_SECONDS=120*60
WORK_SECONDS=90*60
RECOVERY_SECONDS=20*60
ARTIFACT_SECONDS=10*60
WIB=ZoneInfo('Asia/Jakarta')

def require_window(now=None):
    now=datetime.now(timezone.utc)if now is None else now
    if now.tzinfo is None or now.utcoffset()is None:raise ValueError('FOCUSED_AWARE_REAL_CLOCK_REQUIRED')
    local=now.astimezone(WIB);midnight=(local+timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)
    remaining=(midnight-local).total_seconds()
    if remaining<=JOB_SECONDS:raise ValueError('FOCUSED_INSUFFICIENT_REAL_WIB_WINDOW')
    return dict(business_day=local.date().isoformat(),seconds_to_midnight=remaining,required_seconds=JOB_SECONDS,
        job_budget_seconds=JOB_SECONDS,work_budget_seconds=WORK_SECONDS,recovery_reserve_seconds=RECOVERY_SECONDS,
        artifact_reserve_seconds=ARTIFACT_SECONDS,automatic_group_retry=False,product_clock_changed=False)

def single_attempt(business_day):
    path=Path(__file__).resolve().parent.parent/'current-s03-sku-s05-composite-qualification/attempt_policy.py'
    spec=importlib.util.spec_from_file_location('focused_unchanged_no_automatic_retry',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.single_attempt(business_day)

if __name__=='__main__':
    if sys.argv[1:]!=['--require-window']:raise ValueError('FOCUSED_DECLARED_CLOCK_CHECK_ONLY')
    print(json.dumps(require_window(),sort_keys=True))
