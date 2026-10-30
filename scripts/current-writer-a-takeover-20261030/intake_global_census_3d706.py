"""Root recheck of the exact 3d706 metadata Original; no DB or Native credit."""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import argparse
import importlib.util
import json
import subprocess
import zipfile

HEAD = '3d7066b852176d9f343ec831d2f63aee6665579b'
TREE = 'c5a09173421af936df719971b2c5f1043d292818'
ZIP_BYTES = 25922920
ZIP_SHA256 = '1b0180984af615c78dd635b72e6ce8e36f3f45e656cc04fcf955084b7c0605f9'
PINS = {
    'CP7_D1_E_SKU_GLOBAL_CENSUS_MULTISET.json': (151801795, '9d4cd4ddf21977d3ec2ce6683e329e1e6ee51606bcb201ddbb51e0a910f2584b'),
    'T3_PACKAGE_INSTALL.json': (360441, '351b02a1c67c085d9c06c1dd04fcc8cb91ed68f7798a2c8102698f2f4fc162f5'),
    'GLOBAL_ACTUAL_WRITER_SUPPLEMENT_V2.json': (79526731, 'f3183fa6b71e34d46df5e462556396846b457de7e78768bd88b426777850cfa0'),
    'GLOBAL_WRITER_RAW_CAPTURE.json': (100821477, '7b752a13b8ab5fd87a384b27592b114f6149c316b0b8382eb344bff5544c4087'),
    'DE_SKU_GLOBAL_CENSUS_MULTISET_GATE.json': (1206, '4ce79046864f135982ff15c33eaab3f0f66a670a6f292245b5333c3d3b177075'),
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.source.resolve()
    git = lambda *parts: subprocess.check_output(['/usr/bin/git', '-C', str(root), *parts], text=True).strip()
    require(git('rev-parse', 'HEAD^{tree}') == TREE, 'EXACT_ACTUAL_SOURCE_TREE_REQUIRED')
    ns = root / 'scripts/current-de-sku-global-census-multiset-qualification'
    admission = load('root_global_3d_admission', ns / 'admission.py')
    context = load('root_global_3d_fence', root / 'scripts/current-sku-managed-recovery-native27-qualification/source_context.py')
    with context.fenced_source_read() as fence:
        source = admission.preflight()
        archive = args.archive.read_bytes()
        require((len(archive), sha256(archive).hexdigest()) == (ZIP_BYTES, ZIP_SHA256), 'EXACT_ACTUAL_ZIP_REQUIRED')
        args.directory.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.archive) as z:
            require(len(z.namelist()) == 129 and z.testzip() is None, 'COMPLETE_ZIP_CRC_REQUIRED')
            for name, pin in PINS.items():
                require(z.namelist().count(name) == 1, 'EXACT_ROOT_ORIGINAL_MEMBER_REQUIRED:' + name)
                raw = z.read(name)
                require((len(raw), sha256(raw).hexdigest()) == pin, 'ORIGINAL_BYTES_CHANGED:' + name)
                dest = args.directory / name
                if dest.exists():
                    require(dest.read_bytes() == raw, 'EXISTING_ORIGINAL_CHANGED:' + name)
                else:
                    with dest.open('xb') as output:
                        output.write(raw)
        def document(name):
            return admission.document((args.directory / name).read_bytes())
        report = document('CP7_D1_E_SKU_GLOBAL_CENSUS_MULTISET.json')
        package = document('T3_PACKAGE_INSTALL.json')
        original_gate = document('DE_SKU_GLOBAL_CENSUS_MULTISET_GATE.json')
        compiler = load('root_global_3d_compiler', ns / 'compile_modules.py')
        gate = compiler.module('gate').checked(report, package, HEAD, original_directory=args.directory)
        require(all(original_gate.get(k) == v for k, v in gate.items()), 'RECOMPUTED_GATE_DISAGREES')
        supplement = document('GLOBAL_ACTUAL_WRITER_SUPPLEMENT_V2.json')
        raw = document('GLOBAL_WRITER_RAW_CAPTURE.json')
        require(len(raw['raw_groups']) == 19, 'EXACT_19_RAW_QUERIES_REQUIRED')
        stats = {}
        for name, rows in raw['raw_groups'].items():
            counts = Counter(key for key, _ in rows)
            stats[name] = dict(occurrences=len(rows), distinct_identities=len(counts),
                repeated_identities=sum(v > 1 for v in counts.values()),
                repeated_occurrences=sum(v - 1 for v in counts.values()),
                maximum_multiplicity=max(counts.values(), default=0))
        require(set(supplement['groups']) == set(raw['raw_groups']), 'RAW_GROUP_SET_CHANGED')
    receipt = dict(status='ROOT_EXACT_3D706_METADATA_GATE_AND_RAW_LOSSLESS_PROJECTION_PASS',
        head=HEAD, source_tree=TREE, local_source_head=git('rev-parse', 'HEAD'),
        archive=dict(bytes=ZIP_BYTES, sha256=ZIP_SHA256, crc_members=129),
        originals={name: dict(bytes=p[0], sha256=p[1]) for name, p in PINS.items()},
        exact_source_admission=source, source_DB_guard=fence,
        recomputed_gate=gate, raw_query_statistics=stats,
        prior_ee145_failed_raw_query_object='UNKNOWN_NOT_RECONSTRUCTED_FROM_SUCCESSOR',
        runtime_entry=None, actual_Native_credit=0, global_bridge_qualified=False,
        writer_or_phantom_lock_closed=False, permission_closure='UNKNOWN',
        production_go=False, independent_acceptance=False)
    args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(dict(status=receipt['status'], head=HEAD, raw_query_groups=len(stats),
        dependency_groups={k: stats[k] for k in ('dependencies', 'view_relation_dependencies')},
        actual_Native_credit=0, output=str(args.output)), sort_keys=True))


if __name__ == '__main__':
    main()
