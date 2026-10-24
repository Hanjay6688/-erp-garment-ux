"""Bind preserved Originals to current source without claiming a new runtime run.

Read only: every archived byte is verified against the archive index. Product
trees and recursive installation identities are compared separately from the
test harness. Historical PASS/INCOMPLETE remain unchanged; no audit acceptance.
"""
from pathlib import Path
from hashlib import sha256
from collections import Counter
import argparse
import json
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PRODUCT_PATHS = ('src', 'supabase/release', 'supabase/migrations',
                 'supabase/dev', 'scripts/cp7-src', 'package.json', 'package-lock.json')


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()


def matching_objects(value, installation, product, path=''):
    if isinstance(value, dict):
        if value == installation:
            return [dict(path=path, identity='CURRENT_INSTALLATION')]
        if value == product:
            return [dict(path=path, identity='CURRENT_PRODUCT')]
        return [item for key, child in value.items()
                for item in matching_objects(child, installation, product, path+'/'+key)]
    if isinstance(value, list):
        return [item for key, child in enumerate(value)
                for item in matching_objects(child, installation, product, path+'/'+str(key))]
    return []


def file_maps(value, path=''):
    if isinstance(value, dict):
        for key, child in value.items():
            pointer = path+'/'+key
            if key == 'files' and isinstance(child, dict) and child and all(
                    isinstance(p, str) and (p.startswith(('scripts/', 'src/', 'supabase/', 'docs/', '.github/', 'tests/'))
                    or p in ('package.json', 'package-lock.json'))
                    and isinstance(h, str) and len(h) == 64
                    for p, h in child.items()):
                yield pointer, child
            else:
                yield from file_maps(child, pointer)
    elif isinstance(value, list):
        for key, child in enumerate(value):
            yield from file_maps(child, path+'/'+str(key))


def reconcile(archive):
    import cp7_current_installation as current
    installation = current.sources()
    head = git('rev-parse', 'HEAD')
    assert not git('status', '--porcelain', '--', *PRODUCT_PATHS), 'DIRTY_PRODUCT'
    result = dict(contract='cp7.preserved-evidence-source-reconciliation.v1',
                  evidence_type='WRITER_STATIC_SOURCE_COMPARISON', current_head=head,
                  current_tree=git('rev-parse', 'HEAD^{tree}'),
                  archive_bytes=archive.stat().st_size,
                  archive_sha256=sha256(archive.read_bytes()).hexdigest(),
                  product_paths=list(PRODUCT_PATHS),
                  current_product_trees={p:git('rev-parse', head+':'+p) for p in PRODUCT_PATHS},
                  reports=[], newly_executed_cases=0, full_qualification_complete=False,
                  independent_acceptance=False, production_go=False)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None, 'ARCHIVE_CRC_FAILURE'
        assert len(z.namelist()) == len(set(z.namelist())), 'DUPLICATE_ARCHIVE_MEMBERS'
        index = json.loads(z.read('INDEX.json'))
        for receipt in index['report_receipts']:
            for item in receipt['preserved_files']:
                raw = z.read(item['path'])
                assert len(raw) == item['bytes'] and sha256(raw).hexdigest() == item['sha256'], item['path']
            originals = [f for f in receipt['preserved_files'] if Path(f['path']).name == receipt['original_name']]
            assert len(originals) == 1, receipt['original_name']
            raw = z.read(originals[0]['path'])
            assert len(raw) == receipt['original_bytes'] and sha256(raw).hexdigest() == receipt['original_sha256']
            report = json.loads(raw)
            assert report['status'] == receipt['status'], 'HISTORICAL_STATUS_MISMATCH'
            identities = matching_objects(report, installation, installation['product'])
            maps = []
            for pointer, files in file_maps(report.get('source_declaration', {}), '/source_declaration'):
                changed = []
                for path, expected in files.items():
                    target = ROOT/path
                    assert target.resolve().is_relative_to(ROOT), path
                    actual = sha256(target.read_bytes()).hexdigest() if target.is_file() else None
                    if actual != expected:
                        changed.append(dict(path=path, expected=expected, observed=actual))
                maps.append(dict(path=pointer, checked_files=len(files), differences=changed))
            changed_product = git('diff', '--name-only', receipt['head'], head, '--', *PRODUCT_PATHS).splitlines()
            result['reports'].append(dict(original=receipt['original_name'],
                historical_status=receipt['status'], run_id=receipt['run_id'], artifact_id=receipt['artifact_id'],
                qualified_head=receipt['head'], original_bytes=len(raw), original_sha256=sha256(raw).hexdigest(),
                product_path_changes=changed_product, matching_installed_source_objects=identities,
                declared_file_map_comparisons=maps, receipt=receipt['git_receipt_url'],
                runtime_rerun_here=False, historical_status_reclassified=False))
    result['historical_status_counts'] = dict(Counter(r['historical_status'] for r in result['reports']))
    result['all_product_paths_unchanged'] = all(not r['product_path_changes'] for r in result['reports'])
    result['reports_with_direct_current_installation_or_product_identity'] = sum(
        bool(r['matching_installed_source_objects']) for r in result['reports'])
    result['limitations'] = [
        'Source equivalence is not runtime or independent acceptance.',
        'A missing direct installation object is reported, never inferred from UI/source trees.',
        'File-map checks cover repository-relative maps only; stage-local basenames are compared inside recursive product identities, never guessed as repository paths.',
        'Harness/source-map differences remain explicit and do not reclassify historical outcomes.',
        'Archive first failures and earlier narrower PASS runs are preserved; do not add their case budgets twice.',
        'CP6 archive gaps, Native286/current B and factory3600 remain separate qualification obligations.']
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = reconcile(args.archive)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('current_head', 'historical_status_counts',
        'all_product_paths_unchanged', 'reports_with_direct_current_installation_or_product_identity',
        'newly_executed_cases', 'production_go')}))
