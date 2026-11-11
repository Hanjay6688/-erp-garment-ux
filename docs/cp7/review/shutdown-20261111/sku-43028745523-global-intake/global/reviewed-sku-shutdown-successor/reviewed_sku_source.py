"""Exact current SKU adoption; cumulative Mandor is replayed separately.

This source review never creates a passing SKU run or a Global runtime gate.
Run/job IDs are supplied only from actual terminal GitHub metadata.
"""
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import os
import re
import subprocess
import sys

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE / 'afui'))
from verify_terminal_original import require, strict

PREPARED = 'f8d204995c52a8acca76a8732c2111ee21924f27'
PREPARED_TREE = '3fc3c8472754b28dd0b49e97decfab661765cae1'
RECEIPT_FAILURE = '82b03bbac619cd37912af58942dbf326b833f57e'
RECEIPT_FAILURE_TREE = 'f20f430dd46914d5500a72013e2cde4902cb44ca'
OW04_FAILURE = '79dfe1806a9780e87abb9456ec8b21350123e7f6'
OW04_FAILURE_TREE = '6cacc17bcb38571e009413786a020a418dac8c8b'
TYPED_FAILURE = '69124742b7f312290ead868ee8b0bc0e94b25479'
TYPED_FAILURE_TREE = '2022f6f708b9237ebfefbcc8bf28383662c84a9f'
COLD_SOURCE_FAILURE = 'e8dba546e81299b0b8d17c1ae99b178c9ff95986'
COLD_SOURCE_FAILURE_TREE = '8e758fa6728cab3b6dd80df4440e9293adca8a44'
FAILED_SOURCE = '6aebc5888d164203ba7934b322b3edaf67ee36bd'
FAILED_TREE = '82ca481ecb272d82ec2e88ac5e5fac594e8ff2c0'
CHECKPOINT_HEAD = '32590613a08e176536d9a19b3843f6a72f4479b4'
CHECKPOINT_TREE = '262811e77e1a305a9d54baa9374e27df06793d10'
SKU_AREA = 'scripts/current-sku-automatic-composite-preparation/'
PARENT = SKU_AREA + 'MANDOR17_PARENT_ROOT_ACTUAL_INTAKE.json'
WORKFLOW = '.github/workflows/cp7-sku-current-parent-money-automatic-native25.yml'
RECEIPT_REPAIR_PINS = {
    'check_source.py': dict(bytes=16761, sha256='ba8ed36a20010b2e55d3b12f678f7753c25e28f06782435b5cfa4bbb899f5c32'),
    'execution.py': dict(bytes=14154, sha256='2092e0e8e3f6c2dd1c49b81b2d58d311cfd60c35eff838e5f6d00b31cf7aaf32'),
    'test_current_parent.py': dict(bytes=4929, sha256='f6094ccb178b704346c95195928ca1019406d5466599230669e972d287958555'),
    'test_execution.py': dict(bytes=16418, sha256='f6222463a564cb4000871ab9c1bd54047906088bccf746f94005376933ed562f'),
}
OW04_REPAIR_PINS = {
    'package.py': dict(bytes=5180, sha256='3ce662a23545936685d6cdbae22eea5c46d42542ed325d0e365dd0b73a5acc19'),
    'qualification.py': dict(bytes=13375, sha256='5ae299948b71ef2c96273c155fdf5607d2afa1ec8007c7acefa342bc651199df'),
    'test_qualification.py': dict(bytes=17760, sha256='1eb11d102284af1810431c964893132c5774ed7516a553a0d158fb222d5aeff8'),
}
TYPED_REPAIR_PINS = {'package.py': {'bytes': 10587, 'sha256': '2ddec2f38d54aac7919b349c20e1656a1bf252e71f411bbd3bc7ed8d213c8fba'}, 'qualification.py': {'bytes': 13482, 'sha256': 'ca3bd2b86356a9af2c4885795ddfa02cb17e7054d9484bec2b5d4752fc786adc'}, 'test_qualification.py': {'bytes': 23949, 'sha256': 'f1e8d67e32b6699f6c7f192ca4cd096a8285a7949842f4c3440aa31072b60c1a'}}
DEADLINE_REPAIR_PINS = {'browser_deadline.py': {'bytes': 1090, 'sha256': '49b5fa9493a2559bac578053406d4788190cd0c9112075fb95e4158140126817'}, 'browser_prepare.py': {'bytes': 7059, 'sha256': 'cecc0ffbd016652b45dab7804ea946814ec37648bd4f0c3e1d1753d207f96f16'}, 'browser_source.py': {'bytes': 1022, 'sha256': '8b1cbdeff4ca6ad7b0fd25b5ceebc44b3c0ed7c7f82b8f80e8c810e9c6dfc13e'}, 'browser.mjs': {'bytes': 23288, 'sha256': 'b5ecf79cffde7e17dfe2cba945fdf9b379dba54080fa29ce5fe6cf284c5a00b1'}, 'test_browser_deadline.py': {'bytes': 4992, 'sha256': '01a152f31cdf9f5f2fcf6b94b4faadf61fbd46c1b2e9138fc4ad8048f2cace89'}}
DEADLINE_REPAIR_METADATA = {'Native_operation_seconds_unchanged': 120, 'actual_ERP_case_credit': 0, 'cleanup_seconds': 5, 'first_failure_run': 42932723978, 'observed_exact_e8_CI_complete_source_seconds': 199, 'observed_exact_e8_local_cold_source_seconds': 226.135, 'source_assertions_unchanged': True, 'source_seconds': 360}
DEADLINE_REPAIR_DELTA = frozenset(SKU_AREA + name for name in ('SOURCE.json', *DEADLINE_REPAIR_PINS))
TYPED_REPAIR_DELTA = frozenset(SKU_AREA + name for name in ('SOURCE.json', *TYPED_REPAIR_PINS))
RECEIPT_REPAIR_DELTA = frozenset(SKU_AREA + name for name in ('SOURCE.json', *RECEIPT_REPAIR_PINS))
OW04_REPAIR_DELTA = frozenset(SKU_AREA + name for name in ('SOURCE.json', *OW04_REPAIR_PINS))
CHECKPOINT_TEMPLATE = 'sku-current-parent-money-automatic-native25-83.workflow.yml.txt'
CHECKPOINT_ADDED = frozenset(SKU_AREA + name for name in
                             ('checkpoint.py', 'test_checkpoint.py', CHECKPOINT_TEMPLATE))
