"""Own the first Global snapshot provider on the reviewed private runner."""

import argparse
from contextlib import ExitStack, chdir, contextmanager
from hashlib import sha256
from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location
from inspect import signature
import json
import os
from pathlib import Path
import sys
from types import FunctionType, ModuleType, SimpleNamespace

from .dated_lifecycle import DatedLifecycle
from .foundation import Foundation, bind_seed, checked_writer
from .lifecycle import NativePositives
from . import package_routes
from .package_routes import require
from p21 import mode as p21_mode

from global_preseal import (CATALOGUE_PIN, COMBINED, COMBINED_SRC, COMPARATOR, COMPARATOR_SHA, INPUTS, PLAN, ROOT_PIN,
                            candidate_imports, exact, git, observation_tools, verify_candidate)
from realtime_comparator import bind_provider as bind_realtime_provider
from sku_credit_seal import prepare as prepare_credit_seal
from sku_progress import runtime_with_progress


HERE = Path(__file__).resolve().parent
RUNNER_ENTRY = 'qualification/global_owning/owning.py'
FIXTURE_ENTRY = 'qualification/reviewed_ordinary.py'
ORDINARY_BRANCH = 'audit/codex-p20-a752459a'
FIRST = 'scripts/current-global-first-snapshot-preparation/install_routes.py'
ADMISSION = 'scripts/cp7_global_nonpo_envelope/admission.py'
COMPOSITION = 'scripts/cp7_global_nonpo_envelope/composition.py'
SKU = 'scripts/current-sku-automatic-composite-preparation'
SKU_ENTRY = SKU + '/qualification.py'
DONOR = 'scripts/current-vendor-receivable-qualification/probe.py'
FENCE = 'scripts/current-sku-managed-recovery-native27-qualification/source_context.py'
PACKAGE = 'scripts/cp6_t3_package_run.py'
PACKAGE_IO = 'scripts/current-mandor-afui-preparation/report_io.py'
IDENTITY = 'scripts/current-mandor-shop-native-qualification/package_identity.py'
ATTEMPT = 'scripts/current-de-free-date-preparation/attempt_policy.py'
NATIVE = 'scripts/current-complete-de-integration-preparation/native_business.py'
INHERITED_BACKEND = 'scripts/current-final-s03-sku-s05-preparation/frozen_parent.py'
OBSERVER = HERE / 'observe_d1_e.py'
FOUNDATION = HERE / 'foundation.py'
AFTER_COMMIT = "            conn.commit();installed=True\n"

GATES = dict(PARENT_HEAD=None, PARENT_TREE=None, PARENT_ROOT_RECEIPT=None, PARENT_RUN=None,
             PARENT_JOB=None, PARENT_ROOT_CONTRACT=None, INPUT_PROFILE_PIN=None, RUNTIME_ENTRY=None)
REVIEWED_FIXTURES = None
BASELINE_TREE = COMBINED
PENDING = ('reviewed live Global input profile',
           'committed outside-SKU and used-E fixtures', 'lawful dirty and stale/inverse fixtures',
           'real Auth and independent COMMIT/ABORT races', 'actual advisor authority and managed owner admission')

POSITIVES = (
    ('cp7_credit_correction_de.cases', 'scripts/cp7_credit_correction_de/cases.py',
     {'D_AFTER_ACTIVE_APPLY': ('D1',), 'D_REPLAY_EXACT_UUID': ('D1',)}),
    ('cp7_credit_correction_de.e_cases', 'scripts/cp7_credit_correction_de/e_cases.py',
     {'E_SAME_UUID_AND_CHANGED_INTENT': ('E',), 'E_UNDO_ORIGINAL_80_AND_OLD_RECEIPT': ('E',)}),
    ('cp7_ow04_signed_source_cases', 'scripts/cp7_customer_credit/reconciliation/native/cp7_ow04_signed_source_cases.py',
     {'OW04_SIGNED_RETURN_REVERSE_UNCONSUMED_CREDIT': ('SOURCE',),
      'OW04_SIGNED_PAYMENT_REVERSE_UNCONSUMED_CREDIT': ('SOURCE',)}),
)


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def regular(path, error):
    require(path is not None, error)
    path = Path(path).absolute()
    require(path.is_file() and not any(part.is_symlink() for part in (path, *path.parents)), error)
    return path


def read(path, error):
    return regular(path, error).read_bytes()


def load(name, path):
    path = regular(path, 'GLOBAL_CALLER_EXACT_REGULAR_SOURCE_REQUIRED:' + str(path))
    spec = spec_from_file_location(name, path)
    result = module_from_spec(spec)
    exec(compile(path.read_bytes(), str(path), 'exec', dont_inherit=True), result.__dict__)
    return result


