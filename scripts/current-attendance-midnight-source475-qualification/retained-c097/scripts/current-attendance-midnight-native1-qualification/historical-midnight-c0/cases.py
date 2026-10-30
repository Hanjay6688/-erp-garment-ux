"""PREPARED standalone Native1 AFTER qualified original11; no DB/runner creation.

Original f265 component, all eleven callbacks and their monetary oracles remain
byte-exact. Administrative actor fixtures are not real Auth or screen journeys.
"""
from contextlib import contextmanager
from datetime import datetime, time, timedelta
from pathlib import Path
import importlib.util
import json
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ID = 'S03_NATIVE_MIDNIGHT_OUTPUT_UTC17_SAME_SOURCE_CID_5_5_10'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


oracle = load('S03_midnight_pure_oracle', HERE / 'oracle.py')
admission = load('S03_midnight_prerequisite', HERE / 'admission.py')


def originals():
    return load('S03_unchanged_original11', ROOT / 'scripts/current-attendance-period-choice-qualification/cases.py')


def one(cur, statement, args=()):
    return cur.execute(statement, args).fetchone()[0]


def set_utc(cur):
    one(cur, "select set_config('TimeZone','UTC',true)")
    assert one(cur, 'show TimeZone') == 'UTC', 'S03_MIDNIGHT_CALLER_MUST_BE_UTC'


@contextmanager
def timezone_restored(cur):
    """Restore the real caller zone on success AND SQL-error paths; retain error.

    Error rollback does not restore nontransactional sequences and is never
    reported as full boundary restoration. The owning runner still must restore.
    """
    old = one(cur, 'show TimeZone')
    savepoint = 's03_midnight_zone_' + uuid.uuid4().hex
    cur.execute('savepoint ' + savepoint)
    try:
        set_utc(cur)
        yield old
    except BaseException:
        cur.execute('rollback to savepoint ' + savepoint)
        one(cur, "select set_config('TimeZone',%s,true)", (old,))
        assert one(cur, 'show TimeZone') == old, 'S03_MIDNIGHT_CALLER_RESTORE_FAILED'
        cur.execute('release savepoint ' + savepoint)
        raise
    else:
        one(cur, "select set_config('TimeZone',%s,true)", (old,))
        assert one(cur, 'show TimeZone') == old, 'S03_MIDNIGHT_CALLER_RESTORE_FAILED'
        cur.execute('release savepoint ' + savepoint)


def require_quiet_fixed_days(cur, f, plan):
    """One fixed pair, checked before any fixture writes; never date shopping."""
    f.admin(cur)
    occupied = one(cur, """select
       exists(select 1 from erp.payroll_settlements where period_start<=%s and period_end>=%s)
    or exists(select 1 from erp.sewing_terminal_events where erp._cp3_business_date(physical_at)between %s and %s)
    or exists(select 1 from erp.work_completion_events where erp._cp3_business_date(physical_at)between %s and %s)
    or exists(select 1 from erp.attendance_records where attendance_date between %s and %s)
    or exists(select 1 from erp.attendance_hpp_pools where period_start<=%s and period_end>=%s)
    or exists(select 1 from cp7_attendance_choice.decisions_v1 where period_start<=%s and period_end>=%s)
    or exists(select 1 from cp7_attendance_choice.allocations_v1 where output_start<=%s and output_end>=%s)
    """, (plan['right'], plan['left'], plan['left'], plan['right'], plan['left'], plan['right'],
          plan['left'], plan['right'], plan['right'], plan['left'], plan['right'], plan['left'], plan['right'], plan['left']))
    if occupied:
        raise ValueError('S03_MIDNIGHT_FIXED_QUIET_PAIR_UNAVAILABLE_INCOMPLETE')


