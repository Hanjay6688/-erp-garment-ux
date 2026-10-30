"""Exact qualified parent sources and six immutable raw inputs, never a waiver."""
from pathlib import Path, PurePosixPath
from hashlib import sha256
import json
import os

HEAD = '3c0c5defe55e48cf6f221c868594dd6676d17170'
TREE = 'ca20c918201b455ad09df489829b83b9e6afea95'
RUN = 40983410165
JOB = 123828634300
ARTIFACT = 12947563874
ARCHIVE = dict(bytes=8472775, sha256='567e64545493d4806fa613b1306b4fe8c2f70a2ebb327fc60b709737813e5a60')
ROOT_RECEIPT = dict(bytes=6012, sha256='9f0270cf44291ae7cd4b16bddf3fc258e9faf8cdac5a4ab619b3044f81ac66c8')
SOURCE = 'scripts/current-s03-lawful-fixture-successor-qualification/SOURCE.json'
SOURCE_PIN = dict(bytes=106705, sha256='ba59dee4ae71c62df2b2e35c558cb23a7c66254a974c554cc3d17d63b936c555')
PREFIX = 'cp6-proof/t3/S03_PARENT14_ORIGINALS/'
RECEIPT = PREFIX + 'INPUT_RECEIPT.json'
WF = '.github/workflows/cp7-current-s03-browser4-lawful.yml'
BOOTSTRAP = 'scripts/cp7_attendance_period_choice/__init__.py'
BOOTSTRAP_PIN = dict(bytes=75, sha256='7078a6a88cf48a6fc9f9de2a06c7367b3b264613682d9cdbb6dce37fe18f34ea')


def regular(root, name):
    rel = PurePosixPath(name)
    if rel.is_absolute() or str(rel) != name or '..' in rel.parts or '\\' in name:
        raise ValueError('S03_BOUND_UNSAFE_INPUT:' + name)
    path = Path(root)
    for part in rel.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError('S03_BOUND_INPUT_SYMLINK:' + name)
    if not path.is_file():
        raise ValueError('S03_BOUND_REGULAR_INPUT_REQUIRED:' + name)
    return path


def pin(path):
    digest = sha256(); size = 0
    with path.open('rb') as stream:
        for raw in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(raw); size += len(raw)
    return dict(bytes=size, sha256=digest.hexdigest())


def exact(root, name, expected):
    path = regular(root, name)
    if pin(path) != expected:
        raise ValueError('S03_BOUND_EXACT_INPUT_BYTES_REQUIRED:' + name)
    return path


def root_receipt(root, here):
    path = str((here / 'accepted-parent14/ROOT_QUALIFIED_COMPONENT.json').relative_to(root))
    value = json.loads(exact(root, path, ROOT_RECEIPT).read_bytes())
    if (value['head'] != HEAD or value['tree'] != TREE or value['run_id'] != RUN
            or value['job_id'] != JOB or value['artifact_id'] != ARTIFACT
            or value['status'] != 'QUALIFIED_NARROW_ACTUAL_NATIVE11_THEN3_FULL_RESTORE_ALL5'):
        raise ValueError('S03_BOUND_EXACT_ROOT_QUALIFIED14_RECEIPT_REQUIRED')
    return value


