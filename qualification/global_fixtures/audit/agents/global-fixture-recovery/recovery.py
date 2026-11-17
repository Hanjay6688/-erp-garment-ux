"""Private, still-closed wiring over the retained first-Global owner and Native lanes."""

import argparse
from contextlib import contextmanager
from functools import partial
from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import CodeType, FunctionType, SimpleNamespace
import json
import os
import sys

from foundation import Foundation, bind_seed, pin, require
from inherited import bind_advisors, bind_nota, run_nota


HERE = Path(__file__).resolve().parent
CALLER = HERE.parent / 'global-owning-caller-sku457'
CALLER_56 = HERE.parent / 'global-sku56-recovery/caller'
CORE = HERE.parent / 'global-fixture-driver-sku457'
SOURCE_PINS = {
    CALLER / 'owning.py': '67131f3ec8380214ac09cde28e8f7521335952e76376da6124981848d322e8a3',
    CALLER / 'lifecycle.py': '1976381280cce2b1279a8555db262490a077568d1e73457ecda651328b7eaaa6',
    CALLER / 'package_routes.py': 'ea13bbbfb03f9eb33071d1173dcbf67fb7a8ec3b35abbbc8fb01a4a122bf4ba7',
    CALLER / 'SOURCE.json': 'a28461fc6f41dd12ed8d1fad18954f8b6b21dae685e369f08fd341f848d8a26b',
    CORE / 'source_binding.py': '58125c9b1aca741fd1aa6eee199e15236ece02555d9fc99ce21d4a11d01d5075',
    CORE / 'fixture_driver.py': '61cb7793f26785f356181305c107bddde6ee9b9562335011439ee86869ad574e',
    CORE / 'SOURCE.json': '85101dc1a214599a0d2f891621288074d40347a7b185978da42bd797160ccf48',
}
CALLER_56_PINS = {
    'owning.py': 'e23028a65018a7823fef3c88eb39d05de4b616a64937771a132936c2ab95fdb2',
    'lifecycle.py': SOURCE_PINS[CALLER / 'lifecycle.py'],
    'package_routes.py': SOURCE_PINS[CALLER / 'package_routes.py'],
    'SOURCE.json': '7f926ea3e10d9fea344f7b16a00f0922dbfa6f6ca768321654f1d0456f330bce',
}
TREE_457 = '6ca1a7d3bab151f4ebf61034f40f5f3589633133'
TREE_56 = '3f77f6d559a341e254d986928ca09a13712ba2f9'
FIXTURE_56_POSTIMAGES = {
    'scripts/current-global-first-snapshot-preparation/INSTALL_PLAN.json':
        dict(bytes=15526, sha256='1bdede2dd236dab77fad15d41a5aff8327bde73d888975d473ad45bfb67faaf0'),
    'scripts/current-global-first-snapshot-preparation/SOURCE.json':
        dict(bytes=1429, sha256='50b041b9eb308da06d48365f648c793fca738530cc5f4d0335f999fb9d2b2cba'),
}
RUNNER = 'scripts/cp6_auditor_runner.py'
COMMIT = '            conn.commit();installed=True\n'
AFTER_COMMIT = COMMIT + '            _global_lifecycle.foundation.after_commit(cur,report)\n'
OWNER_ROUTE = (
    '            lifecycle = Lifecycle(engine, provider, parent_raw, profile_raw, fixtures)\n',
    '            lifecycle, native, revised = _recover_lifecycle(\n'
    '                engine, provider, parent_raw, profile_raw, fixtures, candidate, sku_checkout,\n'
    '                sku.FROZEN_SKU, roots, native, revised, sku.report_io)\n',
)
LIFECYCLE_ROUTES = (
    ('        measure = self.sku.measured\n',
     '        self.foundation.initialize(cur, report)\n        measure = self.sku.measured\n'),
    ("        first = measure(timings, 'FIRST_GLOBAL_INSTALL'",
     "        measure(timings, 'PRESEAL_FIXTURE_FOUNDATION', self.foundation.bootstrap, cur, report)\n"
     "        first = measure(timings, 'FIRST_GLOBAL_INSTALL'"),
    ('    def verify(self, cur, state):\n        return exact_fields(self.provider.verify',
     '    def verify(self, cur, state):\n        self.foundation.verify(cur)\n'
     '        return exact_fields(self.provider.verify'),
)


