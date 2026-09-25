"""GPT contract follow-up BC, independently asserted boundary on a disposable clone.

BC helpers construct legal fixtures only. The result does not inherit their verdict.
Source-identity limits are explicitly INCOMPLETE, never a product PASS.
"""
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4
from psycopg.types.json import Jsonb

import cp6_bc_probe as bc


def custody_new_key_same_goods(cur, today):
    d = today - timedelta(days=1)
    fx = bc.fixture(cur, d, purchase=False)
    rows = bc.bbp.masters()
    rows['OPENING_ACCESSORY_CUSTODY'] = [dict(
        custody_kind='PENDING_VALUE', custody_key='{C}-PHYSICAL-ONE',
        material_sku=fx['code'], location_code=fx['code']+'IN',
        condition='WAITING', qty='3', notes='fixture physical identifier PHYSICAL-ONE',
    )]
    batch, code, _ = bc.bbp.post_batch(cur, d, rows)
    opening_lots = [x for x in bc.ws(cur, dict(query=fx['code']))['lots']
                    if x['source_kind'] == 'OPENING_PENDING_VALUE']
    if len(opening_lots) != 1:
        return dict(status='INCOMPLETE', stage='initial_lot', count=len(opening_lots))
    first = opening_lots[0]['id']
    bc.inspect(cur, first, bc.local_at(d, 10), 'GPT auditor', usable=3)
    bc.policy(cur, 'ACC_DEC03', dict(credit_account_id=bc.account(cur, '4100'), unit_value_cap='NONE'))
    b0 = bc.ledger(cur)
    bc.svc(cur, 'VALUE_CUSTODY', dict(
        lot_id=first, condition='USABLE', qty='3', unit_value='2.00',
        location_id=fx['main'], physical_at=bc.local_at(d, 11), reason='first custody value'))
    b1 = bc.ledger(cur)
    first_stock = bc.stock(cur, fx['material'], fx['main'])
    second_rows = bc.bbp.masters()
    second_rows['OPENING_ACCESSORY_CUSTODY'] = [dict(
        custody_kind='PENDING_VALUE', custody_key=code+'-PHYSICAL-TWO',
        material_sku=fx['code'], location_code=fx['code']+'IN',
        condition='WAITING', qty='3', notes='asserted same physical identifier PHYSICAL-ONE',
    )]
    second_error = None
    cur.execute('savepoint gbc_second_import')
    try:
        bc.bbp.post_batch(cur, d, second_rows)
        cur.execute('release savepoint gbc_second_import')
    except Exception as exc:
        second_error = str(exc)[:400]
        cur.execute('rollback to savepoint gbc_second_import')
        cur.execute('release savepoint gbc_second_import')
        bc.api.admin(cur)
    remaining = [x for x in bc.ws(cur, dict(query=fx['code']))['lots']
                 if x['source_kind'] == 'OPENING_PENDING_VALUE' and x['id'] != first]
    if second_error is None and len(remaining) == 1:
        bc.inspect(cur, remaining[0]['id'], bc.local_at(d, 12), 'GPT auditor', usable=3)
        bc.svc(cur, 'VALUE_CUSTODY', dict(
            lot_id=remaining[0]['id'], condition='USABLE', qty='3', unit_value='2.00',
            location_id=fx['main'], physical_at=bc.local_at(d, 13), reason='later document claiming same goods'))
    b2 = bc.ledger(cur)
    second_stock = bc.stock(cur, fx['material'], fx['main'])

    # Distinct real receipt is an explicit positive control, not the second
    # document for the opening physical goods.
    saved = bc.internal(cur, 'save_material_purchase_draft_v2', Jsonb(dict(
        purchase_number=fx['code']+'NEW', supplier_id=fx['supplier'],
        location_id=fx['main'], physical_at=bc.local_at(d, 14),
        change_reason='distinct physical receipt', lines=[dict(
            material_id=fx['material'], qty=3, unit_price='2.00',
            price_state='ESTIMATED', price_source='MANUAL_ESTIMATE')])),
        str(uuid4()), None)
    bc.internal(cur, 'post_material_purchase_v2', saved['purchase_id'],
                str(uuid4()), saved['row_version'], 'distinct physical receipt')
    control_stock = bc.stock(cur, fx['material'], fx['main'])

    measured = dict(initial_stock=str(first_stock), after_second=str(second_stock),
                    after_distinct_receipt=str(control_stock),
                    first_gl_delta={k: str(v) for k,v in bc.delta(b0,b1).items()},
                    second_gl_delta={k: str(v) for k,v in bc.delta(b1,b2).items()},
                    second_import_error=second_error, second_lot_count=len(remaining),
                    distinct_receipt_increases_by_3=control_stock-second_stock==3)
    # The import exposes only a caller-assigned custody_key, not a verifiable
    # physical identity. A note claiming the goods are the same is insufficient
    # to adjudicate product failure or acceptance. Record the observed effect.
    return dict(status='INCOMPLETE', reason='NEEDS_SOURCE_IDENTITY_POLICY',
                **measured, oracle='M:3935, M:5290; physical goods once, pending value not final')


def cases(cur, today):
    return [('GBC-1:NEW_CUSTODY_KEY_SAME_PHYSICAL_CLAIM',
             lambda: custody_new_key_same_goods(cur, today))]
