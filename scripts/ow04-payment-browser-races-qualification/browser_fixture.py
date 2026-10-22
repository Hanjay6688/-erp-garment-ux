"""Read-only Native evidence for real product payment/credit browser journeys."""
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse
import json,os,sys,uuid
OP=sys.argv[1]if len(sys.argv)==2 else None
sys.argv=sys.argv[:1]
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path[:0]=[str(REPO/'scripts'),str(REPO/'scripts/ow04-consumer-ui-qualification')]
import browser_fixture as old
import cp7_payment_correction_cases as correction
native=old.native
OUT=REPO/'cp6-proof/t3/payment-current-browser-fixtures'
PHYSICAL=('items','allocations','returns','return_items','fg_lots','hpp_versions','stock_movements','inventory_balances',
 'opening_hpp_states','opening_hpp_corrections','po_hpp_states','po_hpp_events','nonpo_hpp_events','hpp_journals','hpp_balances')


def main():
    assert OP in('first80','correction','second20')
    target=os.environ['AUDITOR_BROWSER_DB_URL'];u=urlparse(target)
    assert u.hostname in('127.0.0.1','localhost')and u.path=='/cp6_auditor_browser'
    p=json.loads(sys.stdin.read());saved=old.load(p['fixture'],p['fixture_sha256']);pair=saved['pair'];action=saved['action']
    assert action in('APPLY','REFUND');index=0 if action=='APPLY'else 1
    gold=json.loads((REPO/'scripts/ow04-payment-source-qualification/EXPECTED.json').read_bytes())['positive'][index]
    later=json.loads((REPO/'scripts/ow04-payment-continuation-qualification/EXPECTED_INTEROP2.json').read_bytes())['cases'][index]
    actor=uuid.UUID(p['actor']);args=p['args'];outcome=p['outcome'];sale=pair['source']['f']['sale']
    with old.psycopg.connect(target)as conn,conn.cursor()as cur:
        native.b.api.admin(cur)
        original=correction.payment_fact(cur,pair['source']['f']['payment'])
        source=cur.execute('select cp7_credit.source_native_snapshot_v1(%s)',(sale,)).fetchone()[0]
        actual=old.business.fixture.profiles(cur,pair)
        native.b.api.admin(cur)
        if OP=='correction':
            assert cur.execute('select payload,expected_version,response from cp7_payment_correction.requests where actor=%s and request_id=%s',
                (actor,args['p_request'])).fetchone()==(args['p_payload'],args['p_expected'],outcome)
            operation=cur.execute("select operation_id from cp7_credit.source_operation_materializations_v1 where actor=%s and request_id=%s and action='PAYMENT_CORRECT'",
                (actor,args['p_request'])).fetchone()[0]
            cur.execute('select cp7_credit.assert_source_operation_closed_v1(%s)',(operation,))
            assert actual==gold['after']
        else:
            assert cur.execute('select payload,expected_versions,response from cp7_credit.consumer_requests_v1 where actor=%s and request_id=%s',
                (actor,args['p_request'])).fetchone()==(args['p_payload'],args['p_expected_versions'],outcome)
            cur.execute('select cp7_credit.assert_consumer_closed_v1(%s)',(outcome['operation_id'],))
            if OP=='first80':assert actual==gold['before']
            else:
                s,t=actual['source'],actual['target'];compact=dict(source_net=s['net'],source_P=s['P'],I=s['I'],C=s['net_consumption'],
                    available=s['available_credit'],source_AR=s['AR'],target_P=t['P'],target_U=t['U'],target_AR=t['AR'],cash=actual['cash'])
                assert {k:compact[k]for k in later['after_spend20']}==later['after_spend20']
                cur.execute('select cp7_credit.payment_consumer_header_proof_v1(%s)',(outcome['operation_id'],))
        file=OUT/(p['fixture']+'.json')
        if OP=='first80':
            assert old.invariant(cur,pair)==saved['native_before']
            observed=dict(original=original,physical={k:source[k]for k in PHYSICAL},first_event=outcome['consumption_event_id'],first_journal=native.journal(cur,outcome['journal_id']))
            raw=json.dumps(old.encoded(observed),separators=(',',':')).encode();OUT.mkdir(parents=True,exist_ok=True)
            with file.open('xb')as stream:stream.write(raw)
        else:
            observed=old.decoded(json.loads(file.read_bytes()))
            assert original==observed['original']
            assert {k:source[k]for k in PHYSICAL}==observed['physical']
            j=cur.execute('select journal_id from cp7_credit.consumption_events where id=%s',(observed['first_event'],)).fetchone()[0]
            assert native.journal(cur,j)==observed['first_journal']
        assert cur.execute('select count(*)from erp.sales_payments where sale_id=%s',(pair['target']['sale'],)).fetchone()[0]==0
        conn.rollback()
    print(json.dumps(dict(status='PASS',stage=OP,actual_Auth_actor_proven=True,observed=actual,payment_id=str(pair['source']['f']['payment']),
        payment_number=next(x['payment_number']for x in source['payments']if x['id']==str(pair['source']['f']['payment'])),
        original_payment_C80_journal_and_all_physical_HPP_retained=True,production_go=False)))


if __name__=='__main__':main()
