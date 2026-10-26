"""Measured qualification phases only; completion of a phase is not suite PASS."""
from datetime import datetime, timezone
from time import monotonic
import json


def measured(trail, phase, operation, *args, **kwargs):
    row = dict(phase=phase, state='RUNNING', started_at_utc=datetime.now(timezone.utc).isoformat())
    trail.append(row)
    print(json.dumps(dict(event='QUALIFICATION_PHASE', **row)), flush=True)
    started = monotonic()
    try:
        result = operation(*args, **kwargs)
    except BaseException as error:
        row.update(state='FAILED', error_type=type(error).__name__)
        raise
    else:
        row['state'] = 'COMPLETED'
        return result
    finally:
        row.update(elapsed_ms=round((monotonic() - started) * 1000, 3),
                   finished_at_utc=datetime.now(timezone.utc).isoformat())
        print(json.dumps(dict(event='QUALIFICATION_PHASE', **row)), flush=True)
