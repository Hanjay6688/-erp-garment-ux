"""Explicit current contracts; the retained AI135 Original remains INCOMPLETE.

Replay six business controls represented by seven legacy IDs. These are named
successor controls, never relabelled old PASS results. No original case is edited.
"""
from datetime import date,timedelta
from decimal import Decimal
import json,re,uuid
import cp6_v2620ai_family as ai
import cp6_v2620ah_family as ah
import cp6_ah_independent_review as work
import cp6_ag_residual_review as returns
import cp6_aa_invoice_partial_audit as production
import cp6_v2620f_final_runtime_regression as final
import cp7_retained_cp6_fixture as fixture
from cp7_ab_bounded_chain import composition as product

actors,base,peer=ai.actors,ai.base,ai.peer
CONTRACTOR='a1000000-0000-0000-0000-000000000001'
IDS=('UNPAYROLLED_PARTIAL_WORK_BLOCKS_REPORT','OWNER_WORK_REFERENCE_BLOCKS_UNTIL_PAYROLLED',
     'OWNER_VENDOR_REFERENCE_BLOCKS_UNTIL_PAYROLLED','RETURN_REBOUND_SOURCE_ATOMIC_REFUSAL',
     'RETURN_ALLOCATION_LIMIT_ATOMIC_REFUSAL','RETURN_REBOUND_CUSTOMER_ATOMIC_REFUSAL')
PHASE_IDS={'explicit_successor':IDS}
REFUSALS={
 'SOURCE':{'baseline':'AH_RETURN_ALLOCATION_SOURCE_MISMATCH','current':'CP7_CREDIT_RETURN_SOURCE_OR_DESTINATION_CHANGED'},
 'LIMIT':{'baseline':'exceeds quantity originally sold','current':'AH_RETURN_EXCEEDS_ORIGINAL_ALLOCATION'},
 'CUSTOMER':{'baseline':'customer does not match original sale customer','current':'OW04_SOURCE_CUSTOMER_MISMATCH'},
}
LEGACY_IDS={IDS[0]:['PARTIAL_WORK'],IDS[1]:['AH_REFERENCE_WORK'],IDS[2]:['AH_REFERENCE_VENDOR'],
 IDS[3]:['SOURCE_REBIND','AH_SOURCE_REBIND'],IDS[4]:['AH_AG_RETURN_SPLIT'],IDS[5]:['AH_AG_RETURN_REBIND_CUSTOMER']}


def data(cur):
    actors.admin(cur)
    return product.catalog._data(cur)


def unpaid(cur,through,lines,qty,amount):
    """AW's linkage policy is mandatory even for zero-rate work; no auto-approval."""
    actors.admin(cur)
    rows=cur.execute("""select contractor_id::text,count(*),sum(remaining_qty),sum(remaining_amount)
        from erp.v_payroll_eligible_work_lines where remaining_qty>0
        and eligible_at<((%s::date+1)::timestamp at time zone 'Asia/Jakarta')group by contractor_id""",(through,)).fetchall()
    assert rows==[(CONTRACTOR,lines,Decimal(str(qty)),Decimal(str(amount)))],rows
    before=data(cur)
    report=peer.confidence(cur,through)
    assert data(cur)==before,'READINESS_READER_CHANGED_DATA_OR_SEQUENCE'
    dc=report['data_confidence'];assert dc['status']=='BLOCKED',dc
    blockers=dc['blockers'];assert len(blockers)==1 and blockers[0]['code']=='PAYROLL_WORK_UNCOVERED',blockers
    b=blockers[0];ref=b['reference']
    assert b['severity']=='POLICY'and ref['contractor_id']==CONTRACTOR and ref['lines']==lines
    assert Decimal(str(ref['remaining_qty']))==Decimal(str(qty))and Decimal(str(ref['remaining_amount']))==Decimal(str(amount)),ref
    actors.admin(cur)
    check=cur.execute('select severity,issue_count from erp.run_v268_financial_report_checks()where check_name=%s',(ai.CHECK,)).fetchone()
    assert check==('CRITICAL',0),check
    return dict(status='PASS',expected='BLOCKED_UNTIL_ACTUAL_WORK_IS_PAYROLLED',report=report,
        independent_eligible_lines=rows,work_lineage_check=check,read_only_all_data_and_sequences=True,
        work_autoapproved=False,original_READY_oracle_retired=False)


