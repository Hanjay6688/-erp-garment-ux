"""Read the two exact terminal SKU Originals through the approved read-only transport."""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import verify_focused_sku as verifier

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'read-only'))
from retain import REPO, api, copy_stream, metadata


ROUTE = f'/repos/{REPO}/actions/'


def get_packet(identity, directory):
    directory.mkdir()
    run_id, job_id = identity['id'], identity['job_id']
    run = metadata(ROUTE + f'runs/{run_id}', directory / 'run.json')
    job = metadata(ROUTE + f'jobs/{job_id}', directory / 'job.json')
    verifier.fields(run, dict(id=run_id, status='completed', head_sha=identity['head_sha']),
                    'SKU_TRANSPORT_TERMINAL_RUN_REQUIRED')
    conclusion = run['conclusion']
    name = ('cp7-sku-current-parent-money-automatic-native25-1' if conclusion == 'success'
            else f'cp7-sku-failure-{run_id}-1')
    artifacts = metadata(ROUTE + f'runs/{run_id}/artifacts?per_page=100', directory / 'artifacts.json')
    matches = [artifact for artifact in artifacts['artifacts'] if artifact['name'] == name]
    verifier.require(len(matches) == 1, 'SKU_TRANSPORT_ONE_CANONICAL_ORIGINAL_REQUIRED')
    artifact, = matches
    verifier.metadata(identity, run, job, artifact)
    artifact_id = artifact['id']
    (directory / 'artifact.json').write_text(json.dumps(artifact, indent=2) + '\n')
    expected = dict(bytes=artifact['size_in_bytes'], sha256=artifact['digest'].removeprefix('sha256:'))
    with api(ROUTE + f'artifacts/{artifact_id}/zip') as source, (directory / 'canonical.zip').open('xb') as target:
        copied = copy_stream(source, target, expected['bytes'])
    verifier.require(copied == expected, 'SKU_TRANSPORT_EXACT_ARCHIVE_DIGEST_REQUIRED')


def main(repo, out):
    scope, shared = verifier.source(repo)
    with TemporaryDirectory(prefix='cp7-sku-terminal-') as temporary:
        origin, current = (Path(temporary) / name for name in ('origin', 'current'))
        get_packet(verifier.CURRENT, current)
        get_packet(verifier.ORIGIN, origin)
        prior = verifier.retained_origin(scope, *verifier.load_inputs(origin))
        packet = verifier.terminal(verifier.CURRENT, *verifier.load_inputs(current))
        result, catalogue = verifier.current_result(scope, shared, prior, packet)
        out.mkdir()
        for name in ('run.json', 'job.json', 'artifact.json'):
            (out / name).write_bytes((current / name).read_bytes())
        (out / 'SKU_CUMULATIVE_TERMINAL_RECEIPT.json').write_text(json.dumps(result, indent=2) + '\n')
        if catalogue is not None:
            (out / verifier.CATALOGUE).write_bytes(catalogue)
    print(json.dumps({key: result[key] for key in ('status', 'run_id', 'conclusion', 'actual_case_credit')}))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise ValueError('SKU_READER_CHECKOUT_AND_OUTPUT_REQUIRED')
    main(*(Path(arg).resolve() for arg in sys.argv[1:]))
