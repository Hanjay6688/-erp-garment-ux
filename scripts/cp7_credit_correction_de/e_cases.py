"""Prepared E1 actual Native cases; never run on import or by a default path.

Root must first qualify the full D1 owner-successor, then install the exact
e_composition on that parent. This is authenticated SQL fixture preparation,
not real Auth/browser evidence. Retained fixtures/date/amount oracles stay exact.
"""
from copy import deepcopy
from decimal import Decimal as D
import json,uuid
import psycopg
from . import cases as de
fixture,basic,native=de.fixture,de.basic,de.native
note=native.note
SCHEMA='cp7_credit_note_carry_de'
IDS=('E_PRICE_INCREASE_80_NET550_AR470','E_PRICE_DECREASE_80_NET100_AR20',
 'E_EXACT_FUNDED_80_PAID','E_BELOW_CARRIED_80_REFUSES_ATOMIC',
 'E_SAME_UUID_AND_CHANGED_INTENT','E_SOURCE_D1_CHANGE_RETIRES_REVIEW',
 'E_LATER_APPLY_20_CURRENT_LEAF','E_UNDO_ORIGINAL_80_AND_OLD_RECEIPT',
 'E_NATIVE_POST_FAILURE_FULL_RESTORE','E_QUANTITY_CHANGE_REFUSES',
 'E_ORIGINAL_DATE_CHANGE_REFUSES','E_CLOSED_ORIGINAL_BOOK_PAIR_REFUSES',
 'E_SECOND_NOTE_REVISION_GUARDED','E_CURRENT_ACCESS_REVOKED_REFUSES',
 'E_JOINT_PREFIX_AFTER_UNDO_120_MIN200_NOT150','E_LATER_NATIVE_REVERSE_REFUSES_ATOMIC',
 'E_LATER_NATIVE_SALE_SAME_LOT_RECONCILES')


def observe(cur,pair):
    native.b.api.admin(cur)
    return dict(D=de.observe(cur,pair),note=note.snapshot(cur),
        consumer={t:native._array(cur,'cp7_credit.'+t,'true',())for t in
          ('consumer_requests_v1','consumer_operations_v1','consumer_completions_v1',
           'consumer_execution_context','consumer_posting_scope_v1','consumer_validation_queue_v1')},
        E={t:native._array(cur,SCHEMA+'.'+t,'true',())for t in('work_v1','operations_v1','assignments_v1')})


def refusal(cur,pair,fn,message):
    before=observe(cur,pair);point='credit_e_'+uuid.uuid4().hex;cur.execute('savepoint '+point)
    try:fn()
    except psycopg.Error as error:
        result=dict(message=error.diag.message_primary,sqlstate=error.sqlstate,detail=error.diag.message_detail or '')
        cur.execute('rollback to savepoint '+point);cur.execute('release savepoint '+point);native.b.api.admin(cur)
        assert result['message']==message,result
    else:
        cur.execute('rollback to savepoint '+point);cur.execute('release savepoint '+point)
        raise AssertionError('E_EXPECTED_REFUSAL_SUCCEEDED')
    assert observe(cur,pair)==before,'E_REFUSAL_CHANGED_NATIVE_NOTE_CONSUMER_OR_CARRY_STATE'
    return result


def intent(cur,pair,price='110.00',subject=None):
    history=note.history(cur,pair['target']['sale'],subject=subject);d=history['current']['detail']
    basis=history['credit_carry'];assert len(d['items'])==1,'E1_RETAINED_SINGLE_LINE_TARGET_CHANGED'
    p=dict(sale_id=d['id'],review_token=d['review_token'],sale_number=d['number'],customer_id=d['customer_id'],
        source_location_id=d['location_id'],sale_date=d['physical_at'],due_date=d['due_date'],payment_terms=d['payment_terms'],notes=d['notes'],
        change_reason='Harga nota, pemindahan kredit dan sisa piutang sudah diperiksa',item_lineage=[i['id']for i in d['items']],
        items=[dict(product_id=i['product_id'],qty_pcs=i['qty_pcs'],unit_price_snapshot=price,discount_amount=i['financial']['discount'],notes=i['notes'])for i in d['items']])
    net=sum(D(i['qty_pcs'])*D(i['unit_price_snapshot'])-D(i['discount_amount'])for i in p['items'])
    p['credit_carry_review']=dict(contract_version='cp7.note-credit-carry-review.v1',basis_sha256=basis['basis_sha256'],
        transfer_amount=basis['transfer_amount'],replacement_net=format(net,'.2f'),remaining_amount=format(net-D(basis['transfer_amount']),'.2f'))
    return p,d['row_version'],basis