CHECKPOINT_PINS = {
    ".github/workflows/cp7-sku-current-parent-money-automatic-native25.yml": {
        "bytes": 35683,
        "sha256": "6224946f5b183f673e7a3160ddb632a18e7be083af0e6bf2b103d6c3d2ebe84c"
    },
    "scripts/current-sku-automatic-composite-preparation/SOURCE.json": {
        "bytes": 58244,
        "sha256": "7adcebd35998d1fd6acb140bed31714c32edf2f25c6deeb9c72e0c514a345432"
    },
    "scripts/current-sku-automatic-composite-preparation/checkpoint.py": {
        "bytes": 6163,
        "sha256": "eaa6d0be747c09d0b3587b0879324818a958e42664b4296a9f3631960957895c"
    },
    "scripts/current-sku-automatic-composite-preparation/package.py": {
        "bytes": 10854,
        "sha256": "0f6aadf3a3f56a33db4999730fc545f6b786d1d84c5aacd7bf72a18eda892c95"
    },
    "scripts/current-sku-automatic-composite-preparation/qualification.py": {
        "bytes": 13627,
        "sha256": "45cf9612ee9ca0c41dde185c58c88942a550e59b1ab741c48d16308216c1fb16"
    },
    "scripts/current-sku-automatic-composite-preparation/sku-current-parent-money-automatic-native25-83.workflow.yml.txt": {
        "bytes": 35683,
        "sha256": "6224946f5b183f673e7a3160ddb632a18e7be083af0e6bf2b103d6c3d2ebe84c"
    },
    "scripts/current-sku-automatic-composite-preparation/test_checkpoint.py": {
        "bytes": 6193,
        "sha256": "a961a7f7ccd0a75a0c0b4545827a413ef7dd889612b88dd95dd4d970b3e5a52e"
    },
    "scripts/current-sku-automatic-composite-preparation/test_execution.py": {
        "bytes": 16549,
        "sha256": "259fb66d236ba71afcbd4bf7e6dd63daaf882386a2f4d5a29d0db77e25001d55"
    },
    "scripts/current-sku-automatic-composite-preparation/test_qualification.py": {
        "bytes": 24449,
        "sha256": "ed6dbfa2cf8327ef44b273abda436b3172b77cb52ec8bc94cf2081f94e80074c"
    },
    "scripts/current-sku-automatic-composite-preparation/workflow.py": {
        "bytes": 11392,
        "sha256": "c8b33243a9a3ad5e0e91226a3fc3fab96f7e03b6150b0ba3b276500b43d1b5f8"
    }
}
CHECKPOINT_DELTA = frozenset(CHECKPOINT_PINS)
SHA256 = re.compile('[a-f0-9]{64}')


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


