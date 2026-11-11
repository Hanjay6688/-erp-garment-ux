"""Check source verification and the moving diagnostic on exact GitHub inputs."""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from statistics import median
from time import perf_counter
from types import CodeType, ModuleType, SimpleNamespace
from unittest.mock import patch
import importlib.util
import json
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
STAGE = ROOT / 'stage/scripts/current-sku-automatic-composite-preparation'
REF = ROOT / 'reference'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_refuses(callback, expected):
    try:
        callback()
    except ValueError as error:
        assert str(error).startswith(expected), str(error)
    else:
        raise AssertionError('Expected refusal: ' + expected)


def verify_sources(repo):
    calls = []

    def git(*args, input=None):
        calls.append(args[0])
        return subprocess.check_output(['git', '-C', str(repo), *args], input=input)

    git('init', '--quiet')
    assembly = load('review_batch_assembly', STAGE / 'assembly.py')
    reference = json.loads((STAGE / 'SOURCE_REFERENCE.json').read_bytes())
    additions = reference['automatic_files']
    parents = reference['unchanged_money_product']['files']
    identities = dict(parents)
    for name, expected in additions.items():
        raw = (ROOT / 'fixture-src' / name).read_bytes()
        assert assembly.admission.pin(raw) == {key: expected[key] for key in ('bytes', 'sha256')}
        identities[name] = git('hash-object', '-w', '--stdin', input=raw).decode().strip()
        assert identities[name] == expected['blob']

    def write_tree(entries):
        index = ''.join(f'100644 {oid}\t{path}\n' for path, oid in sorted(entries.items())).encode()
        git('read-tree', '--empty')
        git('update-index', '--index-info', input=index)
        return git('write-tree', '--missing-ok').decode().strip()

    tree = write_tree(identities)
    reference['automatic_source']['tree'] = tree
    reference_dir = repo / 'fixture-reference'
    reference_dir.mkdir()
    (reference_dir / 'SOURCE_REFERENCE.json').write_text(json.dumps(reference))
    composition = 'scripts/cp7_sku_automatic_pending/composition.py'

    def original():
        for name, oid in parents.items():
            assert git('rev-parse', tree + ':' + name).decode().strip() == oid
        for name, expected in additions.items():
            raw = git('show', tree + ':' + name)
            assert assembly.admission.pin(raw) == {key: expected[key] for key in ('bytes', 'sha256')}
            assert git('rev-parse', tree + ':' + name).decode().strip() == expected['blob']
        source, proof = assembly.derivation.derive(git('show', tree + ':' + composition))
        return reference, source, proof

    legacy_times = []
    new_times = []
    exact_git = assembly.git

    def traced_git(*args, **kwargs):
        calls.append(args[0])
        return exact_git(*args, **kwargs)

    with patch.object(assembly, 'HERE', reference_dir), patch.object(assembly, 'ROOT', repo), \
            patch.object(assembly, 'git', traced_git):
        for _ in range(6):
            calls.clear()
            start = perf_counter()
            old = original()
            legacy_times.append(perf_counter() - start)
            assert len(calls) == 85
            calls.clear()
            start = perf_counter()
            new = assembly.prepared_sources()
            new_times.append(perf_counter() - start)
            assert calls == ['ls-tree', 'cat-file']
            assert new == old
        missing = dict(identities)
        missing.pop(composition)
        missing_tree = write_tree(missing)
        assert_refuses(lambda: assembly.pinned_sources(missing_tree, parents, additions),
                       'SKU_AUTOMATIC_EXACT_SOURCE_PATHS_REQUIRED')
        changed = dict(identities)
        inherited = next(iter(parents))
        changed[inherited] = identities[composition]
        changed_tree = write_tree(changed)
        assert_refuses(lambda: assembly.pinned_sources(changed_tree, parents, additions),
                       'SKU_AUTOMATIC_ORIGINAL_MONEY_PRODUCT_CHANGED:')
        changed = dict(identities)
        changed[composition] = git('hash-object', '-w', '--stdin', input=b'modified\0file').decode().strip()
        changed_tree = write_tree(changed)
        assert_refuses(lambda: assembly.pinned_sources(changed_tree, parents, additions),
                       'SKU_AUTOMATIC_EXACT_REVIEWED_ADDITION_REQUIRED:')
        stale = dict(additions, **{composition: dict(additions[composition], sha256='0'*64)})
        assert_refuses(lambda: assembly.pinned_sources(tree, parents, stale),
                       'SKU_AUTOMATIC_EXACT_REVIEWED_ADDITION_REQUIRED:')
        stale = dict(additions, **{composition: dict(additions[composition], bytes=0)})
        assert_refuses(lambda: assembly.pinned_sources(tree, parents, stale),
                       'SKU_AUTOMATIC_EXACT_BATCH_BLOB_HEADER_REQUIRED:')
    return dict(exact_blob_bodies=len(additions), inherited_git_identities=len(parents),
                baseline_processes=85, revised_processes=2,
                baseline_median_ms=round(1000*median(legacy_times), 2),
                revised_median_ms=round(1000*median(new_times), 2),
                real_candidate_bytes=True, equivalent_derived_output=True, refused_mutations=5,
                full_frozen_checkout_replayed=False)