def static(root, here, config):
    root, here = Path(root), Path(here)
    receipt = root_receipt(root, here); binding = config['backend_binding']
    if (binding['qualifying_commit'] != HEAD or binding['qualifying_tree'] != TREE
            or binding['run_id'] != RUN or binding['job_id'] != JOB
            or binding['artifact_id'] != ARTIFACT or binding['actual_case_count'] != 14
            or binding['runtime_files'] != receipt['runtime7_Git_pins']):
        raise ValueError('S03_BOUND_EXACT_QUALIFIED_RUN_RUNTIME_REQUIRED')
    source = json.loads(exact(root, SOURCE, SOURCE_PIN).read_bytes())
    if len(source['files']) != 475 or source['files'] != binding['full_current_qualifier_source_files']:
        raise ValueError('S03_BOUND_COMPLETE475_CANONICAL_MAP_REQUIRED')
    physical = json.loads((here / 'QUALIFIED_SOURCE_INPUTS.json').read_bytes())
    if (physical['commit'] != HEAD or physical['tree'] != TREE or set(physical['files']) != set(source['files'])
            or physical['manifest'] != dict(path=SOURCE, **SOURCE_PIN)):
        raise ValueError('S03_BOUND_COMPLETE475_PHYSICAL_ROUTES_REQUIRED')
    retained = 0
    for canonical, expected in source['files'].items():
        route = physical['files'][canonical]
        if {key: route[key] for key in ('bytes', 'sha256')} != expected:
            raise ValueError('S03_BOUND_PHYSICAL_ROUTE_PIN_CHANGED:' + canonical)
        target = route['physical_path']
        if route['kind'] == 'CANONICAL_REGULAR_ACCEPTED_BYTES':
            if target != canonical:
                raise ValueError('S03_BOUND_CANONICAL_ROUTE_REQUIRED:' + canonical)
        elif route['kind'] == 'PROOF_ONLY_NOT_IMPORTED_AS_EXECUTING_BACKEND':
            if (target != str(here.relative_to(root)) + '/qualified-parent3c0/' + canonical
                    or canonical in binding['runtime_files'] or canonical == BOOTSTRAP):
                raise ValueError('S03_BOUND_PROOF_COPY_CANNOT_EXECUTE_AS_RUNTIME:' + canonical)
            retained += 1
        else:
            raise ValueError('S03_BOUND_UNKNOWN_SOURCE_ROUTE_KIND')
        exact(root, target, expected)
    if retained != 214:
        raise ValueError('S03_BOUND_EXACT214_RETAINED_PROOF_INPUTS_REQUIRED')
    for name, digest in receipt['runtime7_Git_pins'].items():
        if pin(regular(root, name))['sha256'] != digest:
            raise ValueError('S03_BOUND_CANONICAL_EXECUTING_RUNTIME_CHANGED:' + name)
    exact(root, BOOTSTRAP, BOOTSTRAP_PIN)
    raw = {row['path']: dict(bytes=row['bytes'], sha256=row['sha256']) for row in receipt['accepted_six_originals']}
    if len(raw) != 6 or not isinstance(config['accepted_originals'], dict) or len(config['accepted_originals']) != 6:
        raise ValueError('S03_BOUND_EXACT_SIX_RAW_DESCRIPTORS_REQUIRED')
    described = {}
    for row in config['accepted_originals'].values():
        name = row['path']
        if not name.startswith(PREFIX) or row.get('encoding') != 'raw':
            raise ValueError('S03_BOUND_RAW_INPUT_ROUTE_REQUIRED')
        leaf = name[len(PREFIX):]
        if leaf not in raw or dict(bytes=row['raw_bytes'], sha256=row['raw_sha256']) != raw[leaf]:
            raise ValueError('S03_BOUND_ROOT_RAW_DESCRIPTOR_CHANGED:' + name)
        described[name] = raw[leaf]
    if len(described) != 6:
        raise ValueError('S03_BOUND_SIX_DISTINCT_RAW_INPUTS_REQUIRED')
    return receipt, described


def producer_pins(root, here):
    names = [str((here / name).relative_to(root)) for name in ('fetch_originals.py', 'accepted_inputs.py', 'CONFIG.json')]
    return {name: pin(regular(root, name)) for name in [*names, WF]}


def input_receipt(root, here, acquisition):
    receipt, raw = static(root, here, json.loads((here / 'CONFIG.json').read_bytes()))
    if acquisition not in ('IMMUTABLE_GITHUB_ARTIFACT', 'ROOT_VERIFIED_LOCAL_REPLAY_NO_GET'):
        raise ValueError('S03_BOUND_DECLARED_ACQUISITION_REQUIRED')
    return dict(contract='cp7.s03-browser4.exact-six-Original-inputs.v1',
        status='IMMUTABLE_ARCHIVE_AND_SIX_RAW_BYTES_VERIFIED', acquisition=acquisition,
        head=HEAD, tree=TREE, run_id=RUN, job_id=JOB, artifact_id=ARTIFACT,
        archive=ARCHIVE, source475=SOURCE_PIN, raw_files=raw,
        producer_files=producer_pins(root, here), new_Native_Auth_browser_credit=0)


