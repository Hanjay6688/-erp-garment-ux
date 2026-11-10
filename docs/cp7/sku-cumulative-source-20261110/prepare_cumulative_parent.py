"""Prepare an independent SKU review from the verified Mandor 15+2 evidence."""
import argparse
from collections import Counter
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile


COMBINED_SHA256 = '7d1b37cc03ccdcd62b30756b0f80df18d92de922a6e1195198adda2a33fadf5c'
SOURCE_SHA256 = '2af3b8fa17255aa679553c9682f2d3091d2cd1fe502c32462417f02e42557c49'
GRAPH_SHA256 = '0e21bacea3e9cf08c4ef1f0fea7819ba4bc1b4ebf5463f99c9d2a44c84cf3cd9'
TERMINAL_SHA256 = '9997980438a375c95187b76088172602a3e0d6a4b533b587600203d5f697d30e'
BACKEND = dict(head='a0e7d5616a0ac470876409d31c41388159f17692',
               tree='9e4cea296f2370d7ead31a6ac2b05c132fb09521')
APP = dict(head='e63c758990f54dbec4e635ecf3d53c6e80b03041',
           tree='c7634a3a39254c08894ea1ba5ea0f1b8fc2c7b7a')
SKU = dict(head='1b9d6d18ce206b2a117e0010409540e695ae1c95',
           tree='ebefa23ce99443f74b32e52e8fabebbc23f32d4d')
GROUPS = {'Native9': 9, 'Session4': 4, 'HTTP2': 2, 'BrowserPair': 2}
GATES = {'installed', 'primary_unchanged', 'backup_restore_drill',
         'security_advisors', 'writer_runtime'}


def require(condition, label):
    if not condition:
        raise ValueError(label)


def pin(raw):
    return {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}


def verified_zip(raw, expected):
    require(sha256(raw).hexdigest() == expected, 'EXACT_ARCHIVE_SHA256_REQUIRED')
    archive = ZipFile(BytesIO(raw))
    require(len(set(archive.namelist())) == len(archive.namelist())
            and archive.testzip() is None, 'ARCHIVE_MEMBER_OR_CRC_MISMATCH')
    return archive


def prior_passes(archive, manifest):
    prior = manifest['old_run']
    require((prior['run'], prior['job'], prior['attempt'], prior['head'], prior['conclusion'])
            == (42660429648, 129310209330, 1, BACKEND['head'], 'failure')
            and prior['original_recovery_verified'] is True, 'ORIGINAL_RUN_PROVENANCE')
    members = {}
    for group in manifest['retained_group_originals']:
        label = group['group']
        require(label in ('Native9', 'Session4', 'HTTP2') and label not in members,
                'EXACT_BACKEND_GROUPS_REQUIRED')
        raw = archive.read(f"retained-group-originals/{group['artifact_id']}.zip")
        require(len(raw) == group['archive_bytes'], 'ORIGINAL_ARCHIVE_LENGTH')
        with verified_zip(raw, group['archive_sha256']) as original:
            meta = json.loads(original.read('MANIFEST.json'))
            content = original.read(group['original_name'])
            require(meta['classification'] == 'INCOMPLETE_RUN_ORIGINAL_ONLY_NOT_ACCEPTANCE'
                    and meta['github_run_id'] == str(prior['run'])
                    and meta['github_run_attempt'] == str(prior['attempt'])
                    and meta['qualification_commit'] == prior['head']
                    and meta['original_name'] == group['original_name']
                    and meta['original'] == group['original'] == pin(content), 'ORIGINAL_MEMBER_PIN')
            report = json.loads(content)
            rows = report['races'] if label == 'Session4' else report['cases']
            require(len(rows) == GROUPS[label] and set(rows) == set(group['ids'])
                    and all(row['status'] == 'PASS' for row in rows.values()), 'BACKEND_CASE_RESULT')
            members[label] = set(rows)
    require(set(members) == {'Native9', 'Session4', 'HTTP2'}, 'MISSING_BACKEND_GROUP')
    return members