_successor_raw = Path(__file__).with_name('REVIEWED_980C_SUCCESSORS.json').read_bytes()
require(pin(_successor_raw) == dict(bytes=9153, sha256='5b64bcf06ebe9def4703d911edc78e5ccc11353922f7903c71e67c8e9ed9cce5'),
        'SKU_REVIEWED_SUCCESSOR_SOURCE_PIN_CHANGED')
SUCCESSORS = strict(_successor_raw)
LINEAGE = ((PREPARED, PREPARED_TREE), (RECEIPT_FAILURE, RECEIPT_FAILURE_TREE),
           (OW04_FAILURE, OW04_FAILURE_TREE), (TYPED_FAILURE, TYPED_FAILURE_TREE),
           (COLD_SOURCE_FAILURE, COLD_SOURCE_FAILURE_TREE), (FAILED_SOURCE, FAILED_TREE),
           (CHECKPOINT_HEAD, CHECKPOINT_TREE), *((row['head'], row['tree']) for row in SUCCESSORS))
CANDIDATE, CANDIDATE_TREE = LINEAGE[-1]
IMMEDIATE_PARENT = LINEAGE[-2][0]
SUCCESSOR_PATHS = frozenset(name for row in SUCCESSORS for name in row['files'])
SUCCESSOR_ADDED = frozenset(name for row in SUCCESSORS for name, file in row['files'].items()
                            if file['status'] == 'added')
DELTA = (RECEIPT_REPAIR_DELTA | OW04_REPAIR_DELTA | TYPED_REPAIR_DELTA | DEADLINE_REPAIR_DELTA
         | CHECKPOINT_DELTA | SUCCESSOR_PATHS | {WORKFLOW, SKU_AREA + 'admission.py'})


def git(repo, *args):
    return subprocess.check_output(['git', '--no-lazy-fetch', '-C', str(repo), *args],
                                   env=dict(os.environ, GIT_NO_LAZY_FETCH='1'))


def changes(repo, before, after):
    rows = git(repo, 'diff', '--raw', '--no-abbrev', '--no-renames', '-z', before, after, '--').split(b'\0')
    require(rows.pop() == b'' and len(rows) % 2 == 0, 'SKU_COMPLETE_RAW_SOURCE_DIFF_REQUIRED')
    result = {}
    for header, path in zip(rows[::2], rows[1::2]):
        old_mode, new_mode, old, new, status = header.decode().lstrip(':').split()
        name = path.decode()
        require(name not in result, 'SKU_DUPLICATE_SOURCE_PATH')
        result[name] = dict(old_mode=old_mode, new_mode=new_mode, before=old, after=new, status=status)
    return result