def api(function, *parameters):
    require(callable(function) and tuple(signature(function).parameters) == parameters,
            'GLOBAL_CALLER_EXACT_CALLABLE_PARAMETERS_REQUIRED:' + getattr(function, '__name__', repr(function)))
    return list(parameters)


def source_files(candidate):
    manifest = json.loads((HERE / 'SOURCE.json').read_bytes())
    require(manifest['basis_tree'] == BASELINE_TREE and manifest['installation_plan'] == PLAN
            and manifest['sku_root'] == ROOT_PIN and manifest['sku_catalogue'] == CATALOGUE_PIN,
            'GLOBAL_CALLER_EXACT_FIRST_GLOBAL_SOURCE_TREE_REQUIRED')
    verify_candidate(candidate)
    for name, expected in manifest['candidate_files'].items():
        require(pin(read(candidate / name, 'GLOBAL_CALLER_PINNED_CANDIDATE_SOURCE_REQUIRED:' + name)) == expected,
                'GLOBAL_CALLER_PINNED_CANDIDATE_SOURCE_CHANGED:' + name)
    require(pin(read(OBSERVER, 'GLOBAL_CALLER_EXACT_OBSERVER_SOURCE_REQUIRED')) == manifest['observer'],
            'GLOBAL_CALLER_EXACT_OBSERVER_SOURCE_CHANGED')
    require(pin(read(FOUNDATION, 'GLOBAL_CALLER_EXACT_FOUNDATION_SOURCE_REQUIRED')) == manifest['foundation'],
            'GLOBAL_CALLER_EXACT_FOUNDATION_SOURCE_CHANGED')
    comparator_path = Path(sys.modules[bind_realtime_provider.__module__].__file__).absolute()
    for name, path in (('realtime_comparator', comparator_path),
                       ('daily_partitions', comparator_path.with_name('daily_partitions.py'))):
        require(pin(read(path, 'GLOBAL_CALLER_REGULAR_DATED_CATALOGUE_SOURCE_REQUIRED')) == manifest[name],
                'GLOBAL_CALLER_EXACT_DATED_CATALOGUE_SOURCE_REQUIRED:' + name)
    return manifest


@contextmanager
def import_paths(*paths):
    original = sys.path[:]
    sys.path[0:0] = [str(path) for path in paths]
    try:
        yield
    finally:
        sys.path[:] = original


def prepared_provider(candidate, parent_raw, catalogue_raw):
    from datetime import date

    require(pin(parent_raw) == ROOT_PIN and pin(catalogue_raw) == CATALOGUE_PIN,
            'GLOBAL_CALLER_EXACT_RETAINED_A625_ROOT_AND_CATALOGUE_REQUIRED')
    parent = json.loads(parent_raw)
    entry = candidate / FIRST
    with candidate_imports(candidate):
        loader = load('global_first_snapshot_owning_provider', entry)
        result, proof = loader.load_prepared()
        require(Path(result.__file__) == candidate / COMPOSITION and Path(result.admission.__file__) == candidate / ADMISSION,
                'GLOBAL_CALLER_EXACT_FIRST_GLOBAL_PROVIDER_GRAPH_REQUIRED')
        require(tuple(proof['gates']) == tuple(GATES) and all(getattr(result.admission, key) is None for key in GATES),
                'GLOBAL_CALLER_RETAINED_ALL_EIGHT_CLOSED_GATES_REQUIRED')
        exact(candidate / COMPARATOR, COMPARATOR_SHA)
        comparator = load('global_caller_exact_parent_comparator', candidate / COMPARATOR)
        bindings = loader.review_parent(parent_raw, catalogue_raw, verified_root_pin=ROOT_PIN,
                                        catalogue_groups=loader.snapshot.CATALOGUE_GROUPS)
        require(set(bindings) == {'timezone_overlay', 'nota_opening_advance', 'ow06_s05_snapshot'}
                and all(binding['installation_plan'] == PLAN and binding['root'] == ROOT_PIN
                        and binding['catalogue'] == CATALOGUE_PIN for binding in bindings.values())
                and all(bindings[name]['parent_fingerprint'] == parent['global_parent_catalogue']['fingerprint']
                        for name in ('timezone_overlay', 'ow06_s05_snapshot')),
                'GLOBAL_CALLER_EXACT_THREE_BINDINGS_REQUIRED')
        snapshot = dict(vars(result))
        bound = bind_realtime_provider(result, comparator, catalogue_raw, CATALOGUE_PIN,
                                       archived_startup_day=date(2026, 11, 13))
        contracts = {
            'install': api(bound.install, 'cur', 'parent_receipt_raw', 'input_profile_raw'),
            'verify': api(bound.verify, 'cur', 'state'),
            'rollback_preuse': api(bound.rollback_preuse, 'cur', 'state'),
            'capture': api(bound.capture, 'cur'),
            'fingerprint': api(bound.fingerprint, 'cur', 'value'),
            'runtime_admission': api(bound.admission.runtime_admission, 'parent_raw', 'input_raw'),
        }
        source = result.sources()
        require(source == bound.sources() and source['plan'] == PLAN and bound.admission is result.admission
                and all(vars(result)[name] is value for name, value in snapshot.items())
                and all(getattr(bound, name).__code__ is getattr(result, name).__code__
                        and getattr(bound, name).__globals__ is vars(bound)
                        for name in contracts if name != 'runtime_admission'),
                'GLOBAL_CALLER_DATED_COMPARATOR_CHANGED_PROVIDER_AUTHORITY')
    return bound, dict(derivation=proof['derivation']['derived'], signatures=contracts, plan=source['plan'],
                       catalogue=CATALOGUE_PIN, root=ROOT_PIN, exact_overlay_bindings=sorted(bindings),
                       private_dated_comparator=True, original_provider_unchanged=True)


