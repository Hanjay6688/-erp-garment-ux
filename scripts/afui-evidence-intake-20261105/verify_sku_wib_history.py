"""Validate the WIB reader on the four historical GitHub Actions archives."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


REPOSITORY = 'Hanjay6688/-erp-garment-ux'
SOURCE_HEAD = 'ae0df1ef17b4d84478d50a2a144cf0382d662ad0'
ORIGIN_HEAD = 'e4eaaecebad1f0ba11ab1542b5df89a6423a8a1e'
PREFLIGHT_HEAD = '0de103b71b43a6581ff92378f0d69729f80fd91a'
REVIEW_HEAD = '44ef9b0bebfe2df909dabac009afaf0a26d76a6d'
REVIEW_TREE = '91b4ffbf3397df0aa8d6979e6c199738d84c5b9f'
API = 'https://api.github.com/repos/' + REPOSITORY + '/'
RUNS = (
    ('origin', 43132617378, 130900171009, 13914600256),
    ('delimiter', 43158542850, 130984047828, 13919701197),
    ('capture', 43166466578, 131009386319, 13922802413),
    ('wib-failure', 43174323175, 131034780958, 13927899180),
)
REVIEWER = (
    "docs/cp7/review/shutdown-20261111/sku-43166466578-combined/verify_focused_sku.py",
    "docs/cp7/review/shutdown-20261111/sku-43166466578-combined/prepare_combined_sku_scope.py",
    "docs/cp7/review/shutdown-20261111/sku-43166466578-combined/prepare_non_po_followup.py",
    "docs/cp7/review/shutdown-20261111/sku-43166466578-combined/verify_combined_sku.py",
    "docs/cp7/review/shutdown-20261111/sku-43166466578-combined/verify_cost_capture_successor.py",
    "docs/cp7/review/shutdown-20261111/sku-43166466578-combined/verify_wib_successor.py",
    "docs/cp7/review/shutdown-20261111/sku-43132617378/read-only-stage/scripts/afui-evidence-intake-20261105/sku-intake/global/reviewed-sku-shutdown-successor/reviewed_sku_source.py",
    "docs/cp7/review/shutdown-20261111/sku-43132617378/read-only-stage/scripts/afui-evidence-intake-20261105/sku-intake/global/reviewed-sku-shutdown-successor/REVIEWED_980C_SUCCESSORS.json",
    "docs/cp7/review/shutdown-20261111/sku-43105533441/read-only-stage/scripts/afui-evidence-intake-20261105/sku-intake/global/reviewed-sku-shutdown-successor/verify_terminal_sku.py",
)
AFUI = (
    "docs/cp7/review/shutdown-20261111/sku-43028745523-global-intake/afui/verify_terminal_original.py",
    "docs/cp7/review/shutdown-20261111/sku-43028745523-global-intake/afui/verify_native_original.py",
)


def git(repo, *arguments):
    return subprocess.check_output(['git', '-C', str(repo), *arguments], timeout=180)


def api(path, accept='application/vnd.github+json'):
    request = Request(API + path, headers={'Accept': accept, 'X-GitHub-Api-Version': '2022-11-28'})
    request.add_unredirected_header('Authorization', 'Bearer ' + os.environ['GH_TOKEN'])
    return urlopen(request, timeout=60)


def metadata(path):
    with api(path) as response:
        return json.load(response)


def archive(workspace, identity):
    name, run_id, job_id, recorded_artifact = identity
    run = metadata(f'actions/runs/{run_id}')
    if run['status'] != 'completed' or run['run_attempt'] != 1:
        raise ValueError(f'Original run {run_id} is not terminal attempt 1')
    job = metadata(f'actions/jobs/{job_id}')
    expected = ('cp7-sku-current-parent-money-automatic-native25-1' if run['conclusion'] == 'success'
                else f'cp7-sku-failure-{run_id}-1')
    exact = [row for row in metadata(f'actions/runs/{run_id}/artifacts?per_page=50')['artifacts']
             if row['name'] == expected and not row['expired']]
    if len(exact) != 1 or (recorded_artifact is not None and exact[0]['id'] != recorded_artifact):
        raise ValueError(f'Exact canonical Original unavailable for {run_id}')
    artifact, = exact
    root = workspace / name
    root.mkdir()
    for label, value in (('run', run), ('job', job), ('artifact', artifact)):
        (root / f'{label}.json').write_text(json.dumps(value))
    with api(f"actions/artifacts/{artifact['id']}/zip", 'application/octet-stream') as response:
        if urlsplit(response.url).scheme != 'https':
            raise ValueError('Expected GitHub Actions archive over HTTPS')
        with (root / 'canonical.zip').open('xb') as output:
            shutil.copyfileobj(response, output, 1024 * 1024)
    return root


def reader_files(repo, work):
    if git(repo, 'rev-parse', REVIEW_HEAD + '^{tree}').decode().strip() != REVIEW_TREE:
        raise ValueError('Review tree does not match the archived verifier')
    reader = work / 'global/reviewed-sku-shutdown-successor'
    afui = work / 'afui'
    for directory, paths in ((reader, REVIEWER), (afui, AFUI)):
        directory.mkdir(parents=True)
        for path in paths:
            target = directory / Path(path).name
            target.write_bytes(git(repo, 'show', REVIEW_HEAD + ':' + path))
    return reader


def main():
    if os.environ.get('GITHUB_REPOSITORY') != REPOSITORY or os.environ.get('GITHUB_SERVER_URL') != 'https://github.com':
        raise ValueError('Expected the existing repository only')
    workspace = Path(os.environ['RUNNER_TEMP']) / 'sku-wib-originals'
    workspace.mkdir()
    repo = workspace / 'repo'
    origin = workspace / 'origin-source'
    repo.mkdir()
    git(repo, 'init', '--quiet')
    git(repo, 'remote', 'add', 'origin', 'https://github.com/' + REPOSITORY + '.git')
    git(repo, 'fetch', '--quiet', '--no-tags', 'origin', SOURCE_HEAD, ORIGIN_HEAD, PREFLIGHT_HEAD, REVIEW_HEAD)
    git(repo, 'worktree', 'add', '--quiet', '--detach', str(origin), ORIGIN_HEAD)
    sys.path.insert(0, str(reader_files(repo, workspace)))
    from verify_wib_successor import (
        AFTER_SCOPE_PIN, CATALOGUE, MANDOR_DECISION, PARENT, case_failure, fields,
        install_failure, load_inputs, pin, previous, require, retained_origin, source_review,
        verify_cumulative_mandor,
    )
    from verify_combined_sku import write_json
    from zipfile import ZipFile

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(archive, workspace, identity) for identity in RUNS]
        originals = [future.result(timeout=240) for future in futures]
    original, delimiter, capture, wib = originals
    scope, shared = source_review(repo)
    fields(scope, dict(intervening_install_failure=install_failure(load_inputs(delimiter))),
           'SKU_WIB_EXACT_DELIMITER_FAILURE')
    source = load_inputs(original)
    retained = retained_origin(scope, *source)
    with ZipFile(source[0]) as bundle:
        origin_raw = bundle.read(CATALOGUE)
    require(pin(origin_raw) == dict(bytes=16048163, sha256='5ff582717522b766c12024c1bf3299066475f14a3c6021a3543f378f829e0c07'),
            'SKU_WIB_EXACT_E4EA_CATALOGUE_ORIGINAL_REQUIRED')
    capture_failure = previous.failed_capture(scope, shared, retained, capture)
    wib_failure = case_failure(scope, wib, origin_raw)
    mandor_raw = git(repo, 'show', SOURCE_HEAD + ':' + PARENT)
    mandor = verify_cumulative_mandor(origin, scope['origin']['head'], mandor_raw)
    require(mandor['decision'] == shared[MANDOR_DECISION], 'SKU_WIB_ACTUAL_MANDOR_17_REQUIRED')
    output = Path(os.environ['GITHUB_WORKSPACE']) / 'sku-wib-reader-prerequisites'
    output.mkdir()
    result = dict(status='SKU_WIB_HISTORICAL_ORIGINALS_AND_CATALOGUE_READER_VERIFIED',
                  head=SOURCE_HEAD, scope=AFTER_SCOPE_PIN, retained_origin=retained[0],
                  retained_Native_cases=len(retained[2]), mandor=mandor,
                  delimiter_failure=scope['intervening_install_failure'], capture_failure=capture_failure,
                  prior_wib_failure=wib_failure, actual_new_cases=0, current_terminal=False)
    receipt = write_json(output / 'SKU_WIB_HISTORICAL_READER_PREREQUISITES.json', result)
    print(json.dumps(dict(status=result['status'], actual_new_cases=0, wib_prior_pass=5,
                          wib_prior_guard_refused=8, catalogue=result['prior_wib_failure']['diagnostic_catalogue_equivalence']['status'],
                          receipt=receipt), separators=(',', ':')))


if __name__ == '__main__':
    main()
