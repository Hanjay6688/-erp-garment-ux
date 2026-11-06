"""Read small existing Afui Originals without opening an ERP connection."""
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import ast
import json

import importlib.util

from retain import api, copy_stream, metadata
from verify_terminal import HEAD, JOB, REPOSITORY, RUN, exact, pin, require, strict

ORIGINAL_PREFIX = f'afui-original-{RUN}-1-'
DAY = '2026-11-06'
NATIVE1 = ('9be1035ea8f5d6bfe0008a474f8f267c108a17b448e1bce073d69cb939b507a9', 13490784753)
HOT = ('509a4c7647865b7b3c8796c21255497a5628b593fa8ce33f2911b48fcbe27678', 13490577204)
FIXTURE = ('b2b0bc9672b4ad033888678fe896881b37fbaf11c6bb66bee24658ad82b8ce8d', 13495324529)
CASES = {
    'a359e10ad91088b0655ca4d1b63359ae2b5202c82a22e74ff557840a8cd45f8a':
        ('HTTP', 'NONPAYABLE_AUTH_HTTP_OWNER_ADMIN_DENIAL_REPLAY_CANCEL_AND_STALE_TIMELINE',
         'physical_GOOD_stock_HPP_journal_payroll_and_BC_source_unchanged'),
    'e851782c2b071a7b9de566b7d25f23e72c1eeee894c3a1f5c11db69bc42ea29e':
        ('HTTP', 'NONPAYABLE_AUTH_HTTP_CACHED_REPLAY_OWNER_DEACTIVATED_DURING_REAL_LOCK_WAIT',
         'permission_checked_before_cached_reply'),
    'ec1ec41431f22a1823b2a7a52dceb3ad12be0f01f6409af1643b350ca4b72619':
        ('RACE', 'NONPAYABLE_TWO_SESSION_SAME_REQUEST_ONE_IMMUTABLE_DATE_AND_REPLY',
         'administrative_actor_not_real_Auth'),
    'e54303aade4daaf1cf1692d52a54fbde1cb16cb765d753668c158a9d59fa0f6b':
        ('RACE', 'NONPAYABLE_TWO_SESSION_DIFFERENT_REQUESTS_ONE_DATE_AND_ONE_STALE_TIMELINE',
         'administrative_actor_not_real_Auth'),
}


def inspect(route, destination, suffix, artifact_id, name):
    meta = metadata(route + f'artifacts/{artifact_id}', destination / (suffix + '.api.json'))
    exact(meta, dict(id=artifact_id, name=ORIGINAL_PREFIX + suffix, expired=False), 'AFUI_EXACT_INTERIM_ARTIFACT')
    exact(meta['workflow_run'], dict(id=RUN, head_sha=HEAD), 'AFUI_EXACT_INTERIM_ORIGINAL_SOURCE')
    size = meta['size_in_bytes']
    require(type(size) is int and 0 < size < 32 * 1024 * 1024, 'AFUI_BOUNDED_INTERIM_ORIGINAL_REQUIRED')
    path = destination / (suffix + '.zip')
    with api(route + f'artifacts/{artifact_id}/zip') as source, path.open('xb') as out:
        archive = copy_stream(source, out, size)
    exact(archive, dict(bytes=size, sha256=meta['digest'].removeprefix('sha256:')), 'AFUI_EXACT_INTERIM_ARCHIVE')
    with ZipFile(path) as bundle:
        names = bundle.namelist()
        require(len(names) == len(set(names)) == 2 and 'MANIFEST.json' in names and bundle.testzip() is None,
                'AFUI_EXACT_INTERIM_ORIGINAL_WRAPPER')
        actual = next(item for item in names if item != 'MANIFEST.json')
        require(actual == name, 'AFUI_EXACT_INTERIM_ORIGINAL_NAME')
        raw = bundle.read(actual)
        manifest = strict(bundle.read('MANIFEST.json'))
        exact(manifest, dict(original_name=name, original=pin(raw), github_run_id=str(RUN),
                             github_run_attempt='1', qualification_commit=HEAD), 'AFUI_EXACT_INTERIM_MANIFEST')
    return strict(raw), dict(artifact_id=artifact_id, name=name, archive=archive, original=pin(raw))


