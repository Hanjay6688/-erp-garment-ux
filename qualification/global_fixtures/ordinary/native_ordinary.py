"""Bind retained ordinary Native fixtures to the dated a625 Global owner."""

from argparse import ArgumentParser
from dataclasses import dataclass
from functools import partial
from importlib import import_module
from inspect import signature
import json
import os
from pathlib import Path
from types import FunctionType, SimpleNamespace


CORE = 'agents/global-fixture-driver-sku457'
RECOVERY = 'agents/global-fixture-recovery'
ARCHIVES = {
    CORE + '/fixture_driver.py': '61cb7793f26785f356181305c107bddde6ee9b9562335011439ee86869ad574e',
    CORE + '/source_binding.py': '58125c9b1aca741fd1aa6eee199e15236ece02555d9fc99ce21d4a11d01d5075',
    CORE + '/SOURCE.json': '85101dc1a214599a0d2f891621288074d40347a7b185978da42bd797160ccf48',
    RECOVERY + '/foundation.py': '151a239b0485e722ddaa56ef2bdb9a084a2efb21007edb0f8b634e31ddbb3496',
    RECOVERY + '/inherited.py': 'a4603a06e765f2c4c6e41d390585373a07d48a4203c0908d52630f3b68453620',
    RECOVERY + '/recovery.py': '36c60bc42d4ef4101de906623411117e439a51f01a92c869f181c7a735edb0ea',
    'agents/global-owning-caller-sku457/SOURCE.json': 'a28461fc6f41dd12ed8d1fad18954f8b6b21dae685e369f08fd341f848d8a26b',
}
E_DIR = 'scripts/current-complete-de-integration-preparation/'
E_INPUTS = (E_DIR + 'witness.py', E_DIR + 'WITNESS_ORIGIN.json', E_DIR + 'retained-e17-component.py.txt',
            'scripts/cp6_bd_probe.py')
ORIGINAL_LABELS = ('GLOBAL_COMMITTED_E_OBSERVATION', 'GLOBAL_USED_INVERSE_FULL_STATE',
                   'GLOBAL_STALE_D1', 'GLOBAL_STALE_E')
NATIVE_ROUTES = 'nov13-recovery/global-owning-lanes/native_routes.py'
PREREQUISITES = 'nov13-recovery/global-owning-lanes/snapshot_prerequisites.py'
DIRTY_FIXTURE = 'nov13-recovery/dirty_global_fixture.py'
SEQUENCES = 'scripts/current-sku-managed-recovery-native27-qualification/sequence_prefix.py'
NOTA_SNAPSHOT_SOURCES = {
    'scripts/cp7_note_correction_cases.py': '1f6bfff2974b865d54600dec4fd515bd8b931efdd737c19e50eb8b1a094f604c',
    'scripts/cp6_bd_probe.py': 'c3add21e66d4d5544bf4e4d046a9fa8d64dbcb0cb285551a92c2d7405156b31b',
    'scripts/cp6_successor_regression.py': '7f4649e2ed0ab0ab948c65ebebbfa06b773e66f14bcac88a746143e372ea7b39',
    'scripts/cp6_ao_ap_inventory.py': '8c0715a2cfbcdd869e96c06f2bab3d40e5ce52d2dfa5b6480c9bf7bce1a6880f',
}
ROUTE_PINS = {
    NATIVE_ROUTES: '620734125679e7a0adccd7cdea0ba2511656fc4ebc803a3f38817aca6fee3635',
    PREREQUISITES: 'f8a009af194d1d820939735e197789ffa467efe8a9d461197764768d072c22cb',
    DIRTY_FIXTURE: 'dc811fb4aa9416b3a97349d4e2644e1e2fe0afb3bab8fdd6ee959e74edae0f7b',
    SEQUENCES: '1679d8abdc17c0cc906f026fd51a91510f5809e7323d6ef4dca32c05383f6c5d',
}
COORDINATOR_ROUTES = (
    ("def run_native(lanes, conn, cur, report, *, dirty, sequence, complete_group, observe_native, require_quiet):\n"
     '    """Execute the original groups and retain their observations in the owning report."""\n',
     'def run_native(lanes, conn, cur, report, *, dirty, sequence, complete_group, observe_native, require_quiet,\n'
     '               before_outside_inverse):\n'
     '    """Use the committed outside conversion until all of its consumers are done."""\n'
     '    if not callable(before_outside_inverse):\n'
     "        raise ValueError('GLOBAL_NATIVE_OUTSIDE_POSTED_CONSUMERS_CALLBACK_REQUIRED')\n"),
    ("    report['stale_outside_inverse'] = lanes.stale_after_exact_outside_inverse(conn, cur, outside, require_quiet)\n",
     '    require_quiet()\n'
     "    report['outside_posted_consumers'] = dict(status='INCOMPLETE')\n"
     "    conversion_id = outside['conversion_id']\n"
     '    before_outside_inverse(conversion_id)\n'
     '    require_quiet()\n'
     '    require_outside_posted(lanes, conversion_id)\n'
     "    report['outside_posted_consumers']['status'] = 'COMPLETE'\n"
     "    report['stale_outside_inverse'] = dict(status='INCOMPLETE')\n"
     "    report['stale_outside_inverse'] = lanes.stale_after_exact_outside_inverse(conn, cur, outside, require_quiet)\n"),
)


