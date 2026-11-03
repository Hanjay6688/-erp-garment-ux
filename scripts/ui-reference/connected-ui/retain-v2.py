"""Reuse individually verified screenshots; the predecessor run remains FAILURE."""
import hashlib
import json
import os
import pathlib
import subprocess
import zipfile

SOURCE = '65991506ef0fee90341fb40d95bab41e02cbaa5e'
DIGEST = '1ee5b2ed06f2588b971d1ce920057bbdd31d174ce1a7417039086659c366010b'
SIZE = 6279286


def require(ok, message):
    if not ok:
        raise ValueError(message)


archive = pathlib.Path(os.environ['UI_RETAIN_ARCHIVE'])
raw = archive.read_bytes()
require(len(raw) == SIZE and hashlib.sha256(raw).hexdigest() == DIGEST,
        'EXACT_PREDECESSOR_ORIGINAL_REQUIRED')
fixture = 'scripts/ui-reference/connected-ui/'
same_inputs = ['src', 'package.json', 'package-lock.json', 'vite.config.ts',
               'tests/fixtures/productionRecovery.ts']
same_inputs += [fixture + p for p in ['auth.ts', 'client.ts', 'data.ts',
               'fixture.html', 'fixture.tsx', 'frame.css', 'state.ts',
               'server.mjs', 'vite.config.mjs']]
require(not subprocess.check_output(['git', 'diff', '--name-only', SOURCE, '--', *same_inputs]).strip(),
        'SOURCE_FIXTURE_OR_DEPENDENCIES_CHANGED_REUSE_REFUSED')
expected = set()
states = ['ready', 'long', 'empty', 'loading', 'error', 'pending', 'denied', 'revoked']
for width in [320, 390, 768]:
    expected.update(f'pocket/{state}/{width}' for state in states + ['period-preview', 'pending-reopened'])
    expected.update(f'import/{state}/{width}' for state in
                    ['ready', 'CSV-preview', 'long', 'empty', 'loading', 'error'] +
                    (['denied', 'revoked'] if width != 768 else []))
with zipfile.ZipFile(archive) as z:
    require(z.testzip() is None, 'ORIGINAL_ZIP_CRC')
    require(all(not pathlib.PurePosixPath(n).is_absolute() and '..' not in pathlib.PurePosixPath(n).parts
                for n in z.namelist()), 'UNSAFE_ARCHIVE_MEMBER')
    previous = json.loads(z.read('ui-connected-proof/CONNECTED_UI_CAPTURE.json'))
    require(previous['source'] == SOURCE and previous['status'] == 'INCOMPLETE', 'FAILED_PREDECESSOR_IDENTITY')
    require(previous['server_reaped'] and not previous['cleanup_errors'] and not previous['console_errors'],
            'PREDECESSOR_CLEANUP_AND_CONSOLE')
    require(previous['actual_Auth_cases'] == previous['actual_SQL_executed'] ==
            previous['actual_financial_backend_cases'] == 0, 'NO_BACKEND_ACCEPTANCE')
    failures = previous['failures']
    require(len(failures) == 3 and {f['width'] for f in failures} == {320, 390, 768} and
            all(f['form'] == 'import' and f['state'] == 'pending' and
                'locator.isDisabled: Timeout' in f['error'] and
                'Simpan perubahan draft' in f['error'] for f in failures), 'ONLY_DIAGNOSED_ORACLE_FAILURES')
    variants = previous['variants']
    keys = [f"{v['form']}/{v['state']}/{v['width']}" for v in variants]
    require(len(keys) == 52 and len(set(keys)) == 52 and set(keys) == expected, 'EXACT_52_REUSABLE_IDENTITIES')
    images = {}
    for v in variants:
        shot = v['screenshot']
        name = f"{v['form']}-{v['state']}-{v['width']}.png"
        require(shot['name'] == name, 'EXACT_SCREENSHOT_IDENTITY')
        data = z.read('ui-connected-proof/' + name)
        require(len(data) == shot['bytes'] and hashlib.sha256(data).hexdigest() == shot['sha256'],
                'INDIVIDUAL_PNG_PIN:' + name)
        require(not v['observations']['page_overflow'] and not v['observations']['contrast_findings'],
                'RETAINED_VISUAL_FINDING:' + name)
        v['retained_from'] = {'source': SOURCE, 'run': 41642954385, 'artifact': 13234240500}
        images[name] = data
    recoveries = previous['recoveries']
    require(len(recoveries) == 3 and {r['width'] for r in recoveries} == {320, 390, 768} and
            all(r['form'] == 'pocket' and r['same_payload'] and r['automatic_replay_count'] == 0 and
                not r['backend_idempotence_claim'] for r in recoveries), 'THREE_RETAINED_REOPEN_CHECKS')
    receipt = {'contract': 'cp7.B.individual-UI-evidence-reuse.v1',
               'original': {'source': SOURCE, 'run': 41642954385, 'job': 125940822601,
                            'artifact': 13234240500, 'bytes': SIZE, 'sha256': DIGEST,
                            'run_conclusion': 'FAILURE', 'original_report_status': 'INCOMPLETE'},
               'unchanged_inputs': same_inputs, 'variants': variants, 'recoveries': recoveries,
               'retained_views': 52, 'missing_views_to_capture': 28,
               'scope': 'INDIVIDUAL_FIXTURE_VIEWS_ONLY_NOT_PREDECESSOR_RUN_ACCEPTANCE'}

out = pathlib.Path(os.environ.get('UI_PROOF_DIR', '../ui-connected-proof'))
out.mkdir(parents=False, exist_ok=False)
for name, data in images.items():
    (out / name).write_bytes(data)
(out / 'RETAINED_V2_VIEWS.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'retained_views': 52, 'fresh_views_required': 28,
                  'original_run_conclusion': 'FAILURE', 'source_inputs_unchanged': True}))
