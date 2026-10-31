"""PREPARED additional reader Native3 AFTER unchanged fresh original11.

Fifteen existing function captures is NOT fifteen Native business cases.
Original eleven financial callbacks stay byte-exact; this module creates no
engine, connection, Auth service, workflow or hosted operation.
"""
from datetime import timedelta
from decimal import Decimal as D
from pathlib import Path
import importlib.util
import json
import uuid

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
IDS=(
 'S03_READER_NATIVE_OWNED_ACTIVE_PERIODS_AND_DISJOINT_P2_UNCHANGED',
 'S03_READER_NATIVE_CANCELLED_LIFETIME_AND_STALE_COMPOSITE_NO_EFFECT',
 'S03_READER_NATIVE_EXACT_HELD_P1_BLOCKS_LEGACY_REPLACE_AND_CREATE',
)


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


admission=load('S03_reader3_local_source_admission',HERE/'admission.py')


def original():
    return load('S03_unchanged_financial11_for_reader3',ROOT/'scripts/current-attendance-period-choice-qualification/cases.py')


def pool(cur,s,pid,core):
    workspace=core.f.hp.read(cur,s['owner'])
    found=[row for row in workspace['pools']if row['id']==pid]
    assert len(found)==1,('S03_READER_FIXTURE_POOL_NOT_ON_FIRST_PAGE',pid)
    return found[0]


def legacy_preview(cur,s,day,core):
    return core.f.hp.read(cur,s['owner'],day,day)['preview']


def owned(row,s,made,decision,output,closed):
    assert row['status']in('ACTIVE','CANCELLED')and row['actions']==[],row
    assert row['period_start']==row['period_end']==str(s['day'])
    assert 'period_hold'not in row
    assert type(row['attendance_choice']['output_period_closed'])is bool
    assert row['attendance_choice']==dict(domain='ATTENDANCE_PERIOD_CHOICE',decision_id=decision['decision_id'],
      allocation_id=made['event_id'],source_period_start=str(s['day']),source_period_end=str(s['day']),
      output_period_start=str(output),output_period_end=str(output),output_period_closed=closed)


def held_preview(preview,s,choice):
    assert preview['status']=='BLOCKED'and preview['can_create']is False,preview
    assert preview['blocker']['code']=='CP7_S03_PERIOD_HELD'
    assert preview['period_hold']==dict(domain='ATTENDANCE_PERIOD_CHOICE',decision_id=choice['decision_id'],
        source_period_start=str(s['day']),source_period_end=str(s['day']))
    assert 'attendance_choice'not in preview
    for key in('numerator_amount','denominator_qty','unit_cost_per_sewn_pcs','source_count','destination_count','po_count','manifest_sha256','review_token'):
        assert preview[key]is None,(key,preview[key])
    assert preview['pos']==[]