def require_outside_posted(lanes, conversion_id):
    with lanes.trusted_connection() as conn, conn.cursor() as cur:
        try:
            row = cur.execute(lanes.graph.conversion_query, (conversion_id,)).fetchone()
            if row is None or json.loads(row[0]).get('status') != 'POSTED':
                raise ValueError('GLOBAL_NATIVE_OUTSIDE_CONVERSION_MUST_STILL_BE_POSTED')
        finally:
            conn.rollback()


def preserve_nota_timezone(snapshot):
    """Retain the UTC snapshot data and restore the case's session setting."""
    def capture(cur):
        zone, = cur.execute("select current_setting('TimeZone')").fetchone()
        value = snapshot(cur)
        cur.execute("select set_config('TimeZone',%s,true)", (zone,))
        return value

    return capture


def bind_nota_snapshot(owner, original, roots, report_io, *, legacy_snapshot_root=None):
    """Route the exact case factory's snapshot through an isolated namespace."""
    namespace = original.__globals__
    snapshot = namespace['snapshot']
    boundary = namespace['b'].boundary.snapshot
    data = boundary.__globals__['data']
    routes = ((original, 'cp7_note_correction_cases.py', 'cases'),
              (snapshot, 'cp7_note_correction_cases.py', 'snapshot'),
              (boundary, 'cp6_successor_regression.py', 'snapshot'),
              (data, 'cp6_ao_ap_inventory.py', 'data'))
    require = owner.require
    probe = Path(namespace['b'].__file__).absolute()
    require(any(probe == root / 'scripts/cp6_bd_probe.py' for root in roots),
            'GLOBAL_NOTA_EXACT_SNAPSHOT_PROBE_PATH_REQUIRED')
    owner.exact(probe, NOTA_SNAPSHOT_SOURCES['scripts/cp6_bd_probe.py'])
    for function, filename, name in routes:
        relative = 'scripts/' + filename
        path = Path(function.__code__.co_filename).absolute()
        allowed = roots
        if legacy_snapshot_root is not None and filename in ('cp6_successor_regression.py', 'cp6_ao_ap_inventory.py'):
            allowed = (*roots, legacy_snapshot_root)
        require(any(path == root / relative for root in allowed) and function.__closure__ is None,
                'GLOBAL_NOTA_EXACT_SNAPSHOT_SOURCE_PATH_REQUIRED:' + relative + ':' + str(path))
        raw = owner.exact(path, NOTA_SNAPSHOT_SOURCES[relative])
        require(function.__code__ == report_io.function_code(raw, str(path), name),
                'GLOBAL_NOTA_EXACT_SNAPSHOT_CALLBACK_REQUIRED:' + name)
    require(snapshot.__globals__ is namespace, 'GLOBAL_NOTA_EXPECTED_ORIGINAL_SNAPSHOT_NAMESPACE_REQUIRED')
    wrapped = dict(namespace, snapshot=preserve_nota_timezone(snapshot))
    return FunctionType(original.__code__, wrapped, original.__name__, original.__defaults__)


