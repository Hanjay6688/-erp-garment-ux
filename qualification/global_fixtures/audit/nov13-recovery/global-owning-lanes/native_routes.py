"""Wire the retained Native cases into the disposable Global owner's case phase."""

from functools import partial
from pathlib import Path
from types import SimpleNamespace

from snapshot_prerequisites import observe as snapshot_prerequisites


SIGNED_CASE_CALLBACKS = ('_setup', '_intent', '_refuse')
NOTA_TAGS = {'Asia/Jakarta': 'WIB', 'UTC': 'UTC'}


def signed_fixture(graph):
    root, factory, _ = graph.factories[-1]
    path = root / graph.observer.SIGNED
    expected = graph.observer.FACTORIES[graph.observer.SIGNED]
    graph.observer.exact_function(factory, path, expected, 'cases')
    namespace = factory.__globals__
    functions = {name: namespace[name] for name in SIGNED_CASE_CALLBACKS}
    for name, operation in functions.items():
        graph.observer.exact_function(operation, path, expected, name)
    return SimpleNamespace(**functions, cmd=namespace['cmd'])


def dirty_factory(dirty, graph):
    signed = signed_fixture(graph)
    ids = dirty.CASE_IDS

    def factory(cur, today, lanes):
        operations = (
            partial(dirty.d1_case, cur, today, lanes),
            partial(dirty.e_case, cur, today, lanes),
            partial(dirty.source_case, cur, today, lanes, signed),
        )
        return list(zip(ids, operations, strict=True))

    return factory


def actual_native_cases(report):
    cases = {}
    groups = [report[key]['cases'] for key in ('positive_originals', 'permission_originals', 'lawful_dirty_original')]
    notas = report['nota_originals']
    if notas.keys() != NOTA_TAGS.keys():
        raise ValueError('GLOBAL_NATIVE_EXACT_NOTA_TIMEZONES_REQUIRED')
    groups += [{f'{name}_{tag}': result for name, result in notas[zone]['cases'].items()}
               for zone, tag in NOTA_TAGS.items()]
    for group in groups:
        if cases.keys() & group.keys() or any(case['status'] != 'PASS' for case in group.values()):
            raise ValueError('GLOBAL_NATIVE_EXACT_PASS_ORIGINALS_REQUIRED')
        cases.update(group)
    return cases


def run_native(lanes, conn, cur, report, *, dirty, sequence, complete_group, observe_native, require_quiet):
    """Execute the original groups and retain their observations in the owning report."""
    if 'outside_SKU' in report:
        raise ValueError('GLOBAL_FIXTURE_ONE_COMMITTED_SETUP_ATTEMPT_REQUIRED')
    require_quiet()
    try:
        report['supplier_accessory_prerequisites'] = snapshot_prerequisites(cur)
    finally:
        conn.rollback()
    if report['supplier_accessory_prerequisites']['status'] != 'PASS':
        raise ValueError('GLOBAL_SUPPLIER_ACCESSORY_PREREQUISITES_REFUSED')
    original = lanes.graph.native_observer(())
    dirty_cases = dirty_factory(dirty, lanes.graph)
    report['outside_SKU'] = dict(status='INCOMPLETE')
    outside = lanes.seed_outside(conn, cur, require_quiet)
    report['outside_SKU'] = outside
    before = lanes.isolated_full_state()

    def run_dirty():
        def factory(cursor, today):
            return dirty_cases(cursor, today, lanes)

        def verify(cursor):
            lanes.graph.existing_usage(cursor)
            return lanes.verify_child(cursor)

        with original.output_scope():
            group = original.runner.strict_group('GLOBAL_FIRST_NATIVE_LAWFUL_DIRTY', factory, verify)
        report['lawful_dirty_original'] = group
        return complete_group(group, dirty.CASE_IDS)

    # Each strict group owns its own transaction and leaves the setup committed.
    # Keep the original report from one group even when a later group fails.
    groups = (
        ('positive_originals', partial(lanes.observe_positives, outside, observe_native)),
        ('permission_originals', partial(lanes.observe_permissions, outside, require_quiet)),
        ('lawful_dirty_original', run_dirty),
        ('nota_originals', partial(lanes.run_nota, require_quiet)),
    )
    for name, run in groups:
        require_quiet()
        report[name] = dict(status='INCOMPLETE')
        report[name] = run()
    require_quiet()
    after = lanes.isolated_full_state()
    restored = sequence.strict_rollback(
        dict(catalog=before['full25'], data=before['full_rows_and_sequences']),
        dict(catalog=after['full25'], data=after['full_rows_and_sequences']),
    )
    report['isolated_native_restore'] = dict(
        full25_equal=True, all_current_table_rows_equal=restored['all_current_table_rows_equal'],
        sequence_prefix=restored['sequence_prefix'],
    )
    cases = actual_native_cases(report)
    require_quiet()

    committed = lanes.commit_e(conn, cur, outside, require_quiet)
    report['committed_E'] = committed
    report['used_inverse'] = lanes.used_inverse(committed, require_quiet)
    report['stale_outside_inverse'] = lanes.stale_after_exact_outside_inverse(conn, cur, outside, require_quiet)
    require_quiet()
    return dict(business_cases=cases, used_guard_refused_before_DDL=report['used_inverse']['used_guard_refused_before_DDL'])
