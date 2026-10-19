"""Astra independent cross-boundary oracles, declared before execution.

Fixture constructors and RPC transport: writer CP17/BD. Decisions and expected
physical conservation / 3+1 wage and 2 laundry arithmetic: Astra, not writer
case verdicts. Product files are imported from the frozen candidate unchanged.
All scenarios run in strict_group savepoints; package installation/restoration
remains the reviewed P18 runner. A counterexample is deliberately not green.
"""
from pathlib import Path
import sys, os, json
from decimal import Decimal as D
from types import SimpleNamespace

sys.path.insert(0, str(Path(os.environ['ASTRA_CANDIDATE_ROOT']).resolve() / 'scripts'))
import cp7_cp17_fix_cases as f
import cp7_p18_full_cycle_probe as runner

IDS = ['ASTRA_G1_G2_TEN_PIECES_CONSERVED',
       'ASTRA_G2_UNSEWN_SIX_MUST_NOT_FINISH',
       'ASTRA_G2_SEWN_UNSENT_SIX_MUST_NOT_FINISH']

def cases(cur, today):
    def journey(sewn, delivered):
        g=f.pickup_fixture(cur,today)
        f.work_rates(cur,g)
        initial_wip=D(f.po_wip_balance(cur,g['po']))
        initial_gl=cur.execute("select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.status in('POSTED','REVERSED') and l.po_id=%s and l.account_id=erp.account_id('FG_INVENTORY')",(g['po'],)).fetchone()[0]
        assert initial_gl==0 and initial_wip>0, ('FIXTURE_NOT_PRISTINE',initial_gl,initial_wip)
        completions=[]
        for qty,hour in ((3,10),(sewn-3,11)):
            r=f.sewing_command(cur,f.sewing_workspace(cur,g),qty=qty,at=g['at'](hour))
            completions.append(r['result']['work_completion_id'])
        wages=cur.execute("select coalesce(sum(l.amount_payable),0) from erp.work_completion_lines l where completion_id=any(%s::uuid[])",(completions,)).fetchone()[0]
        assert wages==D(sewn)*4, ('WAGE_ARITHMETIC',wages,sewn*4)
        assert f.po_wip_balance(cur,g['po'])==initial_wip+sewn*4
        wash=dict(f.laundry_for(cur,g),po=g['po'])
        delivery=f.bd.post_priced(cur,wash,{},qty=delivered,hour=12)['delivery_id']
        receipt=f.bd.receive(cur,delivery,wash,delivered,13)['receipt_id']
        f.b.api.admin(cur)
        product,lot=f.bd.finish_goods(cur,wash,receipt,delivered,14)
        f.b.api.admin(cur)
        ready=f.sewn_ready(cur,g)
        assert ready==(sewn,sewn-delivered), ('PHYSICAL_READY',ready)
        workspace=f.finish_workspace(cur,g['po'])
        before=f.po_state(cur,g['po'])
        evidence=dict(cut=10,sewn=sewn,laundry_sent=delivered,fg=delivered,
                      unsewn=10-sewn,sewn_unsent=sewn-delivered,
                      initial_material_wip=str(initial_wip),wages=str(wages),
                      finish_eligible=workspace['eligible'],blockers=workspace['blockers'],hpp_before=workspace['hpp'])
        if delivered<10:
            # Six physical pieces cannot disappear through the ordinary FINISH
            # button: they have neither FG nor scrap/loss disposition.
            cur.execute('savepoint astra_finish_attempt')
            try:
                result=f.finish_command(cur,workspace,reason='Astra verify incomplete production cannot close')
            except Exception as exc:
                cur.execute('rollback to savepoint astra_finish_attempt')
                cur.execute('release savepoint astra_finish_attempt')
                after=f.po_state(cur,g['po'])
                assert after==before, ('REFUSAL_CHANGED_STATE',before,after)
                return dict(status='PASS',refusal=str(exc),**evidence)
            cur.execute('release savepoint astra_finish_attempt')
            after=f.po_state(cur,g['po'])
            assert after['status']=='FINISHED', ('UNEXPECTED_COMMAND_OUTCOME',result,after)
            return dict(status='COUNTEREXAMPLE',expected='refuse completion until every cut piece has a final disposition',
                        result=result,state_after=after,ready_after=f.sewn_ready(cur,g),**evidence)
        result=f.finish_command(cur,workspace,reason='Astra ten cut pieces all finished')
        state=f.po_state(cur,g['po']);hpp,qty=f.po_hpp(cur,g['po'])
        expected=initial_wip+D(10)*D(4)+D(10)*D(2)
        assert (state['status'],state['wip'],qty,hpp)==('FINISHED',D(0),10,expected), ('COMPLETE_CHAIN_CONSERVATION',state,qty,hpp,expected)
        assert f.sewn_ready(cur,g)==(10,0)
        unbalanced=cur.execute('select j.id from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id where l.po_id=%s group by j.id having sum(l.debit)<>sum(l.credit)',(g['po'],)).fetchall()
        assert not unbalanced, ('UNBALANCED_PO_JOURNAL',unbalanced)
        return dict(status='PASS',hpp_total=str(hpp),expected_hpp_total=str(expected),qty=qty,state=state,result=result,**evidence)
    return [(IDS[0],lambda:journey(10,10)),(IDS[1],lambda:journey(4,4)),(IDS[2],lambda:journey(10,4))]

if __name__=='__main__':
    manifest=Path(__file__).with_name('OWN_ORACLES.json')
    declaration=json.loads(manifest.read_text())
    assert declaration['ids']==IDS and declaration['candidate_sha']=='dfab13bf62398a69a02bf6221c06d29075e5e40b'
    runner.cases=SimpleNamespace(EXPECTED=len(IDS),cases=cases)
    runner.OUT=runner.bundle.ROOT/'cp6-proof/t3/ASTRA_OWN_ORACLES.json'
    runner.package._writer_runtime=lambda browser_mode=False:runner.run()
    runner.package.run('install')
