"""Bind exact fixture callables and inspect their sources under the existing fence."""

import argparse
import ast
from contextlib import contextmanager
from dis import get_instructions
from hashlib import sha256
from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location
from inspect import signature
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

from fixture_driver import POSITIVE_IDS, actual_day, require, rollback_on_failure


HERE = Path(__file__).resolve().parent
CALLER = HERE.parent / 'global-owning-caller-sku457'
FENCE = 'scripts/current-sku-managed-recovery-native27-qualification/source_context.py'
E_WITNESS = 'scripts/current-complete-de-integration-preparation/witness.py'
MOVE = 'scripts/cp7_sku_moving_average/qualification_cases.py'
MOVE_FIXTURE = 'scripts/current-sku-pair-conversion-qualification/fixture.py'
FROZEN_MONEY = ('f1674ae84739f577571d68415beabfca3f3b832b', 'ea43f84029993b385722fe8e202adefd2a745f7b')
TREE = '6ca1a7d3bab151f4ebf61034f40f5f3589633133'


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def load(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def paths(*additions):
    original = sys.path[:]
    sys.path[0:0] = [str(path) for path in additions]
    try:
        yield
    finally:
        sys.path[:] = original


def expect(function, parameters):
    require(tuple(signature(function).parameters) == parameters, 'GLOBAL_FIXTURE_EXACT_CALLABLE_REQUIRED:' + function.__name__)


def frozen_money(root):
    overrides = {'GIT_DIR', 'GIT_COMMON_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES'}
    env = {key: value for key, value in os.environ.items() if key not in overrides}
    env.update(GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0')
    head = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD', 'HEAD^{tree}'], env=env).decode().split()
    require(tuple(head) == FROZEN_MONEY, 'GLOBAL_FIXTURE_EXACT_FROZEN_MONEY_HEAD_AND_TREE_REQUIRED')
    require(not subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain', '--untracked-files=no'], env=env),
            'GLOBAL_FIXTURE_CLEAN_FROZEN_MONEY_SOURCE_REQUIRED')


def manifests(candidate, money):
    source = json.loads((HERE / 'SOURCE.json').read_bytes())
    require(source['first_Global_tree'] == TREE and source['actual_ERP_cases'] == 0,
            'GLOBAL_FIXTURE_EXACT_CLOSED_SOURCE_TREE_REQUIRED')
    for label, root in (('candidate', candidate), ('money', money), ('caller', CALLER)):
        for name, expected in source[label].items():
            path = root / name
            require(path.is_file() and not path.is_symlink() and pin(path.read_bytes()) == expected,
                    'GLOBAL_FIXTURE_EXACT_PINNED_SOURCE_REQUIRED:' + label + ':' + name)
    return source


def derive(source, routes):
    changed = source
    for old, new in routes:
        require(changed.count(old) == 1 and new not in changed, 'GLOBAL_FIXTURE_ONE_EXACT_SOURCE_ROUTE_REQUIRED')
        changed = changed.replace(old, new, 1)
    recovered = changed
    for old, new in reversed(routes):
        require(recovered.count(new) == 1, 'GLOBAL_FIXTURE_ONE_EXACT_INVERSE_SOURCE_ROUTE_REQUIRED')
        recovered = recovered.replace(new, old, 1)
    require(recovered == source, 'GLOBAL_FIXTURE_COMPLETE_ORIGINAL_FUNCTION_NOT_RECOVERED')
    return changed, dict(original=pin(source.encode()), derived=pin(changed.encode()), routes=len(routes))


def committed_witness(candidate, existing_usage):
    inherited = load('global_retained_committed_E', candidate / E_WITNESS)
    source, original = inherited.prepared_sources()
    old_tail = source[source.index('        with control.product_catalog(cur):'):]
    require(old_tail.endswith('        return result\n') and 'rollback_delta_preuse' in old_tail,
            'GLOBAL_FIXTURE_EXACT_E17_OLD_INVERSE_TAIL_REQUIRED')
    routes = (
        ('def committed_witness(url, state, business, product, control, financial_truth):\n'
         '    import psycopg\n    with psycopg.connect(url) as conn, conn.cursor() as cur:',
         'def committed_witness(conn, cur, business, financial_truth, observe):\n    with _rollback_on_failure(conn):'),
        ("        cur.execute('grant usage on schema erp to authenticated')  # unchanged isolated Native harness capability only",
         '        _existing_usage(cur)'),
        ('        today = cur.execute("select(statement_timestamp()at time zone\'Asia/Jakarta\')::date").fetchone()[0]',
         '        today = _actual_day(cur)'),
        ('        pair = business.fixture.prepare(cur, today)',
         '        before_global = observe(cur)\n        pair = business.fixture.prepare(cur, today)'),
        ('        conn.commit()',
         '        global_receipt = observe(cur, before_global)\n        _actual_day(cur)\n        conn.commit()'),
        (old_tail, '        return dict(result, **global_receipt)\n'),
    )
    text, proof = derive(source, routes)
    namespace = dict(_rollback_on_failure=rollback_on_failure, _existing_usage=existing_usage, _actual_day=actual_day)
    exec(compile(text, '<Global retained committed E witness>', 'exec', dont_inherit=True), namespace)
    operation = namespace['committed_witness']
    expect(operation, ('conn', 'cur', 'business', 'financial_truth', 'observe'))
    return operation, dict(retained_E17=original, counted_derivation=proof)


def reverse_existing(moving, path):
    raw = path.read_text()
    node, = [node for node in ast.parse(raw).body if isinstance(node, ast.FunctionDef) and node.name == 'exact_group_reverse']
    source = ast.get_source_segment(raw, node) + '\n'
    old = 'def exact_group_reverse(cur,today):\n    x=canonical(cur,today);made,_=forward(cur,x)'
    new = "def reverse_existing(cur,x,conversion_id):\n    made={'conversion_id':conversion_id}"
    text, proof = derive(source, ((old, new),))
    namespace = dict(vars(moving))
    exec(compile(text, '<Global exact existing outside SKU group inverse>', 'exec', dont_inherit=True), namespace)
    result = namespace['reverse_existing']
    expect(result, ('cur', 'x', 'conversion_id'))
    return result, proof


def inverse_contract(provider):
    expect(provider.rollback_preuse, ('cur', 'state'))
    expect(provider._timezone_snapshot, ('cur', 'lock'))
    instructions = list(get_instructions(provider.rollback_preuse))
    guard, = [step.offset for step in instructions if step.opname == 'LOAD_CONST'
              and step.argval == 'GLOBAL_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE:']
    names = ('_snapshot_inverse_preuse', '_timezone_change', 'replace_native')
    first_writes = {name: next(step.offset for step in instructions if step.opname == 'LOAD_GLOBAL' and step.argval == name)
                    for name in names}
    require(all(offset > guard for offset in first_writes.values()), 'GLOBAL_FIXTURE_EXACT_USED_GUARD_BEFORE_DDL_REQUIRED')
    return dict(guard_instruction=guard, first_DDL_routes=first_writes, expected_committed_table='cp7_global_nonpo_envelope.scope_completions_v1')


def graph(candidate, money, *, output=None, originals=None, accepted_roots=(), check_provider=False):
    """Read fixture graph and compile retained operations. No business callback runs."""
    source = manifests(candidate, money)
    frozen_money(money)
    with paths(CALLER, candidate / 'scripts'):
        caller = load('global_sku457_exact_prepared_caller', CALLER / 'owning.py')
        lifecycle = import_module('lifecycle')
        require(Path(lifecycle.__file__).resolve() == CALLER / 'lifecycle.py' and caller.REVIEWED_FIXTURES is None
                and len(caller.GATES) == 8 and all(value is None for value in caller.GATES.values()),
                'GLOBAL_FIXTURE_ORIGINAL_OWNER_AND_EIGHT_CLOSED_GATES_REQUIRED')
        caller.source_files(candidate, verify_receipt=True)
        if check_provider:
            provider, provider_proof = caller.prepared_provider(candidate)
            guard_proof = inverse_contract(provider)
        roots = tuple(dict.fromkeys((candidate, *accepted_roots)))
        observer, runner, factories, native_proof = caller.native_graph(candidate, roots)
        keys = tuple(key for _, _, expected in factories for key in expected)
        require(keys == POSITIVE_IDS, 'GLOBAL_FIXTURE_EXACT_SIX_OWNER_POSITIVES_REQUIRED')
        d1 = import_module('cp7_credit_correction_de.cases')
        e = import_module('cp7_credit_correction_de.e_cases')
        financial_truth = import_module('cp6_bd_probe')
        expect(financial_truth.all_truth, ('cur',))
        expect(financial_truth.truth_quiet, ('before', 'after'))
        require(pin(Path(financial_truth.__file__).read_bytes()) == source['candidate']['scripts/cp6_bd_probe.py'],
                'GLOBAL_FIXTURE_EXACT_E_FINANCIAL_TRUTH_SOURCE_REQUIRED')
        for module, names in ((d1, ('D_ACCESS_REVOKED_NO_EFFECT',)), (e, ('E_CURRENT_ACCESS_REVOKED_REFUSES',))):
            require(all(key in module.IDS for key in names), 'GLOBAL_FIXTURE_EXACT_RETAINED_PERMISSION_CASE_REQUIRED')
            expect(module.refusal, ('cur', 'pair', 'fn', 'message'))
        report_io = load('global_sku457_retained_complete_report_io', candidate / (caller.SKU + '/report_io.py'))
        with paths(money / 'scripts'):
            moving = load('global_exact_frozen_moving_average_cases', money / MOVE)
        require(Path(moving.f.__file__).resolve() == money / MOVE_FIXTURE, 'GLOBAL_FIXTURE_EXACT_OUTSIDE_SKU_FIXTURE_REQUIRED')
        for operation, parameters in ((moving.canonical, ('cur', 'today')), (moving.forward, ('cur', 'x')),
                                      (moving.f.action, ('cur', 'kind', 'payload', 'key'))):
            expect(operation, parameters)
        observe_e, witness_proof = committed_witness(candidate, lifecycle.existing_native_usage)
        inverse, inverse_proof = reverse_existing(moving, money / MOVE)

    def native_observer(selected):
        require(output is not None and originals is not None, 'GLOBAL_FIXTURE_EXACT_OWNING_ORIGINAL_OUTPUT_REQUIRED')
        return lifecycle.NativePositives(observer, runner, selected, output, originals, report_io)

    bundle = SimpleNamespace(d1=d1, e=e, moving=moving, observer=observer, factories=factories,
                             financial_truth=financial_truth, commit_e=observe_e, reverse_existing=inverse,
                             existing_usage=lifecycle.existing_native_usage, native_observer=native_observer)
    proof = dict(status='GLOBAL_FIXTURE_EXACT_SOURCE_GRAPH_CHECKED', tree=TREE, positive_ids=list(keys),
                 native_runner=native_proof, committed_E_witness=witness_proof, outside_SKU_inverse=inverse_proof,
                 all_eight_gates=dict(caller.GATES), reviewed_fixture=None, actual_SQL_executed=0, actual_ERP_cases=0,
                 actual_Auth_cases=0, runtime_admission=False)
    if check_provider:
        proof['compiled_Global_provider'] = provider_proof
        proof['used_inverse_guard'] = guard_proof
    return bundle, proof


def source_check(candidate, money):
    candidate, money = candidate.absolute(), money.absolute()
    manifests(candidate, money)
    old = Path.cwd()
    try:
        os.chdir(candidate)
        fence = load('global_sku457_retained_DB_network_fence', candidate / FENCE)
        with fence.fenced_source_read() as guard:
            _, proof = graph(candidate, money, check_provider=True)
    finally:
        os.chdir(old)
    return dict(proof, fence=guard)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--money', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(source_check(args.candidate, args.money), indent=2))
