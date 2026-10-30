"""Closed generated OUTPUT admission; never a source, DB or financial oracle.

Namespace-independent ABI: admit(root, here, names) -> (path pins, classification).
The caller still rejects every unaccepted untracked name. No output is executed.
"""
from datetime import datetime
from hashlib import sha256
from pathlib import Path, PurePosixPath
import json
import re
import subprocess

PREFIX = 'cp6-proof/t3/'


def _object(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, 'GENERATED_DUPLICATE_JSON_KEY'
        result[key] = value
    return result


def safe_file(root, name):
    rel = PurePosixPath(name)
    assert not rel.is_absolute() and '..' not in rel.parts and str(rel) == name
    root = Path(root).resolve()
    path = root
    for part in rel.parts:
        path = path / part
        assert not path.is_symlink(), 'GENERATED_OUTPUT_SYMLINK:' + name
    assert path.resolve().is_relative_to(root), 'GENERATED_OUTPUT_ESCAPE:' + name
    assert path.is_file(), 'GENERATED_OUTPUT_NOT_REGULAR:' + name
    return path


def raw_file(root, name, maximum=64_000_000):
    path = safe_file(root, name)
    assert path.stat().st_size <= maximum, 'GENERATED_OUTPUT_TOO_LARGE:' + name
    return path.read_bytes()


def json_file(root, name):
    return json.loads(raw_file(root, name, 4_000_000), object_pairs_hook=_object,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('GENERATED_NONFINITE_JSON:' + value)))


