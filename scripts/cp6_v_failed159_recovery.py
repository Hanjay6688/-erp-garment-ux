#!/usr/bin/env python3
"""Recover the pinned failed run and replay its binding predicates, without a DB.

The original raw ZIP is checked before extraction. Recovered data is explicitly
FAILED-RUN evidence, never a successful runtime manifest or a replacement CI run.
"""
import ast
import hashlib
import json
import lzma
import os
import subprocess
import sys
import tarfile
import textwrap
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from unittest.mock import patch

HEAD = '1a1a6b9dd3f572cb9aa23b4bbd6ab92e7a597e2a'
TREE = 'fb4690cd7e84e477e5947c6f2f0ab73bd5961d51'
RUN = 34763643963
ARTIFACT = 10320611163
RAW_BYTES = 643619414
RAW_SHA = 'f9f10a20720f9661d0413d69b09007ba29dc97a6528d099f6635182e6ccf3b4e'
WORKFLOW = '.github/workflows/cp6-full-schema-validation.yml'
SEMANTIC_HEAD = '7be634e663a61545b909cf0367d12461ae7aa798'
SEMANTIC_TREE = 'a29235ba5386cc905cb4fb9ee784e16db4a5ce7a'
SEMANTIC_WORKFLOW_SHA = '848d7bfc1eae21a05442b971068a7994fd088b2477af8a3f9f1703f6c7d2b1cf'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def binder(workflow):
    step = workflow.split('      - name: Bind successful CP6 proof to the exact runtime SHA\n', 1)[1]
    source = step.split("          python - <<'PY'\n", 1)[1].split('\n          PY', 1)[0]
    return textwrap.dedent(source)


def exact_cash_equal(expected, actual):
    left, right = Decimal(expected), Decimal(actual)
    return left.is_finite() and right.is_finite() and left == right


def semantic_prefix(source):
    tree = ast.parse(source)
    stop = next(i for i, node in enumerate(tree.body) if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == 'source_paths' for t in node.targets))
    return ast.Module(body=tree.body[:stop], type_ignores=[])


def corrected_historical_binder():
    """The corrected V contract is immutable; successors must not rewrite history."""
    tree = subprocess.check_output(['git', 'rev-parse', SEMANTIC_HEAD + '^{tree}'], text=True).strip()
    source = subprocess.check_output(['git', 'show', SEMANTIC_HEAD + ':' + WORKFLOW])
    if tree != SEMANTIC_TREE or hashlib.sha256(source).hexdigest() != SEMANTIC_WORKFLOW_SHA:
        raise ValueError('FAILED159_CORRECTED_CONTRACT_IDENTITY_MISMATCH')
    return binder(source.decode('utf8'))


def unit():
    source = binder(Path(WORKFLOW).read_text())
    function = next(n for n in ast.parse(source).body
        if isinstance(n, ast.FunctionDef) and n.name == 'cash_delta_equal')
    namespace = dict(Decimal=Decimal, InvalidOperation=InvalidOperation)
    exec(compile(ast.Module(body=[function], type_ignores=[]), '<actual-cash-predicate>', 'exec'), namespace)
    compare = namespace['cash_delta_equal']
    valid = [('0', '0.0'), ('0', '0.00'), ('-0.00', '0'), ('0.03', '.030'),
        ('-0.03', '-.0300'), ('1.01', '1.010'),
        ('9007199254740993.01', '9007199254740993.010'), ('0.01', '1e-2')]
    invalid = [('0', '0.01'), ('0', '-0.01'), ('0.03', '0.030000000001'),
        ('-0.03', '0.03'), ('9007199254740993.01', '9007199254740993.02'),
        ('NaN', 'NaN'), ('Infinity', 'Infinity'), ('0', 'invalid'), ('0', 0.0), (None, '0')]
    for left, right in valid:
        if not compare(left, right):
            raise AssertionError('CASH_PREDICATE_REJECTED_EQUAL_FINITE_DECIMALS')
    for left, right in invalid:
        if compare(left, right):
            raise AssertionError('CASH_PREDICATE_ACCEPTED_INVALID_OR_UNEQUAL_VALUE')
    if valid[0][0] == valid[0][1]:
        raise AssertionError('FROZEN_RAW_STRING_NEGATIVE_CONTROL_NOT_QUALIFIED')
    print(json.dumps(dict(status='PASS', classification='EXACT_WORKFLOW_CASH_PREDICATE_UNIT',
        completed_case_count=len(valid) + len(invalid), valid_cases=len(valid), rejection_cases=len(invalid),
        frozen_string_negative_control_rejected=True, tolerance=0, rounding_applied=False)))


