"""Predeclared D1 actual Native qualifier. Importing performs no SQL.

Root owns running/publication on the signed disposable predecessor. Literal
financial amounts and retained assertions are preserved by the explicit lawful
two-piece fixture adapter. No Auth/browser
claim: the retained actor fixture is authenticated SQL only.
"""
from copy import deepcopy
from decimal import Decimal as D
import json,uuid
import psycopg
from cp7_credit_correction_de import native_fixture as fixture
import native_basic_cases as basic
import cp7_sales_return_correction_cases as correction
from cp7_credit_multi import cases as multi
native=fixture.native
IDS=('D_POSITIVE_CREDIT_INCREMENT','D_AFTER_ACTIVE_APPLY','D_AFTER_REFUND_EXTRA_STAYS_CREDIT',
 'D_MULTIFAMILY_ORDINAL','D_REPLAY_EXACT_UUID','D_STALE_REVIEW_NO_EFFECT','D_ACCESS_REVOKED_NO_EFFECT',
 'D_SHORTFALL_NAMES_UNDO','D_ROOT_BOOK_FLOOR_REFUSAL','D_ATOMIC_POST_FAILURE_RESTORE',
 'D_SECOND_REVISION_ORDINAL_HISTORY','D_AFTER_NAMED_UNDO_NO_FALSE_BLOCKER','E_UNIMPLEMENTED_INCOMING_CORRECTION_STAYS_GUARDED')
SCHEMA='cp7_credit_correction_de'


def observe(cur,pair):
    native.b.api.admin(cur)
    return dict(retained=basic.observation(cur,pair),
        correction={name:native._array(cur,name,'true',())for name in ('cp7_sales_return_correction.requests','cp7_sales_return_correction.context','cp7_sales_return_correction.links','cp7_sales_return_correction.journal_restatements','cp7_sales_return_correction.helper_sources','cp7_fg.correction_movements')},
        D={name:native._array(cur,SCHEMA+'.'+name,'true',())for name in ('work_v1','operations_v1','plans_v1','parts_v1','posting_v1')})


def refusal(cur,pair,fn,message):
    before=observe(cur,pair);point='de_refusal_'+uuid.uuid4().hex;cur.execute('savepoint '+point)
    try:fn()
    except psycopg.Error as error:
        result=dict(sqlstate=error.sqlstate,message=error.diag.message_primary,detail=error.diag.message_detail or '')
        cur.execute('rollback to savepoint '+point);cur.execute('release savepoint '+point);native.b.api.admin(cur)
        assert result['message']==message,result
    else:
        cur.execute('rollback to savepoint '+point);cur.execute('release savepoint '+point)
        raise AssertionError('D_EXPECTED_REFUSAL_SUCCEEDED')
    assert observe(cur,pair)==before,'D_REFUSAL_CHANGED_COMPLETE_NATIVE_OR_PRIVATE_STATE'
    return result


def payload(cur,pair,amount='250.00',return_id=None,subject=None):
    f=pair['source']['f'];ret=return_id or pair['initial_result']['return_id']
    w=correction.workspace(cur,f,ret,subject=subject);document=w['document']
    rows=[{key:line[key]for key in ('allocation_id','location_id','qty_pcs','quality_grade','refund_amount','notes')}for line in document['items']]
    assert len(rows)==1,'D1_QUALIFIER_SINGLE_LINE_FIXTURE_CHANGED';rows[0]['refund_amount']=amount
    p=dict(sale_id=f['sale'],return_id=ret,review_token=w['source']['review_token'],return_review_token=w['return_review_token'],
        change_reason='Nilai retur dan tambahan kredit customer sudah diperiksa',
        replacement=dict(physical_at=document['physical_at'],notes=document['notes'],items=rows))
    preview=correction.workspace(cur,f,ret,subject=subject,proposed=dict(replacement=p['replacement'],change_reason=p['change_reason']))
    quote=preview['credit_correction'];p['credit_review_token']=quote['review_token']
    return p,w['source']['row_version'],quote


def post(cur,pair,amount='250.00',return_id=None,subject=None):
    p,v,q=payload(cur,pair,amount,return_id,subject)
    assert q['state']=='READY'and q['source_authority_proven']is True,q
    key=uuid.uuid4();out=correction.correct(cur,p,v,key,subject=subject)
    cur.execute('set constraints all immediate');cur.execute('set constraints all deferred');native.b.api.admin(cur)
    return out,p,v,q,key


