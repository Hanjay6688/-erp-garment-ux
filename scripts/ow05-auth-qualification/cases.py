"""Real GoTrue/PostgREST writes; Native SQL is used for isolated fixtures/read oracles."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal as D
import time
import uuid

from cp7_contractor_correction import native_cases as n

IDS=('OW05_REAL_AUTH_UNDO_CORRECT_NEW_RATE_AND_NOTA24',
     'OW05_TWO_DISTINCT_AUTH_USERS_SAME_PO_ONE_EFFECT')
REASON='OW05 koreksi mandor melalui login nyata'


def body(reply):
    assert reply['status']==200,reply
    return reply['body']


def prepare(http,today,reverse):
    with http.connect()as conn,conn.cursor()as cur:
        g=n.fixture(cur,today,reverse)
        n.auth.b.api.admin(cur)
        conn.commit()
    return g


def quote(user,g):
    return body(user.rpc('erp_cp7_get_mandor_correction_v1',dict(p_po=g['po'])))


def command_args(w,g):
    return dict(p_payload=dict(po_id=g['po'],contractor_id=g['target'],review_token=w['review_token'],change_reason=REASON),
                p_request=str(uuid.uuid4()))


def fp(http,g):
    with http.connect()as conn,conn.cursor()as cur:
        n.auth.b.api.admin(cur)
        result=n.one(cur,'select cp7_contractor_correction.financial_fingerprint_v1(%s)',(g['po'],))
        conn.rollback()
        return result


def journey(http,today):
    user=http.login('OWNER',label='ow05-journey')
    g=prepare(http,today,False)
    blocked=quote(user,g)
    assert not blocked['eligible'] and 'WORK'in{x['kind']for x in blocked['blockers']}
    refused=user.rpc('erp_cp7_correct_mandor_v1',command_args(blocked,g))
    assert refused['status']==400 and 'CP7_MANDOR_CORRECTION_DEPENDENCIES'in str(refused['body']),refused
    w=body(user.rpc('erp_cp7_get_sewing_completion_v1',dict(p_group=g['group'])))
    body(user.rpc('erp_cp7_save_sewing_completion_v1',dict(p_payload=dict(action='REVERSE',group_id=g['group'],
        event_id=g['terminal'],review_token=w['review_token'],change_reason=REASON),p_request=str(uuid.uuid4()),p_expected=w['group_version'])))
    before=fp(http,g);w=quote(user,g);assert w['eligible'],w
    args=command_args(w,g);r=body(user.rpc('erp_cp7_correct_mandor_v1',args))
    assert r['status']=='PICKUPS_REPLACED' and r['sewing_repost_required'] and fp(http,g)==before
    assert body(user.rpc('erp_cp7_correct_mandor_v1',args))==r and fp(http,g)==before
    w=body(user.rpc('erp_cp7_get_sewing_completion_v1',dict(p_group=g['group'])))
    sewing=body(user.rpc('erp_cp7_save_sewing_completion_v1',dict(p_payload=dict(action='RECORD',group_id=g['group'],qty_pcs='4',
        physical_at=g['at'](10).isoformat(),rate_choice='NEW',review_token=w['review_token'],change_reason=REASON),
        p_request=str(uuid.uuid4()),p_expected=w['group_version'])))
    assert D(str(sewing['result']['wage_amount']))==D('24.00'),sewing
    cards=body(user.rpc('erp_cp7_get_nota_workspace_v1',dict(p_section='SOURCES',p_query=dict(contractor_id=g['target']))))['page']['rows']
    assert cards
    with http.connect()as conn,conn.cursor()as cur:
        day=n.one(cur,"select(%s::timestamptz at time zone'Asia/Jakarta')::date",(g['at'](10),));conn.rollback()
    saved=body(user.rpc('erp_cp7_save_nota_v1',dict(p_action='SAVE',p_payload=dict(contractor_id=g['target'],note_date=str(today),
        period_start=str(day),period_end=str(today),notes=REASON,
        cards=[dict(card_key=c['card_key'],source_token=c['source_token'])for c in cards]),p_request=str(uuid.uuid4()),p_expected=None)))
    posted=body(user.rpc('erp_cp7_save_nota_v1',dict(p_action='POST',p_payload=dict(id=saved['note_id'],change_reason=REASON),
        p_request=str(uuid.uuid4()),p_expected=str(saved['row_version']))))
    payroll=body(user.rpc('erp_cp7_get_payroll_workspace_v1',dict(p_section='PAYROLLS',p_query=dict(id=posted['payroll_id']))))['page']['rows'][0]
    assert payroll['net_payable']=='24.00' and payroll['labor_total']=='24.00',payroll
    with http.connect()as conn,conn.cursor()as cur:
        n.auth.b.api.admin(cur)
        assert n.balance(cur,g['po'],'WIP')==g['base_wip']+D('24.00')
        assert n.balance(cur,None,'CONTRACTOR_PAYABLE',g['mandor'])==0
        assert n.balance(cur,None,'CONTRACTOR_PAYABLE',g['target'])==D('-24.00')
        assert n.one(cur,'select status from erp.work_completion_events where id=%s',(g['completion'],))=='REVERSED'
        conn.rollback()
    return dict(status='PASS',real_Auth=True,actual_PostgREST_inverse_correction_repost_and_nota=True,
        old_mandor_payable='0.00',new_mandor_payable='24.00',new_nota_payroll='24.00',
        correction_stock_HPP_unchanged=True,old_history_retained=True,winner_replay_zero_effect=True,
        fixture_master_data_created_in_browser=False,product_budgets_unchanged=True,production_go=False)


def two_users(http,today):
    users=[http.login('OWNER',label='ow05-race-'+str(i))for i in range(2)]
    assert users[0].auth_user_id!=users[1].auth_user_id
    g=prepare(http,today,True);args=[command_args(quote(u,g),g)for u in users];before=fp(http,g);blocked=[]
    with ThreadPoolExecutor(max_workers=2)as pool:
        with http.connect()as holder,holder.cursor()as cur:
            pid=cur.execute("select pg_backend_pid(),pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))").fetchone()[0]
            futures=[pool.submit(user.rpc,'erp_cp7_correct_mandor_v1',arg)for user,arg in zip(users,args)]
            try:
                deadline=time.monotonic()+20
                while True:
                    cur.execute('select pg_stat_clear_snapshot()')
                    blocked=cur.execute('''select pid,wait_event_type,wait_event from pg_stat_activity
                        where datname=current_database()and %s=any(pg_blocking_pids(pid))order by pid''',(pid,)).fetchall()
                    if len(blocked)==2:break
                    assert time.monotonic()<deadline,('OW05_TWO_AUTH_WAITERS_NOT_OBSERVED',blocked)
                    assert not any(f.done()for f in futures),[f.result()if f.done()else'pending'for f in futures]
                    time.sleep(.03)
                assert all(row[1:]==('Lock','advisory')for row in blocked),blocked
            finally:holder.rollback()
        replies=[f.result(timeout=60)for f in futures]
    winners=[i for i,r in enumerate(replies)if r['status']==200]
    assert len(winners)==1,replies
    win=winners[0];lose=1-win;r=body(replies[win])
    assert replies[lose]['status']==400 and 'CP7_MANDOR_CORRECTION_STALE_REVIEW'in str(replies[lose]['body']),replies
    assert body(users[win].rpc('erp_cp7_correct_mandor_v1',args[win]))==r
    lost=users[lose].rpc('erp_cp7_correct_mandor_v1',args[lose])
    assert lost['status']==400 and 'CP7_MANDOR_CORRECTION_STALE_REVIEW'in str(lost['body']),lost
    assert fp(http,g)==before
    with http.connect()as conn,conn.cursor()as cur:
        n.auth.b.api.admin(cur)
        assert n.one(cur,'select count(*)from cp7_contractor_correction.history_v1 where po_id=%s',(g['po'],))==1
        assert n.one(cur,"select count(*)from cp7_contractor_correction.requests_v1 where payload->>'po_id'=%s",(g['po'],))==1
        assert n.one(cur,"select count(*)from erp.cutting_pickups pk join erp.cutting_groups cg on cg.id=pk.cutting_group_id where cg.po_id=%s and pk.status='POSTED'",(g['po'],))==1
        assert n.one(cur,'select count(*)from cp7_contractor_correction.context_v1')==0
        conn.rollback()
    return dict(status='PASS',two_distinct_real_Auth_users=True,both_actual_PostgREST_backends_waited=blocked,
        one_success_one_stale_review=True,one_history_request_and_posted_pickup_only=True,
        winner_replay_zero_effect=True,loser_replay_zero_effect=True,stock_HPP_and_old_payments_unchanged=True,
        product_budgets_unchanged=True,production_go=False)


def http_cases(http,today):
    return [(IDS[0],lambda:journey(http,today)),(IDS[1],lambda:two_users(http,today))]