def replay(old_source, proof):
    namespace = {'__name__': '__failed159_replay__'}
    expected_error = None
    try:
        exec(compile(semantic_prefix(old_source), '<frozen159-bind>', 'exec'), namespace)
    except AssertionError as exc:
        trace = exc.__traceback__
        while trace.tb_next:
            trace = trace.tb_next
        expected_error = {'type': type(exc).__name__, 'line': trace.tb_lineno}
    if expected_error != {'type': 'AssertionError', 'line': 587}:
        raise AssertionError('FAILED159_ORIGINAL_PREDICATE_NOT_REPRODUCED:' + str(expected_error))
    core = json.loads((proof / 'CP6_V2620V_MISC_FINANCE_BUSINESS_DATE_REGRESSION.json').read_text())
    races = json.loads((proof / 'V_MISC_FINANCE_NATIVE_RACES/manifest.json').read_text())
    pairs = []
    for name, case in core['cases'].items():
        for day, row in case['daily_evidence'].items():
            pairs.append(dict(kind='CORE', case=name, day=day,
                expected=row['expected_cash_delta'], actual=row['actual_cash_delta']))
    for case in races['cases']:
        for day, row in case['per_date_cash'].items():
            pairs.append(dict(kind='RACE', case=case['case'], day=day,
                expected=row['expected'], actual=row['actual']))
    for pair in pairs:
        pair['raw_string_equal'] = pair['expected'] == pair['actual']
        pair['finite_decimal_equal'] = exact_cash_equal(pair['expected'], pair['actual'])
    if not all(p['finite_decimal_equal'] for p in pairs):
        raise AssertionError('FAILED159_REAL_CASH_DISCREPANCY')
    if sum(not p['raw_string_equal'] for p in pairs if p['kind'] == 'CORE') != 8:
        raise AssertionError('FAILED159_CORE_ZERO_SCALE_REPRODUCTION_COUNT')
    return expected_error, pairs