def clone(function, namespace):
    result = FunctionType(function.__code__, namespace, function.__name__, function.__defaults__, function.__closure__)
    result.__kwdefaults__ = function.__kwdefaults__
    return result


def private_admission(original, gates):
    namespace = dict(vars(original), **gates)
    namespace['runtime_admission'] = clone(original.runtime_admission, namespace)
    return SimpleNamespace(**namespace)


def private_provider(original, admission):
    result = ModuleType('cp7_global_nonpo_envelope.owning_first_snapshot_composition')
    result.__dict__.update(vars(original), admission=admission)
    for name, value in vars(original).items():
        if isinstance(value, FunctionType) and value.__globals__ is original.__dict__:
            result.__dict__[name] = clone(value, result.__dict__)
    return result


def require_gates(gates):
    require(gates.keys() == GATES.keys() and all(value is not None for value in gates.values()),
            'CP7_GLOBAL_ENVELOPE_ACTUAL_FINAL_PARENT_AND_OWNING_SCOPE_PENDING')


def receipt_and_profile(parent_receipt, input_profile):
    parent = read(parent_receipt, 'GLOBAL_CALLER_ACTUAL_SKU_PARENT_RECEIPT_REQUIRED')
    profile = read(input_profile, 'GLOBAL_CALLER_EXACT_REVIEWED_INPUT_PROFILE_REQUIRED')
    return parent, profile


def ordinary_ref():
    return 'refs/heads/' + (p21_mode.BRANCH if p21_mode.enabled() else ORDINARY_BRANCH)


def runner_ci_identity(runner, head):
    """Bind the actual public push to this tracked runner checkout."""
    require(Path(runner) == Path(__file__).absolute().parents[2],
            'P21_PUBLIC_TRACKED_RUNNER_REQUIRED')
    return p21_mode.public_identity(head)

def tracked_source(runner, relative):
    name = Path(relative)
    require(not name.is_absolute() and '..' not in name.parts,
            'GLOBAL_CALLER_EXACT_TRACKED_RELATIVE_SOURCE_REQUIRED')
    path = runner / name
    raw = read(path, 'GLOBAL_CALLER_EXACT_TRACKED_REGULAR_SOURCE_REQUIRED')
    blob = git(runner, 'hash-object', '--stdin', input=raw)
    require(git(runner, 'ls-tree', 'HEAD', '--', relative) == f'100644 blob {blob}\t{relative}',
            'GLOBAL_CALLER_TRACKED_PRIVATE_ENTRY_REQUIRED:' + relative)
    return path, raw


def runtime_checkout(candidate, sku_checkout):
    entry = Path(__file__).absolute()
    runner = entry.parents[2]
    require(len({candidate, sku_checkout, runner}) == 3 and runner / RUNNER_ENTRY == entry
            and sys.flags.optimize == 0 and git(runner, 'rev-parse', '--show-toplevel') == str(runner)
            and os.environ.get('GITHUB_REF') == ordinary_ref(),
            'GLOBAL_CALLER_EXACT_SEPARATE_OWNING_ENTRY_REQUIRED')
    _, raw = tracked_source(runner, RUNNER_ENTRY)
    head = git(runner, 'rev-parse', 'HEAD')
    identity = runner_ci_identity(runner, head)
    require(identity['run_attempt'] == 1, 'GLOBAL_CALLER_EXACT_FIRST_RUN_ATTEMPT_REQUIRED')
    return runner, dict(entry=RUNNER_ENTRY, head=head, tree=git(runner, 'rev-parse', 'HEAD^{tree}'),
                        source=pin(raw), github=identity)