@contextmanager
def paths(*roots):
    before = sys.path[:]
    sys.path[:0] = [str(root) for root in roots]
    try:
        yield
    finally:
        sys.path[:] = before


def load(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    exec(compile(path.read_bytes(), str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


def checked_archives(caller_dir):
    require(caller_dir in (CALLER, CALLER_56), 'GLOBAL_RECOVERY_EXACT_CLOSED_CALLER_REQUIRED')
    pins = SOURCE_PINS
    if caller_dir == CALLER_56:
        pins = dict(SOURCE_PINS) | {caller_dir / name: sha for name, sha in CALLER_56_PINS.items()}
    for path, expected in pins.items():
        require(path.is_file() and not any(part.is_symlink() for part in (path, *path.parents))
                and pin(path.read_bytes())['sha256'] == expected,
                'GLOBAL_RECOVERY_EXACT_RETAINED_SOURCE_REQUIRED:' + path.name)


def derive(source, routes):
    changed = source
    for before, after in routes:
        require(changed.count(before) == 1 and after not in changed, 'GLOBAL_RECOVERY_ONE_EXACT_ROUTE_REQUIRED')
        changed = changed.replace(before, after, 1)
    restored = changed
    for before, after in reversed(routes):
        require(restored.count(after) == 1, 'GLOBAL_RECOVERY_ONE_EXACT_INVERSE_ROUTE_REQUIRED')
        restored = restored.replace(after, before, 1)
    require(restored == source, 'GLOBAL_RECOVERY_COMPLETE_SOURCE_INVERSE_REQUIRED')
    compile(changed, '<Global fixture recovery>', 'exec', dont_inherit=True)
    return changed, dict(before=pin(source.encode()), after=pin(changed.encode()), routes=len(routes))


def forbid_postseal_seed(cur):
    raise ValueError('GLOBAL_RECOVERY_FOUNDATION_SEED_FORBIDDEN_AFTER_SEAL')


def clone_namespace(value, **overrides):
    return SimpleNamespace(**dict(vars(value), **overrides))


def guarded_runner(runner, candidate, roots, report_io):
    path = Path(runner.__file__).absolute()
    require(any(path == root / RUNNER for root in roots) and path.is_file()
            and not any(part.is_symlink() for part in (path, *path.parents)),
            'GLOBAL_RECOVERY_EXACT_NATIVE_RUNNER_PATH_REQUIRED')
    raw = path.read_bytes()
    expected = json.loads((CALLER / 'SOURCE.json').read_bytes())['candidate_files'][RUNNER]
    require(pin(raw) == expected and raw == (candidate / RUNNER).read_bytes(),
            'GLOBAL_RECOVERY_EXACT_NATIVE_RUNNER_BYTES_REQUIRED')
    namespace = dict(vars(runner), api=clone_namespace(runner.api, seed=forbid_postseal_seed))
    for name in ('strict_group', '_strict_group_once'):
        operation = getattr(runner, name)
        require(operation.__globals__ is runner.__dict__ and operation.__closure__ is None
                and operation.__code__ == report_io.function_code(raw, str(path), name),
                'GLOBAL_RECOVERY_EXACT_NATIVE_RUNNER_CALLABLE_REQUIRED:' + name)
        namespace[name] = FunctionType(operation.__code__, namespace, name, operation.__defaults__)
    return clone_namespace(runner, strict_group=namespace['strict_group'], _strict_group_once=namespace['_strict_group_once'],
                           api=namespace['api'])


def guarded_graph(graph, runner, output, originals, report_io):
    from lifecycle import NativePositives

    def native_observer(selected):
        return NativePositives(graph.observer, runner, selected, output, originals, report_io)

    moving = graph.moving
    api = clone_namespace(moving.f.b.api, seed=forbid_postseal_seed)
    mover = clone_namespace(moving, f=clone_namespace(moving.f, b=clone_namespace(moving.f.b, api=api)))
    return clone_namespace(graph, moving=mover, native_observer=native_observer)


def prepared_lifecycle(caller_dir):
    archived = import_module('lifecycle')
    require(Path(archived.__file__).absolute() == caller_dir / 'lifecycle.py',
            'GLOBAL_RECOVERY_EXACT_ARCHIVED_LIFECYCLE_MODULE_REQUIRED')
    source, proof = derive((caller_dir / 'lifecycle.py').read_text(), LIFECYCLE_ROUTES)
    # The dataclass and all other routes keep their original module globals.
    module = compile(source, str(caller_dir / 'lifecycle.py'), 'exec', dont_inherit=True)
    block, = [code for code in module.co_consts if isinstance(code, CodeType) and code.co_name == 'Lifecycle']
    methods = {code.co_name: code for code in block.co_consts if isinstance(code, CodeType)}
    original = archived.Lifecycle
    overrides = {name: FunctionType(methods[name], vars(archived), name)
                 for name in ('install_cycle', 'verify')}
    return type('RecoveredLifecycle', (original,), overrides), proof


def fixture_binding(caller_dir):
    path = CORE / 'source_binding.py'
    if caller_dir == CALLER:
        return load('global_recovery_exact_fixture_binding_457', path), None

    def source_56():
        source = json.loads((CORE / 'SOURCE.json').read_bytes())
        source['first_Global_tree'] = TREE_56
        source['candidate'].update(FIXTURE_56_POSTIMAGES)
        source['caller'] = {name: pin((caller_dir / name).read_bytes()) for name in source['caller']}
        return source

    routes = (("CALLER = HERE.parent / 'global-owning-caller-sku457'", 'CALLER = _caller_56'),
              (f"TREE = '{TREE_457}'", f"TREE = '{TREE_56}'"),
              ("source = json.loads((HERE / 'SOURCE.json').read_bytes())", 'source = _source_56()'))
    text, proof = derive(path.read_text(), routes)
    spec = spec_from_file_location('global_recovery_exact_fixture_binding_56', path)
    binding = module_from_spec(spec)
    binding.__dict__.update(_caller_56=caller_dir, _source_56=source_56)
    exec(compile(text, str(path), 'exec', dont_inherit=True), binding.__dict__)
    return binding, dict(proof, changed_candidate_metadata=FIXTURE_56_POSTIMAGES, tree=TREE_56)


def recover_lifecycle(engine, provider, parent_raw, profile_raw, fixtures, candidate, sku_checkout,
                      money, roots, native, revised, report_io, *, caller_dir):
    require('make_native_lanes' in vars(fixtures) and fixtures.make_native_lanes is None,
            'GLOBAL_RECOVERY_REVIEWED_FIXTURE_NATIVE_LANE_BINDING_PENDING')
    with paths(caller_dir, CORE, candidate / 'scripts'):
        binding, _ = fixture_binding(caller_dir)
        core = import_module('fixture_driver')
        archived_lifecycle = import_module('lifecycle')
        require(Path(binding.__file__).absolute() == CORE / 'source_binding.py'
                and Path(core.__file__).absolute() == CORE / 'fixture_driver.py',
                'GLOBAL_RECOVERY_EXACT_RETAINED_FIXTURE_CORE_REQUIRED')
        graph, _ = binding.graph(candidate, money, accepted_roots=roots)
        cls, _ = prepared_lifecycle(caller_dir)
        notes, _ = bind_nota(candidate, roots, report_io)
        advisors = bind_advisors(candidate)

    seed, identities, donor = bind_seed(sku_checkout.parent / 'writer')
    reviewed = clone_namespace(fixtures, capture_advisors=advisors.capture, review_advisors=advisors.review)
    lifecycle = cls(engine, provider, parent_raw, profile_raw, reviewed)
    lifecycle.foundation = Foundation(seed, identities, donor, provider, core.actual_day)
    guarded = guarded_runner(native, candidate, roots, report_io)
    originals = report_io.complete_originals()
    output = candidate / 'cp6-proof/t3'
    graph = guarded_graph(graph, guarded, output, originals, report_io)
    nota_output = archived_lifecycle.NativePositives(graph.observer, guarded, (), output, originals, report_io)

    def retain(name, value):
        require(name in ('GLOBAL_COMMITTED_E_OBSERVATION', 'GLOBAL_USED_INVERSE_FULL_STATE',
                         'GLOBAL_STALE_D1', 'GLOBAL_STALE_E'), 'GLOBAL_RECOVERY_EXACT_NATIVE_ORIGINAL_NAME_REQUIRED')
        return originals.save_sorted(output / (name + '.json'), value, 'GLOBAL_RECOVERY_NATIVE_ORIGINAL_CONFLICT')

    def make_native_lanes(state):
        def verify(cur):
            return lifecycle.verify(cur, state)

        lanes = core.NativeLanes(provider=provider, parent_raw=parent_raw, profile_raw=profile_raw, state=state, graph=graph,
                                 trusted_connection=engine.trusted_installer_connection, verify=verify, retain=retain)
        lanes.run_nota = partial(run_nota, notes, guarded, verify, nota_output.output_scope, core.complete_group)
        return lanes

    fixtures.make_native_lanes = make_native_lanes
    prepared, _ = derive(revised, ((COMMIT, AFTER_COMMIT),))
    return lifecycle, guarded, prepared


def bind_owner(caller_dir=CALLER):
    checked_archives(caller_dir)
    with paths(caller_dir):
        owner = load('global_recovery_exact_archived_owner', caller_dir / 'owning.py')
        cls, lifecycle_proof = prepared_lifecycle(caller_dir)
    require(all(value is None for value in owner.GATES.values()) and len(owner.GATES) == 8
            and owner.REVIEWED_FIXTURES is None, 'GLOBAL_RECOVERY_ALL_ACTUAL_BINDINGS_MUST_STAY_CLOSED')
    source, proof = derive((caller_dir / 'owning.py').read_text(), (OWNER_ROUTE,))
    original = owner.runtime.__wrapped__
    full = compile(source, original.__code__.co_filename, 'exec', dont_inherit=True)
    code, = [code for code in full.co_consts if isinstance(code, CodeType) and code.co_name == 'runtime']
    handler = partial(recover_lifecycle, caller_dir=caller_dir)
    callback = FunctionType(code, dict(vars(owner), _recover_lifecycle=handler), 'runtime')
    callback.__kwdefaults__ = original.__kwdefaults__
    return SimpleNamespace(runtime=contextmanager(callback), source_check=owner.source_check, owner=owner, cls=cls,
                           routes=dict(owner=proof, lifecycle=lifecycle_proof))


def source_check(candidate, money, writer, *, caller_dir=CALLER):
    """Check exact archived and recovery source routes under the original DB/network fence."""
    candidate, money, writer = [Path(path).absolute() for path in (candidate, money, writer)]
    owner = bind_owner(caller_dir)
    previous = Path.cwd()
    fence = load('global_recovery_retained_DB_and_network_fence', candidate / owner.owner.FENCE)
    try:
        os.chdir(candidate)
        with fence.fenced_source_read() as guard, paths(caller_dir, CORE, candidate / 'scripts'):
            binding, rebind = fixture_binding(caller_dir)
            graph, fixture_proof = binding.graph(candidate, money, check_provider=True)
            _, seed_base, writer_proof = bind_seed(writer)
            sku = load('global_recovery_exact_SKU_source_entry', candidate / owner.owner.SKU_ENTRY)
            _, revised, _ = owner.owner.package_sources(sku, candidate / owner.owner.DONOR)
            _, commit_proof = derive(revised, ((COMMIT, AFTER_COMMIT),))
            _, runner, _, _ = owner.owner.native_graph(candidate, (candidate,))
            guarded = guarded_runner(runner, candidate, (candidate,), sku.report_io)
            require(guarded.strict_group.__code__ is runner.strict_group.__code__
                    and guarded._strict_group_once.__code__ is runner._strict_group_once.__code__,
                    'GLOBAL_RECOVERY_NATIVE_STRICT_RUNNER_CODE_CHANGED')
            guarded_graph(graph, guarded, None, None, sku.report_io)
            _, nota_proof = bind_nota(candidate, (candidate,), sku.report_io)
            advisor_proof = bind_advisors(candidate).source
    finally:
        os.chdir(previous)
    return dict(status='GLOBAL_FIXTURE_RECOVERY_SOURCE_CHECKED', archive_routes=owner.routes, fixture_source_rebind=rebind,
                writer=writer_proof, synthetic_CP6_seed_subject=seed_base.OPERATOR_AUTH,
                exact_retained_fixture=fixture_proof, existing_package_commit_route=commit_proof,
                inherited_Native_Nota=nota_proof, Global_advisor_sources=advisor_proof,
                strict_native_group_code_unchanged=True, source_fence=guard,
                gates=dict(owner.owner.GATES), reviewed_fixtures=None, actual_ERP_cases=0,
                actual_Auth_cases=0, runtime_admission=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--money', type=Path, required=True)
    parser.add_argument('--writer', type=Path, required=True)
    parser.add_argument('--basis', choices=('457', '56e7'), default='457')
    args = parser.parse_args()
    print(json.dumps(source_check(args.candidate, args.money, args.writer,
                                  caller_dir=CALLER_56 if args.basis == '56e7' else CALLER), indent=2))
