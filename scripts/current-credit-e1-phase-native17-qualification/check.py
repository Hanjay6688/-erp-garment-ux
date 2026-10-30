"""Default/runtime admission stays CLOSED; offline checks never import ERP."""
from pathlib import Path
import argparse
import importlib.util
import json

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--source-only', '--offline', action='store_true')
    group.add_argument('--runtime', action='store_true')
    args = parser.parse_args(argv)
    if args.source_only:
        source = load('e1_phase_offline_source', HERE / 'admission.py').source_only()
        cfg = json.loads((HERE / 'CONFIG.json').read_bytes())
        print(json.dumps(dict(status='PASS_SOURCE_ONLY_NOT_RUNTIME_CREDIT', source_files=len(source['files']),
            prerequisite_closed=cfg['accepted_D1'] is None, actual_Native_cases=0, production_go=False)))
    else:
        load('e1_phase_source_cli_probe', HERE / 'probe.py').main(['--check'])


if __name__ == '__main__':
    main()
