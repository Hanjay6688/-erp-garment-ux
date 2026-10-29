"""Default admission refuses closed prerequisites before runtime; offline opt-in."""
from pathlib import Path
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True


def load(name,path):
    spec = importlib.util.spec_from_file_location(name,path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def run(source_only=False):
    if source_only:
        source = load('continuation_offline_source',HERE/'admission.py').source_only()
        return dict(status='PASS_SOURCE_ONLY_NOT_NATIVE_CREDIT',files=len(source['files']),actual_cases=0,
            prerequisite_closed=json.loads((HERE/'CONFIG.json').read_bytes())['accepted_native13']is None,database_calls=0,production_go=False)
    load('continuation_default_closed_gate',HERE/'gate.py').selected(json.loads((HERE/'CONFIG.json').read_bytes()))
    proof = load('continuation_after_gate_runtime',HERE/'probe.py').runtime().admitted()
    return dict(status=proof['status'],actual_cases=0,database_calls=0,production_go=False)


if __name__ == '__main__':
    if sys.argv[1:]not in ([],['--source-only']):
        raise SystemExit('Use no arguments for closed admission or --source-only for offline source proof.')
    print(json.dumps(run(sys.argv[1:]==['--source-only'])))
