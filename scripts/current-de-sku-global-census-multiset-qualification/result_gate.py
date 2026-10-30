"""Current-head outer/all5 gate plus separate exact supplemental Original."""
from pathlib import Path
from hashlib import sha256
import argparse
import importlib.util
import json
import subprocess

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, default=ROOT / 'cp6-proof/t3'); args = parser.parse_args()
    admission = load('global_census_gate_first_admission', HERE / 'admission.py'); admission.preflight()
    names = ('CP7_D1_E_SKU_GLOBAL_CENSUS_MULTISET.json', 'T3_PACKAGE_INSTALL.json')
    raws = [admission.regular(str((args.directory / name).relative_to(ROOT))).read_bytes() for name in names]
    report, package = [admission.document(raw) for raw in raws]
    head = subprocess.check_output(['/usr/bin/git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    gate = load('global_census_strict_result_loader', HERE / 'loader.py').gate()
    result = gate.checked(report, package, head, original_directory=args.directory)
    result['originals'] = {name: dict(bytes=len(raw), sha256=sha256(raw).hexdigest()) for name, raw in zip(names, raws)}
    result['supplemental_original'] = report['committed'][admission.CASE]['global_writer_supplemental_reference']
    result['runtime_entry'] = None
    result['writer_or_phantom_lock_closed'] = False
    result['permission_closure'] = 'UNKNOWN'
    # No metadata data rows enter stdout. The separate Original remains in the
    # inherited artifact directory and is referenced by exact raw byte digest.
    path = args.directory / 'DE_SKU_GLOBAL_CENSUS_MULTISET_GATE.json'
    with path.open('x') as stream: stream.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(status=result['status'], head=head, actual_Native_credit=0,
        production_go=False, independent_acceptance=False, runtime_entry=None), sort_keys=True))


if __name__ == '__main__': main()
