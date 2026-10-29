"""Three PREPARED actual Native continuations; no execution or SQL on import.

Owning-repaired D1 installation and its complete actual Native13 PASS must be
admitted by the outer adapter. Neither old077 nor these local controls prove it.
"""
from copy import deepcopy
from pathlib import Path
import importlib.util
import re
import uuid

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


n = load('d1_cont_retained_native_fixture', HERE / 'native_fixture.py')
guard = load('d1_cont_exact_source_guard', HERE / 'source_guard.py')
IDS = ('D1_CONT_ADDED_CAPACITY_APPLY220_NAMED_UNDO',
       'D1_CONT_MANUAL_REFUND230_NAMED_UNDO',
       'D1_CONT_SECOND_INCREASE275_AFTER_SIGNED_HISTORY')
NATIVE13_IDS = (
    'D_POSITIVE_CREDIT_INCREMENT', 'D_AFTER_ACTIVE_APPLY',
    'D_AFTER_REFUND_EXTRA_STAYS_CREDIT', 'D_MULTIFAMILY_ORDINAL',
    'D_REPLAY_EXACT_UUID', 'D_STALE_REVIEW_NO_EFFECT',
    'D_ACCESS_REVOKED_NO_EFFECT', 'D_SHORTFALL_NAMES_UNDO',
    'D_ROOT_BOOK_FLOOR_REFUSAL', 'D_ATOMIC_POST_FAILURE_RESTORE',
    'D_SECOND_REVISION_ORDINAL_HISTORY', 'D_AFTER_NAMED_UNDO_NO_FALSE_BLOCKER',
    'E_UNIMPLEMENTED_INCOMING_CORRECTION_STAYS_GUARDED',
)
ADMISSION = None
INSTALLED_STATE = None


def admit_native13(native_group, *, original_report_sha256, qualified_backend_commit, installed_state):
    """Outer adapter authenticates the raw original/package and owning successor.

    This dependency gate cannot validate a hosted run or open a connection. The
    callback factory separately verifies the full actual installed catalog.
    """
    global ADMISSION, INSTALLED_STATE
    ADMISSION, INSTALLED_STATE = None, None
    source = guard.admitted()
    assert re.fullmatch('[a-f0-9]{64}', original_report_sha256), 'D1_CONT_ORIGINAL_DIGEST_REQUIRED'
    assert re.fullmatch('[a-f0-9]{40}', qualified_backend_commit), 'D1_CONT_QUALIFIED_SUCCESSOR_COMMIT_REQUIRED'
    assert qualified_backend_commit not in (guard.BASE['published_commit'], guard.BASE['equivalent_local_commit']), 'D1_CONT_OWNING_REPAIRED_SUCCESSOR_REQUIRED'
    assert native_group.get('status') == 'PASS' and native_group.get('counts') == {'PASS': 13}, 'D1_CONT_ACTUAL_NATIVE13_PASS_REQUIRED'
    assert native_group.get('complete_boundary_restored') is True and not native_group.get('error'), 'D1_CONT_NATIVE13_COMPLETE_RESTORE_REQUIRED'
    assert set(native_group.get('cases', {})) == set(NATIVE13_IDS) == set(n.d1.IDS), 'D1_CONT_EXACT_NATIVE13_IDS_REQUIRED'
    assert all(case.get('status') == 'PASS' and case.get('full_boundary_restored') is True
               for case in native_group['cases'].values()), 'D1_CONT_NATIVE13_CASE_RESTORE_REQUIRED'
    assert installed_state['sources'] == n.product.sources(), 'D1_CONT_EXACT_INSTALLED_STAGE_REQUIRED'
    *_, catalog = n.product.runtime()
    assert set(installed_state['after']) == set(catalog.QUERIES) and len(installed_state['after']) == 22, 'D1_CONT_INSTALLED_ALL22_REQUIRED'
    INSTALLED_STATE = deepcopy(installed_state)
    ADMISSION = dict(qualified_backend_commit=qualified_backend_commit, original_report_sha256=original_report_sha256,
        source_manifest_sha256=source['source_manifest_sha256'], exact_native13_ids=list(NATIVE13_IDS),
        raw_actual_original_and_owning_repair_admitted_by_outer_adapter=True,
        callbacks_actual_execution=False, production_go=False, independent_acceptance=False)
    return deepcopy(ADMISSION)


