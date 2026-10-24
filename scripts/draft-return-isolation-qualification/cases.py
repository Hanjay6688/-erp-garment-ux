"""Real Native counterexample and controls for sibling DRAFT customer isolation."""
from datetime import timedelta
from pathlib import Path
import importlib.util

REPO=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('retained_contract6_business',REPO/'scripts/current-cp6-contract-qualification/cases.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
PATCHED=False
USED_GUARD=None
IDS=('VALID_RETURN_WITH_BAD_CUSTOMER_SIBLING_DRAFT','DRAFT_CUSTOMER_REMAINS_HASHED_DEPENDENCY',
     'RETAINED_SOURCE_REBIND_REFUSAL','RETAINED_THREE_PIECE_ALLOCATION_LIMIT')
COUNTEREXAMPLES=IDS[:2]
FIXTURES={}


def malformed(cur,day):
    f=old.returns.posted_fixture(cur,day);f['ordinary_draft_creation']=True
    rid=old.returns.create_return(cur,day,f,old.base.LOCATION,'GRADE_A')
    old.returns.success(old.peer.operation(cur,'update erp.sales_returns set customer_id=%s where id=%s',(f['customers'][1],rid)))
    old.actors.admin(cur)
    row=cur.execute('select to_jsonb(r)from erp.sales_returns r where id=%s',(rid,)).fetchone()[0]
    return f,rid,row


def customer_refusal(cur,rid):
    before=old.data(cur);catalog=old.product.catalog._catalog_rows(cur)
    result=old.peer.operation(cur,'select erp.post_sales_return(%s)',(rid,))
    code='CP7_NATIVE_EMPTY_ACTIVE_SOURCE_REQUIRED'if PATCHED else'OW04_SOURCE_CUSTOMER_MISMATCH'
    assert result['refused']and result['error']['sqlstate']=='P0001'and result['error']['message'].splitlines()[0]==code,result
    assert old.data(cur)==before and old.product.catalog._catalog_rows(cur)==catalog
    return dict(result=result,all_data_and_sequences_unchanged=True,full22_unchanged=True)


def valid_sibling(cur,day,today):
    f,rid,draft=malformed(cur,day)
    refused=customer_refusal(cur,rid)
    valid=old.positive_return(cur,day,f)
    old.actors.admin(cur)
    assert cur.execute('select to_jsonb(r)from erp.sales_returns r where id=%s',(rid,)).fetchone()[0]==draft
    assert draft['status']=='DRAFT'and draft['customer_id']==str(f['customers'][1])
    assert cur.execute("select count(*)from erp.journal_entries where source_type='SALES_RETURN'and source_id=%s",(rid,)).fetchone()[0]==0
    assert cur.execute("select count(*)from erp.fg_stock_movements m join erp.sales_return_items i on i.id=m.source_id where i.return_id=%s and m.source_type='SALES_RETURN_ITEM'",(rid,)).fetchone()[0]==0
    used=USED_GUARD(cur)if PATCHED else None
    return dict(status='PASS',malformed_draft=draft,invalid_selected_return_atomic_refusal=refused,
        legitimate_sibling=valid,malformed_draft_unchanged_no_stock_or_journal=True,used_inverse_refused_before_DDL=used)


def source(cur,sale):
    old.actors.admin(cur);before=old.data(cur)
    result=cur.execute('select ow04_source_proposal.locked_source_family(%s)',(sale,)).fetchone()[0]
    assert old.data(cur)==before,'SOURCE_COLLECTOR_CHANGED_ROWS_OR_SEQUENCES'
    assert result['source_status']=='BASE_COLLECTED'and not result['blockers'],result
    return result


def dependency(cur,day,today):
    f=old.returns.posted_fixture(cur,day);f['ordinary_draft_creation']=True
    sale=f['sale']['sale_id'];before=source(cur,sale)
    rid=old.returns.create_return(cur,day,f,old.base.LOCATION,'GRADE_A');draft=source(cur,sale)
    old.returns.success(old.peer.operation(cur,'update erp.sales_returns set customer_id=%s where id=%s',(f['customers'][1],rid)))
    malformed_source=source(cur,sale)
    assert before['events']==draft['events']==malformed_source['events']
    assert before['events_sha256']==draft['events_sha256']==malformed_source['events_sha256']
    assert len({before['state_sha256'],draft['state_sha256'],malformed_source['state_sha256']})==3
    doc=next(x for x in malformed_source['documents']if x['kind']=='RETURN'and x['id']==str(rid))
    assert doc['status']=='DRAFT'and doc['current_document_state']['customer_id']==str(f['customers'][1]),doc
    assert str(rid)in malformed_source['source_lock_ids']['returns']
    refused=customer_refusal(cur,rid)
    return dict(status='PASS',source_states=dict(before=before,draft=draft,malformed=malformed_source),
        changed_draft_hashed_and_locked=True,financial_events_unchanged=True,selected_wrong_customer_still_refused=refused)


def cases(cur,today):
    day=today-timedelta(days=3);stage='fixed'if PATCHED else'unfixed'
    old.fixture.prepare(cur,today,current=True,closed_through=day-timedelta(days=5),evidence=FIXTURES.setdefault(stage,{}))
    operations=(valid_sibling,dependency,
        lambda c,d,t:old.rebound('SOURCE')(c,d,t,True),
        lambda c,d,t:old.limit(c,d,t,True))
    def wrap(name,fn):
        def run():
            row=fn(cur,day,today)
            return dict(status=row['status'],original_result=row,regression_control=name,delta_installed=PATCHED)
        return run
    return [(name,wrap(name,fn))for name,fn in zip(IDS,operations)]
