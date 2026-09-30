"""Required F03 cost continuations on the combined26-role stack.

This extends the P13 report reader to existing CP6 pocket and conversion
sources. It does not change frozen CP6 or invent an opening/refund policy.
"""
from datetime import timedelta
from decimal import Decimal as D
import uuid
import cp6_be_pocket_probe as pocket
import cp6_be_cost_probe as conversion
import cp6_be_probe as be
import cp7_finance_cases as finance
b = pocket.b


def report(cur, today, start):
    return finance.read(cur, today, **{'from':str(start)})


def amounts(cur, today, start):
    r=report(cur,today,start)['snapshot']
    return dict(WIP=D(r['financial_position']['wip_inventory']),
                FG_INVENTORY=D(r['financial_position']['fg_inventory']),
                COGS=D(r['performance']['cogs_gl']),
                OTHER_EXPENSE=D(r['performance']['operating_and_other_expense']))


def o18(cur,today):
    cut=today-timedelta(days=10)
    f=b.bbp.production_post(cur,today,pocket.active_unit(cur,pocket.rows(cut)))
    origin=b.one(cur,'select id::text from erp.be_pocket_usage_v1 where batch_id=%s',f['batch'])
    start=cut-timedelta(days=1)
    original=b.one(cur,'select to_jsonb(u) from erp.be_pocket_usage_v1 u where id=%s',origin)
    events=lambda:(b.one(cur,'select count(*) from erp.material_stock_movements'),b.one(cur,'select count(*) from erp.sewing_terminal_events'))
    source_events=events();before=pocket.amounts(cur);report_before=amounts(cur,today,start)
    preview=pocket.preview(cur,start,cut)
    assert preview['quantity']=='10' and preview['amount']=='11.25' and preview['can_post'],preview
    request=uuid.uuid4();payload=dict(period_start=str(start),period_end=str(cut),expected_revision=preview['revision'],reason='F03 O18 existing historical pocket oracle')
    posted=pocket.call(cur,'POST_PERIOD',payload,request)
    assert pocket.call(cur,'POST_PERIOD',payload,request)==posted
    first=pocket.difference(before,pocket.amounts(cur))
    expected=dict(WIP=D('5.62'),FG_INVENTORY=D('3.38'),COGS=D('2.25'),OTHER_EXPENSE=D('-11.25'))
    assert {k:first[k] for k in expected}==expected,first
    assert pocket.difference(report_before,amounts(cur,today,start))==expected
    changed=pocket.call(cur,'CORRECT_OPENING_USAGE',dict(usage_id=origin,amount='15.00',expected_amount='11.25',economic_date=str(cut+timedelta(days=1)),reason='F03 O18 source sheet corrected, same ten pieces'))
    current=pocket.difference(before,pocket.amounts(cur))
    corrected=dict(WIP=D('7.50'),FG_INVENTORY=D('4.50'),COGS=D('3.00'),OTHER_EXPENSE=D('-11.25'))
    assert {k:current[k] for k in corrected}==corrected,current
    assert pocket.difference(report_before,amounts(cur,today,start))==corrected
    assert events()==source_events and b.one(cur,'select to_jsonb(u) from erp.be_pocket_usage_v1 u where id=%s',origin)==original
    revision=b.one(cur,'select erp.pocket_period_state_v1(%s)',posted['id'])['revision']
    pocket.call(cur,'CANCEL_PERIOD',dict(id=posted['id'],expected_revision=revision,reason='Cancel allocation; retain actual source history'))
    inverse=pocket.difference(before,pocket.amounts(cur))
    expected_inverse=dict(WIP=D(0),FG_INVENTORY=D(0),COGS=D(0),OTHER_EXPENSE=D('3.75'))
    assert {k:inverse[k] for k in expected_inverse}==expected_inverse,inverse
    assert pocket.difference(report_before,amounts(cur,today,start))==expected_inverse and events()==source_events
    return dict(status='PASS',oracle='O18',source='LAWFUL_HISTORICAL_IMPORT',denominator=10,WIP_qty=5,FG_qty=3,sold_qty=2,initial=first,corrected=current,inverse=inverse,CP7_report_matches_exact_worksheet=True,same_request_one_period=True,no_material_or_sewing_event_repeated=True,opening_source_row_immutable=True,source_correction=changed,full_E07_acceptance=False)


def required(cur,today,operation,contract):
    result=operation(cur,today)
    assert result.get('status')=='PASS',result
    return dict(result,contract=contract,installed_stack='EXPLICIT_F03_26_ROLES',production_go=False,independent_acceptance=False,not_new_independent_CP6_acceptance=True)


def cases(cur,today):
    return [
      ('F03_O18_POCKET_EXACT_AND_P13_REPORT',lambda:o18(cur,today)),
      ('F03_E07_RECEIPT_POCKET_ZERO_DELTA_AND_REPRICE',lambda:required(cur,today,lambda c,d:pocket.receipt_correction(c,d,True),'E07/O18_ZERO_DELTA_CERTAINTY')),
      ('F03_E07_POCKET_SALE_RETURN_CONVERSION',lambda:required(cur,today,lambda c,d:pocket.stock_continuation(c,d,True),'E07_SALE_RETURN_CONVERSION')),
      ('F03_E04_CONVERSION_SOLD_CHILD_COST',lambda:required(cur,today,lambda c,d:conversion.chain_cost(c,d,True,be.fixture,be.be),'E04_SELECTED_CONVERSION_BRANCH')),
    ]