def reviewed_profile(provider, raw, root_raw):
    _, profile = provider.admission.runtime_admission(root_raw, raw)
    names = profile.get('relations')
    require(profile.get('installation_plan') == provider.sources()['plan'] and type(names) is list
            and all(type(name) is str for name in names) and names == sorted(set(names)) and bool(names)
            and all(type(profile.get(key)) is dict for key in ('parent_catalogue_fingerprint', 'timezone_overlay',
                                                             'nota_opening_advance', 'ow06_s05_snapshot')),
            'GLOBAL_CALLER_COMPLETE_FIRST_SNAPSHOT_INPUT_PROFILE_REQUIRED')


def package_sources(sku, path):
    raw = read(path, 'GLOBAL_CALLER_EXACT_VENDOR_ENGINE_DONOR_REQUIRED')
    original, proof = sku.package_source.derive(raw)
    revised, routes = package_routes.derive(original)
    require(proof['source_sha256'] == routes['parent_sha256'], 'GLOBAL_CALLER_EXACT_SKU_ENGINE_DERIVATION_REQUIRED')
    return original, revised, routes


def foundation_writer(revised):
    """Read the committed fixture from the owning installer before other sessions."""
    hook = '            _global_lifecycle.foundation.after_commit(cur,report)\n'
    require(revised.count(AFTER_COMMIT) == 1 and hook not in revised,
            'GLOBAL_CALLER_EXACT_EXISTING_FOUNDATION_COMMIT_REQUIRED')
    result = revised.replace(AFTER_COMMIT, AFTER_COMMIT + hook, 1)
    require(result.replace(hook, '', 1) == revised, 'GLOBAL_CALLER_FOUNDATION_WRITER_SOURCE_NOT_RECOVERED')
    compile(result, '<Global owning foundation writer>', 'exec', dont_inherit=True)
    return result


@contextmanager
def inherited_scope(sku):
    api(sku.inherited_scope)
    with sku.inherited_scope():
        yield


def native_graph(candidate, accepted_roots):
    binder = load('global_exact_native_business_sources', candidate / NATIVE)
    observer = load('global_exact_inside_savepoint_observer', OBSERVER)
    api(observer.bind, 'installer', 'parent_raw', 'profile_raw', 'state', 'root', 'factory',
        'expected_operations', 'outside_conversion_id', 'retain')
    factories = []
    with binder.fixture_imports():
        for name, relative, expected in POSITIVES:
            module = import_module(name)
            path = Path(module.__file__).absolute()
            roots = [root for root in accepted_roots if path == root / relative]
            require(len(roots) == 1, 'GLOBAL_CALLER_EXACT_NATURAL_NATIVE_FACTORY_PATH_REQUIRED:' + relative)
            observer.exact_function(module.cases, path, observer.FACTORIES[relative], 'cases')
            api(module.cases, 'cur', 'today')
            require(tuple(key for key in module.IDS if key in expected) == tuple(expected),
                    'GLOBAL_CALLER_EXACT_NATIVE_FACTORY_IDS_REQUIRED:' + relative)
            fixture = Path(module.native.__file__).absolute()
            require(any(fixture == root / observer.FIXTURE for root in accepted_roots),
                    'GLOBAL_CALLER_EXACT_NATURAL_SHARED_NATIVE_FIXTURE_PATH_REQUIRED')
            observer.exact_function(module.native.isolated.__wrapped__, fixture, observer.FIXTURE_SHA, 'isolated')
            factories.append((roots[0], module.cases, expected))
        signed = factories[-1][1].__globals__['_positive']
        observer.exact_function(signed, Path(signed.__code__.co_filename), observer.FACTORIES[observer.SIGNED], '_positive')
        runner = import_module('cp6_auditor_runner')
    require(factories[0][1].__globals__['native'] is factories[1][1].__globals__['native']
            is factories[2][1].__globals__['native'], 'GLOBAL_CALLER_SHARED_NATIVE_FIXTURE_IDENTITY_REQUIRED')
    proof = binder.inspect_runner_contract(runner)
    origin = Path(runner.__file__).absolute()
    require(any(origin == root / 'scripts/cp6_auditor_runner.py' for root in accepted_roots),
            'GLOBAL_CALLER_EXACT_NATURAL_STRICT_RUNNER_PATH_REQUIRED:' + str(origin))
    return observer, runner, factories, dict(proof, runner_source_root=str(origin.parents[1]))


def inherited_native_roots(candidate, sku, checkout):
    backend = load('global_exact_inherited_SKU_backend', sku.FROZEN_AFUI / INHERITED_BACKEND).admitted()
    return tuple(dict.fromkeys((candidate, checkout, sku.FROZEN_AFUI, sku.FROZEN_PARENT, Path(backend['path']))))