def main():
    if sys.argv[1:] == ['--unit']:
        unit()
        return
    if len(sys.argv) != 3:
        raise SystemExit('usage: cp6_v_failed159_recovery.py RAW_ZIP OUTPUT_DIRECTORY')
    raw, output = map(lambda s: Path(s).resolve(), sys.argv[1:])
    if raw.is_symlink() or not raw.is_file() or output.exists():
        raise ValueError('FAILED159_INVALID_INPUT_OR_EXISTING_OUTPUT')
    if raw.stat().st_size != RAW_BYTES or digest(raw) != RAW_SHA:
        raise ValueError('FAILED159_ORIGINAL_ZIP_IDENTITY_MISMATCH')
    repo = Path.cwd()
    git = lambda *args: subprocess.check_output(['git', *args], text=True).strip()
    if git('rev-parse', HEAD + '^{tree}') != TREE:
        raise ValueError('FAILED159_SOURCE_TREE_MISMATCH')
    recovery_head, recovery_tree = git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')
    if recovery_head != os.environ['GITHUB_SHA']:
        raise ValueError('FAILED159_RECOVERY_CHECKOUT_MISMATCH')
    old_source = binder(git('show', HEAD + ':' + WORKFLOW))
    new_source = corrected_historical_binder()
    # The exact old gate must fail; the pinned corrected V semantic assertions
    # must all pass against the same frozen native inputs. Neither prefix writes
    # a runtime manifest, changes proof files, or runs a database command.
    worktree = output.parent / 'cp6-failed159-frozen-source'
    if worktree.exists():
        raise ValueError('FAILED159_WORKTREE_ALREADY_EXISTS')
    subprocess.run(['git', 'worktree', 'add', '--detach', str(worktree), HEAD], check=True)
    output.mkdir(parents=True)
    proof = worktree / 'cp6-proof'
    proof.mkdir()
    files = {}
    try:
        with zipfile.ZipFile(raw) as archive:
            entries = archive.infolist()
            if len({e.filename for e in entries}) != len(entries):
                raise ValueError('FAILED159_DUPLICATE_ZIP_PATH')
            for entry in entries:
                logical = PurePosixPath(entry.filename)
                if (logical.is_absolute() or '..' in logical.parts or '\\' in entry.filename
                        or any(part.startswith('.') for part in logical.parts)
                        or ((entry.external_attr >> 16) & 0o170000) == 0o120000):
                    raise ValueError('FAILED159_UNSAFE_ZIP_PATH')
                if entry.is_dir():
                    continue
                target = proof / entry.filename
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(entry) as source, target.open('wb') as dest:
                    while block := source.read(1048576):
                        dest.write(block)
                if target.stat().st_size != entry.file_size:
                    raise ValueError('FAILED159_TRUNCATED_PAYLOAD')
                files[entry.filename] = dict(bytes=entry.file_size, sha256=digest(target))
        if (proof / 'CP6_V2620V_RUNTIME_MANIFEST.json').exists():
            raise ValueError('FAILED159_UNEXPECTED_SUCCESS_MANIFEST')
        # A prefix only reads proof. Source pin material is separately checked
        # against the immutable frozen commit rather than the recovery checkout.
        with patch.dict(os.environ, {'GITHUB_SHA': HEAD}):
            os.chdir(worktree)
            failure, pairs = replay(old_source, proof)
            semantic_error = None
            try:
                exec(compile(semantic_prefix(new_source), '<corrected-cash-bind>', 'exec'),
                    {'__name__': '__read_only_failed159_semantic_check__'})
            except Exception as exc:
                trace = exc.__traceback__
                while trace.tb_next:
                    trace = trace.tb_next
                semantic_error = dict(type=type(exc).__name__, line=trace.tb_lineno, message=str(exc))
            os.chdir(repo)
        for name, expected in files.items():
            if digest(proof / name) != expected['sha256']:
                raise AssertionError('FAILED159_REPLAY_MUTATED_INPUT:' + name)
        path_node = next(node for node in ast.parse(old_source).body if isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == 'source_paths' for t in node.targets))
        source_pins = {}
        for name in ast.literal_eval(path_node.value):
            content = subprocess.check_output(['git', 'show', HEAD + ':' + name])
            source_pins[name] = dict(bytes=len(content), sha256=hashlib.sha256(content).hexdigest())
        archive_path = output / 'CP6_FAILED159_PROOF.tar.xz'
        filters = [{'id': lzma.FILTER_LZMA2, 'preset': 1, 'dict_size': 16 * 1024 * 1024}]
        with lzma.open(archive_path, 'wb', filters=filters) as compressed, \
                tarfile.open(fileobj=compressed, mode='w', format=tarfile.PAX_FORMAT) as tar:
            for name in sorted(files):
                path = proof / name
                info = tar.gettarinfo(str(path), arcname=name)
                info.uid = info.gid = info.mtime = 0
                info.uname = info.gname = ''
                info.mode = 0o644
                with path.open('rb') as stream:
                    tar.addfile(info, stream)
        if archive_path.stat().st_size > 500 * 1024 * 1024:
            raise ValueError('FAILED159_RECOVERY_EXCEEDS_TRANSFER_LIMIT')
        report = dict(status='RECOVERED_FAILED_RUN_NOT_ACCEPTANCE', production_go=False,
            format='CP6_FAILED159_LOSSLESS_RECOVERY_V1', source_failed_run=RUN,
            source_failed_head=HEAD, source_failed_tree=TREE, source_artifact_id=ARTIFACT,
            source_zip_bytes=RAW_BYTES, source_zip_sha256=RAW_SHA, source_zip_verified=True,
            recovery_head=recovery_head, recovery_tree=recovery_tree,
            corrected_contract_head=SEMANTIC_HEAD, corrected_contract_tree=SEMANTIC_TREE,
            corrected_contract_workflow_sha256=SEMANTIC_WORKFLOW_SHA,
            recovery_run=int(os.environ['GITHUB_RUN_ID']), original_failure=failure,
            numeric_operands=pairs, all_existing_semantic_assertions_after_numeric_fix_pass=semantic_error is None,
            corrected_semantic_error=semantic_error,
            all_recovered_payload_bytes_unchanged=True, success_runtime_manifest_created=False,
            files=files, source_pins=source_pins,
            archive=dict(name=archive_path.name, bytes=archive_path.stat().st_size,
                sha256=digest(archive_path)))
        (output / 'CP6_FAILED159_RECOVERY.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({k: report[k] for k in ('status', 'source_zip_verified', 'original_failure',
            'all_existing_semantic_assertions_after_numeric_fix_pass', 'archive')}, default=str))
        if semantic_error is not None:
            raise AssertionError('FAILED159_CORRECTED_SEMANTIC_REPLAY_REFUSED:' + str(semantic_error))
    finally:
        os.chdir(repo)
        subprocess.run(['git', 'worktree', 'remove', '--force', str(worktree)], check=True)


if __name__ == '__main__':
    main()
