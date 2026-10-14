"""Three first-attempt probes of R3-01/R3-08 after authorized Fable exposure.

Fixture/transport attribution: unchanged candidate P12/P15 helpers. Oracles:
accrued completed work remains payable after SCRAP, and a corrected cutting
posting cannot make the public restated material history negative.
"""
from datetime import timedelta
from decimal import Decimal as D
import uuid
import cp7_nota_cases as nota
import cp7_cutting_correction_cases as cutting
import cp7_material_cases as material
from cases_stage import admin,check,save,wrap
from cases_payroll_leads import attempt

def rework(cur,today,all_bs):
    combined,b=nota.combined,nota.b
    f=combined.fixture(cur,today)
    wash=combined.wash(cur,f,range(4),11)
    combined.finish(cur,f,[wash],range(4),13,bs={3:2})
    bs=b.one(cur,"select id::text from erp.bs_cases where po_id=%s and product_id=%s and status='OPEN'",f['po'],f['roots'][3])
    b.chain.bs_action(cur,'CLASSIFY_BS',dict(bs_case_id=bs,cause_source='UNKNOWN',components=[dict(work_component_id=combined.prod.COMPONENT,completed_before_bs_qty=0)],change_reason='Astra two unfinished components'),b.chain.version(cur,'bs_cases',bs))
    component=b.one(cur,'select id::text from erp.bs_case_components where bs_case_id=%s and work_component_id=%s',bs,combined.prod.COMPONENT)
    bom=b.one(cur,'select erp.resolve_rework_accessory_bom_v1(%s,%s)::text',bs,f['when'](15))
    made=b.chain.bs_action(cur,'SAVE_REWORK',dict(rework_number='AS-R3-'+uuid.uuid4().hex[:10],bs_case_id=bs,destination_type='CONTRACTOR',contractor_id=combined.prod.CONTRACTOR,vendor_id=None,qty_sent=2,physical_sent_at=f['when'](15).isoformat(),status='IN_PROGRESS',return_fg_location_id=combined.base.LOCATION,accessory_bom_version_id=bom,accessory_bom_item_ids=[],change_reason='Astra two actually performed repairs',components=[dict(bs_case_component_id=component,qty_performed=2)]))
    rid=made['result']['rework_order_id']
    completed=b.chain.bs_action(cur,'COMPLETE_REWORK',dict(rework_order_id=rid,qty_good=0 if all_bs else 2,qty_bs=2 if all_bs else 0,completed_at=f['when'](16).isoformat(),return_fg_location_id=combined.base.LOCATION,change_reason='Astra first measured completed work'),b.chain.version(cur,'rework_orders',rid))
    disposed=None
    if all_bs:
        disposed=b.chain.bs_action(cur,'DISPOSE_BS',dict(bs_case_id=bs,resolution_type='SCRAP',qty_pcs=2,compensation_amount=0,source_laundry_claim_id=None,physical_at=f['when'](17).isoformat(),change_reason='Astra both irreparable pieces physically scrapped'),b.chain.version(cur,'bs_cases',bs))
    admin(cur)
    state=cur.execute('select status from erp.bs_cases where id=%s',(bs,)).fetchone()[0]
    lines=cur.execute('select id::text,qty_newly_payable,rate_snapshot,amount_payable from erp.rework_component_lines where rework_order_id=%s order by id',(rid,)).fetchall()
    journals=cur.execute("""select j.id::text,j.status,j.transaction_date,j.economic_date,l.debit,l.credit
      from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
      where j.source_type='REWORK_COMPLETION' and j.source_id=%s
      and l.account_id=erp.account_id('CONTRACTOR_PAYABLE') order by j.id,l.id""",(rid,)).fetchall()
    eligible=cur.execute("select to_jsonb(v) from erp.v_payroll_eligible_work_lines v where source_type='REWORK' and source_id=any(%s::uuid[]) order by source_id",([x[0]for x in lines],)).fetchall()
    workspace=nota.read(cur,'SOURCES',contractor_id=combined.prod.CONTRACTOR)
    cards=[c for c in workspace['page']['rows']if c['origin_id']==rid]
    witness=dict(lead='Fable R3-01',oracle_origin='ASTRA_AFTER_EXPOSURE',all_bs=all_bs,bs=bs,rework=rid,bs_status=state,completed=completed,disposed=disposed,component_lines=lines,journals=journals,eligible=eligible,public_source_workspace=workspace,matching_cards=cards)
    save('CP17_R3_REWORK_'+str(all_bs)+'_FIRST',witness)
    # Preconditions are fixture qualification, never business FAIL/PASS masking.
    assert state==('SCRAPPED'if all_bs else 'RESOLVED'),witness
    assert len(lines)==1 and lines[0][1:]==(2,D(30),D(60)),witness
    assert len(journals)==1 and journals[0][1]=='POSTED'and journals[0][-2:]==(D(0),D(60)),witness
    check(len(eligible)==1 and len(cards)==1,'Completed accrued contractor work must remain selectable for payroll after final BS disposition',witness=witness)
    card=cards[0]
    assert D(card['remaining_amount'])==60 and card['lines'][0]['remaining_qty']=='2',witness
    payload=dict(contractor_id=combined.prod.CONTRACTOR,note_date=str(today),period_start=str(today),period_end=str(today),cards=[dict(card_key=card['card_key'],source_token=card['source_token'])])
    n=nota.command(cur,'SAVE',payload);posted=nota.act(cur,'POST',n)
    labor=cur.execute('select labor_total from erp.payroll_settlements where id=%s',(posted['payroll_id'],)).fetchone()[0]
    check(labor==60,'Exactly the performed two components become payable once',labor=labor,posted=posted)
    witness.update(posted_note=posted,payroll_labor=labor)
    return witness