def same(left, right):
    """JSON booleans must not compare equal to integer0/1 in source metadata."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(same(left[key],right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(same(a,b) for a,b in zip(left,right))
    return left == right


def _kv(raw):
    result = {}
    for line in raw.decode('utf-8').splitlines():
        key, sep, value = line.partition('=')
        assert sep and key not in result, 'GENERATED_BAD_KEY_VALUE_RECEIPT'
        result[key] = value
    return result


def _sha(value):
    return isinstance(value, str) and re.fullmatch('[a-f0-9]{64}', value) is not None


def _integer(value):
    return type(value) is int


def _stamp(value):
    at = datetime.fromisoformat(value)
    assert at.tzinfo is not None and at.utcoffset().total_seconds() == 0


def _head(root):
    return subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()


def _startup(root, names):
    folder = PREFIX + 'disposable-startup-attempts/'
    selected = {name for name in names if name.startswith(folder)}
    if not selected:
        return set()
    receipt_name = folder + 'STARTUP_ATTEMPTS.json'
    data = json_file(root, receipt_name)
    assert set(data) == {'status','scope','maximum_attempts','image_tags_changed','ERP_tests_retried','attempts'}
    assert data['status'] == 'PASS' and data['scope'] == 'DISPOSABLE_STARTUP_BEFORE_ERP_TESTS'
    assert data['maximum_attempts'] == 4 and data['image_tags_changed'] is False and data['ERP_tests_retried'] is False
    attempts = data['attempts']
    assert isinstance(attempts, list) and 1 <= len(attempts) <= 4
    accepted = {receipt_name}
    for number, attempt in enumerate(attempts, 1):
        final = number == len(attempts)
        assert set(attempt) == ({'number','registry','status','started_at_utc','start'} if final else {'number','registry','status','started_at_utc','start','stop'})
        assert type(attempt['number']) is int and attempt['number'] == number
        assert attempt['registry'] == ('public.ecr.aws' if number == 2 else 'default_ghcr')
        assert attempt['status'] == ('PASS' if final else 'FAILED')
        _stamp(attempt['started_at_utc'])
        for operation in ('start',) if final else ('start','stop'):
            row = attempt[operation]
            assert set(row) == {'exit_code','log','bytes','sha256'}
            assert _integer(row['exit_code']) and _integer(row['bytes']) and row['bytes'] >= 0 and _sha(row['sha256'])
            assert row['log'] == 'attempt-' + str(number) + '-' + operation + '.log'
            if operation == 'start':
                assert (row['exit_code'] == 0) is final
            name = folder + row['log']
            raw = raw_file(root, name)
            assert len(raw) == row['bytes'] and sha256(raw).hexdigest() == row['sha256'], 'GENERATED_STARTUP_LOG_CHANGED'
            accepted.add(name)
    assert selected == accepted, 'GENERATED_UNKNOWN_STARTUP_OUTPUT'
    return accepted


def _aligned(root, contract, names):
    name = PREFIX + 'ALIGNED_CHAIN.json'
    if name not in names:
        return set()
    actual = json_file(root, name)
    # Fixed AB bootstrap/workflow and its reported per-object alignment are
    # unchanged inputs. This is output provenance, not a new hosted/DB proof.
    assert same(actual,contract['aligned_document']), 'GENERATED_AB_ALIGNMENT_PROVENANCE_CHANGED'
    return {name}


def _clone(root, contract, names):
    prefix = PREFIX + 'CLONE_install'
    required = {prefix + suffix for suffix in ('.txt','.connection-fence.txt','.database-identity.txt','.source-erp.sql','.clone-erp.sql')}
    if not (required & set(names)):
        return set()
    assert required <= set(names), 'GENERATED_PARTIAL_CLONE_OUTPUTS'
    evidence = _kv(raw_file(root, prefix + '.txt', 16_000))
    assert set(evidence) == {'source_pg_cron','clone_pg_cron','erp_dump_sha256','erp_dump_bytes','erp_schema_owners_grants_sequences_rows','database_owner_acl_connectivity','public_schema_owner_acl_role_privileges','status'}
    assert evidence['source_pg_cron'] == evidence['clone_pg_cron'] == '1' and evidence['status'] == 'PASS'
    assert all(evidence[key] == 'IDENTICAL' for key in ('erp_schema_owners_grants_sequences_rows','database_owner_acl_connectivity','public_schema_owner_acl_role_privileges'))
    assert evidence['erp_dump_bytes'].isdigit() and _sha(evidence['erp_dump_sha256'])
    source = raw_file(root, prefix + '.source-erp.sql')
    clone = raw_file(root, prefix + '.clone-erp.sql')
    assert source == clone and len(source) == int(evidence['erp_dump_bytes']) and sha256(source).hexdigest() == evidence['erp_dump_sha256'], 'GENERATED_CLONE_DIAGNOSTIC_BYTES_CHANGED'
    assert b'\x00' not in source and b'\\restrict CP6CloneBoundary20260904' in source and b'\\unrestrict CP6CloneBoundary20260904' in source
    identity = _kv(raw_file(root, prefix + '.database-identity.txt', 32_000))
    assert set(identity) == {'source_database_identity','clone_database_identity','source_public_schema_identity','clone_public_schema_identity'}
    for kind in ('database_identity','public_schema_identity'):
        left = json.loads(identity['source_' + kind], object_pairs_hook=_object)
        right = json.loads(identity['clone_' + kind], object_pairs_hook=_object)
        assert same(left,right) and same(left,contract['clone_identity'][kind]), 'GENERATED_CLONE_IDENTITY_CHANGED'
    fence = _kv(raw_file(root, prefix + '.connection-fence.txt', 16_000))
    fixed = contract['clone_fence_fixed']
    assert set(fence) == set(fixed) | {'terminated_source_connections'}
    assert all(fence[key] == value for key, value in fixed.items())
    assert fence['terminated_source_connections'].isdigit()
    return required


def _package(root, contract, names):
    files_name, package_name = (PREFIX + n for n in ('T3_PACKAGE_FILES_INSTALL.json','T3_PACKAGE_INSTALL.json'))
    if not ({files_name,package_name} & set(names)):
        return set()
    assert {files_name,package_name} <= set(names), 'GENERATED_PARTIAL_PACKAGE_OUTPUTS'
    files = json_file(root, files_name)
    assert same(files,contract['package_files_document']), 'GENERATED_PACKAGE_FILE_PROVENANCE_CHANGED'
    package = json_file(root, package_name)
    assert set(package) <= set(contract['package_allowed_keys'])
    assert package['label'] == 'T3_PREP' and package['mode'] == 'install'
    assert package['status'] in ('INCOMPLETE','ALL_STAGES_INSTALLED')
    assert package['production_go'] is False and package['release_evidence'] is False
    assert same(package['stages'],contract['package_stages']), 'GENERATED_PACKAGE_STAGE_SOURCE_CHANGED'
    identity = package['run_identity']
    assert set(identity) == set(contract['package_run_identity_keys'])
    for key,value in contract['package_run_identity_static'].items():
        assert same(identity[key],value)
    head = _head(root)
    assert identity['tool_head'] == identity['github_sha'] == head, 'GENERATED_PACKAGE_TOOL_HEAD_CHANGED'
    assert set(contract['package_allowed_events']) <= {'push','workflow_dispatch'} and contract['package_allowed_events']
    assert identity['event'] in contract['package_allowed_events'] and identity['job'] == 'p21'
    assert identity['workflow'] == contract['package_workflow_name']
    assert isinstance(identity['run_id'],str) and identity['run_id'].isdigit()
    assert isinstance(identity['run_attempt'],str) and identity['run_attempt'].isdigit() and int(identity['run_attempt']) > 0
    # An in-progress report intentionally has no writer_runtime/final gate.
    # Their later values do not turn this source-output allowance into PASS.
    return {files_name,package_name}


def admit(root, here, names):
    root, here, names = Path(root), Path(here), set(names)
    contract = json.loads((here / 'LATER_GENERATED_RECEIPTS.json').read_bytes(), object_pairs_hook=_object)
    assert contract['contract'] == 'CLOSED_GENERATED_LATER_OUTPUTS_V1'
    for name,pin in contract['producer_files'].items():
        raw = safe_file(root,name).read_bytes()
        assert len(raw) == pin['bytes'] and sha256(raw).hexdigest() == pin['sha256'], 'GENERATED_PRODUCER_SOURCE_CHANGED:' + name
    groups = dict(startup=_startup(root,names), aligned=_aligned(root,contract,names),
                  clone=_clone(root,contract,names), package=_package(root,contract,names))
    accepted = set().union(*groups.values())
    assert accepted <= names
    pins = {}
    for name in sorted(accepted):
        value = raw_file(root,name)
        pins[name] = dict(bytes=len(value),sha256=sha256(value).hexdigest())
    return pins, dict(status='GENERATED_OUTPUT_PROVENANCE_ONLY_NOT_NATIVE_PASS',
        classes={key:len(value) for key,value in groups.items()}, accepted=len(pins),
        SQL_diagnostics_executed=False, financial_oracles_changed=False, actual_Native_credit=0)
