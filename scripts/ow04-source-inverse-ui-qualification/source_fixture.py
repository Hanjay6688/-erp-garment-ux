"""Read-only assertions for the original consumer browser fixture's source.

Only the fixed disposable browser DB is admitted. All business actions are
performed by the real product browser. This helper reads facts and stores exact
test observations; it never issues a financial command or alters a product row.
"""
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse
import json
import os
import sys
import uuid

OP = sys.argv[1] if len(sys.argv) == 2 else None
sys.argv = sys.argv[:1]
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path[:0] = [str(REPO/'scripts'), str(REPO/'scripts/ow04-consumer-ui-qualification')]
import browser_fixture as old
import native_refund_cases as refund

OUT = REPO/'cp6-proof/t3/source-inverse-ui-fixtures'
native = old.native
signed = old.business.fixture.signed


def save(key, stage, value):
    assert str(uuid.UUID(key)) == key and stage in ('initial', 'undone')
    raw = json.dumps(old.encoded(value), separators=(',', ':')).encode()
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT/(key+'.'+stage+'.json')).open('xb') as stream:
        stream.write(raw)
    return sha256(raw).hexdigest()


def load(key, stage, expected):
    assert str(uuid.UUID(key)) == key and stage in ('initial', 'undone')
    raw = (OUT/(key+'.'+stage+'.json')).read_bytes()
    assert sha256(raw).hexdigest() == expected
    return old.decoded(json.loads(raw))


def compact(profile):
    s = profile['source']
    return dict(gross=s['gross'],net=s['net'],P=s['P'],I=s['I'],
        C=s['net_consumption'],available=s['available_credit'],AR=s['AR'],cash=profile['cash'])