def physical(cur,pair):
    native.b.api.admin(cur);lots=[pair[k]['lot']for k in('target',)]+[pair['source']['f']['lot']]
    return dict(positions=cur.execute("select product_id,lot_id,location_id,quality_grade,physical_qty,reserved_qty,available_qty from cp7_fg.positions('',true)where lot_id=any(%s::uuid[])order by product_id,lot_id,location_id,quality_grade",(lots,)).fetchall(),
        HPP=native._array(cur,'erp.hpp_versions','lot_id=any(%s::uuid[])',(lots,)),
        cash=cur.execute('select coalesce(sum(l.debit-l.credit),0)from erp.journal_lines l where account_id=%s',(native.payments.bank_account(cur,pair['source']['f']),)).fetchone()[0])


def profile(cur,pair,original,current,net,incoming,available):
    """Independent bounded raw GL sum; no new E current-event/profile helper."""
    native.b.api.admin(cur);ids=[original,current];ar=pair['ar']['target'];customer=pair['target']['customer']
    assert cur.execute('select count(*)from erp.sales_payments where sale_id=any(%s::uuid[])',(ids,)).fetchone()[0]==0
    assert cur.execute('select count(*)from erp.sales_returns where sale_id=any(%s::uuid[])',(ids,)).fetchone()[0]==0
    actual_net=cur.execute('select sum(line_total)from erp.sales_items where sale_id=%s',(current,)).fetchone()[0]
    actual_u=cur.execute("select coalesce(sum(amount),0)from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=any(%s::uuid[])",(ids,)).fetchone()[0]
    raw=cur.execute("""with recursive seeds(id)as(
      select j.id from erp.journal_entries j where j.source_type='SALE'and j.source_id=any(%s::uuid[])
      union select j.id from cp7_note.journal_restatements s join erp.journal_entries j on j.id in(s.neutral_journal_id,s.effective_journal_id)where s.previous_sale_id=%s
      union select e.journal_id from cp7_credit.consumption_events e where e.event_kind='APPLY'and e.target_sale_id=any(%s::uuid[])
     ),walk(id)as(select id from seeds union select j.id from walk w join erp.journal_entries j on j.reversal_of_id=w.id or(j.source_type='JOURNAL_REVERSAL'and j.source_id=w.id))
     select coalesce(sum(l.debit-l.credit),0)from walk w join erp.journal_lines l on l.journal_entry_id=w.id where l.account_id=%s and l.customer_id=%s""",(ids,original,ids,ar,customer)).fetchone()[0]
    assert(actual_net,actual_u,raw)==(D(net),D(incoming),D(net)-D(incoming)),(actual_net,actual_u,raw)
    f=dict(pair['target'],sale=current);detail=native.source.read(cur,f)['detail'];native.b.api.admin(cur)
    assert {k:detail['financial'][k]for k in('gross_total','net_total','paid_total','open_balance')}==dict(gross_total=net,net_total=net,paid_total=incoming,open_balance=format(D(net)-D(incoming),'.2f'))
    assert detail['status']==('PAID'if D(net)==D(incoming)else'PARTIAL_PAID'if D(incoming)>0 else'POSTED')
    source=de.profile(cur,pair,'200.00',available)
    cur.execute('set constraints all immediate');cur.execute('set constraints all deferred')
    return dict(net=net,U=incoming,AR=format(raw,'.2f'),source=source)


def post(cur,pair,price='110.00'):
    p,v,basis=intent(cur,pair,price);assert basis['issues']==[],basis
    before=physical(cur,pair);original=pair['target']['sale'];facts=note.unchanged_facts(cur,original)
    events=native._array(cur,'cp7_credit.consumption_events','true',());journals={e['journal_id']:native.journal(cur,e['journal_id'])for e in events['document']}
    key=uuid.uuid4();out=note.correct(cur,p,v,key);native.b.api.admin(cur)
    cur.execute('set constraints all immediate');cur.execute('set constraints all deferred')
    assert physical(cur,pair)==before,'E_PRICE_ONLY_CHANGED_PHYSICAL_HPP_OR_CASH'
    assert note.unchanged_facts(cur,original)==facts
    assert native._array(cur,'cp7_credit.consumption_events','true',())==events,'E_CREATED_OR_CHANGED_CONSUMER_MONEY'
    for jid,j in journals.items():assert native.journal(cur,jid)==j,'E_MUTATED_ORIGINAL_CONSUMER_GL'
    assignment_ids=cur.execute('select event_id::text from cp7_credit_note_carry_de.assignments_v1 where replacement_sale_id=%s order by event_id',(out['sale_id'],)).fetchall()
    expected_ids=sorted((e['id'],)for e in events['document']if e['event_kind']=='APPLY'and e['target_sale_id']==original)
    assert assignment_ids==expected_ids
    for e in events['document']:
        cur.execute('select cp7_credit.assert_consumer_closed_v1(%s)',(e['id'],))
    return out,p,v,basis,key