def profile(cur,pair,expected_i,expected_available):
    """Separate actual GL sum including the exact new restatement legs.

    The retained consumer fixture's GL oracle predates return restatements and
    is not changed or silently relaxed; this qualifier supplies the full source
    set explicitly, compares Native source AR and computes P/U/I independently.
    """
    native.b.api.admin(cur);sale=pair['source']['f']['sale'];ar=pair['ar']['source']
    data=cur.execute('select cp7_credit.source_document_snapshot_v1(%s)',(sale,)).fetchone()[0]
    gross,paid,returned=cur.execute("select(select coalesce(sum(line_total),0)from erp.sales_items where sale_id=%s),(select coalesce(sum(amount),0)from erp.sales_payments where sale_id=%s and status='POSTED'),(select coalesce(sum(i.refund_amount),0)from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id where r.sale_id=%s and r.status='POSTED')",(sale,sale,sale)).fetchone();net=gross-returned
    issued=cur.execute('select coalesce(sum(q.amount),0)from cp7_credit.return_families f join cp7_credit.cohorts c on c.family_id=f.id join cp7_credit.recognition_plans p on p.cohort_id=c.id join cp7_credit.recognition_components cc on cc.plan_id=p.id join cp7_credit.component_parts q on q.component_id=cc.id join cp7_credit.component_journals j on j.part_id=q.id where f.family_root_sale_id=%s',(sale,)).fetchone()[0]
    consumed=cur.execute('select coalesce(sum(e.amount),0)from cp7_credit.return_families f join cp7_credit.cohorts c on c.family_id=f.id join cp7_credit.consumption_events e on e.cohort_id=c.id where f.family_root_sale_id=%s',(sale,)).fetchone()[0]
    raw=cur.execute("""select coalesce(sum(l.debit-l.credit),0)from erp.journal_lines l where l.account_id=%s and l.journal_entry_id in(
     select substring(e->>'id'from 9)::uuid from jsonb_array_elements(%s::jsonb)e
     union select j.journal_id from cp7_credit.return_families f join cp7_credit.cohorts c on c.family_id=f.id join cp7_credit.recognition_plans p on p.cohort_id=c.id join cp7_credit.recognition_components cc on cc.plan_id=p.id join cp7_credit.component_parts q on q.component_id=cc.id join cp7_credit.component_journals j on j.part_id=q.id where f.family_root_sale_id=%s)""",(ar,json.dumps(data['base_events']),sale)).fetchone()[0]
    assert issued==D(expected_i)and issued-consumed==D(expected_available),(issued,consumed)
    assert paid-issued==net and raw==0,(paid,issued,net,raw)
    detail=native.source.read(cur,pair['source']['f'])['detail'];native.b.api.admin(cur)
    assert {k:detail['financial'][k]for k in ('net_total','paid_total','open_balance')}==dict(net_total=format(net,'.2f'),paid_total=format(net,'.2f'),open_balance='0.00'),detail
    cur.execute('select cp7_credit.assert_current_materialized_profile(%s,%s,%s)',(sale,sale,sale))
    assert not cur.execute('select exists(select 1 from '+SCHEMA+'.work_v1)or exists(select 1 from '+SCHEMA+'.posting_v1)').fetchone()[0]
    return dict(I=format(issued,'.2f'),available=format(issued-consumed,'.2f'),net=format(net,'.2f'),AR='0.00')


