"""OW05 initial Native journeys; money is read from Native journals, not UI totals."""
from decimal import Decimal as D
import json
import uuid

import cp7_cp17_fix_cases as old
import cp7_snapshot_cases as auth

IDS = ('OW05_ACTIVE_WAGE_GUIDANCE', 'OW05_NATIVE_SUCCESSOR_OLD_RATE',
       'OW05_NATIVE_SUCCESSOR_NEW_RATE', 'OW05_LOST_REPLY_REPLAY',
       'OW05_CHANGED_UUID_REFUSED', 'OW05_STALE_REVIEW_REFUSED',
       'OW05_INACTIVE_TARGET_REFUSED', 'OW05_LATE_NATIVE_POST_ATOMIC',
       'OW05_PRIVATE_CAPABILITY_DENIED', 'OW05_HISTORY_IMMUTABLE')
REASON = 'OW05 salah mandor baru diketahui sesudah jahit'


def one(cur, sql, args=()):
    return cur.execute(sql, args).fetchone()[0]


def workspace(cur, po):
    auth.actor(cur)
    result = one(cur, 'select public.erp_cp7_get_mandor_correction_v1(%s)', (po,))
    auth.b.api.admin(cur)
    return result


def payload(w, target):
    return dict(po_id=w['po_id'], contractor_id=target,
                review_token=w['review_token'], change_reason=REASON)


def command(cur, body, key=None):
    auth.actor(cur)
    result = one(cur, 'select public.erp_cp7_correct_mandor_v1(%s,%s)',
                 (json.dumps(body), str(key or uuid.uuid4())))
    auth.b.api.admin(cur)
    return result


def balance(cur, po, account, contractor=None):
    return one(cur, """select coalesce(sum(jl.debit-jl.credit),0)
        from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
        where jl.po_id=%s and jl.account_id=erp.account_id(%s)
        and je.status in('POSTED','REVERSED')
        and(%s::uuid is null or jl.contractor_id=%s::uuid)""", (po, account, contractor, contractor))


def fixture(cur, today, reverse=True):
    g = old.pickup_fixture(cur, today)
    rates = old.work_rates(cur, g)
    g['base_wip'] = balance(cur, g['po'], 'WIP')
    old.sewing_command(cur, old.sewing_workspace(cur, g), qty=4, at=g['at'](10))
    g['completion'] = str(one(cur, "select id from erp.work_completion_events where po_id=%s and status='POSTED'", (g['po'],)))
    g['terminal'] = str(one(cur, "select id from erp.sewing_terminal_events where po_id=%s and event_kind='SELESAI_DIJAHIT'", (g['po'],)))
    assert balance(cur, g['po'], 'WIP') == g['base_wip']+D('16.00')
    assert balance(cur, g['po'], 'CONTRACTOR_PAYABLE', g['mandor']) == D('-16.00')
    g['target'] = old.mandor_row(cur, 'OW05-B-'+uuid.uuid4().hex[:8])
    model = one(cur, 'select model_id from erp.production_orders where id=%s', (g['po'],))
    cur.execute("""insert into erp.contractor_work_rates(contractor_id,model_id,work_component_id,rate_per_pcs,effective_from)
        values(%s,%s,%s,5,%s)""", (g['target'], model, rates['component'], g['at'](0)))
    if reverse:
        old.sewing_command(cur, old.sewing_workspace(cur, g), event=g['terminal'])
        assert balance(cur, g['po'], 'WIP') == g['base_wip']
        assert balance(cur, g['po'], 'CONTRACTOR_PAYABLE', g['mandor']) == 0
    return g


def preserved(cur, g):
    return dict(payment_stock_HPP=one(cur, 'select cp7_contractor_correction.financial_fingerprint_v1(%s)', (g['po'],)),
        old_work=one(cur, 'select to_jsonb(we) from erp.work_completion_events we where id=%s', (g['completion'],)),
        old_lines=cur.execute('select to_jsonb(wl)from erp.work_completion_lines wl where completion_id=%s order by id', (g['completion'],)).fetchall(),
        old_allocations=cur.execute('''select to_jsonb(al)from erp.cutting_distribution_allocations al
            join erp.cutting_distribution_batches bt on bt.id=al.batch_id where bt.pickup_id=%s order by al.id''', (g['pickup'],)).fetchall())


def correct(cur, g, key=None):
    w = workspace(cur, g['po']); assert w['eligible'], w
    before = preserved(cur, g)
    response = command(cur, payload(w, g['target']), key)
    assert preserved(cur, g) == before
    assert response['status']=='PICKUPS_REPLACED' and response['sewing_repost_required'] is True
    assert len(response['replacements'])==1
    assert one(cur, 'select contractor_id::text from erp.production_orders where id=%s', (g['po'],))==g['target']
    assert one(cur, 'select status from erp.cutting_pickups where id=%s', (g['pickup'],))=='REVERSED'
    new_pickup = response['replacements'][0]['new_pickup_id']
    assert new_pickup != g['pickup']
    assert cur.execute('select contractor_id::text,picked_up_at from erp.cutting_pickups where id=%s', (new_pickup,)).fetchone()==(
        g['target'], one(cur, 'select picked_up_at from erp.cutting_pickups where id=%s', (g['pickup'],)))
    assert one(cur, 'select count(*)from cp7_contractor_correction.history_v1 where po_id=%s', (g['po'],))==1
    return w, response