def package_graph(package, io, candidate, accepted_roots):
    path = Path(package.__file__).absolute()
    require(any(path == root / PACKAGE for root in accepted_roots)
            and path.read_bytes() == (candidate / PACKAGE).read_bytes(), 'GLOBAL_CALLER_EXACT_FROZEN_T3_PACKAGE_REQUIRED')
    return dict(run=api(package.run, 'mode'), writer_runtime=api(package.writer_runtime, 'browser_mode'),
                private_package_run=api(io.private_package_run, 'package', 'output', 'writer'),
                package_identity_scope=api(io.package_identity_scope, 'identity'))


def source_check(candidate, parent_raw, catalogue_raw, *, sku_checkout, writer_checkout=None):
    """Load the physical source graph under the retained pre-database fence."""
    candidate = Path(candidate).absolute()
    sku_checkout = Path(sku_checkout).absolute()
    writer_checkout = Path(writer_checkout).absolute() if writer_checkout else sku_checkout.parent / 'writer'
    manifest = source_files(candidate)
    fence = load('global_exact_pre_database_fence', candidate / FENCE)
    previous = Path.cwd()
    try:
        # The unmodified CP6 AO definitions read their retained inputs relative to cwd.
        os.chdir(candidate)
        with fence.fenced_source_read() as guard, import_paths(candidate / 'scripts'):
            provider, install_proof = prepared_provider(candidate, parent_raw, catalogue_raw)
            sku = load('global_exact_Sku_source_entry', candidate / SKU_ENTRY)
            _, revised, route_proof = package_sources(sku, candidate / DONOR)
            from sku_inputs import HEAD, TREE, git
            require((git(sku_checkout, 'rev-parse', 'HEAD'), git(sku_checkout, 'rev-parse', 'HEAD^{tree}')) == (HEAD, TREE)
                    and not git(sku_checkout, 'status', '--porcelain', '--untracked-files=no'),
                    'GLOBAL_CALLER_EXACT_SKU_CREDIT_SOURCE_CHECKOUT_REQUIRED')
            credit_entry = load('global_exact_SKU_credit_entry', sku_checkout / SKU_ENTRY)
            prepare_credit_seal(credit_entry)
            import dated_sku_install
            dated_sku_install.verify_source()
            _, _, foundation_proof = bind_seed(writer_checkout)
            _, _, factories, native_proof = native_graph(candidate, (candidate,))
            package = import_module('cp6_t3_package_run')
            io = load('global_exact_T3_io', candidate / PACKAGE_IO)
            t3 = package_graph(package, io, candidate, (candidate,))
            writer = io.private_package_run(package, candidate / 'cp6-proof/t3', None)
            require(writer.__code__ is package.run.__code__ and writer.__globals__ is not package.__dict__,
                    'GLOBAL_CALLER_EXACT_PRIVATE_T3_WRITER_ROUTE_REQUIRED')
            sku_api = dict(runtime=api(sku.runtime), inherited_scope=api(sku.inherited_scope))
            scope_api = api(observation_tools(), 'cur', 'names')
            require(all(getattr(provider.admission, key) is None and GATES[key] is None for key in GATES),
                    'GLOBAL_CALLER_ALL_EIGHT_GATES_MUST_STAY_CLOSED')
            assert_closed(provider, parent_raw)
    finally:
        os.chdir(previous)
    return dict(status='GLOBAL_OWNING_SOURCE_GRAPH_CHECKED', tree=manifest['basis_tree'],
                candidate_source_files=len(manifest['candidate_files']), Global=install_proof,
                sku_source_api=sku_api, package_derivation=route_proof, t3=t3, source_fence=guard,
                dated_laundry_and_credit_source_verified=True,
                existing_foundation_commit_writer=pin(foundation_writer(revised).encode()),
                exact_foundation_writer=foundation_proof,
                installed_scope_observer_parameters=scope_api,
                native_runner=native_proof, selected_Native_ids=[key for _, _, expected in factories for key in expected],
                gates=dict(GATES), pending=PENDING, exact_a625_root_verified=True,
                actual_SKU_Root_adopted=False, actual_ERP_cases=0,
                actual_Auth_cases=0, runtime_admission=False)