def partial(cur,day,today,current):
    # Same 4+6+1 limit and12.50 money control as the frozen partial_work case.
    f=work.work_draft(cur,day,Decimal('1.25'))
    returns.success(peer.operation(cur,'update erp.work_completion_lines set qty_completed=4,qty_payable=4 where completion_id=%s',(f['completion'],)))
    returns.success(peer.operation(cur,'select erp.post_work_completion(%s)',(f['completion'],)))
    actors.admin(cur);header=base.one(cur,'select to_jsonb(h)from erp.work_completion_events h where id=%s',(f['completion'],))
    def draft(qty):
        target=uuid.uuid4();peer.ordinary(cur)
        cur.execute("insert into erp.work_completion_events(id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status)values(%s,%s,%s,%s,%s,%s,'DRAFT')",
            (target,'CURRENT-PART-'+target.hex,header['po_id'],header['contractor_id'],header['cutting_group_id'],header['physical_at']))
        cur.execute('insert into erp.work_completion_lines(completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot)values(%s,%s,%s,%s,%s,0)',
            (target,f['snapshot'],f['component'],qty,qty))
        return target
    second=draft(6);returns.success(peer.operation(cur,'select erp.post_work_completion(%s)',(second,)))
    third=draft(1);before=data(cur)
    error=returns.refusal(cur,'select erp.post_work_completion(%s)',(third,),'melebihi Potongan efektif')
    assert data(cur)==before,'PARTIAL_OVER_LIMIT_CHANGED_FULL_DATA_OR_SEQUENCE'
    actors.admin(cur)
    amount=base.one(cur,"select sum(l.amount_payable)from erp.work_completion_lines l join erp.work_completion_events e on e.id=l.completion_id where e.po_id=%s and e.status='POSTED'",(f['po'],))
    assert amount==Decimal('12.50'),amount
    return dict(unpaid(cur,day,2,10,'12.50'),expected_total='12.50',actual_total=amount,over_limit=error)


def reference(target):
    def run(cur,day,today,current):
        # Retain the original lawful DRAFT insertion identity, private backend
        # invoice post and full physical fixture. Refused OWNER insert fails;
        # there is no admin fallback, new SELECT grant or trigger EXECUTE grant.
        table='work_completion_lines'if target=='WORK'else'vendor_invoice_items'
        relation='erp.production_orders'if target=='WORK'else'erp.laundry_receipt_lines'
        trigger='erp.validate_work_completion()'if target=='WORK'else'erp.validate_vendor_invoice_item_lineage()'
        actors.admin(cur)
        rights=cur.execute("select has_table_privilege('authenticated',%s,'SELECT'),has_function_privilege('authenticated',%s,'EXECUTE')",(relation,trigger)).fetchone()
        assert rights==(False,False),rights
        observations=[]
        class OwnerInsert:
            def __getattr__(self,name):return getattr(cur,name)
            def execute(self,query,params=None,**kwargs):
                if re.search(r'insert\s+into\s+erp\.'+table+r'\b',str(query),re.I):
                    identity=peer.ordinary(cur)
                    result=cur.execute(query,params,**kwargs)
                    observations.append(dict(table=table,identity=identity,ordinary_refusal=None))
                    return result
                if 'select erp.post_vendor_invoice('in str(query):actors.admin(cur)
                return cur.execute(query,params,**kwargs)
        proxy=OwnerInsert()
        if target=='WORK':
            f=production.estimated_receipt(cur,day);production.partial_production(proxy,f)
        else:
            actors.admin(cur);ai.prior.set_open_period(cur,date(2026,8,31))
            f=final.base.fresh(cur,'a')
            delivery=final.base.post_delivery(cur,f,final.base.BASE_PROCESS,'2026-09-01T11:00:00Z')
            _,_,receipt=final.base.post_receipt(cur,str(delivery['delivery_id']),final.base.BASE_PROCESS,'2026-09-02T11:00:00Z')
            final.finalize_laundry_invoice(proxy,receipt,Decimal('10'))
        assert len(observations)==1 and observations[0]['identity']==('authenticated','authenticated','OWNER'),observations
        actors.admin(cur)
        assert cur.execute("select has_table_privilege('authenticated',%s,'SELECT'),has_function_privilege('authenticated',%s,'EXECUTE')",(relation,trigger)).fetchone()==rights
        return dict(unpaid(cur,today,1,10,0),observations=observations,reference_rights_widened=False,
            invoice_posting_backend_only=target=='VENDOR')
    return run