def present(root, here, config, *, required=False):
    _, expected = static(root, here, config)
    folder = Path(root) / PREFIX
    found = {str(path.relative_to(root)) for path in folder.rglob('*') if path.is_file() or path.is_symlink()} if folder.exists() else set()
    if folder.is_symlink():
        raise ValueError('S03_BOUND_INPUT_SYMLINK:' + PREFIX.rstrip('/'))
    if not found:
        if required:
            raise ValueError('S03_BOUND_SIX_ACTUAL_ORIGINALS_NOT_MATERIALIZED')
        return set(), dict(status='EXACT_METADATA_ONLY_SIX_RAW_INPUTS_ABSENT', actual_originals_admitted=False)
    if found != set(expected) | {RECEIPT}:
        raise ValueError('S03_BOUND_PARTIAL_MIXED_OR_UNKNOWN_RAW_INPUTS:' + repr(sorted(found ^ (set(expected) | {RECEIPT}))))
    for name, expected_pin in expected.items():
        exact(root, name, expected_pin)
    record = json.loads(regular(root, RECEIPT).read_bytes())
    if record != input_receipt(root, here, record.get('acquisition')):
        raise ValueError('S03_BOUND_INPUT_STAGE_OR_PRODUCER_CHANGED')
    if os.environ.get('GITHUB_ACTIONS') == 'true' and record['acquisition'] != 'IMMUTABLE_GITHUB_ARTIFACT':
        raise ValueError('S03_BOUND_CI_REQUIRES_IMMUTABLE_ARTIFACT_GET')
    return found, dict(status='SIX_EXACT_ACTUAL_ORIGINAL_BYTES_AND_PRODUCER_PRESENT',
        raw_Originals=6, acquisition=record['acquisition'], new_Native_Auth_browser_credit=0)


def actual_identity(documents, binding):
    package = documents['package']; report = documents['report']; case = report['committed']['S03_ATTENDANCE_NATIVE14_AND_USED_INVERSE']
    identity = package['run_identity']
    if (identity['tool_head'] != HEAD or identity['github_sha'] != HEAD or identity['run_id'] != str(RUN)
            or identity['run_attempt'] != '1' or identity['job'] != 'p21' or identity['mode'] != 'install'
            or identity['workflow'] != 'CP7 A S03 lawful fixture successor Native11 then Reader3'
            or package['auth_users_before'] != 0 or package['auth_users_after'] != 0
            or package['primary_unchanged'] is not True or package['backup_restore_drill'] != 'RESTORED_IDENTICAL'):
        raise ValueError('S03_BOUND_ACTUAL_PARENT_PACKAGE_RUN_AUTH_IDENTITY_REQUIRED')
    capture = case['actual_installed_capture']
    if (len(capture['originals']) != 15 or len(capture['definitions']) != 15 or len(capture['clones']) != 2
            or len(capture['actual_all22']) != 22 or capture['source_derived_local_ABI_used'] is not False
            or case['both_groups_same_actual_installation'] is not True
            or case['reader3_requires_actual_fresh_original11'] is not True
            or case['combined_strict14_fabricated'] is not False
            or case['original_accrual_and_source_binding_unchanged'] is not True
            or not case['committed_choice_and_allocation'] or not case['independent_Native_pool_oracle']):
        raise ValueError('S03_BOUND_ACTUAL15_PLUS2_AND_COMMITTED_SOURCE_LINEAGE_REQUIRED')
    if (report['baseline_role_cleanup']['baseline_roles_exact'] is not True
            or not report['restore_components'] or not all(value is True for value in report['restore_components'].values())):
        raise ValueError('S03_BOUND_COMPLETE_ACTUAL_RESTORE_ROLES_REQUIRED')
