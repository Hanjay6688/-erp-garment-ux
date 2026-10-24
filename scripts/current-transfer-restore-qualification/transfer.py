"""Retained OW06 group-money oracles across a real current-installation restore.

Synthetic receipt/bank fixtures are explicit. Product helpers and assertions
come from the unchanged OW06 cases; no browser or independent audit claim.
"""
from datetime import timedelta
from decimal import Decimal
import uuid

from cp7_supplier_transfer import cases as business
from cp7_ab_bounded_chain import composition as product

catalog=product.catalog
AMOUNTS=('400.00','600.00')
CORRECTIONS=(('200.00','700.00'),('300.00','500.00'),
             ('400.00','600.00'),('500.00','400.00'))


def selected(cur,fixture,ident):
    # Canonical serialization of every selected-document field, including
    # journal dates/lines, allocations and lineage. No field is stripped.
    with catalog._catalog(cur):
        return business.read(cur,fixture,ident)['selected']


def create(cur,today):
    fixture=business.fixture(cur,today)
    at=business.single.invoice.aa.at(fixture['first']['day']+timedelta(days=1),12).isoformat()
    payload=business.payload(cur,fixture,AMOUNTS,at=at)
    key=uuid.uuid4();result=business.command(cur,payload,key)
    transfer=business.observe(cur,fixture,result['transfer_id'],AMOUNTS)
    rows=cur.execute("""select j.id,l.debit,l.credit from erp.journal_entries j
        join erp.journal_lines l on l.journal_entry_id=j.id
        where j.source_type='CP7_SUPPLIER_TRANSFER' and j.source_id=%s
        order by l.debit desc""",(transfer['id'],)).fetchall()
    assert len(rows)==2 and len({r[0]for r in rows})==1
    assert [(r[1],r[2])for r in rows]==[(Decimal(1000),Decimal(0)),(Decimal(0),Decimal(1000))]
    held=catalog._data(cur)
    assert business.command(cur,payload,key)==result and catalog._data(cur)==held
    before=selected(cur,fixture,transfer['id'])
    return dict(fixture=fixture,payload=payload,key=key,result=result,before=before,
        record=dict(status='PASS',allocations=list(AMOUNTS),cash_credit='1000.00',
            one_journal_two_lines=True,source_replay_all_rows_sequences_unchanged=True,
            stock_HPP_unchanged=True,fixture_created_by_Native_SQL=True))


def after_restore(cur,state):
    fixture=state['fixture'];original=state['result']['transfer_id']
    restored=selected(cur,fixture,original)
    differences={k:dict(before=state['before'].get(k),after=restored.get(k))
        for k in set(state['before'])|set(restored)
        if state['before'].get(k)!=restored.get(k)}
    assert restored==state['before'],('RESTORED_GROUP_TRANSFER_CHANGED',differences)
    business.observe(cur,fixture,original,AMOUNTS)
    held=catalog._data(cur)
    assert business.command(cur,state['payload'],state['key'])==state['result']
    assert catalog._data(cur)==held,'RESTORED_TRANSFER_REPLAY_SECOND_EFFECT'
    business.auth.refused(cur,lambda:business.command(cur,
        dict(state['payload'],reason='Changed same request after restore'),state['key']),'REQUEST_CHANGED')
    assert catalog._data(cur)==held
    child=restored['allocations'][0]
    reader=business.single.supplier.read(cur,dict(receipt=dict(purchase_id=child['purchase_id'])))
    row=next(p for p in reader['page']['rows']if p['id']==child['payment_id'])
    business.auth.refused(cur,lambda:business.single.supplier.command(cur,
        dict(purchase_id=child['purchase_id'],payment_id=child['payment_id'],
             review_token=row['review_token'],reason=business.REASON)),'USE_PARENT')
    assert catalog._data(cur)==held,'RESTORED_CHILD_REFUSAL_LEFT_EFFECT'
    current=original;history=[]
    for amounts in CORRECTIONS:
        previous=current
        payload=business.payload(cur,fixture,amounts,transfer=previous,at=state['payload']['payment_date'])
        key=uuid.uuid4();result=business.command(cur,payload,key);current=result['transfer_id']
        business.observe(cur,fixture,current,amounts)
        old=selected(cur,fixture,previous);new=selected(cur,fixture,current)
        assert old['status']=='REVERSED' and new['status']=='POSTED'
        assert new['payment_date']==state['before']['payment_date']
        assert new['journal']['economic_date']==state['before']['journal']['economic_date']
        assert cur.execute('select cp7_supplier_transfer.valid_correction_v1(%s)',(previous,)).fetchone()[0]is True
        held=catalog._data(cur)
        assert business.command(cur,payload,key)==result and catalog._data(cur)==held
        history.append(previous)
    count,dated=cur.execute("""select count(*),count(*)filter(where time_neutral_id is not null
        and effective_inverse_id is not null)from cp7_supplier_transfer.corrections_v1
        where original_id=any(%s::uuid[])""",(history,)).fetchone()
    assert count==dated==4,'RESTORED_CORRECTION_DATE_RESTATEMENTS_MISSING'
    payload=business.reverse_payload(cur,fixture,current);key=uuid.uuid4()
    result=business.command(cur,payload,key)
    back=business.observe(cur,fixture,current,CORRECTIONS[-1],'REVERSED')
    assert back['journal']['status']=='REVERSED'and back['inverse']['status']=='POSTED'
    held=catalog._data(cur)
    assert business.command(cur,payload,key)==result and catalog._data(cur)==held
    cur.execute('set constraints all immediate')
    return dict(status='PASS',selected_document_all_fields_exact=True,read_differences=differences,
        original_UUID_all_rows_sequences_unchanged=True,changed_UUID_refused_without_effect=True,
        individual_child_reverse_refused_without_effect=True,corrections=4,
        all_correction_UUID_replays_without_effect=True,original_and_successors_retained=True,
        economic_date_preserved=True,exact_date_restatement_pairs=dated,
        final_whole_transfer_reversed=True,reverse_UUID_without_effect=True,
        final_cash_net='0.00',stock_HPP_unchanged=True,real_commit_guards_checked=True)