def cases(cur,today):
    def increased():
        cap_controls={}
        # The retained one-piece fixture is a real negative control: 200.02
        # must refuse, while Native's exact +0.01 tolerance still accepts.
        with native.isolated(cur):
            pair=fixture.retained.prepare(cur,today)
            p,v,q=payload(cur,pair,'200.02')
            assert q['state']=='REFUSE'and 'REFUND_EXCEEDS_ORIGINAL_NET_SALES_CAP'in q['issues'],q
            cap_controls['one_piece_200_02_refusal']=refusal(cur,pair,lambda:correction.correct(cur,p,v),'CP7_CREDIT_DE_REVIEW_REFUSED')
            post(cur,pair,'200.01')
            cap_controls['one_piece_200_01_actual']=profile(cur,pair,'200.01','200.01')
        with native.isolated(cur):
            pair=fixture.prepare(cur,today)
            p,v,q=payload(cur,pair,'400.02')
            assert q['state']=='REFUSE'and 'REFUND_EXCEEDS_ORIGINAL_NET_SALES_CAP'in q['issues'],q
            cap_controls['two_piece_400_02_refusal']=refusal(cur,pair,lambda:correction.correct(cur,p,v),'CP7_CREDIT_DE_REVIEW_REFUSED')
            _,_,tolerance=payload(cur,pair,'400.01')
            assert tolerance['state']=='READY',tolerance
            cap_controls['two_piece_400_01_preview_ready']=True
        with native.isolated(cur):
            pair=fixture.prepare(cur,today);old=correction.original_fact(cur,pair['initial_result']['return_id']);native.b.api.admin(cur)
            bank=native.payments.bank_account(cur,pair['source']['f']);cash=cur.execute('select coalesce(sum(debit-credit),0)from erp.journal_lines where account_id=%s',(bank,)).fetchone()[0]
            out,p,v,q,key=post(cur,pair);assert q['credit_delta']=='50.00'and q['after_available']=='250.00',q
            actual=profile(cur,pair,'250.00','250.00')
            assert correction.original_fact(cur,p['return_id'])==old
            assert cur.execute('select coalesce(sum(debit-credit),0)from erp.journal_lines where account_id=%s',(bank,)).fetchone()[0]==cash
            native.b.api.admin(cur);assert cur.execute('select count(*)from cp7_credit.return_families where family_root_sale_id=%s',(p['sale_id'],)).fetchone()[0]==1
            assert not cur.execute('select exists(select 1 from cp7_credit.initial_refund_operations where actor=auth.uid()and request_id=%s)',(key,)).fetchone()[0]
            return dict(status='PASS',source=actual,extra_credit='50.00',same_customer=True,old_return_immutable=True,new_family_created=False,outcome=out,cap_controls=cap_controls)
    def used():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today);applied,_,_=basic.apply(cur,pair,'180.00');post(cur,pair)
            actual=profile(cur,pair,'250.00','70.00');native.b.api.admin(cur)
            assert not cur.execute('select exists(select 1 from cp7_credit.consumption_events where restores_event_id=%s)',(applied['consumption_event_id'],)).fetchone()[0]
            return dict(status='PASS',source=actual,original_application_still_active=applied['consumption_event_id'])
    def refunded():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today,'REFUND');native.b.api.admin(cur);bank=native.payments.bank_account(cur,pair['source']['f'])
            cash=cur.execute('select coalesce(sum(debit-credit),0)from erp.journal_lines where account_id=%s',(bank,)).fetchone()[0]
            post(cur,pair);actual=profile(cur,pair,'250.00','50.00')
            assert cur.execute('select coalesce(sum(debit-credit),0)from erp.journal_lines where account_id=%s',(bank,)).fetchone()[0]==cash
            return dict(status='PASS',source=actual,extra_cash_out='0.00',extra_value_remains_customer_credit=True)
    def ordinal():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today);multi.later_return(cur,pair,'1','100.00','CREDIT','100.00',2)
            native.b.api.admin(cur);sale=pair['source']['f']['sale'];before=native._array(cur,'cp7_credit.return_families','family_root_sale_id=%s',(sale,))
            post(cur,pair);assert native._array(cur,'cp7_credit.return_families','family_root_sale_id=%s',(sale,))==before
            return dict(status='PASS',source=profile(cur,pair,'350.00','350.00'),family_registration_and_ordinals_unchanged=True)
    def replay():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today);out,p,v,q,key=post(cur,pair);before=observe(cur,pair)
            assert correction.correct(cur,p,v,key)==out and observe(cur,pair)==before
            bad=deepcopy(p);bad['replacement']['items'][0]['refund_amount']='250.01'
            refusal(cur,pair,lambda:correction.correct(cur,bad,v,key),'CP7_RETURN_CORRECTION_REQUEST_CHANGED')
            return dict(status='PASS',exact_UUID_one_effect=True,changed_intent_refused=True)
    def stale():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today);p,v,q=payload(cur,pair);p['replacement']['items'][0]['refund_amount']='251.00'
            outcome=refusal(cur,pair,lambda:correction.correct(cur,p,v),'CP7_CREDIT_DE_STALE_REVIEW')
            p,v,_=payload(cur,pair);post(cur,pair)
            # A lawful competing correction retires the old source. Posted
            # allocation/item cap facts are never mutated to manufacture stale.
            competing=refusal(cur,pair,lambda:correction.correct(cur,p,v),'CP7_RETURN_CORRECTION_STALE_REVIEW')
            return dict(status='PASS',actual_refusal=outcome,competing_source_refusal=competing,complete_no_effect=True)
    def revoked():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today);subject,_=native.auth.custom_actor(cur);native.b.api.admin(cur)
            role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
            cur.execute('update erp.app_users set role_id=%s where auth_user_id=%s',(role,subject));p,v,q=payload(cur,pair,subject=subject)
            native.b.api.admin(cur);cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.hpp.view'",(role,))
            outcome=refusal(cur,pair,lambda:correction.correct(cur,p,v,subject=subject),'CP7_RETURN_CORRECTION_DENIED')
            return dict(status='PASS',actual_refusal=outcome,current_access_rechecked=True,authenticated_SQL_fixture_not_Auth_browser=True)
    def shortfall():
        outcomes={}
        for mode in ('CREDIT','REFUND'):
            with native.isolated(cur):
                pair=fixture.prepare(cur,today,mode)
                if mode=='CREDIT':
                    applied,_,_=basic.apply(cur,pair,'180.00');event=applied['consumption_event_id'];route='Batalkan penggunaan kredit di invoice tujuan'
                else:event=pair['initial_result']['refund_event_id'];route='Batalkan pengembalian uang kredit'
                p,v,q=payload(cur,pair,'100.00')
                assert q['state']=='REFUSE'and 'UNDO_ACTIVE_CONSUMERS_FIRST'in q['issues'],q
                assert any(e['event_id']==event and e['undo_action']==route for e in q['active_consumers']),q
                outcome=refusal(cur,pair,lambda:correction.correct(cur,p,v),'CP7_CREDIT_DE_REVIEW_REFUSED')
                assert route in outcome['detail'];outcomes[mode]=q['active_consumers']
        return dict(status='PASS',active_named_undo=outcomes,no_new_receivable=True,complete_no_effect=True)
    def floor():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today);native.b.api.admin(cur)
            book=cur.execute("select transaction_date from erp.journal_entries where source_type='SALES_RETURN'and source_id=%s and reversal_of_id is null",(pair['initial_result']['return_id'],)).fetchone()[0]
            native.source.fg.ax.boundary.historical.prior.set_open_period(cur,book)
            p,v,q=payload(cur,pair);assert q['state']=='REFUSE'and 'CAUSAL_BOOK_FLOOR_ADAPTER_REQUIRED'in q['issues'],q
            outcome=refusal(cur,pair,lambda:correction.correct(cur,p,v),'CP7_CREDIT_DE_REVIEW_REFUSED')
            return dict(status='PASS',actual_refusal=outcome,closed_book_floor_guard_retained=True)
    def post_failure():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today);p,v,q=payload(cur,pair);native.b.api.admin(cur)
            cur.execute("""create function cp7_credit_correction_de.test_part_failure()returns trigger
             language plpgsql security invoker set search_path=''as $$
             declare w cp7_credit_correction_de.work_v1;j erp.journal_entries;old_credit numeric;detail jsonb;begin
              select *into strict w from cp7_credit_correction_de.work_v1 where operation_id=new.operation_id and phase='RECONCILING';
              perform cp7_credit.assert_source_native_trigger_census_v1();
              perform cp7_credit_correction_de.assert_source_change_v1(w.before_source,w.actual_source,w.return_id,w.replacement_id);
              perform cp7_credit_correction_de.assert_plan_set_v1(w.operation_id);
              select *into strict j from erp.journal_entries where id=new.journal_id;
              select coalesce(sum(q.amount),0)into old_credit from cp7_credit.component_parts q
               join cp7_credit.recognition_components c on c.id=q.component_id join cp7_credit.recognition_plans p on p.id=c.plan_id
               join cp7_credit.cohorts h on h.id=p.cohort_id join cp7_credit.return_families f on f.id=h.family_id
               where f.family_root_sale_id=w.sale_id and p.plan_kind='INITIAL';
              if old_credit<>200 or j.status<>'POSTED'or j.source_type<>'CP7_CUSTOMER_CREDIT_RECOGNITION'or j.source_id<>new.part_id
               or not exists(select 1 from cp7_credit.component_journals l where l.part_id=new.part_id and l.journal_id=j.id)
               or not exists(select 1 from cp7_credit_correction_de.parts_v1 s where s.part_id=new.part_id and s.journal_id=j.id)
               or not exists(select 1 from cp7_credit.component_parts q where q.id=new.part_id and q.amount=50)
               or(select coalesce(sum(l.debit),0)from erp.journal_lines l where l.journal_entry_id=j.id)<>50
               or(select coalesce(sum(l.credit),0)from erp.journal_lines l where l.journal_entry_id=j.id)<>50
               or not exists(select 1 from erp.sales_returns r where r.id=w.return_id and r.status='REVERSED')
               or not exists(select 1 from erp.sales_returns r where r.id=w.replacement_id and r.status='POSTED')then
               raise exception 'CP7_CREDIT_DE_TEST_FAILURE_POINT_NOT_PROVEN';end if;
              detail:=jsonb_build_object('phase',w.phase,'actual_Native_credit_journal_inserted',true,
               'component_journal_link_inserted',true,'private_part_inserted',true,'new_recognition','50.00','old_initial_credit','200.00',
               'old_recognition_immutable',true,'actual_Native_inverse_replacement_validated',true,'Native_trigger_census_unchanged',true);
              raise exception 'CP7_CREDIT_DE_TEST_PART_FAILURE'using detail=detail::text;
             end$$;
             create trigger test_de_part_failure after insert on cp7_credit_correction_de.parts_v1
              for each row execute function cp7_credit_correction_de.test_part_failure();""",prepare=False)
            outcome=refusal(cur,pair,lambda:correction.correct(cur,p,v),'CP7_CREDIT_DE_TEST_PART_FAILURE')
            proof=json.loads(outcome['detail'])
            assert proof==dict(phase='RECONCILING',actual_Native_credit_journal_inserted=True,component_journal_link_inserted=True,
                private_part_inserted=True,new_recognition='50.00',old_initial_credit='200.00',old_recognition_immutable=True,
                actual_Native_inverse_replacement_validated=True,Native_trigger_census_unchanged=True),proof
            return dict(status='PASS',failure_AFTER_actual_Native_journal_insert_before_private_completion=True,
                actual_refusal=outcome,failure_point_proof=proof,complete_reverse_repost_credit_restore=True)
    def second_revision():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today);first,p,v,q,key=post(cur,pair);old=deepcopy(first);second,*_=post(cur,pair,'275.00',first['return_id'])
            actual=profile(cur,pair,'275.00','275.00');native.b.api.admin(cur)
            chain=cur.execute('select operation_ordinal,predecessor_id,operation_id from cp7_credit_correction_de.operations_v1 where sale_id=%s order by operation_ordinal',(p['sale_id'],)).fetchall()
            assert len(chain)==2 and chain[0][0]==1 and chain[1][0]==2 and chain[1][1]==chain[0][2]
            assert correction.correct(cur,p,v,key)==old
            return dict(status='PASS',source=actual,explicit_operation_ordinal_chain=True,old_UUID_receipt_still_exact=True,outcome=second)
    def undone():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today);applied,_,_=basic.apply(cur,pair,'180.00')
            undo=basic.review(cur,basic.payload(pair,action='UNDO',original=applied['consumption_event_id']))
            basic.command(cur,undo,uuid.uuid4());out,p,v,q,key=post(cur,pair)
            assert q['active_consumers']==[],q
            return dict(status='PASS',source=profile(cur,pair,'250.00','250.00'),legitimately_reversed_consumers_not_active=True,signed_history_retained=True)
    def incoming_guard():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today);basic.apply(cur,pair,'80.00');p,v=native.note.edit(cur,pair['target'],price='110')
            before=observe(cur,pair);point='de_E_protected';cur.execute('savepoint '+point)
            try:native.note.correct(cur,p,v)
            except psycopg.Error as error:
                message=error.diag.message_primary;cur.execute('rollback to savepoint '+point);cur.execute('release savepoint '+point);native.b.api.admin(cur)
                assert message.startswith('CP7_'),message
            else:raise AssertionError('E_UNIMPLEMENTED_ADAPTER_WAS_ADMITTED')
            assert observe(cur,pair)==before
            return dict(status='PASS',retained_refusal=message,E_complete=False)
    result=list(zip(IDS,(increased,used,refunded,ordinal,replay,stale,revoked,shortfall,floor,post_failure,second_revision,undone,incoming_guard)))
    assert tuple(name for name,_ in result)==IDS;return result