def main():
    assert OP in ('initial', 'blocked', 'undone', 'verify_inverse')
    target = os.environ['AUDITOR_BROWSER_DB_URL']
    url = urlparse(target)
    assert url.hostname in ('127.0.0.1','localhost') and url.path == '/cp6_auditor_browser'
    p = json.loads(sys.stdin.read())
    fixture = old.load(p['fixture'],p['fixture_sha256'])
    assert fixture['action'] == 'UNDO'
    pair = fixture['pair']
    source = pair['source']
    sale, returned = source['f']['sale'], pair['initial_result']['return_id']
    gold = json.loads((HERE/'EXPECTED.json').read_bytes())
    with old.psycopg.connect(target) as conn, conn.cursor() as cur:
        native.b.api.admin(cur)
        if OP == 'initial':
            actual = old.business.fixture.profiles(cur,pair)
            assert compact(actual) == gold['initial']
            row = cur.execute('select return_number from erp.sales_returns where id=%s and sale_id=%s',
                (returned,sale)).fetchone()
            assert row is not None
            digest = save(p['fixture'],'initial',signed._observe(cur,source))
            result = dict(status='PASS',return_id=str(returned),return_number=row[0],
                initial_sha256=digest,expected=gold['initial'],observed=compact(actual))
        elif OP == 'blocked':
            assert signed._observe(cur,source) == load(p['fixture'],'initial',p['initial_sha256'])
            result = dict(status='PASS',all_Native_and_private_facts_unchanged=True,
                original_source_inverse_refused_before_named_undo=True)
        elif OP == 'undone':
            actual = old.business.fixture.profiles(cur,pair)
            assert compact(actual) == gold['after_named_undo']
            events = native._array(cur,'cp7_credit.consumption_events','cohort_id=%s',
                (pair['initial_result']['credit_id'],))
            assert len(events['document']) == 2
            positive = next(e for e in events['document'] if e['amount'] == '200.00')
            inverse = next(e for e in events['document'] if e['amount'] == '-200.00')
            assert inverse['restores_event_id'] == positive['id']
            assert positive['id'] == pair['initial_result']['refund_event_id']
            held = dict(events=events,journals={str(e['journal_id']):native.journal(cur,str(e['journal_id']))
                for e in events['document']},source_return_journal=native.journal(cur,
                    pair['initial_actual']['native_return_journal']['document']['header']['id']),
                stock=native._array(cur,'erp.fg_stock_movements','lot_id=%s',(source['f']['lot'],)),
                hpp=native._array(cur,'erp.hpp_versions','lot_id=%s',(source['f']['lot'],)),
                lot=native._raw(cur,"select to_jsonb(l)-array['cached_qty_pcs','is_open']from erp.fg_lots l where id=%s",(source['f']['lot'],)))
            digest = save(p['fixture'],'undone',held)
            result = dict(status='PASS',undone_sha256=digest,expected=gold['after_named_undo'],observed=compact(actual))
        else:
            held = load(p['fixture'],'undone',p['undone_sha256'])
            args, outcome, actor = p['args'], p['outcome'], uuid.UUID(p['actor'])
            assert args['p_action'] == 'RETURN_REVERSE'
            assert args['p_payload']['sale_id'] == str(sale) and args['p_payload']['return_id'] == str(returned)
            request = uuid.UUID(args['p_request'])
            row = cur.execute('select action,payload,expected_version,response from cp7_sales.requests where actor=%s and request_id=%s',
                (actor,request)).fetchone()
            assert row == ('RETURN_REVERSE',args['p_payload'],args['p_expected'],outcome)
            assert outcome['return_id'] == str(returned) and outcome['return_status'] == 'REVERSED'
            operation = cur.execute('select operation_id from cp7_credit.source_operation_materializations_v1 '
                'where actor=%s and request_id=%s and action=%s and sale_id=%s and source_id=%s',
                (actor,request,'RETURN_REVERSE',sale,returned)).fetchall()
            assert len(operation) == 1
            cur.execute('select cp7_credit.assert_source_operation_closed_v1(%s)',(operation[0][0],))
            actual = old.business.fixture.profiles(cur,pair)
            assert actual == refund.GOLD['cases'][8]['expected']
            assert compact(actual) == gold['after_source_inverse']
            native.b.api.admin(cur)
            assert native._array(cur,'cp7_credit.consumption_events','cohort_id=%s',
                (pair['initial_result']['credit_id'],)) == held['events']
            for key, journal in held['journals'].items():
                assert native.journal(cur,key) == journal
            inverse = signed._assert_actual_inverse(cur,held['source_return_journal'])
            stock = native._array(cur,'erp.fg_stock_movements','lot_id=%s',(source['f']['lot'],))['document']
            old_ids = {m['id'] for m in held['stock']['document']}
            assert all(m in stock for m in held['stock']['document'])
            added = [m for m in stock if m['id'] not in old_ids]
            original = pair['initial_actual']['return_movement']['document']
            assert len(added) == len(original) == 1
            move, previous = added[0], original[0]
            assert (move['movement_type'],move['source_type'],move['source_id'],move['reversal_of_id']) == (
                'REVERSAL','FG_MOVEMENT_REVERSAL',previous['id'],previous['id'])
            for key in ('product_id','lot_id','location_id','quality_grade','unit_hpp_snapshot','customer_id'):
                assert move[key] == previous[key], key
            assert old.Decimal(move['qty_signed']) == -old.Decimal(previous['qty_signed'])
            assert native._array(cur,'erp.hpp_versions','lot_id=%s',(source['f']['lot'],)) == held['hpp']
            assert native._raw(cur,"select to_jsonb(l)-array['cached_qty_pcs','is_open']from erp.fg_lots l where id=%s",(source['f']['lot'],)) == held['lot']
            assert native.payment_snapshot(cur,source['f']['payment']) == source['payment_before']
            assert cur.execute('select count(*)from erp.sales_payments where sale_id=%s',(pair['target']['sale'],)).fetchone() == (0,)
            result = dict(status='PASS',actual_Auth_actor_proven=True,one_owning_source_request_and_operation=True,
                source_operation_closed=True,retained_signed_REFUND_and_named_UNDO_and_journals=True,
                original_payment_fact_unchanged=True,actual_linked_stock_and_journal_inverse=True,
                original_HPP_versions_and_lot_identity_unchanged=True,
                expected=gold['after_source_inverse'],observed=compact(actual),
                source_inverse_journal_id=inverse['document']['header']['id'],production_go=False)
        conn.rollback()
    print(json.dumps(result,default=str))


if __name__ == '__main__':
    main()