def cases(cur,today,*,state,evidence,fresh_original11):
    proof=admission.admit(fresh_original11)
    core=original();f=core.f
    # The owning accepted adapter supplies its physical catalogue context for
    # the exact inherited harness overlay, never dictionary projection.
    parent=core.admission.admit(core.composition.predecessor.sources())
    installed=core.composition.verify(cur,state)
    evidence['reader3_source_and_fresh11_admission']=proof
    evidence['reader3_retained_vendor_parent']=parent
    evidence['reader3_actual_installed15_capture_boundary']=installed

    def active_and_disjoint():
        source_day,out=f.quiet_days(cur,today);s=f.source(cur,today,day=source_day)
        choice=core.choose(cur,s)
        f.hp.sewn(cur,s['contractor'],'S03-READER-P2',out)
        made=core.allocate(cur,s,out);f.assert_pool(cur,s,made,out)
        # Legitimate P2 source/pool coexists; no overlap/output blanket hold.
        payroll=f.earned(cur,s['contractor'],out,D('20.02'))
        normal=f.native(cur,'select erp.create_attendance_hpp_pool_v1(%s::jsonb,%s)',
          (json.dumps(dict(period_start=str(out),period_end=str(out),reason=f.REASON)),uuid.uuid4()))
        f.native(cur,'select erp.activate_attendance_hpp_pool_v1(%s,%s,%s,%s)',
          (normal['pool_id'],f.REASON,uuid.uuid4(),normal['row_version']))
        f.assert_pool(cur,s,made,out)
        f.hp.set_closed(cur,s['day']);before=f.census(cur)
        row=pool(cur,s,made['pool_id'],core);owned(row,s,made,choice,out,False)
        assert row['period_closed']is True
        ordinary=pool(cur,s,normal['pool_id'],core)
        assert 'attendance_choice'not in ordinary and 'period_hold'not in ordinary
        assert ordinary['actions']==['CANCEL']and ordinary['period_closed']is False
        native_row=next(p for p in f.hp.native_pools(cur,out)if p['id']==normal['pool_id'])
        f.hp.same(cur,ordinary,native_row)
        preview=legacy_preview(cur,s,out,core)
        assert 'period_hold'not in preview and preview['status']=='READY'
        assert D(preview['numerator_amount'])==D('20.02')and preview['denominator_qty']==10
        assert f.census(cur)==before
        assert f.one(cur,'select period_start from erp.payroll_settlements where id=%s',(payroll,))==out
        return dict(status='PASS',owned_source_closed_output_open=True,permanent_owned_metadata=True,
                    ordinary_disjoint_P2_financial_fields_equal_Native=True,ordinary_P2_CANCEL_remains=True,
                    P2_source_amount='20.02',P1_carry_amount='1000.03',read_full_rows_and_sequences_equal=True)

    def lifetime_and_stale():
        source_day,out=f.quiet_days(cur,today);s=f.source(cur,today,day=source_day)
        choice=core.choose(cur,s)
        f.hp.sewn(cur,s['contractor'],'S03-READER-LIFETIME',out)
        made=core.allocate(cur,s,out);f.assert_pool(cur,s,made,out)
        f.admin(cur);old=f.one(cur,'select to_jsonb(p)from erp.attendance_hpp_pools p where id=%s',(made['pool_id'],))
        cancelled=f.save(cur,s['owner'],'CANCEL_ALLOCATION',f.body(s['day']));core.choice_audit(cur,s,cancelled)
        f.refused(cur,lambda:f.native(cur,'select cp7_hpp_pool.pool_json(jsonb_populate_record(null::erp.attendance_hpp_pools,%s::jsonb),null)',
            (json.dumps(old,default=str),)),'CP7_S03_HPP_READ_CHANGED')
        first=pool(cur,s,made['pool_id'],core);owned(first,s,made,choice,out,False)
        # Explicit accepted accounting-control fixture reopens source P1 for
        # owning correction; original accrual/restoration book dates stay fixed.
        f.hp.set_closed(cur,s['day']-timedelta(days=1))
        replacement=f.save(cur,s['owner'],'CORRECT',f.body(s['day'],'CARRY'));core.choice_audit(cur,s,replacement)
        assert replacement['decision_id']!=choice['decision_id']
        owned(pool(cur,s,made['pool_id'],core),s,made,choice,out,False)
        reversed_choice=f.save(cur,s['owner'],'REVERSE',f.body(s['day']));core.choice_audit(cur,s,reversed_choice)
        before=f.census(cur);owned(pool(cur,s,made['pool_id'],core),s,made,choice,out,False)
        assert f.read(cur,s['owner'],s['day'])['current_choice']is None
        assert f.census(cur)==before
        return dict(status='PASS',cancelled_pool_S03_ownership_survives_correction_and_reversal=True,
                    stale_composite_explicit_READ_CHANGED_full_no_effect=True,read_full_rows_and_sequences_equal=True)

    def exact_hold():
        s=f.source(cur,today);g=f.hp.sewn(cur,s['contractor'],'S03-READER-ORDINARY-P1',s['day'])
        ordinary=f.native(cur,'select erp.create_attendance_hpp_pool_v1(%s::jsonb,%s)',
          (json.dumps(dict(period_start=str(s['day']),period_end=str(s['day']),reason=f.REASON)),uuid.uuid4()))
        active=f.native(cur,'select erp.activate_attendance_hpp_pool_v1(%s,%s,%s,%s)',
          (ordinary['pool_id'],f.REASON,uuid.uuid4(),ordinary['row_version']))
        f.native(cur,'select erp.cancel_attendance_hpp_pool_v1(%s,%s,%s,%s)',
          (ordinary['pool_id'],f.REASON,uuid.uuid4(),active['row_version']))
        f.admin(cur);event,version=cur.execute("select id,row_version from erp.sewing_terminal_events where cutting_group_id=%s and event_kind='SELESAI_DIJAHIT'",(g['group'],)).fetchone()
        f.native(cur,'select erp.reverse_sewing_terminal_v1(%s,%s,%s,%s)',(event,f.REASON,uuid.uuid4(),version))
        s['capture']=f.native(cur,'select cp7_attendance_choice.capture_v1(%s,%s,true)',(s['day'],s['day']))
        choice=core.choose(cur,s)
        before=f.census(cur);row=pool(cur,s,ordinary['pool_id'],core)
        assert row['status']=='CANCELLED'and row['actions']==[]and 'attendance_choice'not in row
        assert row['period_hold']==dict(domain='ATTENDANCE_PERIOD_CHOICE',decision_id=choice['decision_id'],
          source_period_start=str(s['day']),source_period_end=str(s['day']))
        held_preview(legacy_preview(cur,s,s['day'],core),s,choice)
        # An overlapping but different exact source period is not held.
        adjacent=s['day']+timedelta(days=1)
        overlap=f.hp.read(cur,s['owner'],s['day'],adjacent)['preview'];assert 'period_hold'not in overlap
        assert f.census(cur)==before
        # Valid late old-period output may change eligibility while a choice waits.
        # Native preview is now READY, but its exact source period remains held.
        f.hp.sewn(cur,s['contractor'],'S03-READER-LATE-P1',s['day'])
        before=f.census(cur)
        native=f.native(cur,'select erp.preview_attendance_hpp_pool_v1(%s,%s)',(s['day'],s['day']))
        assert native['status']=='READY'and native['denominator_qty']==10
        held_preview(legacy_preview(cur,s,s['day'],core),s,choice)
        assert f.census(cur)==before
        f.refused(cur,lambda:f.native(cur,'select erp.create_attendance_hpp_pool_v1(%s::jsonb,%s)',
          (json.dumps(dict(period_start=str(s['day']),period_end=str(s['day']),reason=f.REASON)),uuid.uuid4())),'CP7_S03_PERIOD_CLAIMED')
        return dict(status='PASS',ordinary_historical_pool_not_mislabelled_S03_owned=True,
                    exact_source_hold_disables_legacy_REPLACE_CREATE=True,different_overlapping_source_not_held=True,
                    late_output_Native_READY_vs_legacy_held_BLOCKED=True,unchanged_financial_guard_refusal_full_no_effect=True,
                    read_full_rows_and_sequences_equal=True)

    return list(zip(IDS,(active_and_disjoint,lifetime_and_stale,exact_hold)))