def output_pair(cur, f, source, plan):
    """One accepted cutting/pickup chain; Native work+terminal5/5, same source CID.

    Only snapshot/DRAFT work headers/lines are fixture inserts, as in the frozen
    accepted helper. Native writers perform every POST. The underlying helper
    also creates an actual material receipt10@10 and consumes that roll; this
    creation is real DML and has additional material economics, never no-DML.
    """
    src = f.hp.cp17().instal.wip_source.b
    prod = src.chain.production
    saved_contractor = prod.CONTRACTOR
    recorded = dict(work_ids=[], event_ids=[], actual_caller_zones=[])

    def setup(cur, po, group, batch, yields, when):
        assert sum(qty for _, _, qty in yields) == 10
        snapshot = str(uuid.uuid4())
        f.admin(cur)
        cur.execute('insert into erp.po_work_component_snapshots(id,po_id,work_component_id,sequence_no,rate_per_pcs_snapshot,committed_at)values(%s,%s,%s,1,0,%s)',
                    (snapshot, po, prod.COMPONENT, when(9, 30)))
        for instant in (plan['before'], plan['after']):
            completion = str(uuid.uuid4())
            src.chain.peer.ordinary(cur)
            set_utc(cur)
            cur.execute("insert into erp.work_completion_events(id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status,notes,created_by)values(%s,%s,%s,%s,%s,%s,'DRAFT',%s,%s)",
                        (completion, 'S03-MIDNIGHT-' + completion, po, source['contractor'], group, instant, f.REASON, src.chain.base.OPERATOR_APP))
            cur.execute('insert into erp.work_completion_lines(completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot)values(%s,%s,%s,5,5,0)',
                        (completion, snapshot, prod.COMPONENT))
            recorded['actual_caller_zones'].append(dict(writer='post_work_completion',zone=one(cur, 'show TimeZone')))
            cur.execute('select erp.post_work_completion(%s)', (completion,))
            prod.owner(cur)
            set_utc(cur)
            recorded['actual_caller_zones'].append(dict(writer='erp_record_sewing_terminal_v1',zone=one(cur, 'show TimeZone')))
            response = one(cur, 'select public.erp_record_sewing_terminal_v1(%s::jsonb,%s)',
                           (json.dumps(dict(work_completion_id=completion,qty_pcs=5,reason=f.REASON)), uuid.uuid4()))
            recorded['work_ids'].append(completion)
            recorded['event_ids'].append(response['sewing_terminal_event_id'])

    try:
        prod.CONTRACTOR = source['contractor']
        physical = src.two_size_fixture(cur, plan['left'] + timedelta(days=2), 'S03-MIDNIGHT-UTC17',q1=7,q2=3,work_setup=setup)
    finally:
        prod.CONTRACTOR = saved_contractor
    assert prod.CONTRACTOR == saved_contractor
    assert physical['day'] == plan['left']
    return dict(physical=physical, **recorded)


def read_events(cur, f, fixture):
    f.admin(cur)
    rows = cur.execute("""select e.id::text,e.source_work_completion_id::text,e.po_id::text,e.cutting_group_id::text,
      e.contractor_id::text,w.contractor_id::text,e.event_kind,e.qty_signed,w.status,
      erp._cp3_epoch_microseconds(e.physical_at),erp._cp3_epoch_microseconds(w.physical_at),
      (e.physical_at at time zone 'Asia/Jakarta')::date::text,(e.physical_at at time zone 'UTC')::date::text
      from erp.sewing_terminal_events e join erp.work_completion_events w on w.id=e.source_work_completion_id
      where e.id=any(%s::uuid[])order by e.physical_at,e.id""", (fixture['event_ids'],)).fetchall()
    keys = ('event_id','work_id','po_id','group_id','contractor_id','work_contractor_id','kind','qty','work_status',
            'event_epoch_us','work_epoch_us','wib_day','utc_day')
    return [dict(zip(keys, row)) for row in rows]


