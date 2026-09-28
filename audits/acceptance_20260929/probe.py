"""Independent boundary controls on unchanged product; disclosed fixture reuse."""
from datetime import timedelta
import uuid
import cp6_independent_final_probe as original
import cp6_bf_conversion_history_probe as h

p,b,bf,one=h.p,h.b,h.bf,h.one


def boundary(cur,today,source=False,reversed_=False):
    f=h.fixture(cur,today)
    initial_books=p.books(cur)
    initial_source=p.stock(cur,f['source'])
    posted=h.post(cur,f)
    if reversed_:
        bf.be.be(cur,'REVERSE',dict(conversion_id=posted['conversion_id'],reason='Independent reversal history control'))
    stamp=f['when'](15)
    root=f['roots'][1] if source else f['target']
    old=f['a']['sku'] if source else f['target_a']['sku']
    new=f['z']['sku'] if source else f['target_z']['sku']
    ids=[f['a']['id'],f['z']['id']] if source else [f['target_a']['id'],f['target_z']['id']]
    def label(at):return one(cur,'select erp.bf_commercial_sku_at_v1(%s,%s)',root,at)
    def facts():
        return dict(document=h.document(cur,f),books=p.books(cur),source=p.stock(cur,f['source']),
            destination=p.stock(cur,posted['destination_lot_id']),
            historical=p.report(cur,f['target_a']['sku'],stamp)['groups'])
    def versions():
        return cur.execute('select sku_id,revision,effective_from,effective_to,settings from erp.bf_sku_versions_v1 where sku_id=any(%s::uuid[]) order by sku_id,revision',(ids,)).fetchall()
    def payload(at):
        value=h.move_payload(cur,f,15,source=source)
        value['effective_from']=at.isoformat()
        value['reason']='Independent microsecond history boundary'
        for g in value['groups']:
            g['legacy_basis']=one(cur,'select erp.bf_legacy_basis_v1(%s::uuid[],%s)',g['members'],at)
        return value
    before=facts();before_versions=versions()
    checks={'old_identity':label(stamp)==old}
    for name,at in [('one_microsecond_before',stamp-timedelta(microseconds=1)),('same_instant',stamp)]:
        value=payload(at)
        rejection=b.refused(cur,lambda:bf.call(cur,'SAVE_GROUPS',value),'BF_TARIFF_HISTORY')
        checks[name+'_refused']=rejection['ok']
        checks[name+'_atomic']=facts()==before and versions()==before_versions
    after_time=stamp+timedelta(microseconds=1)
    value=payload(after_time);key=str(uuid.uuid4())
    saved=bf.call(cur,'SAVE_GROUPS',value,key)
    after_versions=versions()
    replay=bf.call(cur,'SAVE_GROUPS',value,key)
    checks.update(later_change_accepted=saved.get('status')=='SAVED',
        exact_boundary=label(stamp)==old and label(after_time)==new,
        history_and_money_unchanged=facts()==before,
        replay_no_second_effect=replay.get('replayed') is True and versions()==after_versions and facts()==before)
    if not reversed_:
        bf.be.be(cur,'REVERSE',dict(conversion_id=posted['conversion_id'],reason='Independent inverse after allowed range move'))
    checks.update(inverse_books=p.books(cur)==initial_books,
        inverse_source=p.stock(cur,f['source'])==initial_source,
        inverse_destination=p.stock(cur,posted['destination_lot_id'])==0,
        reversed_document_keeps_labels=h.document(cur,f)['target_sku']==before['document']['target_sku']
          and h.document(cur,f)['source_sku']==before['document']['source_sku'])
    failed=[k for k,v in checks.items() if v is not True]
    return dict(status='FAIL' if failed else 'PASS',checks=checks,failed=failed,source=source,
        reversed_before_move=reversed_,physical_at=stamp.isoformat(),accepted_at=after_time.isoformat(),
        old_label=old,new_label=new,before=before,after=h.document(cur,f))


def cases(cur,today):
    return original.cases(cur,today)+[
      (f'OWN_ACCEPT:BOUNDARY_{side}_{status}',lambda source=(side=='SOURCE'),rev=(status=='REVERSED'):boundary(cur,today,source,rev))
      for side in ['SOURCE','DESTINATION'] for status in ['POSTED','REVERSED']
    ]+[('WRITER_RERUN:POPULATED_GRADE_B_RETURN',lambda:h.grade_b_return(cur,today))]


def races(tools,today):
    return [(f'WRITER_RERUN:CONVERSION_MASTER_{first}_{"COMMIT" if commit else "ABORT"}',
             lambda first=first,commit=commit:h.race(tools,today,first,commit))
            for first in ['CONVERSION','MOVE'] for commit in [True,False]]