@dataclass(frozen=True)
class OrdinaryFixtures:
    owner: object
    core: object
    inherited: object
    graph: object
    runner: object
    notes: object
    report_io: object
    run_native: object
    advisors: object
    proof: dict

    def positives(self, output, originals):
        return self.owner.NativePositives(self.graph.observer, self.runner, self.graph.factories,
                                          Path(output), originals, self.report_io)

    def make_lanes(self, lifecycle, state, *, verify, trusted_connection, output, originals):
        """Accept the installed dated child and the owner's existing callbacks."""
        signature(verify).bind(object())
        signature(trusted_connection).bind()
        output = Path(output)

        def native_observer(selected):
            return self.owner.NativePositives(self.graph.observer, self.runner, selected,
                                              output, originals, self.report_io)

        def retain(name, value):
            self.owner.require(name in ORIGINAL_LABELS, 'GLOBAL_ORDINARY_EXACT_ORIGINAL_NAME_REQUIRED')
            return originals.save_sorted(output / (name + '.json'), value, 'GLOBAL_ORDINARY_ORIGINAL_CONFLICT')

        graph = SimpleNamespace(**(vars(self.graph) | dict(native_observer=native_observer)))
        lanes = self.core.NativeLanes(provider=lifecycle.provider, parent_raw=lifecycle.parent_raw,
                                      profile_raw=lifecycle.profile_raw, state=state, graph=graph,
                                      trusted_connection=trusted_connection, verify=verify, retain=retain)
        output_scope = native_observer(()).output_scope
        lanes.run_nota = partial(self.inherited.run_nota, self.notes, self.runner, verify,
                                 output_scope, self.core.complete_group)
        return lanes