def cases(cur,today):
    def priced(price,net):
        with native.isolated(cur):
            pair=fixture.prepare(cur,today);basic.apply(cur,pair,'80.00');out,*_=post(cur,pair,price)
            return dict(status='PASS',profile=profile(cur,pair,pair['target']['sale'],out['sale_id'],net,'80.00','120.00'),actual_Native_price_only=True)
    def below():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today);basic.apply(cur,pair,'80.00');p,v,b=intent(cur,pair,'16.00')
            p['items'][0]['discount_amount']='0.01';p['credit_carry_review'].update(replacement_net='79.99',remaining_amount='-0.01')
            return dict(status='PASS',actual_refusal=refusal(cur,pair,lambda:note.correct(cur,p,v),'CP7_CREDIT_NOTE_CARRY_REVIEW_REFUSED'),no_auto_credit_or_AR=True)
    def replay():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today);basic.apply(cur,pair,'80.00');out,p,v,b,key=post(cur,pair);before=observe(cur,pair)
            assert note.correct(cur,p,v,key)==out and observe(cur,pair)==before
            changed=deepcopy(p);changed['items'][0]['unit_price_snapshot']='111.00'
            refusal(cur,pair,lambda:note.correct(cur,changed,v,key),'CP7_NOTE_REQUEST_CHANGED')
            return dict(status='PASS',confirmed_lost_reply_same_UUID_one_effect=True,changed_intent_refused=True)
    def upstream():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today);basic.apply(cur,pair,'80.00');p,v,b=intent(cur,pair);de.post(cur,pair,'250.00')
            return dict(status='PASS',actual_refusal=refusal(cur,pair,lambda:note.correct(cur,p,v),'CP7_CREDIT_NOTE_CARRY_STALE_REVIEW'),target_U_unchanged_source_context_rechecked=True)
    def later(undo):
        with native.isolated(cur):
            pair=fixture.prepare(cur,today);first,_,_=basic.apply(cur,pair,'80.00');original=pair['target']['sale'];out,*_=post(cur,pair)
            current=deepcopy(pair);current['target']['sale']=out['sale_id']
            if undo:
                p=basic.payload(current,'UNDO',original=first['consumption_event_id']);envelope=basic.review(cur,p);made=basic.command(cur,envelope,uuid.uuid4())
                assert made['amount']=='-80.00'and made['target_sale_id']==out['sale_id']and made['restores_event_id']==first['consumption_event_id']
            else:made,*_=basic.apply(cur,current,'20.00')
            native.b.api.admin(cur);cur.execute('select cp7_credit.assert_consumer_closed_v1(%s)',(first['operation_id'],))
            cur.execute('select cp7_credit.assert_consumer_closed_v1(%s)',(made['operation_id'],))
            return dict(status='PASS',profile=profile(cur,pair,original,out['sale_id'],'550.00','0.00'if undo else'100.00','200.00'if undo else'100.00'),old_completion_still_exact=True)
    def late_failure():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today);applied,_,_=basic.apply(cur,pair,'80.00');p,v,b=intent(cur,pair);native.b.api.admin(cur)
            trigger_census_sql="""select coalesce(jsonb_agg(to_jsonb(t)order by t.oid),'[]'::jsonb)
             from pg_catalog.pg_trigger t join pg_catalog.pg_class c on c.oid=t.tgrelid
             join pg_catalog.pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'"""
            original_ERP_triggers=cur.execute(trigger_census_sql).fetchone()[0]
            cur.execute("""create function cp7_credit_note_carry_de.test_post_failure()returns trigger
            language plpgsql security invoker set search_path=''set timezone='UTC'as $e_late_point$
            declare late_work cp7_credit_note_carry_de.work_v1;late_request cp7_note.requests;
             late_assignment cp7_credit_note_carry_de.assignments_v1;late_event cp7_credit.consumption_events;
             late_sale_journal erp.journal_entries;late_original_journal erp.journal_entries;
             late_net numeric;late_count bigint;late_contexts bigint;late_basis jsonb;late_guards jsonb:='[]'::jsonb;
            begin
             select *into late_work from cp7_credit_note_carry_de.work_v1 w where w.operation_id=new.operation_id
              and w.backend_pid=pg_backend_pid()and w.transaction_id=txid_current()and w.actor=auth.uid();
             select *into late_request from cp7_note.requests q where q.actor=new.actor and q.request_id=new.request_id;
             select(select count(*)from cp7_note.context c where c.backend_pid=pg_backend_pid()and c.transaction_id=txid_current())+
              (select count(*)from cp7_sales.command_context c where c.backend_pid=pg_backend_pid()and c.transaction_id=txid_current())into late_contexts;
             if late_work.operation_id is null or late_work.phase<>'MATERIALIZED'or new.actor is distinct from auth.uid()
              or(new.actor,new.request_id,new.source_sale_id,new.replacement_sale_id,new.revision_id,new.payload,new.expected_version,new.proof)is distinct from
               (late_work.actor,late_work.request_id,late_work.source_sale_id,late_work.replacement_sale_id,late_work.revision_id,late_work.payload,late_work.expected_version,to_jsonb(late_work))
              or late_request.actor is null or(late_request.payload,late_request.expected_version,late_request.response)is distinct from(new.payload,new.expected_version,new.response)
              or late_contexts<>0 or not exists(select 1 from cp7_note.revisions r where r.id=new.revision_id and r.root_sale_id=new.source_sale_id
               and r.previous_sale_id=new.source_sale_id and r.replacement_sale_id=new.replacement_sale_id and r.revision=1
               and r.actor=new.actor and r.request_id=new.request_id)then
              raise exception 'E_TEST_LATE_POINT_SETUP_FAILED'using detail='actual MATERIALIZED work, revision, final response or cleared owning context missing';end if;
             select *into late_sale_journal from erp.journal_entries j where j.id=(new.proof#>>'{actual_proof,replacement_journal,journal,id}')::uuid
              and j.source_type='SALE'and j.source_id=new.replacement_sale_id;
             select coalesce(sum(i.line_total),0)into late_net from erp.sales_items i where i.sale_id=new.replacement_sale_id;
             if late_sale_journal.id is null or late_sale_journal.status<>'POSTED'or late_net<>550.00
              or new.proof#>'{actual_proof,replacement_journal}'is distinct from cp7_credit.materialized_journal_payload(late_sale_journal.id)
              or new.proof#>'{actual_proof,no_consumer_money_created}'is distinct from'true'::jsonb
              or new.proof#>'{actual_proof,same_physical_and_HPP}'is distinct from'true'::jsonb
              or not exists(select 1 from erp.sales_headers h where h.id=new.replacement_sale_id and h.status='PARTIAL_PAID')then
              raise exception 'E_TEST_LATE_POINT_SETUP_FAILED'using detail='actual posted replacement SALE journal, net550, price-only effect or receiving status missing';end if;
             select count(*)into late_count from cp7_credit_note_carry_de.assignments_v1 a where a.operation_id=new.operation_id;
             select *into late_assignment from cp7_credit_note_carry_de.assignments_v1 a where a.operation_id=new.operation_id order by a.event_id limit 1;
             select *into late_event from cp7_credit.consumption_events e where e.id=late_assignment.event_id;
             select *into late_original_journal from erp.journal_entries j where j.id=late_event.journal_id;
             select v into late_basis from jsonb_array_elements(late_work.basis->'incoming_facts')v where v#>>'{event,id}'=late_event.id::text;
             if late_count<>1 or coalesce(jsonb_array_length(late_work.basis->'incoming_facts'),0)<>1 or late_event.id is null
              or(late_assignment.event_kind,late_assignment.historical_target_id,late_assignment.root_sale_id,late_assignment.replacement_sale_id)is distinct from
               ('APPLY',new.source_sale_id,new.source_sale_id,new.replacement_sale_id)
              or(late_event.event_kind,late_event.target_sale_id,late_event.amount)is distinct from('APPLY',new.source_sale_id,80.00::numeric)
              or late_original_journal.status is distinct from'POSTED'or late_assignment.event_snapshot is distinct from to_jsonb(late_event)
              or late_assignment.journal_snapshot is distinct from cp7_credit.materialized_journal_payload(late_event.journal_id)
              or late_basis->'event'is distinct from to_jsonb(late_event)or late_basis->'journal'is distinct from cp7_credit.materialized_journal_payload(late_event.journal_id)
              or late_assignment.event_sha256 is distinct from cp7_credit.pg_jsonb_sha256(to_jsonb(late_event))
              or late_assignment.journal_sha256 is distinct from cp7_credit.pg_jsonb_sha256(cp7_credit.materialized_journal_payload(late_event.journal_id))then
              raise exception 'E_TEST_LATE_POINT_SETUP_FAILED'using detail='actual carried80 assignment or immutable original APPLY/event/journal/basis proof missing';end if;
             perform cp7_credit.assert_source_native_trigger_census_v1();late_guards:=late_guards||jsonb_build_array('assert_source_native_trigger_census_v1');
             perform cp7_credit_note_carry_de.assert_historical_v1(new.source_sale_id);late_guards:=late_guards||jsonb_build_array('assert_historical_v1');
             perform cp7_credit.assert_current_materialized_profile(new.replacement_sale_id,new.source_sale_id,new.replacement_sale_id);
             late_guards:=late_guards||jsonb_build_array('assert_current_materialized_profile');
             raise exception using errcode='P0001',message='E_TEST_ACTUAL_NATIVE_POST_FAILURE',detail=jsonb_build_object(
              'failure_point','AFTER_NATIVE_POST_DURING_E_FINISH','operation_id',new.operation_id,'request_id',new.request_id,
              'revision_id',new.revision_id,'source_sale_id',new.source_sale_id,'replacement_sale_id',new.replacement_sale_id,
              'work_phase',late_work.phase,'owning_contexts_remaining',late_contexts,'replacement_sale_journal_id',late_sale_journal.id,
              'replacement_sale_journal_status',late_sale_journal.status,'replacement_native_net',late_net::text,
              'assignment_count',late_count,'carried_amount',late_event.amount::text,'original_APPLY_event_id',late_event.id,
              'original_APPLY_journal_id',late_event.journal_id,'original_APPLY_target_id',late_event.target_sale_id,
              'original_APPLY_event_sha256',late_assignment.event_sha256,'original_APPLY_journal_sha256',late_assignment.journal_sha256,
              'actual_guards_returned',late_guards)::text;
            end $e_late_point$;
            create trigger test_e_post_failure after insert on cp7_credit_note_carry_de.operations_v1
             for each row execute function cp7_credit_note_carry_de.test_post_failure();""",prepare=False)
            assert cur.execute(trigger_census_sql).fetchone()[0]==original_ERP_triggers,'E_TEST_PRIVATE_DDL_CHANGED_ERP_TRIGGER_CENSUS'
            request=uuid.uuid4();actual=refusal(cur,pair,lambda:note.correct(cur,p,v,request),'E_TEST_ACTUAL_NATIVE_POST_FAILURE')
            detail=json.loads(actual['detail'])
            assert actual['sqlstate']=='P0001'and detail['failure_point']=='AFTER_NATIVE_POST_DURING_E_FINISH'
            assert detail['request_id']==str(request)and detail['source_sale_id']==pair['target']['sale']and detail['work_phase']=='MATERIALIZED'
            assert detail['replacement_sale_journal_status']=='POSTED'and D(detail['replacement_native_net'])==550 and D(detail['carried_amount'])==80
            assert detail['assignment_count']==1 and detail['owning_contexts_remaining']==0
            assert detail['original_APPLY_event_id']==applied['consumption_event_id']and detail['original_APPLY_journal_id']==applied['journal_id']
            assert detail['original_APPLY_target_id']==pair['target']['sale']
            assert detail['actual_guards_returned']==['assert_source_native_trigger_census_v1','assert_historical_v1','assert_current_materialized_profile']
            assert cur.execute(trigger_census_sql).fetchone()[0]==original_ERP_triggers,'E_TEST_FAILURE_CHANGED_ERP_TRIGGER_CENSUS'
            return dict(status='PASS',actual_refusal=actual,full_inverse_draft_stock_HPP_and_money_atomic=True,
                failure_after_actual_Native_post_during_E_finish=True,unchanged_ERP_trigger_census=True)
    def altered(date):
        with native.isolated(cur):
            pair=fixture.prepare(cur,today);basic.apply(cur,pair,'80.00');p,v,b=intent(cur,pair)
            if date:p['sale_date']=pair['source']['physical']['returned']
            else:p['items'][0]['qty_pcs']='4'
            message='CP7_NOTE_SOURCE_IDENTITY_CHANGED'if date else'CP7_CREDIT_NOTE_CARRY_PRICE_ONLY_REQUIRED'
            return dict(status='PASS',actual_refusal=refusal(cur,pair,lambda:note.correct(cur,p,v),message))
    def closed():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today);basic.apply(cur,pair,'80.00');native.b.api.admin(cur)
            day=cur.execute("select economic_date from erp.journal_entries where source_type='SALE'and source_id=%s",(pair['target']['sale'],)).fetchone()[0]
            native.source.fg.ax.boundary.historical.prior.set_open_period(cur,day)
            p,v,b=intent(cur,pair);assert 'ORIGINAL_NOTE_BOOK_PAIR_ADAPTER_REQUIRED'in b['issues'],b
            return dict(status='PASS',actual_refusal=refusal(cur,pair,lambda:note.correct(cur,p,v),'CP7_CREDIT_NOTE_CARRY_REVIEW_REFUSED'))
    def second():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today);basic.apply(cur,pair,'80.00');out,*_=post(cur,pair);pair['target']['sale']=out['sale_id'];p,v,b=intent(cur,pair)
            assert 'NEXT_NOTE_REVISION_ADAPTER_REQUIRED'in b['issues'],b
            return dict(status='PASS',actual_refusal=refusal(cur,pair,lambda:note.correct(cur,p,v),'CP7_CREDIT_NOTE_CARRY_REVIEW_REFUSED'))
    def revoked():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today);basic.apply(cur,pair,'80.00');subject,_=native.auth.custom_actor(cur);native.b.api.admin(cur)
            role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0];cur.execute('update erp.app_users set role_id=%s where auth_user_id=%s',(role,subject))
            p,v,b=intent(cur,pair,subject=subject);cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.hpp.view'",(role,))
            return dict(status='PASS',actual_refusal=refusal(cur,pair,lambda:note.correct(cur,p,v,subject=subject),'CP7_NOTE_ACCESS_DENIED'),real_Auth_browser=False)
    def prefix():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today);first,*_=basic.apply(cur,pair,'80.00');basic.apply(cur,pair,'120.00')
            undo=basic.payload(pair,'UNDO',original=first['consumption_event_id']);native.b.api.admin(cur)
            undo['physical_at']=cur.execute('select clock_timestamp()').fetchone()[0].isoformat()
            basic.command(cur,basic.review(cur,undo),uuid.uuid4());p,v,b=intent(cur,pair,'30.00')
            assert b['transfer_amount']=='120.00'and b['minimum_replacement_net']=='200.00',b
            return dict(status='PASS',actual_refusal=refusal(cur,pair,lambda:note.correct(cur,p,v),'CP7_CREDIT_NOTE_CARRY_REVIEW_REFUSED'),genuine_later_named_undo_not_a_historical_capacity_waiver=True)
    def reverse():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today);basic.apply(cur,pair,'80.00');out,*_=post(cur,pair);current=dict(pair['target'],sale=out['sale_id'])
            p,v=native.cmd.review(cur,current)
            return dict(status='PASS',actual_refusal=refusal(cur,pair,lambda:native.cmd.command(cur,'SALE_REVERSE',p,v),'CP7_CREDIT_NOTE_CARRY_LATER_NATIVE_MUTATION_ADAPTER_REQUIRED'),no_carried_credit_escape_via_replacement_UUID=True)
    def later_sale():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today);basic.apply(cur,pair,'80.00');original=pair['target']['sale'];out,*_=post(cur,pair)
            later=dict(pair['target'],tag=pair['target']['tag']+'-LATER-E',sale_at=cur.execute('select clock_timestamp()').fetchone()[0].isoformat())
            note.posted(cur,later,'1','100.00');native.b.api.admin(cur)
            alignment=cur.execute('select cp7_credit.source_first_nonpo_hpp_alignment_v1(cp7_credit.source_native_snapshot_v1(%s))',(out['sale_id'],)).fetchone()[0]
            assert native.cmd.available(cur,pair['target'])==4
            return dict(status='PASS',profile=profile(cur,pair,original,out['sale_id'],'550.00','80.00','120.00'),actual_later_Native_sale_same_lot_qty1=True,HPP_alignment=alignment)
    functions=(lambda:priced('110.00','550.00'),lambda:priced('20.00','100.00'),lambda:priced('16.00','80.00'),below,replay,upstream,
        lambda:later(False),lambda:later(True),late_failure,lambda:altered(False),lambda:altered(True),closed,second,revoked,prefix,reverse,later_sale)
    result=list(zip(IDS,functions));assert len(result)==len(IDS)==17;return result