def reject(cur,rid,kind,current):
    before=data(cur);actors.admin(cur);catalog=product.catalog._catalog_rows(cur)
    result=peer.operation(cur,'select erp.post_sales_return(%s)',(rid,))
    assert result['refused']and result['error']['sqlstate']=='P0001',result
    first=result['error']['message'].splitlines()[0];expected=REFUSALS[kind]['current'if current else'baseline']
    assert (first==expected if current else expected in first),(expected,result)
    assert data(cur)==before,'REFUSED_RETURN_CHANGED_MONEY_STOCK_HPP_DATA_OR_SEQUENCE'
    assert product.catalog._catalog_rows(cur)==catalog,'REFUSED_RETURN_CHANGED_CATALOG_OR_RIGHTS'
    return dict(refusal=result,expected_guard=expected,all_data_and_sequences_unchanged=True,full22_catalog_unchanged=True)


def positive_return(cur,day,f):
    rid=returns.create_return(cur,day,f,base.LOCATION,'GRADE_A')
    returns.success(peer.operation(cur,'select erp.post_sales_return(%s)',(rid,)))
    actors.admin(cur)
    rows=cur.execute("""select m.location_id::text,m.product_id::text,m.customer_id::text,m.quality_grade,m.qty_signed
        from erp.fg_stock_movements m join erp.sales_return_items i on i.id=m.source_id
        where i.return_id=%s and m.movement_type='SALE_RETURN'""",(rid,)).fetchall()
    assert rows==[(str(base.LOCATION),str(f['products'][0]),str(f['customers'][0]),'GRADE_A',1)],rows
    report=peer.confidence(cur,day);assert report['data_confidence']['status']=='READY',report
    return dict(return_id=str(rid),movement=rows,report=report)


def rebound(kind):
    def run(cur,day,today,current):
        f=returns.posted_fixture(cur,day);f['ordinary_draft_creation']=True
        rid=returns.create_return(cur,day,f,base.LOCATION,'GRADE_A')
        if kind=='CUSTOMER':returns.success(peer.operation(cur,'update erp.sales_returns set customer_id=%s where id=%s',(f['customers'][1],rid)))
        else:
            payload=dict(f['payload'],sale_number='CURRENT-OTHER-'+uuid.uuid4().hex,reason='Other legitimate sale')
            other=returns.success(peer.operation(cur,'select erp.save_sale_draft_v2(%s::jsonb,%s,null)',(json.dumps(payload),uuid.uuid4())))
            returns.success(peer.operation(cur,'select erp.post_sale_v2(%s,%s,%s)',(other['sale_id'],uuid.uuid4(),other['row_version'])))
            returns.success(peer.operation(cur,'update erp.sales_returns set sale_id=%s where id=%s',(other['sale_id'],rid)))
        result=reject(cur,rid,kind,current)
        good=positive_return(cur,day,f)
        return dict(status='PASS',**result,valid_ordinary_return_control=good)
    return run


def limit(cur,day,today,current):
    f=returns.posted_fixture(cur,day);f['ordinary_draft_creation']=True
    good=[positive_return(cur,day,f)for _ in range(3)]
    rid=returns.create_return(cur,day,f,base.LOCATION,'GRADE_A')
    result=reject(cur,rid,'LIMIT',current)
    actors.admin(cur)
    totals=cur.execute("""select count(*),sum(i.qty_pcs),sum(i.refund_amount)from erp.sales_return_items i
        join erp.sales_returns r on r.id=i.return_id where r.sale_id=%s and r.status='POSTED'""",(f['sale']['sale_id'],)).fetchone()
    assert totals==(3,3,Decimal('60')),totals
    return dict(status='PASS',**result,posted_return_count_qty_refund=totals,valid_ordinary_returns=good)


def cases(cur,today,*,current,evidence):
    day=today-timedelta(days=3)
    fixture.prepare(cur,today,current=current,closed_through=day-timedelta(days=5),evidence=evidence)
    operations=(partial,reference('WORK'),reference('VENDOR'),rebound('SOURCE'),limit,rebound('CUSTOMER'))
    def wrapped(name,fn):
        def run():
            row=fn(cur,day,today,current)
            return dict(status=row['status'],original_result=row,successor_control=name,
                legacy_ids=LEGACY_IDS[name],legacy_results_relabelled=False,current_AB=current)
        return run
    return [(name,wrapped(name,fn))for name,fn in zip(IDS,operations)]