def assert_signed_history(history, applied, undone, kind, amount):
    events = {row['id']: row for row in history['events']['document']}
    assert set(events) == {applied['consumption_event_id'], undone['consumption_event_id']}
    original, inverse = events[applied['consumption_event_id']], events[undone['consumption_event_id']]
    assert original['event_kind'] == inverse['event_kind'] == kind
    assert n.oracle.cents(original['amount']) == n.oracle.cents(amount)
    assert n.oracle.cents(inverse['amount']) == -n.oracle.cents(amount)
    assert original['restores_event_id'] is None and inverse['restores_event_id'] == original['id']
    assert undone['action'] == 'UNDO' and undone['restores_event_id'] == original['id']
    assert undone['amount'] == format(-n.oracle.cents(amount), '.2f')
    assert len(history['operations']['document']) == len(history['completions']['document']) == 2


def old_movements_retained(before, after, extra):
    old = {row['id']: row for row in before['document']}
    current = {row['id']: row for row in after['document']}
    assert len(current) == len(old) + extra and all(current.get(ident) == row for ident, row in old.items()), 'D1_CONT_OLD_MOVEMENT_MUTATED_OR_EXTRA_PHYSICAL_ROWS'


def prepare_250(cur, today, label):
    pair = n.fixture.prepare(cur, today, 'CREDIT')
    initial = n.observe(cur, pair, 'INITIAL_200')
    static = n.static_facts(cur, pair)
    movements = n.movements(cur, pair)
    original = n.correction.original_fact(cur, pair['initial_result']['return_id'])
    (out, p, v, q, key), evidence = n.invoke(cur, label+'_D1_250', lambda: n.d1.post(cur, pair))
    assert q['credit_delta'] == '50.00' and q['after_available'] == '250.00'
    assert n.static_facts(cur, pair) == static, 'D1_CONT_D1_CHANGED_STATIC_NATIVE_FACTS'
    assert n.correction.original_fact(cur, p['return_id']) == original
    old_movements_retained(movements, n.movements(cur, pair), 2)
    current = n.observe(cur, pair, 'D1_250')
    n.native.b.api.admin(cur)
    assert cur.execute('select count(*)from cp7_credit.initial_refund_operations where cohort_id=%s', (pair['initial_result']['credit_id'],)).fetchone()[0] == 0
    return dict(pair=pair, initial=initial, current=current, out=out, payload=p, version=v, quote=q, request=key,
                static=static, original=original, movements=n.movements(cur, pair),
                first_replacement_fact=n.correction.original_fact(cur, out['return_id']),
                history=n.d1_history(cur, [key]), evidence=evidence)


def assert_old(cur, setup):
    pair = setup['pair']
    assert n.static_facts(cur, pair) == setup['static'], 'D1_CONT_STATIC_PHYSICAL_HPP_SALE_PAYMENT_CHANGED'
    assert n.correction.original_fact(cur, setup['payload']['return_id']) == setup['original']
    assert n.correction.original_fact(cur, setup['out']['return_id']) == setup['first_replacement_fact']
    assert n.d1_history(cur, [setup['request']]) == setup['history'], 'D1_CONT_OLD_D1_FACTS_CHANGED'


def replay_d1(cur, setup, label):
    made, evidence = n.invoke(cur, label, lambda: n.correction.correct(cur, setup['payload'], setup['version'], setup['request']), no_effect=True)
    assert made == setup['out'], 'D1_CONT_D1_OLD_RECEIPT_CHANGED'
    return evidence