def run_boundary(cur, today, original):
    f = original.f
    plan = oracle.fixed_plan(today)
    with timezone_restored(cur) as caller_zone:
        f.admin(cur)
        if one(cur,'select erp.bb_business_today_v1()') != today:
            raise ValueError('S03_MIDNIGHT_NATIVE_BUSINESS_TODAY_MISMATCH')
        require_quiet_fixed_days(cur, f, plan)
        # The unmodified source helper chooses an exact quiet old period<=today-5.
        # No additional source money is added after the owning CARRY claim.
        source = f.source(cur, today)
        assert source['day'] < plan['left']
        set_utc(cur)
        accrual = original.original_accrual(cur, source)
        choice = original.choose(cur, source)
        assert choice['native_result'] is None and choice['inverse_journal_id'] is None
        fixture = output_pair(cur, f, source, plan)
        assert len(fixture['actual_caller_zones']) == 4
        assert all(row['zone'] == 'UTC' for row in fixture['actual_caller_zones'])
        set_utc(cur)
        events = read_events(cur, f, fixture)
        before, after = oracle.assert_events(events, plan, source)
        assert original.original_accrual(cur, source) == accrual
        assert f.native(cur, 'select cp7_attendance_choice.capture_v1(%s,%s,true)', (source['day'], source['day'])) == source['capture']
        f.admin(cur)
        assert one(cur, "select count(*)from erp.journal_entries where source_type='WORK_COMPLETION'and source_id=any(%s::uuid[])", (fixture['work_ids'],)) == 0
        assert one(cur, "select count(*)from erp.payroll_settlements where contractor_id=%s", (source['contractor'],)) == 1
        unassigned = one(cur,"""select coalesce(sum(l.debit-l.credit),0)from erp.journal_lines l
          join erp.journal_entries j on j.id=l.journal_entry_id where j.status='POSTED'
          and l.contractor_id=%s and l.po_id is null and l.account_id=erp.account_id('WIP')""",(source['contractor'],))
        assert unassigned * 100 == oracle.CENTS, 'S03_MIDNIGHT_ORIGINAL_UNASSIGNED_WIP_CHANGED'
        summaries = {}
        no_dml_before = f.census(cur)
        set_utc(cur)
        for name, start, end, expected in (
            ('BEFORE',plan['left'],plan['left'],[before]),
            ('AFTER',plan['right'],plan['right'],[after]),
            ('BOTH',plan['left'],plan['right'],[before,after]),
        ):
            assert one(cur, 'show TimeZone') == 'UTC'
            native = f.native(cur, 'select erp._build_attendance_hpp_manifest_v1(%s,%s)', (start, end))
            carried = f.native(cur, 'select cp7_attendance_choice.carry_preview_v1(%s,%s,%s)', (choice['decision_id'], start, end))
            payload = dict(f.body(source['day'],output=start),output_end=str(end))
            public = f.review(cur,source['owner'],'ALLOCATE',payload)
            summaries[name] = oracle.assert_manifest(native,carried,public,source,choice,start,end,expected)
            assert one(cur, 'show TimeZone') == 'UTC'
        assert f.census(cur) == no_dml_before, 'S03_MIDNIGHT_READ_CHANGED_FULL_ROWS_OR_SEQUENCES'
        assert original.original_accrual(cur, source) == accrual
        workspace = f.read(cur,source['owner'],source['day'])
        assert workspace['current_choice']['decision_id'] == choice['decision_id']
        assert workspace['current_choice']['journal_id'] is None
        assert workspace['current_allocation'] is None and workspace['amount_cents'] == str(oracle.CENTS)
        assert f.census(cur) == no_dml_before, 'S03_MIDNIGHT_WORKSPACE_CHANGED_FULL_ROWS_OR_SEQUENCES'
        assert one(cur, 'show TimeZone') == 'UTC'
    assert one(cur, 'show TimeZone') == caller_zone
    return dict(status='PASS',classification='ACTUAL_NATIVE_SESSION_FIXTURE_NOT_REAL_AUTH_BROWSER',
                source_period=str(source['day']),output_dates=[str(plan['left']),str(plan['right'])],
                contractor_id=source['contractor'],source_payroll=source['payroll'],source_cents=oracle.CENTS,
                physical_rows=events,exact_epoch_delta_us=1,actual_native_caller_zones=fixture['actual_caller_zones'],
                previews=summaries,full_business_rows_and_sequences_unchanged_for_reads=True,
                original_accrual_unchanged=True,source_recognition_once=True,choice_waiting_without_allocation=True,
                caller_zone_before=caller_zone,caller_zone_after=one(cur,'show TimeZone'),
                fixture_creation_has_Native_material_and_physical_DML=True,
                attendance_is_DATE_not_claimed_timestamp_boundary=True,
                production_go=False,independent_acceptance=False)


def cases(cur, today, *, state, evidence, fresh_original11, retained_original):
    """Outer caller owns install/full restore/gates; refuses before DB if unpinned."""
    proof = admission.admit(fresh_original11, retained_original, state_sources=state.get('sources'))
    original = originals()
    installed = original.f.composition.verify(cur, state)
    evidence['midnight_original11_admission'] = proof
    evidence['midnight_actual_installed_boundary'] = installed
    return [(ID, lambda: run_boundary(cur,today,original))]