def bind(candidate, money, audit, *, owner, native_graph, report_io, accepted_roots, writer_checkout=None):
    """Resolve exact sources under the owner's existing source fence."""
    candidate, money, audit = (Path(path).absolute() for path in (candidate, money, audit))
    accepted_roots = tuple(Path(root).absolute() for root in accepted_roots)
    require = owner.require
    if writer_checkout is not None:
        from global_owning.foundation import checked_writer

        writer_checkout, _ = checked_writer(writer_checkout)
    observer, runner, factories, strict_proof = native_graph
    selected = [(Path(root).absolute(), factory, expected) for root, factory, expected in factories]
    require(len(selected) == len(owner.POSITIVES) == 3 and candidate in accepted_roots,
            'GLOBAL_ORDINARY_EXACT_CURRENT_NATIVE_GRAPH_REQUIRED')
    for (root, factory, expected), (name, relative, owning_expected) in zip(selected, owner.POSITIVES, strict=True):
        require(root in accepted_roots and factory is import_module(name).cases
                and tuple(expected.items()) == tuple(owning_expected.items()),
                'GLOBAL_ORDINARY_EXACT_CURRENT_NATIVE_FACTORY_REQUIRED:' + relative)
        observer.exact_function(factory, root / relative, observer.FACTORIES[relative], 'cases')

    for path, digest in ARCHIVES.items():
        owner.exact(audit / path, digest)
    manifest = json.loads((audit / CORE / 'SOURCE.json').read_bytes())
    for path in E_INPUTS:
        owner.exact(candidate / path, manifest['candidate'][path]['sha256'])
    for path, expected in manifest['money'].items():
        owner.exact(money / path, expected['sha256'])

    with owner.import_paths(audit / CORE, audit / RECOVERY, candidate / 'scripts'):
        core = import_module('fixture_driver')
        inherited = import_module('inherited')
        foundation = import_module('foundation')
        for module, expected in ((core, audit / CORE / 'fixture_driver.py'),
                                 (inherited, audit / RECOVERY / 'inherited.py'),
                                 (foundation, audit / RECOVERY / 'foundation.py')):
            require(Path(module.__file__).absolute() == expected,
                    'GLOBAL_ORDINARY_RETAINED_MODULE_COLLISION:' + module.__name__)
        archived = owner.load('global_ordinary_retained_binding', audit / CORE / 'source_binding.py')
        recovery = owner.load('global_ordinary_retained_recovery', audit / RECOVERY / 'recovery.py')
        archived.frozen_money(money)
        guarded = recovery.guarded_runner(runner, candidate, accepted_roots, report_io)
        require(guarded.strict_group.__code__ is runner.strict_group.__code__
                and guarded._strict_group_once.__code__ is runner._strict_group_once.__code__,
                'GLOBAL_ORDINARY_STRICT_RUNNER_CODE_CHANGED')
        original_notes, nota_proof = inherited.bind_nota(candidate, accepted_roots, report_io)
        notes = bind_nota_snapshot(owner, original_notes, accepted_roots, report_io, legacy_snapshot_root=writer_checkout)
        nota_proof.update(canonical_snapshot_session_restored=True, snapshot_sources=NOTA_SNAPSHOT_SOURCES,
                          legacy_snapshot_writer_checkout_verified=writer_checkout is not None)
        advisors = inherited.bind_advisors(candidate)
        with owner.import_paths(money / 'scripts'):
            moving = owner.load('global_ordinary_frozen_moving_cases', money / archived.MOVE)
        fixture = moving.f
        require(Path(fixture.__file__).absolute() == money / archived.MOVE_FIXTURE,
                'GLOBAL_ORDINARY_EXACT_FROZEN_OUTSIDE_FIXTURE_REQUIRED')
        owner.exact(Path(fixture.bf.__file__).absolute(), manifest['money']['scripts/cp6_bf_probe.py']['sha256'])
        for operation, parameters in ((moving.canonical, ('cur', 'today')), (moving.forward, ('cur', 'x')),
                                      (fixture.opening, ('cur', 'product', 'qty', 'unit', 'day', 'location')),
                                      (fixture.action, ('cur', 'kind', 'payload', 'key'))):
            owner.api(operation, *parameters)
        inverse, inverse_proof = archived.reverse_existing(moving, money / archived.MOVE)
        from global_owning.lifecycle import existing_native_usage
        committed_e, e_proof = archived.committed_witness(candidate, existing_native_usage)
        financial_truth = import_module('cp6_bd_probe')
        truth_path = Path(financial_truth.__file__).absolute()
        require(any(truth_path == root / E_INPUTS[-1] for root in (*accepted_roots, money))
                and financial_truth is fixture.b, 'GLOBAL_ORDINARY_EXACT_E_FINANCIAL_TRUTH_MODULE_REQUIRED')
        owner.exact(truth_path, manifest['candidate'][E_INPUTS[-1]]['sha256'])
        owner.api(financial_truth.all_truth, 'cur')
        owner.api(financial_truth.truth_quiet, 'before', 'after')

    positives = tuple(key for _, _, expected in selected for key in expected)
    require(positives == core.POSITIVE_IDS, 'GLOBAL_ORDINARY_EXACT_SIX_NATIVE_CASES_REQUIRED')
    # Only NativeLanes.seed_outside looks up this fallback. Canonical and forward
    # still run with the original frozen function globals and fixture helpers.
    clone = recovery.clone_namespace
    guarded_api = clone(fixture.b.api, seed=recovery.forbid_postseal_seed)
    moving = clone(moving, f=clone(fixture, b=clone(fixture.b, api=guarded_api)))
    d1, e = (import_module(name) for name, _, _ in owner.POSITIVES[:2])
    graph = SimpleNamespace(d1=d1, e=e, moving=moving, observer=observer, factories=selected,
                            financial_truth=financial_truth, commit_e=committed_e, reverse_existing=inverse,
                            existing_usage=existing_native_usage, conversion_query=core.CONVERSION)
    prerequisites = import_module('snapshot_prerequisites')
    owner.exact(Path(prerequisites.__file__).absolute(), ROUTE_PINS[PREREQUISITES])
    route_path = audit / NATIVE_ROUTES
    route_source, schedule_proof = recovery.derive(owner.exact(route_path, ROUTE_PINS[NATIVE_ROUTES]).decode(),
                                                    COORDINATOR_ROUTES)
    coordinator = dict(__name__='global_ordinary_scheduled_native_routes', __file__=str(route_path),
                       require_outside_posted=require_outside_posted)
    exec(compile(route_source, str(route_path), 'exec', dont_inherit=True), coordinator)
    require(coordinator['snapshot_prerequisites'] is prerequisites.observe,
            'GLOBAL_ORDINARY_EXACT_NATIVE_PREREQUISITES_REQUIRED')
    owner.exact(audit / DIRTY_FIXTURE, ROUTE_PINS[DIRTY_FIXTURE])
    owner.exact(candidate / SEQUENCES, ROUTE_PINS[SEQUENCES])
    dirty = owner.load('global_ordinary_lawful_dirty_fixture', audit / DIRTY_FIXTURE)
    sequence = owner.load('global_ordinary_sequence_prefix', candidate / SEQUENCES)
    owner.api(coordinator['run_native'], 'lanes', 'conn', 'cur', 'report', 'dirty', 'sequence', 'complete_group',
              'observe_native', 'require_quiet', 'before_outside_inverse')
    owner.api(sequence.strict_rollback, 'before', 'after')
    dirty_ids = tuple(key for key, _ in coordinator['dirty_factory'](dirty, graph)(None, None, None))
    nota_tags = coordinator['NOTA_TAGS']
    require(dirty_ids == dirty.CASE_IDS and tuple(nota_tags) == tuple(nota_proof['session_timezones']),
            'GLOBAL_ORDINARY_EXACT_DIRTY_AND_NOTA_ROUTE_REQUIRED')
    case_ids = (*positives, *(key for key, _ in core.PERMISSION), *dirty_ids,
                *(f'{key}_{tag}' for tag in nota_tags.values() for key in nota_proof['selected']))
    require(len(set(case_ids)) == len(case_ids) == 17, 'GLOBAL_ORDINARY_EXACT_NATIVE_CASE_IDS_REQUIRED')

    def run_native(lanes, conn, cur, report, *, observe_native, require_quiet, before_outside_inverse):
        result = coordinator['run_native'](lanes, conn, cur, report, dirty=dirty, sequence=sequence,
                                           complete_group=core.complete_group, observe_native=observe_native,
                                           require_quiet=require_quiet, before_outside_inverse=before_outside_inverse)
        require(tuple(result['business_cases']) == case_ids, 'GLOBAL_ORDINARY_NATIVE_CASE_REPORT_IDS_CHANGED')
        return result

    proof = dict(status='GLOBAL_A625_ORDINARY_FIXTURE_SOURCE_BOUND', tree=owner.COMBINED,
                 frozen_money_head=archived.FROZEN_MONEY[0], frozen_money_tree=archived.FROZEN_MONEY[1],
                 positive_ids=list(positives), Nota=nota_proof, strict_runner=strict_proof,
                 unchanged_strict_runner_code=True, committed_E=e_proof, outside_inverse=inverse_proof,
                 native_route_sources=ROUTE_PINS, outside_schedule=schedule_proof, native_case_ids=list(case_ids),
                 dirty_ids=list(dirty_ids), advisor_sources=advisors.source,
                 archive_pins=ARCHIVES, frozen_money_files=manifest['money'], actual_SQL_executed=0,
                 actual_Native_cases=0, actual_business_cases=0, runtime_admission=False, production_go=False)
    return OrdinaryFixtures(owner, core, inherited, graph, guarded, notes, report_io, run_native, advisors, proof)