def cases(cur, today):
    def active():
        g=fixture(cur,today,False);w=workspace(cur,g['po'])
        assert not w['eligible'] and {'SEWING','WORK','WORK_JOURNAL'} <= {x['kind']for x in w['blockers']}
        before=auth.b.boundary.snapshot(cur)
        auth.refused(cur,lambda:command(cur,payload(w,g['target'])),'CP7_MANDOR_CORRECTION_DEPENDENCIES')
        assert auth.b.boundary.snapshot(cur)==before
        return dict(status='PASS',active_wage_not_reassigned=True,steps=w['blockers'])

    def successor(new_rate=False):
        g=fixture(cur,today);correct(cur,g)
        w=old.sewing_workspace(cur,g)
        body=dict(action='RECORD',group_id=g['group'],qty_pcs='4',physical_at=g['at'](10).isoformat(),
            review_token=w['review_token'],change_reason=REASON,rate_choice='NEW'if new_rate else'OLD')
        auth.actor(cur)
        one(cur,'select public.erp_cp7_save_sewing_completion_v1(%s,%s,%s)',(json.dumps(body),str(uuid.uuid4()),w['group_version']))
        auth.b.api.admin(cur)
        wage=D('24.00')if new_rate else D('16.00')
        assert balance(cur,g['po'],'WIP')==g['base_wip']+wage
        assert balance(cur,g['po'],'CONTRACTOR_PAYABLE',g['mandor'])==0
        assert balance(cur,g['po'],'CONTRACTOR_PAYABLE',g['target'])==-wage
        assert one(cur,"select status from erp.work_completion_events where id=%s",(g['completion'],))=='REVERSED'
        assert one(cur,"select count(*)from erp.work_completion_events where po_id=%s and status='POSTED'and contractor_id=%s",(g['po'],g['target']))==1
        assert not cur.execute('''select je.id from erp.journal_entries je join erp.journal_lines jl on jl.journal_entry_id=je.id
            where jl.po_id=%s group by je.id having sum(jl.debit-jl.credit)<>0''',(g['po'],)).fetchall()
        return dict(status='PASS',Native_old_mandor_payable='0.00',Native_new_mandor_payable=str(wage),
            WIP_increment=str(wage),four_pcs_original_physical_time=True,old_history_retained=True)

    def replay(changed=False):
        g=fixture(cur,today);key=str(uuid.uuid4());w,r=correct(cur,g,key);p=payload(w,g['target'])
        before=auth.b.boundary.snapshot(cur)
        if changed:
            p['change_reason']=REASON+' diubah'
            auth.refused(cur,lambda:command(cur,p,key),'CP7_MANDOR_CORRECTION_REQUEST_CHANGED')
        else:assert command(cur,p,key)==r
        assert auth.b.boundary.snapshot(cur)==before
        return dict(status='PASS',zero_repeat_effect=True)

    def stale():
        g=fixture(cur,today);w=workspace(cur,g['po'])
        cur.execute('update erp.contractors set contractor_name=contractor_name||%s where id=%s',(' berubah',g['target']))
        before=auth.b.boundary.snapshot(cur)
        auth.refused(cur,lambda:command(cur,payload(w,g['target'])),'CP7_MANDOR_CORRECTION_STALE_REVIEW')
        assert auth.b.boundary.snapshot(cur)==before
        return dict(status='PASS',changed_target_cancels_review=True)

    def inactive():
        g=fixture(cur,today);cur.execute('update erp.contractors set is_active=false where id=%s',(g['target'],))
        w=workspace(cur,g['po']);before=auth.b.boundary.snapshot(cur)
        auth.refused(cur,lambda:command(cur,payload(w,g['target'])),'CP7_MANDOR_CORRECTION_TARGET')
        assert auth.b.boundary.snapshot(cur)==before
        return dict(status='PASS',inactive_mandor_refused=True)

    def late():
        g=fixture(cur,today);w=workspace(cur,g['po']);before=auth.b.boundary.snapshot(cur)
        cur.execute("""create function cp7_contractor_correction.test_fail_post()returns trigger language plpgsql as $$
            begin if new.status='POSTED'and old.status='DRAFT'then raise exception 'OW05_TEST_LAST_NATIVE_POST';end if;return new;end$$;
            create trigger ow05_test_last_post before update on erp.cutting_pickups for each row
            execute function cp7_contractor_correction.test_fail_post()""",prepare=False)
        try:auth.refused(cur,lambda:command(cur,payload(w,g['target'])),'OW05_TEST_LAST_NATIVE_POST')
        finally:
            auth.b.api.admin(cur);cur.execute('drop trigger ow05_test_last_post on erp.cutting_pickups;drop function cp7_contractor_correction.test_fail_post()',prepare=False)
        assert auth.b.boundary.snapshot(cur)==before
        assert one(cur,'select count(*)from cp7_contractor_correction.context_v1')==0
        assert one(cur,'select count(*)from cp7_contractor_correction.requests_v1')==0
        return dict(status='PASS',PO_old_pickup_group_and_new_drafts_all_rolled_back=True)

    def private():
        def attempt():
            auth.actor(cur)
            return one(cur,'select cp7_contractor_correction.admitted_group_v1(%s)',(str(uuid.uuid4()),))
        auth.refused(cur,attempt,'permission denied')
        auth.b.api.admin(cur)
        return dict(status='PASS',authenticated_cannot_create_or_read_capability=True)

    def immutable():
        g=fixture(cur,today);correct(cur,g)
        for sql in ['update cp7_contractor_correction.history_v1 set reason=reason||\' changed\'',
                    'delete from cp7_contractor_correction.history_v1','truncate cp7_contractor_correction.history_v1']:
            auth.refused(cur,lambda sql=sql:cur.execute(sql),'CP7_CUTTING_CORRECTION_HISTORY_IMMUTABLE')
        return dict(status='PASS',history_update_delete_truncate_refused=True)

    operations=(active,lambda:successor(False),lambda:successor(True),lambda:replay(False),lambda:replay(True),stale,inactive,late,private,immutable)
    assert len(operations)==len(IDS)
    return list(zip(IDS,operations))
