"""Use the genuine six-hour guard and reserve time for setup before launch."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import json
import sys

SETUP_RESERVE_SECONDS = 25 * 60


def require_setup_margin(window):
    if window['seconds_to_midnight'] <= window['required_seconds'] + SETUP_RESERVE_SECONDS:
        raise ValueError('AFUI_INSUFFICIENT_WIB_WINDOW_FOR_MEASURED_SETUP_RESERVE')
    return dict(window, setup_reserve_seconds=SETUP_RESERVE_SECONDS)


def require_window(source):
    path = Path(source) / 'scripts/current-de-free-date-preparation/attempt_policy.py'
    spec = spec_from_file_location('afui_original_day_window', path)
    policy = module_from_spec(spec)
    spec.loader.exec_module(policy)
    return require_setup_margin(policy.require_window())


if __name__ == '__main__':
    print(json.dumps(require_window(sys.argv[1]), sort_keys=True))