def source_check(candidate, money, audit, *, check_schedule=False):
    """Resolve and register the original callbacks while the database is fenced."""
    from global_owning import owning

    candidate, money, audit = (Path(path).absolute() for path in (candidate, money, audit))
    fence = owning.load('global_ordinary_source_fence', candidate / owning.FENCE)
    previous = Path.cwd()
    try:
        os.chdir(candidate)
        with fence.fenced_source_read() as guard, owning.import_paths(candidate / 'scripts'):
            owning.source_files(candidate)
            roots = (candidate,)
            sku = owning.load('global_ordinary_current_sku_entry', candidate / owning.SKU_ENTRY)
            bindings = bind(candidate, money, audit, owner=owning, native_graph=owning.native_graph(candidate, roots),
                            report_io=sku.report_io, accepted_roots=roots)
            schedule_control = None
            if check_schedule:
                from verify_schedule import verify

                schedule_control = verify(bindings.run_native, bindings.proof['native_case_ids'])

            class NoCursor:
                def __getattr__(self, name):
                    raise AssertionError('Ordinary case registration touched a cursor: ' + name)

            positives = bindings.positives(candidate / 'cp6-proof/t3', None)
            owning.require(positives.ids == tuple(bindings.proof['positive_ids'])
                           and positives.runner is bindings.runner, 'GLOBAL_ORDINARY_POSITIVE_RUNNER_ROUTE_CHANGED')
            for _, factory, expected in positives.factories:
                callbacks = [name for name, callback in factory(NoCursor(), None)
                             if name in expected and callable(callback)]
                owning.require(callbacks == list(expected), 'GLOBAL_ORDINARY_POSITIVE_REGISTRATION_CHANGED')
            selected = bindings.proof['Nota']['selected']
            nota = [name for name, callback in bindings.notes(NoCursor(), None) if name in selected and callable(callback)]
            owning.require(nota == selected and len(owning.GATES) == 8 and all(value is None for value in owning.GATES.values())
                           and owning.REVIEWED_FIXTURES is None, 'GLOBAL_ORDINARY_EXACT_NOTA_AND_CLOSED_OWNER_REQUIRED')
            admission = owning.load('global_ordinary_closed_provider_admission', candidate / owning.ADMISSION)

            def untouched_connection():
                raise AssertionError('Closed ordinary adapter touched a connection')

            closed = SimpleNamespace(provider=SimpleNamespace(admission=admission), parent_raw=b'', profile_raw=b'')
            try:
                bindings.make_lanes(closed, NoCursor(), verify=lambda cursor: None,
                                    trusted_connection=untouched_connection, output=candidate / 'cp6-proof/t3',
                                    originals=None)
            except ValueError as error:
                owning.require(str(error) == 'CP7_GLOBAL_ENVELOPE_ACTUAL_FINAL_PARENT_AND_OWNING_SCOPE_PENDING',
                               'GLOBAL_ORDINARY_EXACT_CLOSED_ADMISSION_REQUIRED')
            else:
                raise AssertionError('Closed ordinary adapter reached an installed state')
    finally:
        os.chdir(previous)
    return dict(bindings.proof, registered_without_cursor=True, current_positive_runner_route_bound=True,
                adapter_refused_before_state_or_connection=True, source_fence=guard, ordinary_schedule_control=schedule_control,
                gates=dict(owning.GATES), reviewed_fixtures=None)


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    for field in ('candidate', 'money', 'audit'):
        parser.add_argument('--' + field, required=True, type=Path)
    parser.add_argument('--check-schedule', action='store_true')
    args = parser.parse_args()
    print(json.dumps(source_check(args.candidate, args.money, args.audit, check_schedule=args.check_schedule), indent=2))