def main():
    directory = Path(__file__).resolve().parent
    for name in ('retain.py', 'verify_terminal.py', 'stage_mandor.py'):
        ast.parse((directory / name).read_bytes(), filename=name)
    yaml_present = importlib.util.find_spec('yaml') is not None
    route = f'/repos/{REPOSITORY}/actions/'
    with TemporaryDirectory(prefix='afui-access-originals-') as tmp:
        dest = Path(tmp)
        job = metadata(route + f'jobs/{JOB}', dest / 'source-job.json')
        exact(job, dict(id=JOB, head_sha=HEAD, run_id=RUN, run_attempt=1), 'AFUI_EXACT_INTERIM_OWNING_JOB')
        hot, _ = inspect(route, dest, *HOT, 'AFUI_COMPLETE_STATE_PREREQUISITE_RESULT.json')
        exact(hot, dict(status='PASS_COMPLETE_HOT_STATE_PREREQUISITE'), 'AFUI_ACTUAL_CURRENT_HOT_STATE')
        first, _ = inspect(route, dest, *NATIVE1, NATIVE1[0] + '.jsonl')
        fixture, witness = inspect(route, dest, *FIXTURE, 'AFUI_BROWSER_NATIVE_PREREQUISITE.json')
        exact(fixture, dict(status='ACTUAL_NATIVE_NONPAYABLE_BROWSER_PREREQUISITE_PREPARED',
                           expected_positive_HPP='20', expected_reimbursement='0', expected_new_entitlements=0),
              'AFUI_EXACT_INTERIM_COMMITTED_FIXTURE')
        evidence = fixture['observer_catalogue']
        require(len(evidence['after']) == 22 and evidence['original'] == hot['browser_settings_state_original']
                and evidence['cache'] == hot['browser_settings_cache_original']
                and evidence['after'] == first['actual_full22_case_boundary']['before']['actual_all22'],
                'AFUI_INTERIM_FIXTURE_CURRENT_CACHE_AND_EXACT_FULL22_REQUIRED')
        witnessed = [dict(witness, status=fixture['status'], catalogue_groups=22,
                        catalogue_sha256=sha256(json.dumps(evidence['after'], sort_keys=True,
                                                         separators=(',', ':')).encode()).hexdigest())]
        index = metadata(route + f'runs/{RUN}/artifacts?per_page=100', dest / 'source-artifacts.json')
        for suffix, (mode, case, important) in CASES.items():
            matches = [row for row in index['artifacts'] if row['name'] == ORIGINAL_PREFIX + suffix]
            if not matches:
                continue
            require(len(matches) == 1, 'AFUI_EXACT_ONE_INTERIM_CASE_WRAPPER')
            row, proof = inspect(route, dest, suffix, matches[0]['id'], suffix + '.jsonl')
            exact(row, dict(case=case, status='PASS', session_leaks=[],
                            business_day=dict(planned=DAY, before=DAY, after=DAY),
                            **{important: True, 'real_Auth_HTTP' if mode == 'HTTP' else 'actual_two_database_sessions': True}),
                  'AFUI_INTERIM_RUNTIME_CASE')
            witnessed.append(dict(proof, status=row['status'], mode=mode, case=case))

    print('AFUI_INTERIM_VERIFIED ' + json.dumps(dict(run=RUN, job=JOB, head=HEAD, attempt=1, results=witnessed,
                full_package_credit=0, new_ERP_commands_executed=0, remote_verifier_syntax=True,
                remote_stage_yaml_dependency=yaml_present), separators=(',', ':')), flush=True)


if __name__ == '__main__':
    main()