def assert_closed(provider, parent_raw):
    class Unavailable:
        def __fspath__(self):
            raise AssertionError('Global closed caller touched a path')

        def __getattr__(self, name):
            raise AssertionError('Global closed installer touched the cursor')

    def refuses(action):
        try:
            action()
        except ValueError as error:
            require(str(error) == 'CP7_GLOBAL_ENVELOPE_ACTUAL_FINAL_PARENT_AND_OWNING_SCOPE_PENDING',
                    'GLOBAL_CALLER_UNEXPECTED_CLOSED_REFUSAL')
        else:
            raise AssertionError('Global admission opened')

    def owning():
        with runtime(Unavailable(), Unavailable(), parent_receipt=Unavailable()):
            raise AssertionError('Global owning runtime opened')

    refuses(owning)
    refuses(lambda: provider.install(Unavailable(), parent_raw, b'{}'))
    require(REVIEWED_FIXTURES is None, 'GLOBAL_CALLER_UNVERIFIED_FIXTURES_ADMITTED')


def verify_preseal_source(candidate, catalogue_raw, output, *, sku_checkout):
    """Private runner entry from the existing preseal-source action."""
    parent_raw = exact(INPUTS / 'SKU_A625_VERIFIED_ROOT.json', ROOT_PIN['sha256'])
    proof = source_check(candidate, parent_raw, catalogue_raw, sku_checkout=sku_checkout)
    with (output / 'GLOBAL_OWNING_SOURCE_VALIDATION.json').open('x') as stream:
        json.dump(proof, stream, indent=2)
        stream.write('\n')
    print('GLOBAL_PARENT_GLOBAL_OWNING_CALLER_SOURCE_VERIFIED tree=' + BASELINE_TREE + ' gates_open=0', flush=True)
    return proof


def fixture_graph(fixtures, candidate, sku_checkout, parent_raw, profile_raw, *, ordinary, transfer, auth):
    api(fixtures.admit, 'candidate', 'sku_checkout', 'parent_raw', 'profile_raw')
    require(fixtures.HTTP_CASE_IDS == auth.plan.HTTP_CASE_IDS
            and fixtures.NATIVE_CASE_IDS == tuple(ordinary.proof['native_case_ids'])
            and fixtures.RPC_ALLOWLIST == auth.plan.RPC_PLAN
            and fixtures.TRANSFER_CASE_ID == transfer.CASE == 'OW06_TRANSFER_PAGE_25_TO_26',
            'GLOBAL_CALLER_EXACT_NATIVE_TRANSFER_AND_HTTP_CASES_REQUIRED')
    fixtures.admit(candidate, sku_checkout, parent_raw, profile_raw)
    return fixtures


def case_sources(candidate, runner, sku, roots, graph, writer_checkout, originals, require_reviewed):
    from . import dated_auth

    assets = runner / 'qualification/global_fixtures'
    audit = assets / 'audit'
    files = {
        'ordinary/native_ordinary.py': 'c9f99417a2f26c315626df04f6b40879c25561318352c42b6953a050abb1c0d9',
        'transfer/transfer_page_roots.py': '2db6e41c3f2c7fd53230de87b00121f30670c9c6a7f8a2fad9e53bb13ee22b17',
        'transfer/rebind.py': '3d645ff00268175db58ae2c7d94389e0b4547828b841a84f7a5eb74d8b2c886f',
    }
    for relative, digest in files.items():
        exact(assets / relative, digest)
    native = load('global_dated_private_ordinary', assets / 'ordinary/native_ordinary.py')
    with import_paths(assets / 'ordinary'):
        ordinary = native.bind(candidate, sku.FROZEN_SKU, audit, owner=sys.modules[__name__],
                               native_graph=graph, report_io=sku.report_io, accepted_roots=roots,
                               writer_checkout=writer_checkout)
    source = load('global_dated_ordinary_transfer', assets / 'transfer/transfer_page_roots.py')
    checked_writer(writer_checkout)
    transfer = source.bind(audit, assets / 'transfer/rebind.py',
                           accepted_roots=tuple(dict.fromkeys((*roots, writer_checkout))))
    with import_paths(candidate / 'scripts'):
        transfer.fixture_sources()
    auth = dated_auth.bind(audit, candidate, assets / 'auth_case_plan.py', originals,
                           require_reviewed=require_reviewed)
    return ordinary, transfer, auth


