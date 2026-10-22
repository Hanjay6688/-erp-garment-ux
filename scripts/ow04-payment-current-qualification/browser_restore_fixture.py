"""Read-only actual evidence for UI restoration; writes proof files only."""
from pathlib import Path
from hashlib import sha256
from urllib.parse import urlparse
import json,os,sys,uuid
OP=sys.argv[1]if len(sys.argv)==2 else None
sys.argv=sys.argv[:1]
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parent
sys.path[:0]=[str(ROOT),str(ROOT/'ow04-consumer-ui-qualification')]
import browser_fixture as old
import cp7_payment_correction_cases as payment
native=old.native
PHYSICAL=('items','allocations','returns','return_items','fg_lots','hpp_versions','stock_movements','inventory_balances',
 'opening_hpp_states','opening_hpp_corrections','po_hpp_states','po_hpp_events','nonpo_hpp_events','hpp_journals','hpp_balances')


def main():
    assert OP in('capture900','restored1000')
    url=os.environ['AUDITOR_BROWSER_DB_URL'];u=urlparse(url)
    assert u.hostname in('127.0.0.1','localhost')and u.path=='/cp6_auditor_browser'
    p=json.load(sys.stdin);saved=old.load(p['fixture'],p['fixture_sha256']);pair=saved['pair'];action=saved['action']
    args=p['args'];outcome=p['outcome'];actor=uuid.UUID(p['actor']);sale=pair['source']['f']['sale']
    file=REPO/'cp6-proof/t3/payment-restore-browser-fixtures'/(p['fixture']+'.json')
    with old.psycopg.connect(url)as conn,conn.cursor()as cur:
        cur.execute('set transaction read only');native.b.api.admin(cur)
        assert cur.execute('select payload,expected_version,response from cp7_payment_correction.requests where actor=%s and request_id=%s',
            (actor,args['p_request'])).fetchone()==(args['p_payload'],args['p_expected'],outcome)
        if OP=='capture900':
            assert args['p_payload']['replacement']['amount']=='900.00'
            source=cur.execute('select cp7_credit.source_native_snapshot_v1(%s)',(sale,)).fetchone()[0]
            events=native._array(cur,'cp7_credit.consumption_events','cohort_id=%s',(pair['initial_result']['credit_id'],))
            assert len(events['document'])==2
            first=old.decoded(json.loads((REPO/'cp6-proof/t3/payment-current-browser-fixtures'/(p['fixture']+'.json')).read_bytes()))
            original=payment.payment_fact(cur,pair['source']['f']['payment']);assert original==first['original']
            record=dict(lowered_id=outcome['payment_id'],original=original,lowered=payment.payment_fact(cur,outcome['payment_id']),
                events=events,journals={str(e['journal_id']):native.journal(cur,e['journal_id'])for e in events['document']},
                physical={k:source[k]for k in PHYSICAL})
            raw=json.dumps(old.encoded(record),separators=(',',':')).encode();file.parent.mkdir(parents=True,exist_ok=True)
            with file.open('xb')as stream:stream.write(raw)
            answer=dict(status='PASS',lowered_payment_id=outcome['payment_id'],read_only=True,proof_sha256=sha256(raw).hexdigest())
        else:
            record=old.decoded(json.loads(file.read_bytes()))
            assert args['p_payload']['payment_id']==record['lowered_id']and args['p_payload']['replacement']['amount']=='1000.00'
            assert payment.payment_fact(cur,pair['source']['f']['payment'])==record['original']
            assert payment.payment_fact(cur,record['lowered_id'])==record['lowered']
            assert native._array(cur,'cp7_credit.consumption_events','cohort_id=%s',(pair['initial_result']['credit_id'],))==record['events']
            for ident,value in record['journals'].items():assert native.journal(cur,ident)==value
            source=cur.execute('select cp7_credit.source_native_snapshot_v1(%s)',(sale,)).fetchone()[0]
            assert {k:source[k]for k in PHYSICAL}==record['physical']
            a=old.business.fixture.profiles(cur,pair);s,t=a['source'],a['target']
            actual=dict(source_net=s['net'],source_P=s['P'],I=s['I'],C=s['net_consumption'],available=s['available_credit'],
                source_AR=s['AR'],target_P=t['P'],target_U=t['U'],target_AR=t['AR'],cash=a['cash'])
            gold=json.loads((ROOT/'ow04-payment-positive-qualification/EXPECTED.json').read_bytes())['cases'][1 if action=='APPLY'else 3]['after_restore']
            assert actual==gold,(actual,gold)
            op=cur.execute("select operation_id from cp7_credit.source_operation_materializations_v1 where actor=%s and request_id=%s and action='PAYMENT_CORRECT'",(actor,args['p_request'])).fetchone()[0]
            cur.execute('select cp7_credit.assert_source_operation_closed_v1(%s)',(op,))
            answer=dict(status='PASS',actual_Auth_actor_request_and_source_operation=True,original_P1000_P900_C_journals_stock_HPP_retained=True,
                expected=gold,observed=actual,read_only=True,production_go=False)
        conn.rollback()
    print(json.dumps(answer))


if __name__=='__main__':main()