def repost(cur,today):
    f=cutting.fixture(cur,today)
    admin(cur)
    f['material'],f['location'],cut_at=cur.execute('select r.material_id::text,g.source_location_id::text,g.cut_at from erp.cutting_groups g join erp.cutting_group_rolls x on x.cutting_group_id=g.id join erp.material_rolls r on r.id=x.roll_id where g.id=%s',(f['group'],)).fetchone()
    cutoff=cut_at+timedelta(days=1)
    def observe():
        admin(cur)
        moves=cur.execute('select to_jsonb(m) from erp.material_stock_movements m where roll_id=%s and location_id=%s order by physical_at,system_created_at,id',(f['roll'],f['location'])).fetchall()
        dated=cur.execute('select coalesce(sum(qty_signed),0) from erp.material_stock_movements where roll_id=%s and location_id=%s and physical_at<=%s',(f['roll'],f['location'],cutoff)).fetchone()[0]
        entries=cur.execute("select to_jsonb(j) from erp.journal_entries j where (source_type='CUTTING_MATERIAL_ISSUE' and source_id=%s) or (source_type='JOURNAL_REVERSAL' and source_id in(select id from erp.journal_entries where source_type='CUTTING_MATERIAL_ISSUE' and source_id=%s)) order by transaction_date,id",(f['group'],f['group'])).fetchall()
        return dict(dated_qty=dated,current_qty=cutting.stock(cur,f),movements=moves,journals=entries,public_material_ledger=material.ledger(cur,f,f['location']))
    before=observe();assert before['dated_qty']==0 and before['current_qty']==0,before
    p,v=cutting.payload(cur,f);r=cutting.command(cur,p,v)
    d=cutting.verify_effect(cur,f,p,r)
    reopened=observe();assert reopened['dated_qty']==0 and reopened['current_qty']==10,reopened
    payload=dict(id=f['group'],action='SAVE_DRAFT',po_id=f['po'],pattern_id=d['pattern_id'],source_location_id=d['source_location_id'],cut_at=d['cut_at'],change_reason='Astra reviewed same ten pieces after reopen',size_slots=[{k:s[k]for k in('slot_no','size_id','drawing_no','label_override')}for s in d['size_slots']],rolls=[dict(roll_id=f['roll'],qty_issued=10,qty_consumed=10,qty_reported_remaining=0,yields=[dict(slot_no=1,qty_pcs=10)])])
    prod=cutting.cutting.qc.physical.b.chain.production
    saved=prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',payload,expected_version=int(r['row_version']))
    result=attempt(cur,lambda:prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',dict(payload,action='POST'),expected_version=int(saved['row_version'])))
    after=observe()
    witness=dict(lead='Fable R3-08',oracle_origin='ASTRA_AFTER_EXPOSURE',group=f['group'],cut_at=cut_at,cutoff=cutoff,before=before,reopened=reopened,repost_attempt=result,after=after)
    save('CP17_R3_CUTTING_REPOST_FIRST',witness)
    if not result['accepted']:
        # A rejected operation is not accepted as evidence that a complete
        # correction flow exists; retain exact refusal for manual disposition.
        return dict(witness,refusal_only=True,complete_correction_flow_proven=False)
    check(after['dated_qty']==before['dated_qty'] and after['current_qty']==0,'Identical corrected cutting must not double-issue dated physical stock',witness=witness)
    check(all(D(x['running_qty'])>=0 for x in after['public_material_ledger']['page']['rows']),'Public material ledger cannot contain a negative restated prefix',witness=witness)
    return witness

def cases(cur,today):
    return [wrap('CP17-ASTRA-R3-01-REWORK-GOOD-CONTROL',lambda:rework(cur,today,False)),
      wrap('CP17-ASTRA-R3-02-REWORK-ALL-BS-SCRAP',lambda:rework(cur,today,True)),
      wrap('CP17-ASTRA-R3-03-CUTTING-REPOST-CHRONOLOGY',lambda:repost(cur,today))]