def consume_undo(cur, setup, kind, label):
    pair = setup['pair']
    amount, stage, restored = ('220.00', 'APPLY_220', 'APPLY_UNDONE') if kind == 'APPLY' else ('230.00', 'REFUND_230', 'REFUND_UNDONE')
    assert n.oracle.cents(amount) > n.oracle.cents('200.00'), 'D1_CONT_MUST_USE_NEWLY_ADDED_CAPACITY'
    call = (lambda: n.basic.apply(cur, pair, amount)) if kind == 'APPLY' else (lambda: n.refunds.refund(cur, pair, amount))
    (made, envelope, request), posted = n.invoke(cur, label+'_POST', call)
    assert made['action'] == made['event_kind'] == kind and made['amount'] == amount
    original_journal = n.native.journal(cur, made['journal_id'])
    used = n.observe(cur, pair, stage)
    assert_old(cur, setup)
    assert n.movements(cur, pair) == setup['movements'], 'D1_CONT_CONSUMER_CHANGED_STOCK_HISTORY'
    replay, replay_evidence = n.invoke(cur, label+'_POST_SAME_UUID', lambda: n.basic.command(cur, envelope, request), no_effect=True)
    assert replay == made
    undo_envelope, review = n.invoke(cur, label+'_NAMED_UNDO_REVIEW',
        lambda: n.basic.review(cur, n.basic.payload(pair, 'UNDO', original=made['consumption_event_id'])), no_effect=True)
    undo_request = uuid.uuid4()
    undone, inverse_evidence = n.invoke(cur, label+'_NAMED_UNDO', lambda: n.basic.command(cur, undo_envelope, undo_request))
    again, undo_replay = n.invoke(cur, label+'_UNDO_SAME_UUID', lambda: n.basic.command(cur, undo_envelope, undo_request), no_effect=True)
    assert again == undone
    duplicate = n.refused(cur, label+'_SECOND_UNDO_NEW_UUID', lambda: n.basic.command(cur, undo_envelope, uuid.uuid4()),
                         'CP7_CREDIT_CONSUMER_ORIGINAL_ALREADY_UNDONE')
    after = n.observe(cur, pair, restored)
    history = n.consumer_history(cur, pair)
    assert_signed_history(history, made, undone, kind, amount)
    assert n.native.journal(cur, made['journal_id']) == original_journal, 'D1_CONT_UNDO_MUTATED_ORIGINAL_CONSUMER_JOURNAL'
    assert_old(cur, setup)
    assert n.movements(cur, pair) == setup['movements']
    old_replay = replay_d1(cur, setup, label+'_OLD_D1_SAME_UUID')
    evidence = dict(post=posted, post_replay=replay_evidence, undo_review=review, undo=inverse_evidence,
                    undo_replay=undo_replay, duplicate_undo_refusal=duplicate, old_d1_replay=old_replay)
    raw = n.retain('D1_CONT_'+label+'_'+uuid.uuid4().hex.upper(), 'SIGNED_HISTORY', history)
    return dict(used=used, restored=after, original=made, undo=undone, evidence=evidence, raw_history=raw, history=history)


def apply_undo(cur, today):
    with n.native.isolated(cur):
        setup = prepare_250(cur, today, 'APPLY')
        actual = consume_undo(cur, setup, 'APPLY', 'APPLY220')
        return dict(status='PASS',coverage='ACTUAL_D1_ADDED_CAPACITY_TO_EXISTING_NATIVE_APPLY_AND_NAMED_UNDO',
            setup_evidence=setup['evidence'], used=actual['used'], restored=actual['restored'],
            signed_events=[actual['original'],actual['undo']], complete_prefixes=actual['evidence'], history_original=actual['raw_history'],
            immutable_old_D1_and_source_facts=True, old200_capacity_insufficient_for220=True,
            new_Auth_or_browser_claim=False, D_complete=False, E_complete=False, production_go=False)


def refund_undo(cur, today):
    with n.native.isolated(cur):
        setup = prepare_250(cur, today, 'REFUND')
        actual = consume_undo(cur, setup, 'REFUND', 'REFUND230')
        return dict(status='PASS',coverage='ACTUAL_EXPLICIT_MANUAL_REFUND_AFTER_D1_AND_NAMED_UNDO',
            setup_evidence=setup['evidence'], cash_after_D1='1000.00', used=actual['used'], restored=actual['restored'],
            signed_events=[actual['original'],actual['undo']], complete_prefixes=actual['evidence'], history_original=actual['raw_history'],
            immutable_old_D1_and_source_facts=True, old200_capacity_insufficient_for230=True,
            D1_auto_refund_created=False, manual_refund_only=True, new_Auth_or_browser_claim=False,
            D_complete=False, E_complete=False, production_go=False)


