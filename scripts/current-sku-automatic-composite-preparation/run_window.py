"""Budget one owning SKU attempt on its real WIB business day."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import argparse
import importlib.util
import json
import math
import os
import time


ROOT = Path(__file__).resolve().parents[2]
WIB = ZoneInfo('Asia/Jakarta')
DAY = 'SKU_CURRENT_AUTOMATIC_WIB_BUSINESS_DAY'
CUTOFF = 'SKU_CURRENT_AUTOMATIC_WIB_WORK_CUTOFF'
JOB_START = 'SKU_CURRENT_AUTOMATIC_JOB_START_MONOTONIC'
RECOVERY_SECONDS = 20 * 60
ARTIFACT_SECONDS = 10 * 60
TERMINATION_SECONDS = 35
# The last runner took about 19 minutes to reach the worker.
SETUP_RESERVE_SECONDS = 30 * 60
SETUP_KILL_SECONDS = 10


def retained_policy():
    path = ROOT / 'scripts/current-de-free-date-preparation/attempt_policy.py'
    spec = importlib.util.spec_from_file_location('sku_retained_attempt_policy', path)
    policy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(policy)
    return policy


def budget(*, record=False, policy=None):
    now = time.monotonic()
    local = datetime.now(timezone.utc).astimezone(WIB)
    day = local.date().isoformat()
    midnight = (local + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    remaining = (midnight - local).total_seconds()
    if not record and os.environ.get(DAY) != day:
        raise ValueError('SKU27_ADMITTED_WIB_DAY_REQUIRED')
    policy = retained_policy() if policy is None else policy
    recorded_cutoff = os.environ.get(CUTOFF)
    if record and (DAY in os.environ or recorded_cutoff is not None):
        raise ValueError('SKU27_WIB_WINDOW_ALREADY_RECORDED')
    try:
        start = float(os.environ.get(JOB_START, ''))
    except ValueError:
        raise ValueError('SKU27_REAL_JOB_START_REQUIRED') from None
    if not (math.isfinite(now) and math.isfinite(start) and 0 < start <= now):
        raise ValueError('SKU27_REAL_JOB_START_REQUIRED')
    job_cutoff = start + policy.JOB_BUDGET_SECONDS - RECOVERY_SECONDS - ARTIFACT_SECONDS
    wall_cutoff = now + remaining - RECOVERY_SECONDS - ARTIFACT_SECONDS - TERMINATION_SECONDS

    if record and remaining > policy.JOB_BUDGET_SECONDS + TERMINATION_SECONDS:
        return dict(mode='STANDARD', **policy.require_window(local))
    if not record and recorded_cutoff is None:
        # Setup consumes time from the originally admitted six-hour window.
        if now >= job_cutoff or job_cutoff > wall_cutoff:
            raise ValueError('SKU27_ADMITTED_STANDARD_WIB_WINDOW_EXHAUSTED')
        return dict(mode='STANDARD', business_day=day, seconds_to_midnight=remaining,
                    required_seconds=policy.JOB_BUDGET_SECONDS, automatic_group_retry=False,
                    product_clock_changed=False)

    try:
        cutoff = wall_cutoff if record else float(recorded_cutoff)
    except ValueError:
        raise ValueError('SKU27_SHORT_WINDOW_WORK_DEADLINE_EXHAUSTED') from None
    if not (math.isfinite(cutoff) and now < cutoff):
        raise ValueError('SKU27_SHORT_WINDOW_WORK_DEADLINE_EXHAUSTED')
    cutoff = min(cutoff, job_cutoff, wall_cutoff)
    work = cutoff - now
    if work <= (SETUP_RESERVE_SECONDS if record else 0):
        raise ValueError('SKU27_SHORT_WINDOW_INSUFFICIENT_WORK_AND_SETUP_TIME')
    return dict(mode='SHORT_WIB_WINDOW', business_day=day, seconds_to_midnight=remaining,
                work_cutoff_monotonic=cutoff, work_seconds_remaining=work,
                recovery_reserve_seconds=RECOVERY_SECONDS, artifact_reserve_seconds=ARTIFACT_SECONDS,
                termination_buffer_seconds=TERMINATION_SECONDS, setup_reserve_seconds=SETUP_RESERVE_SECONDS,
                automatic_group_retry=False, product_clock_changed=False)


def bind_supervisor(module, claim_worker):
    original = module.supervise

    def supervise(command, *, work_seconds, recovery_seconds):
        plan = budget()
        short = plan['mode'] == 'SHORT_WIB_WINDOW'
        if short:
            if (recovery_seconds != RECOVERY_SECONDS
                    or module.JOB_SECONDS - module.WORK_SECONDS - recovery_seconds != ARTIFACT_SECONDS):
                raise ValueError('SKU27_SHORT_WINDOW_ORIGINAL_RECOVERY_AND_ARTIFACT_RESERVES_REQUIRED')
            # Leave time to acquire the on-disk claim before Popen.
            work_seconds = min(work_seconds, plan['work_seconds_remaining'] - 1)
            if work_seconds <= 0:
                raise ValueError('SKU27_SHORT_WINDOW_WORK_DEADLINE_EXHAUSTED')
        claim_worker()
        result = original(command, work_seconds=work_seconds, recovery_seconds=recovery_seconds)
        if short:
            result['wib_window'] = dict(plan, effective_worker_seconds=work_seconds)
        return result

    module.supervise = supervise


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--record', action='store_true')
    mode.add_argument('--require', action='store_true')
    mode.add_argument('--setup-limit', action='store_true')
    args = parser.parse_args()
    plan = budget(record=args.record)
    if args.record:
        with open(os.environ['GITHUB_ENV'], 'a', encoding='ascii') as stream:
            stream.write(f"{DAY}={plan['business_day']}\n")
            if plan['mode'] == 'SHORT_WIB_WINDOW':
                stream.write(f"{CUTOFF}={plan['work_cutoff_monotonic']}\n")
    if args.setup_limit:
        if plan['mode'] == 'STANDARD':
            return
        seconds = math.floor(plan['work_seconds_remaining']) - SETUP_KILL_SECONDS - 2
        if seconds <= 0:
            raise ValueError('SKU27_SHORT_WINDOW_DATABASE_SETUP_DEADLINE_EXHAUSTED')
        print(f'{seconds}s')
    else:
        print(json.dumps(plan, sort_keys=True))


if __name__ == '__main__':
    main()