def browser_passes(archive, manifest):
    reader = manifest['read_only_verification']
    require((reader['run'], reader['job'], reader['attempt'], reader['artifact_id'])
            == (42770344036, 129676405024, 1, 13741144096), 'ARCHIVE_READER_PROVENANCE')
    raw = archive.read('MANDOR_BROWSER_PAIR_READ_ONLY_RECEIPT.zip')
    with verified_zip(raw, reader['archive_sha256']) as receipt:
        record_raw = receipt.read('TERMINAL_RECEIPT.json')
    require(sha256(record_raw).hexdigest() == reader['receipt_sha256'] == TERMINAL_SHA256,
            'EXACT_ARCHIVE_READER_RECEIPT')
    record = json.loads(record_raw)
    pair = manifest['browser_pair']
    keys = ('run', 'job', 'attempt', 'head', 'tree', 'artifact_id', 'archive', 'conclusion')
    require(all(record[key] == pair[key] for key in keys)
            and (record['run'], record['job'], record['attempt'], record['artifact_id'])
            == (42752853455, 129620303386, 1, 13741014130)
            and record['head'] == APP['head'] and record['tree'] == APP['tree']
            and record['conclusion'] == 'success', 'EXACT_PAIRED_BROWSER_RUN')
    require(all(record[key] is True for key in ('all_member_crc_verified', 'backup_restored',
                'worker_reaped', 'primary_Auth_restored')) and len(record['members']) == 29
            and record['five_gates'] == pair['five_gates'] == dict.fromkeys(GATES, True)
            and record['boundary'] == pair['restore'] and len(record['boundary']) == 6
            and all(value is True for value in record['boundary'].values())
            and record['browser_handoff'] == pair['handoff'], 'BROWSER_GATES_RESTORE_OR_HANDOFF')
    return set(record['actual_browser_passes'])


def prepare(combined_raw, source_raw):
    with verified_zip(combined_raw, COMBINED_SHA256) as combined:
        manifest = json.loads(combined.read('MANDOR17_COMBINED_TECHNICAL_EVIDENCE.json'))
        expected = prior_passes(combined, manifest)
        expected['BrowserPair'] = browser_passes(combined, manifest)
    rows = manifest['cases']
    require(len({row['case_id'] for row in rows}) == len(rows) == 17
            and Counter(row['group'] for row in rows) == GROUPS
            and all(row['observed'] == 'PASS' and row['case_id'] in expected[row['group']]
                    for row in rows), 'EXACT_15_PLUS_2_DISTINCT_CASES')
    require(manifest['candidate'] == APP and manifest['prior_runs_aggregated'] is True
            and manifest['production_go'] is False and manifest['independent_acceptance'] is False,
            'CUMULATIVE_REVIEW_ONLY')
    with verified_zip(source_raw, SOURCE_SHA256) as source:
        graph = source.read('MANDOR_PAIR_GITHUB_SOURCE_GRAPH.json')
    require(sha256(graph).hexdigest() == GRAPH_SHA256, 'EXACT_FENCED_PARENT_GRAPH')
    return {
        'status': 'SKU_CUMULATIVE_PARENT_REVIEW_INPUT_VERIFIED',
        'mode': 'CUMULATIVE_15_PLUS_2',
        'prior_runs_aggregated': True,
        'backend_source': BACKEND,
        'tested_browser_app': APP,
        'closed_sku_preimage': SKU,
        'mandor_source_graph': json.loads(graph),
        'mandor_source_graph_pin': pin(graph),
        'inputs': {'combined': pin(combined_raw), 'closed_money_source': pin(source_raw)},
        'original_run': manifest['old_run'],
        'paired_browser_run': manifest['browser_pair'],
        'archive_verification': manifest['read_only_verification'],
        'cases': rows,
        'runtime_admission': False,
        'production_go': False,
        'independent_acceptance': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('combined', type=Path)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = prepare(args.combined.read_bytes(), args.source.read_bytes())
    with args.output.open('x') as output:
        json.dump(result, output, sort_keys=True, indent=2)
        output.write('\n')


if __name__ == '__main__':
    main()