def exact_checkout(repo, head):
    refs = [commit + '^{tree}' for commit, _ in LINEAGE]
    trees = [tree for _, tree in LINEAGE]
    require(head == CANDIDATE
            and git(repo, 'rev-parse', 'HEAD', *refs).decode().splitlines() == [CANDIDATE, *trees]
            and not git(repo, 'status', '--porcelain', '--untracked-files=no').strip(),
            'SKU_EXACT_REVIEWED_CANDIDATE_CLEAN_CHECKOUT_REQUIRED')
    for (previous, _), (commit, _) in zip(LINEAGE, LINEAGE[1:]):
        require(git(repo, 'rev-list', '--parents', '-n', '1', commit).decode().split() == [commit, previous],
                'SKU_EXACT_REVIEWED_CANDIDATE_CLEAN_CHECKOUT_REQUIRED')


def verify_cumulative_mandor(repo, head, raw):
    exact_checkout(repo, head)
    require(raw == git(repo, 'show', head+':'+PARENT)
            == git(repo, 'show', PREPARED+':'+PARENT),
            'SKU_IMMUTABLE_CUMULATIVE_MANDOR_BYTES_REQUIRED')
    here = Path(repo) / SKU_AREA
    path = here / 'cumulative_runtime.py'
    spec = importlib.util.spec_from_file_location('global_actual_SKU_cumulative_parent_replay', path)
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    money = Path(repo) / 'scripts/current-sku-money-composite-preparation/SKU_MONEY_PREPARED_SOURCE_INTAKE.json'
    decision = runtime.review_files(raw, money.read_bytes(), (here/'PREPARED_NATIVE25_PLAN.json').read_bytes())
    require(decision['mode'] == 'CUMULATIVE_15_PLUS_2'
            and decision['original_run']['conclusion'] == 'failure'
            and decision['paired_browser_run']['conclusion'] == 'success'
            and len(decision['cases']) == 17
            and decision['actual_SKU_cases'] == 0
            and decision['production_go'] is False,
            'SKU_EXPLICIT_CUMULATIVE_PARENT_REPLAY_REQUIRED')
    return dict(mode=decision['mode'], decision=pin((here/runtime.DECISION).read_bytes()),
                original_failed_run_preserved=True, parent_case_count=17,
                actual_new_SKU_cases=0, production_go=False)