@contextmanager
def runtime(candidate, sku_checkout, *, parent_receipt=None, input_profile=None, sku_catalogue=None,
            reviewed_ordinary=False):
    """Bind the actual parent and child in one private runtime, under its scopes."""
    require(reviewed_ordinary is True, 'CP7_GLOBAL_ENVELOPE_ACTUAL_FINAL_PARENT_AND_OWNING_SCOPE_PENDING')
    candidate, sku_checkout = Path(candidate).absolute(), Path(sku_checkout).absolute()
    runner_checkout, runner_proof = runtime_checkout(candidate, sku_checkout)
    fixture_path, fixture_raw = tracked_source(runner_checkout, FIXTURE_ENTRY)
    fixtures = load('global_reviewed_owning_fixtures', fixture_path)
    profile_path, _ = tracked_source(runner_checkout, fixtures.PROFILE_PATH)
    _, fixture_manifest = tracked_source(runner_checkout, fixtures.MANIFEST_PATH)
    require(Path(input_profile).absolute() == profile_path, 'GLOBAL_CALLER_EXACT_TRACKED_PROFILE_REQUIRED')
    parent_raw, profile_raw = receipt_and_profile(parent_receipt, profile_path)
    catalogue_raw = read(sku_catalogue, 'GLOBAL_CALLER_EXACT_SKU_CATALOGUE_ORIGINAL_REQUIRED')
    gates = fixtures.GATES

    def require_reviewed():
        require_gates(gates)
        require(gates['RUNTIME_ENTRY'] == RUNNER_ENTRY and pin(parent_raw) == gates['PARENT_ROOT_RECEIPT']
                and pin(profile_raw) == gates['INPUT_PROFILE_PIN'],
                'GLOBAL_CALLER_EXACT_ORDINARY_SCOPE_REQUIRED')

    require_reviewed()
    writer_checkout = sku_checkout.parent / 'writer'
    manifest = source_files(candidate)
    admission = private_admission(load('global_exact_closed_admission', candidate / ADMISSION), gates)
    parent, _ = admission.runtime_admission(parent_raw, profile_raw)
    fence = load('global_exact_pre_database_fence', candidate / FENCE)
    with ExitStack() as scopes:
        scopes.enter_context(chdir(writer_checkout))
        with fence.fenced_source_read() as guard:
            provider, _ = prepared_provider(candidate, parent_raw, catalogue_raw)
            provider = private_provider(provider, admission)
            with candidate_imports(candidate):
                reviewed_profile(provider, profile_raw, parent_raw)
            for name in (SKU_ENTRY, SKU + '/package.py', SKU + '/run_window.py', SKU + '/report_io.py'):
                require(pin(read(sku_checkout / name, 'GLOBAL_CALLER_EXACT_ACTUAL_SKU_SOURCE_REQUIRED:' + name))
                        == manifest['candidate_files'][name], 'GLOBAL_CALLER_SKU_SUCCESSOR_SOURCE_REBIND_REQUIRED:' + name)
            sku = load('global_actual_accepted_SKU_entry', sku_checkout / SKU_ENTRY)
            sku.frozen(sku_checkout, parent['head'], parent['tree'])
            scopes.enter_context(inherited_scope(sku))
            engine = runtime_with_progress(sku, use_reviewed_digest=True)
            scopes.enter_context(engine.inherited_admission.parent_scope())
            source_proof = engine.admitted()
            with candidate_imports(sku_checkout):
                credit = prepare_credit_seal(sku)
            api(engine._sku_install_parent, 'cur')
            for operation in (engine._sku_install_delta, engine._sku_verify_installed):
                api(operation, 'cur', 'state')
            api(engine.trusted_installer_connection)
            api(engine.runner.scheduler_quiet, 'url')
            original, revised, _ = package_sources(sku, Path(engine.__file__))
            roots = inherited_native_roots(candidate, sku, sku_checkout)
            graph = native_graph(candidate, roots)
            native = graph[1]
            io = load('global_exact_frozen_T3_io', candidate / PACKAGE_IO)
            package_graph(engine.package, io, candidate, roots)
            identity_path = sku_checkout / IDENTITY
            require(pin(read(identity_path, 'GLOBAL_CALLER_EXACT_SKU_T3_IDENTITY_SOURCE_REQUIRED'))
                    == manifest['candidate_files'][IDENTITY], 'GLOBAL_CALLER_SKU_T3_IDENTITY_SOURCE_CHANGED')
            identity = load('global_exact_SKU_T3_identity', identity_path)
            identity.source()
            attempts = load('global_exact_single_attempt_policy', sku.FROZEN_AFUI / ATTEMPT)
            window = load('global_exact_Sku_real_WIB_budget', sku_checkout / SKU / 'run_window.py')
            originals = sku.report_io.complete_originals()
            ordinary, transfer, auth = case_sources(candidate, runner_checkout, sku, roots, graph, writer_checkout,
                                                     originals, require_reviewed)
            reviewed = fixture_graph(fixtures, candidate, sku_checkout, parent_raw, profile_raw,
                                      ordinary=ordinary, transfer=transfer, auth=auth)
            seed, identities, foundation_proof = bind_seed(writer_checkout)

            from . import p20_batch
            if p20_batch.enabled() or p21_mode.enabled():
                provider = p20_batch.bind_provider(provider, runner_checkout, candidate)

            def actual_day(cur):
                day = native.business_day.wib_day(cur)
                require(day.isoformat() == os.environ.get(window.DAY), 'GLOBAL_FOUNDATION_EXACT_REAL_WIB_DAY_REQUIRED')
                return day

            foundation = Foundation(seed, identities, foundation_proof, provider, actual_day)
            profile = json.loads(profile_raw)
            if p21_mode.enabled():
                from p21.g04_catalogue import bind_switch_roll

                tracked_source(runner_checkout, 'qualification/p21/g04_catalogue.py')
                switch_roll_receipt = bind_switch_roll(provider, candidate.parent / 'g04-product')
            lifecycle = DatedLifecycle(engine, provider, parent_raw, profile_raw, reviewed, credit=credit,
                                       sku_catalogue=catalogue_raw, inputs=profile, foundation=foundation)
            output = candidate / 'cp6-proof/t3'
            positives = ordinary.positives(output, originals)
            source_identity = dict(runner=runner_proof, candidate_head=parent['head'],
                                   candidate_tree=manifest['basis_tree'], candidate_src=COMBINED_SRC,
                                   sku_root=pin(parent_raw), input_profile=pin(profile_raw),
                                   fixture_entry=pin(fixture_raw), fixture_manifest=pin(fixture_manifest))
            auth_attempt = auth.attempt(source_identity, output)
            from . import case_schedule, ordinary_case_scope, ordinary_http
            http = ordinary_http.bind(
                runner_checkout / 'qualification/global_fixtures', candidate, plan=auth.plan, graph=graph,
                accepted_roots=roots, catalogue_raw=catalogue_raw, lifecycle=lifecycle,
                trusted_connection=engine.trusted_installer_connection, source_identity=source_identity,
                business_day=lambda: foundation.day)
            lifecycle.fixtures = case_schedule.bind(
                ordinary, transfer, lifecycle=lifecycle, attempt=auth_attempt, http_ids=reviewed.HTTP_CASE_IDS,
                http=http, db_scheduler=engine.runner.scheduler_quiet,
                trusted_connection=engine.trusted_installer_connection, output=output, originals=originals,
                observe_scope=ordinary_case_scope.bind(lifecycle))
            routes = lifecycle.runner(positives, observe_scope=observation_tools())
            owner = auth.writer(engine, lifecycle, routes, sku.report_io, original, revised, source_identity, auth_attempt)
            if p21_mode.enabled():
                from p21.installed import exercise
                from p21.checkpoints import record_case
                from p21.followup import auth_scope

                namespace = owner.run_inner.__globals__
                scoped_auth = auth_scope(namespace['_global_auth'])
                namespace['_global_auth'] = scoped_auth

                def observe_p21(conn, cur, state, report):
                    exercise(conn, cur, state, report, lifecycle=lifecycle, candidate=candidate,
                             switch_roll_receipt=switch_roll_receipt(state.global_installation), checkpoint=record_case,
                             auth=scoped_auth,package=namespace['package'])

                owner.run_inner.__globals__['_p21_installed_checks'] = observe_p21

        started = False

        def run_package():
            nonlocal started
            require(not started, 'GLOBAL_CALLER_SINGLE_OWNING_ATTEMPT_REQUIRED')
            require(receipt_and_profile(parent_receipt, input_profile) == (parent_raw, profile_raw),
                    'GLOBAL_CALLER_REVIEWED_PARENT_OR_PROFILE_CHANGED_BEFORE_WRITER')
            window.budget(policy=attempts)
            package_run = io.private_package_run(engine.package, owner.output.parent,
                                                 lambda browser_mode=False: owner.run())
            started = True
            with io.package_identity_scope(identity), attempts.single_attempt(native.business_day):
                package_run('install')
            return json.loads((owner.output.parent / 'T3_PACKAGE_INSTALL.json').read_bytes())

        yield SimpleNamespace(run=run_package, sku_source_proof=source_proof, source_fence=guard,
                              runner_source=runner_proof, candidate_tree=manifest['basis_tree'])


if __name__ == '__main__':
    cli = argparse.ArgumentParser()
    cli.add_argument('--source-check', required=True, type=Path, metavar='FIRST_GLOBAL_SOURCE')
    cli.add_argument('--sku-root', required=True, type=Path)
    cli.add_argument('--sku-catalogue', required=True, type=Path)
    cli.add_argument('--sku-checkout', required=True, type=Path)
    cli.add_argument('--writer-checkout', type=Path)
    args = cli.parse_args()
    print(json.dumps(source_check(args.source_check, args.sku_root.read_bytes(), args.sku_catalogue.read_bytes(),
                                  sku_checkout=args.sku_checkout, writer_checkout=args.writer_checkout), indent=2))