def verify_moving(repo):
    diag = load('review_moving_diagnostics', STAGE / 'moving_diagnostics.py')
    derive_path = REF / 'sku_current_parent_derive.py'
    deriver = load('review_moving_original_deriver', derive_path)
    moving_path = repo.parent / 'qualified-sku-money/scripts/cp7_sku_moving_average/composition.py'
    moving_path.parent.mkdir(parents=True)
    raw = (REF / 'moving_original.py').read_bytes()
    moving_path.write_bytes(raw)
    (moving_path.parent / 'valuation.sql').write_text('review trace value')
    source, proof = deriver.derive(raw)
    filename = str(moving_path) + '::current_mandor_parent'
    code, = [obj for obj in compile(source, filename, 'exec').co_consts
             if isinstance(obj, CodeType) and obj.co_name == 'install_delta']
    from types import FunctionType
    recorded = []
    measured = []
    value = {'functions': {}}
    prior = {'after': value, 'parent': {'preinstall_data_and_sequences': ['preinstall']}}
    failure = ValueError('preserve original installation error')

    def record(name, result=None):
        def call(*args, **kwargs):
            recorded.append(name)
            return result
        return call

    @contextmanager
    def scope(name):
        recorded.append('enter:' + name)
        try:
            yield
        finally:
            recorded.append('exit:' + name)

    @contextmanager
    def observe(name):
        measured.append(('STARTED', name))
        try:
            yield
        except BaseException:
            measured.append(('FAILED', name))
            raise
        else:
            measured.append(('COMPLETED', name))

    predecessor = SimpleNamespace(atomic=lambda _: scope('atomic'), predecessor=SimpleNamespace(
        predecessor=SimpleNamespace(_locks=record('lock'))))
    catalogue = SimpleNamespace(_catalog_rows=record('catalogue', value), _data=record('data', ['data']))
    delta = SimpleNamespace(SIGNATURES=(), patched=record('definitions', {}))
    cur = SimpleNamespace(execute=record('execute'))
    moving = ModuleType('current_mandor_moving_for_money')
    moving.__file__ = str(moving_path)
    moving.__dict__.update(runtime=record('runtime', (None, None, None, predecessor, catalogue)),
                           parent=lambda: SimpleNamespace(verify=record('parent.verify', 'Mandor proof')),
                           private_delta=delta, consumer_delta=delta, reader_delta=delta, credit_delta=delta,
                           reader_handover=lambda _: scope('handover'), as_owner=lambda *_: scope('owner'),
                           HERE=moving_path.parent, TABLES=(), FUNCTIONS=(), READER_OWNERS=(),
                           reader_access=SimpleNamespace(grant=record('grant')), sources=record('sources', 'pinned'),
                           binding=record('binding', 'digest'), transition=record('transition'), verify=record('verify'))
    moving.install_delta = FunctionType(code, moving.__dict__)
    old = moving.install_delta(cur, prior)
    original_trace = list(recorded)
    recorded.clear()
    with patch.object(diag, 'ROOT', repo), patch.object(diag, 'DERIVER', derive_path):
        receipt = diag.bind(moving, observe)
        assert moving.install_delta(cur, prior) == old
        assert recorded == original_trace
        assert len(measured) == 16
        assert measured[0] == ('STARTED', 'SKU_MOVING_RUNTIME_SOURCE')
        assert measured[-1] == ('COMPLETED', 'SKU_MOVING_VERIFY_MOVING')
        assert_refuses(lambda: diag.bind(moving, observe), 'SKU_MOVING_DIAGNOSTIC_EXACT_PRIVATE_MODULE_REQUIRED')
    measured.clear()
    recorded.clear()

    def failed_ddl(*args, **kwargs):
        raise failure

    cur.execute = failed_ddl
    try:
        moving.install_delta(cur, prior)
    except ValueError as observed:
        assert observed is failure
    else:
        raise AssertionError('Original DDL failure was suppressed')
    assert measured[-1] == ('FAILED', 'SKU_MOVING_DDL_AND_GRANTS')
    assert recorded[-3:] == ['exit:owner', 'exit:handover', 'exit:atomic']
    assert 'binding' not in recorded
    return dict(**receipt, exact_install_trace_equal=True, original_failure_identity_preserved=True,
                failed_subphase_recorded=True, original_composition_sha256=sha256(raw).hexdigest(),
                original_deriver_sha256=sha256(derive_path.read_bytes()).hexdigest(),
                exact_preceding_derivation=proof['original_recovered_exactly'])


if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as tmp:
        repository = Path(tmp) / 'auditor'
        repository.mkdir()
        print(json.dumps(dict(source_batch=verify_sources(repository), moving_observer=verify_moving(repository),
                              actual_ERP_case_credit=0, restoration_verified=False, workflow_changed=False), indent=2))
