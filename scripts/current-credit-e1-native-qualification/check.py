"""Default is closed admission; --source-only checks bytes without runtime."""
from pathlib import Path
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def run(source_only=False):
    if source_only:
        source = load('e1_offline_source_only', HERE/'admission.py').source_only()
        return dict(status='PASS_SOURCE_ONLY_NOT_RUNTIME_CREDIT', source_files=len(source['files']), actual_cases=0,
            prerequisite_closed=json.loads((HERE/'CONFIG.json').read_bytes())['accepted_D1'] is None,
            database_calls=0, production_go=False, independent_acceptance=False)
    load('e1_closed_check', HERE/'gate.py').selected(json.loads((HERE/'CONFIG.json').read_bytes()))
    engine = load('e1_after_closed_gate_runtime', HERE/'probe.py').runtime()
    proof = engine.admitted()
    return dict(status=proof['status'], actual_cases=0, database_calls=0, retained_D1=proof['retained_D1'], production_go=False)


if __name__ == '__main__':
    if sys.argv[1:] not in ([], ['--source-only']):
        raise SystemExit('Use no arguments for closed prerequisite admission or --source-only for offline byte checks.')
    print(json.dumps(run(sys.argv[1:] == ['--source-only'])))
