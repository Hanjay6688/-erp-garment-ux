"""Same retained two-session schedule, explicit current refusal and full boundary.

The old SALE_REVERSE_COMMIT result remains INCOMPLETE and is not relabelled.
This successor checks the original final state and financial report, then adds
all-table, all-sequence and complete catalog equality for the refused return.
The original SALE_REVERSE_ABORT positive control executes byte unchanged.
"""
from datetime import timedelta
from urllib.parse import urlparse
import threading,traceback
import cp7_retained_cp6_fixture as fixture
import cp6_v2620ah_concurrency as ah
from cp7_ab_bounded_chain import composition as product

CURRENT=False
IDS=('SALE_REVERSE_COMMIT_RETURN_ATOMIC_CURRENT_GUARD',
     'SALE_REVERSE_ABORT_RETURN_RETAINED_SUCCESS')
old,catalog=ah.old,product.catalog


def committed_reversal():
    f=ah.fixture();response={};thread=None
    expected_primary='CP7_NATIVE_EMPTY_ACTIVE_SOURCE_REQUIRED'if CURRENT else'Original sale must be active/posted'
    with old.connect('return-atomic-first')as first,old.connect('return-atomic-second')as second:
        try:
            with first.cursor()as cur:
                ah.reverse(cur,f)
                # Resolve deferred constraints as the operation's real actor.
                # Only then use the existing audit identity for complete reads.
                cur.execute('set constraints all immediate')
                ah.actors.admin(cur)
                expected_data=catalog._data(cur)
                expected_catalog=catalog._catalog_rows(cur)
            thread=threading.Thread(target=old.worker,args=(second,ah.post(1),f,response),daemon=True)
            thread.start();lock=old.await_lock(second.info.backend_pid)
            assert first.info.backend_pid in lock[2],lock
            first.commit()
            thread.join(30);assert not thread.is_alive(),'RETURN_ATOMIC_SECOND_SESSION_STUCK'
        finally:
            first.rollback()
            if thread is not None and thread.is_alive():second.cancel();thread.join(5)
    assert response.get('committed')is False and response.get('sqlstate')=='P0001',response
    assert response.get('error','').splitlines()[0]==expected_primary,response
    with old.connect('return-atomic-observe')as conn,conn.cursor()as cur:
        ah.actors.admin(cur)
        actual_data=catalog._data(cur);actual_catalog=catalog._catalog_rows(cur)
        data_changes={k:dict(expected=expected_data.get(k),actual=actual_data.get(k))
            for k in set(expected_data)|set(actual_data)if expected_data.get(k)!=actual_data.get(k)}
        catalog_changes={k:sorted(n for n in set(expected_catalog[k])|set(actual_catalog[k])
            if expected_catalog[k].get(n)!=actual_catalog[k].get(n))
            for k in expected_catalog if expected_catalog[k]!=actual_catalog[k]}
        assert not data_changes,('REFUSED_RETURN_CHANGED_ROWS_OR_SEQUENCES',data_changes)
        assert not catalog_changes,('REFUSED_RETURN_CHANGED_FULL22',catalog_changes)
        state=cur.execute("""select s.status,
          (select coalesce(sum(i.qty_pcs),0)from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id
           where r.sale_id=s.id and r.status='POSTED'),
          (select count(*)from erp.sales_returns r where r.sale_id=s.id and r.status='POSTED')
          from erp.sales_headers s where s.id=%s""",(f['sale']['sale_id'],)).fetchone()
        assert state==('REVERSED',0,0),state
        today=ah.base.one(cur,"select(statement_timestamp()at time zone'Asia/Jakarta')::date")
        report=ah.family.report(cur,today)
    return dict(status='PASS',observed_lock=lock,second=response,final_state=state,report=report,
        expected_refusal_primary=expected_primary,all_data_and_sequences=actual_data,
        first_reversal_only_data_sha256=catalog.digest(expected_data),refused_return_data_sha256=catalog.digest(actual_data),
        first_reversal_only_catalog_sha256=catalog.digest(expected_catalog),refused_return_catalog_sha256=catalog.digest(actual_catalog),
        catalog_group_count=len(actual_catalog),all22_equal=True,refused_return_zero_persisted_effects=True,
        original_final_state_and_financial_oracle_unchanged=True,fixture_admin_changed_posted_data=False)


def races(tools,today):
    url=urlparse(tools.admin)
    assert url.hostname in('127.0.0.1','localhost')and url.path=='/cp6_auditor_race'
    result=[]
    for name,operation in zip(IDS,(committed_reversal,lambda:ah.run_case('SALE_REVERSE_ABORT'))):
        def run(n=name,fn=operation):
            preparation={};previous=old.CLONE;old.CLONE=tools.admin
            try:
                with tools.connect()as conn,conn.cursor()as cur:
                    old.actors.admin(cur)
                    day=old.base.one(cur,"select(statement_timestamp()at time zone'Asia/Jakarta')::date")-timedelta(days=3)
                    assert day==today-timedelta(days=3),'RETAINED_RACE_BUSINESS_DAY_CHANGED'
                    old.prior.set_open_period(cur,day-timedelta(days=5))
                    fixture.prepare(cur,today,current=CURRENT,closed_through=day-timedelta(days=5),evidence=preparation)
                raw=fn();assert raw['status']=='PASS',raw
                return dict(status='PASS',case_id=n,original_result=raw,fixture_day=str(day),
                    seed_prerequisite_preparation=preparation,legacy_result_relabelled=False)
            except Exception as error:
                return dict(status='INCOMPLETE',case_id=n,error=str(error),traceback=traceback.format_exc(),
                    seed_prerequisite_preparation=preparation)
            finally:old.CLONE=previous
        result.append((name,run))
    assert tuple(name for name,_ in result)==IDS
    return result