def source_candidate(repo, head, mandor_raw):
    exact_checkout(repo, head)
    actual = changes(repo, PREPARED, head)
    added = CHECKPOINT_ADDED | SUCCESSOR_ADDED | {WORKFLOW}
    require(set(actual) == DELTA and all(row['new_mode'] == '100644'
            and row['status'] == ('A' if name in added else 'M')
            and row['old_mode'] == ('000000' if name in added else '100644')
            for name, row in actual.items()), 'SKU_ONLY_REVIEWED_ADOPTION_AND_REPAIR_PATHS_REQUIRED')
    show = lambda ref, name: git(repo, 'show', ref+':'+SKU_AREA+name)
    for before, after, delta, pins in (
        (RECEIPT_FAILURE, OW04_FAILURE, RECEIPT_REPAIR_DELTA, RECEIPT_REPAIR_PINS),
        (OW04_FAILURE, TYPED_FAILURE, OW04_REPAIR_DELTA, OW04_REPAIR_PINS),
        (TYPED_FAILURE, COLD_SOURCE_FAILURE, TYPED_REPAIR_DELTA, TYPED_REPAIR_PINS),
        (COLD_SOURCE_FAILURE, FAILED_SOURCE, DEADLINE_REPAIR_DELTA, DEADLINE_REPAIR_PINS),
    ):
        direct = changes(repo, before, after)
        require(set(direct) == delta and all(row['status'] == 'M' for row in direct.values()),
                'SKU_EXACT_OW04_FAILURE_TO_REPAIR_DELTA_REQUIRED')
        for name, expected in pins.items():
            require(pin(show(after, name)) == expected,
                    'SKU_EXACT_REVIEWED_REPAIR_BYTES_REQUIRED:' + name)
    for name, expected in (RECEIPT_REPAIR_PINS | OW04_REPAIR_PINS | TYPED_REPAIR_PINS | DEADLINE_REPAIR_PINS).items():
        require(pin(show(FAILED_SOURCE, name)) == expected, 'SKU_FINAL_REPAIR_BYTES_REQUIRED:' + name)
    direct = changes(repo, FAILED_SOURCE, CHECKPOINT_HEAD)
    require(set(direct) == CHECKPOINT_DELTA and all(row['new_mode'] == '100644'
            and row['status'] == ('A' if name in CHECKPOINT_ADDED else 'M')
            and row['old_mode'] == ('000000' if name in CHECKPOINT_ADDED else '100644')
            for name, row in direct.items()), 'SKU_EXACT_CHECKPOINT_SOURCE_DELTA_REQUIRED')
    for name, expected in CHECKPOINT_PINS.items():
        require(pin(git(repo, 'show', CHECKPOINT_HEAD+':'+name)) == expected,
                'SKU_EXACT_CHECKPOINT_BYTES_REQUIRED:' + name)
    for successor in SUCCESSORS:
        commit = successor['head']
        direct = changes(repo, successor['base'], commit)
        require(set(direct) == set(successor['files']), 'SKU_EXACT_SUCCESSOR_SOURCE_DELTA_REQUIRED')
        for path, file in successor['files'].items():
            is_addition = file['status'] == 'added'
            require(direct[path]['after'] == file['sha'] and direct[path]['new_mode'] == '100644'
                    and direct[path]['status'] == ('A' if is_addition else 'M')
                    and direct[path]['old_mode'] == ('000000' if is_addition else '100644')
                    and pin(git(repo, 'show', commit+':'+path)) == dict(bytes=file['bytes'], sha256=file['sha256']),
                    'SKU_EXACT_SUCCESSOR_SOURCE_BYTES_REQUIRED:' + path)
    decision = strict(show(PREPARED, 'CUMULATIVE_RUNTIME_BINDING.json'))
    expected_admission = show(PREPARED, 'admission.py').decode()
    for name, value in decision['bindings'].items():
        before = name+' = None'
        require(expected_admission.count(before) == 1, 'SKU_EXACT_CLOSED_GATE_PREIMAGE_REQUIRED')
        expected_admission = expected_admission.replace(before, name+' = '+repr(value), 1)
    require(show(head, 'admission.py') == expected_admission.encode(),
            'SKU_ONLY_EXACT_FIVE_GATE_VALUES_MAY_CHANGE')
    workflow = show(PREPARED, 'sku-current-parent-money-automatic-native25-81.workflow.yml.txt')
    require(git(repo, 'show', FAILED_SOURCE+':'+WORKFLOW) == workflow,
            'SKU_EXACT_REVIEWED_81_STEP_WORKFLOW_REQUIRED')
    checkpoint_workflow = show(CHECKPOINT_HEAD, CHECKPOINT_TEMPLATE)
    require(git(repo, 'show', CHECKPOINT_HEAD+':'+WORKFLOW) == checkpoint_workflow,
            'SKU_EXACT_ORIGINAL_CHECKPOINT_WORKFLOW_REQUIRED')
    current_workflow = show(head, CHECKPOINT_TEMPLATE)
    require(git(repo, 'show', head+':'+WORKFLOW) == current_workflow,
            'SKU_EXACT_REVIEWED_83_STEP_WORKFLOW_REQUIRED')
    expected_manifest = strict(show(PREPARED, 'SOURCE.json'))
    expected_manifest['files']['admission.py'] = pin(expected_admission.encode())
    expected_manifest.update(active_workflow_added=True, active_workflow_source=pin(workflow),
                             all_admission_values_unset=False, actual_parent_adopted=True,
                             cumulative_parent_adopted=True)
    for before, pins in ((RECEIPT_FAILURE, RECEIPT_REPAIR_PINS), (OW04_FAILURE, OW04_REPAIR_PINS),
                         (TYPED_FAILURE, TYPED_REPAIR_PINS), (COLD_SOURCE_FAILURE, DEADLINE_REPAIR_PINS)):
        require(strict(show(before, 'SOURCE.json')) == expected_manifest,
                'SKU_EXACT_FAILED_CANDIDATE_MANIFEST_REQUIRED')
        expected_manifest['files'].update(pins)
    expected_manifest['bounded_cold_source_deadline_repair'] = DEADLINE_REPAIR_METADATA
    require(strict(show(FAILED_SOURCE, 'SOURCE.json')) == expected_manifest,
            'SKU_EXACT_SHUTDOWN_CANDIDATE_MANIFEST_REQUIRED')
    expected_manifest['files'].update({name.removeprefix(SKU_AREA): value for name, value in CHECKPOINT_PINS.items()
                                       if name.startswith(SKU_AREA) and name != SKU_AREA + 'SOURCE.json'})
    expected_manifest.update(active_workflow_source=pin(checkpoint_workflow),
                             reviewable_workflow_steps=83)
    require(strict(show(CHECKPOINT_HEAD, 'SOURCE.json')) == expected_manifest,
            'SKU_ONLY_EXPLICIT_ADMISSION_MANIFEST_FIELDS_MAY_CHANGE')
    parent = verify_cumulative_mandor(repo, head, mandor_raw)
    subprocess.run([sys.executable, '-B', str(Path(repo) / SKU_AREA / 'workflow.py'), '--check'], cwd=repo,
                   env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', GIT_NO_LAZY_FETCH='1'),
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=120)
    # Run the actual byte-pinned checker, including its complete physical parent
    # and executable/untracked-input checks, before admitting this source.
    check = Path(repo) / SKU_AREA / 'check_source.py'
    result = subprocess.run([sys.executable, '-B', str(check), '--runtime'], cwd=repo,
                            env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', GIT_NO_LAZY_FETCH='1',
                                     GITHUB_SHA=head), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            check=True, timeout=120)
    proof = strict(result.stdout)
    require(proof['absent_sparse_parent_files'] == 0 and proof['actual_ERP_cases'] == 0
            and proof['active_workflow_added'] is True and proof['actual_runtime_adoption_pending'] is False,
            'SKU_COMPLETE_PHYSICAL_SOURCE_REQUIRED')
    return dict(head=head, tree=CANDIDATE_TREE, parents=[IMMEDIATE_PARENT], files=actual,
                parent=parent, complete_physical_source=True, actual_ERP_cases=0)