def second_increase(cur, today):
    with n.native.isolated(cur):
        setup = prepare_250(cur, today, 'SECOND')
        signed = consume_undo(cur, setup, 'APPLY', 'SECOND_APPLY220')
        pair = setup['pair']
        (second, p, v, q, key), evidence = n.invoke(cur, 'SECOND_D1_275',
            lambda: n.d1.post(cur, pair, '275.00', setup['out']['return_id']))
        assert q['credit_delta'] == '25.00' and q['after_available'] == '275.00' and q['active_consumers'] == [], q
        actual = n.observe(cur, pair, 'SECOND_D1_275')
        assert_old(cur, setup)
        assert n.consumer_history(cur, pair) == signed['history'], 'D1_CONT_SECOND_CORRECTION_MUTATED_CONSUMER_HISTORY'
        old_movements_retained(setup['movements'], n.movements(cur, pair), 2)
        n.native.b.api.admin(cur)
        chain = cur.execute('select operation_ordinal,predecessor_id::text,operation_id::text,return_id::text,replacement_id::text '
                            'from cp7_credit_correction_de.operations_v1 where sale_id=%s order by operation_ordinal', (p['sale_id'],)).fetchall()
        assert len(chain) == 2 and chain[0][0:2] == (1, None) and chain[1][0] == 2 and chain[1][1] == chain[0][2], chain
        assert chain[1][3] == setup['out']['return_id'] and chain[1][4] == second['return_id']
        statuses = cur.execute('select id::text,status from erp.sales_returns where id=any(%s::uuid[])order by id',
                              ([setup['payload']['return_id'], setup['out']['return_id'], second['return_id']],)).fetchall()
        assert dict(statuses) == {setup['payload']['return_id']:'REVERSED', setup['out']['return_id']:'REVERSED', second['return_id']:'POSTED'}
        assert setup['out']['return_status'] == 'POSTED', 'D1_CONT_OLD_HISTORICAL_RECEIPT_WAS_REWRITTEN'
        replay, second_replay = n.invoke(cur, 'SECOND_D1_SAME_UUID', lambda: n.correction.correct(cur, p, v, key), no_effect=True)
        assert replay == second
        first_replay = replay_d1(cur, setup, 'FIRST_D1_REPLAY_AFTER_SECOND_REVISION')
        history = n.d1_history(cur, [setup['request'], key])
        raw = n.retain('D1_CONT_SECOND_'+uuid.uuid4().hex.upper(), 'IMMUTABLE_CHAIN', dict(
            D1=history, consumers=signed['history'], live_return_statuses=statuses,
            historical_first_receipt=setup['out'], static_physical_HPP_original_sale_payment=setup['static']))
        return dict(status='PASS',coverage='ACTUAL_D1_SECOND_INCREASE_AFTER_SIGNED_APPLY_UNDO_HISTORY',
            source_and_target=actual, signed_events=[signed['original'],signed['undo']], operation_chain=chain,
            initial_D1_evidence=setup['evidence'], signed_consumer_prefixes=signed['evidence'],
            second_correction_prefix=evidence, exact_second_UUID=second_replay, exact_first_UUID_after_second=first_replay,
            immutable_old_D1_and_source_and_consumer_facts=True, raw_history=raw,
            live_first_replacement_legitimately_REVERSED=True, historical_first_receipt_still_POSTED=True,
            same_physical_and_static_nonPO_HPP=True, new_Auth_or_browser_claim=False,
            D_complete=False, E_complete=False, production_go=False)


def cases(cur, today):
    assert ADMISSION is not None and INSTALLED_STATE is not None, 'D1_CONT_REQUIRES_PRIOR_ACTUAL_NATIVE13_PASS_ON_OWNING_REPAIRED_STAGE'
    source = guard.admitted()
    assert source['source_manifest_sha256'] == ADMISSION['source_manifest_sha256'], 'D1_CONT_ADMITTED_SOURCE_CHANGED'
    n.require_local(cur)
    # Only the existing Native harness ERP test-usage grant is temporarily
    # restored for product verification, matching the frozen13 runner pattern.
    with n.helper.control.product_catalog(cur):
        n.product.verify(cur, INSTALLED_STATE)
    return [(name, lambda operation=operation: operation(cur, today))
            for name, operation in zip(IDS, (apply_undo, refund_undo, second_increase))]