def load_reviewed(raw, digest):
    require(type(digest) is str and SHA256.fullmatch(digest) and sha256(raw).hexdigest() == digest,
            'SKU_REVIEWED_OWNING_MANIFEST_PIN_CHANGED')
    value = strict(raw)
    require(type(value) is dict and set(value) == {'head','tree','run_id','job_id','parents','files'}
            and value['head'] == CANDIDATE and value['tree'] == CANDIDATE_TREE
            and value['parents'] == [IMMEDIATE_PARENT] and type(value['files']) is dict
            and set(value['files']) == DELTA
            and all(type(value[k]) is int and value[k] > 0 for k in ('run_id','job_id')),
            'SKU_REAL_RUN_JOB_AND_EXACT_CANDIDATE_SOURCE_REQUIRED')
    return value


def verify_source(repo, head, reviewed, mandor_raw):
    proof = source_candidate(repo, head, mandor_raw)
    require(all(reviewed[key] == proof[key] for key in ('head','tree','parents','files')),
            'SKU_REVIEWED_OWNING_SOURCE_CHANGED')
    return proof['files']


def add_cli(parser):
    parser.add_argument('--reviewed-sku', type=Path, required=True)
    parser.add_argument('--reviewed-sku-sha256', required=True)


def from_cli(args):
    return load_reviewed(args.reviewed_sku.read_bytes(), args.reviewed_sku_sha256)
