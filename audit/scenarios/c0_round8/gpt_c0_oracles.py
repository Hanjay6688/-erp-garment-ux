"""Independent C0 D01 oracles, 8 AS + 12 calendar + 4 AO + 1 adjustment.

Authority: ratified C0 e83d56e6, sections 3.1-3.5; Master 3816/3818/3820/3825.
Writer helpers only construct ordinary fixtures and transport commands. Expected
money is Decimal arithmetic here; dates and prefix reports are checked here.
No replacement of frozen T2 results. Disposable clone, savepoint per case.
"""
from datetime import date, timedelta
from decimal import Decimal as D, ROUND_HALF_UP
import calendar
import json
import uuid

import cp6_aw_probe as awp

api, prod, boundary = awp.api, awp.chain.production, awp.boundary
KEYS = ('MATERIAL_INVENTORY','WIP','FG_INVENTORY','COGS','AP_SUPPLIER','GRNI_MATERIAL','OTHER_EXPENSE')
FIELDS = dict(MATERIAL_INVENTORY='material_inventory',WIP='wip_inventory',
              FG_INVENTORY='fg_inventory',AP_SUPPLIER='supplier_final_ap',GRNI_MATERIAL='grni_estimated_liability')


def cent(x):
    return D(str(x)).quantize(D('.01'), rounding=ROUND_HALF_UP)


def serial(x):
    if isinstance(x, dict): return {str(k):serial(v) for k,v in x.items()}
    if isinstance(x, (list,tuple)): return [serial(v) for v in x]
    if isinstance(x, (D,date,uuid.UUID)): return str(x)
    return x


def observe(cur, days):
    """Independent account cache / raw journal / public financial report reads."""
    out = {}
    for day in sorted(set(days)):
        api.admin(cur)
        daily = {k:D(str(cur.execute('''select coalesce(sum(debit_total-credit_total),0)
            from erp.account_daily_balances where account_id=erp.account_id(%s)
            and balance_date<=%s''',(k,day)).fetchone()[0])) for k in KEYS}
        journal = {k:D(str(cur.execute('''select coalesce(sum(l.debit-l.credit),0)
            from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
            where l.account_id=erp.account_id(%s) and j.status in ('POSTED','REVERSED')
            and j.transaction_date<=%s''',(k,day)).fetchone()[0])) for k in KEYS}
        api.ordinary(cur)
        report = cur.execute('select erp.get_owner_financial_snapshot_v2(%s,%s,%s)',
                             (min(days),day,day)).fetchone()[0]
        flat = {k:D(str(report['financial_position'][f]))*(-1 if k in ('AP_SUPPLIER','GRNI_MATERIAL') else 1)
                for k,f in FIELDS.items()}
        flat['COGS'] = D(str(report['performance']['cogs_gl']))
        confidence=report.get('data_confidence',{})
        out[str(day)] = dict(daily=daily,journal=journal,report=flat,
            confidence=dict(status=confidence.get('status'),changed_since_filing=confidence.get('changed_since_filing'),
                filing_present=bool(confidence.get('filing')),
                blocker_codes=sorted({str(b.get('code')) for b in confidence.get('blockers',[])})))
    api.admin(cur)
    return out


def differences(actual, before, wanted):
    errors = {}
    for day, targets in wanted.items():
        for source in ('daily','journal','report'):
            for key, target in targets.items():
                if key not in actual[day][source]: continue  # OTHER_EXPENSE has no direct report field in this helper.
                got = actual[day][source][key]-before[day][source][key]
                if got != target:
                    errors[f'{day}/{source}/{key}'] = dict(expected=target,actual=got)
    return errors


def deltas(actual,before):
    return {day:{source:{k:v-before[day][source][k] for k,v in actual[day][source].items()}
                 for source in ('daily','journal','report')} for day in actual}


def expected_production(days,e,g,today,material,ap,grni,closed=False):
    out = {}
    for day in days:
        row = {k:D(0) for k in KEYS}
        if day >= e:
            historical = closed and day < today
            m,a,r = (D(100),D(0),D(100)) if historical else (material,ap,grni)
            row.update(AP_SUPPLIER=-a,GRNI_MATERIAL=-r)
            if day < g: row['MATERIAL_INVENTORY'] = m
            else:
                total=cent(m+70)
                row.update(WIP=total-cent(total/2),FG_INVENTORY=cent(total*D('.3')),
                           COGS=cent(total*D('.2')))
        out[str(day)] = row
    return out


def journal_ids(cur):
    api.admin(cur)
    return {r[0] for r in cur.execute('select id from erp.journal_entries').fetchall()}


def fresh_journals(cur,old):
    api.admin(cur)
    return [r for r in cur.execute('''select id,source_type,economic_date,transaction_date,status
        from erp.journal_entries order by id''').fetchall() if r[0] not in old]


def invoice(cur,f,today,e,received,qty,rate,zone):
    api.admin(cur)
    version=cur.execute('select row_version from erp.material_purchase_headers where id=%s',
                        (f['purchase'],)).fetchone()[0]
    payload=dict(purchase_id=f['purchase'],supplier_invoice_number='G8C0-'+uuid.uuid4().hex,
        invoice_date=e,received_at=prod.at(received,15),reason='GPT independent C0 prefix oracle',
        lines=[dict(purchase_item_id=f['item'],qty_invoiced=qty,final_unit_price=str(rate))])
    cur.execute("select set_config('TimeZone',%s,true)",(zone,))
    key=uuid.uuid4()
    result=prod.rpc(cur,'erp.finalize_material_purchase_invoice_v2',payload,key,int(version))
    api.admin(cur); b=boundary.snapshot(cur)
    replay=prod.rpc(cur,'erp.finalize_material_purchase_invoice_v2',payload,key,int(version))
    api.admin(cur); same=replay==result and boundary.snapshot(cur)==b
    return result,same


def production_case(cur,today,e,zone,steps,old_id,closed=False):
    g,received=e+timedelta(days=1),today-timedelta(days=1)
    days=sorted({e-timedelta(days=1),e,g,received-timedelta(days=1),received,today})
    api.admin(cur);prod.prior.set_open_period(cur,e-timedelta(days=1))
    quiet=None
    if closed: quiet=awp.quiet_seed(cur,e,e)
    before=observe(cur,days)
    f=prod.estimated_receipt(cur,e+timedelta(days=3))
    prod.partial_production(awp.OrdinaryDraftCursor(cur),f)
    initial=observe(cur,days)
    initial_errors=differences(initial,before,expected_production(days,e,g,today,D(100),D(0),D(100)))
    if initial_errors:
        return serial(dict(status='INCOMPLETE',stage='FIXTURE',old_case=old_id,mismatches=initial_errors))
    api.admin(cur)
    source_before=cur.execute('select input_unit_cost from erp.material_stock_movements where id=%s',
                             (f['movement'],)).fetchone()[0]
    filed=None
    if closed:
        ready=awp.preflight(cur,e)
        if ready.get('status')!='READY':
            return serial(dict(status='INCOMPLETE',stage='CLOSE_PREFLIGHT',old_case=old_id,preflight=ready,quiet=quiet))
        api.ordinary(cur);cur.execute('select erp.close_accounting_through(%s,%s)',(e,'GPT C0 closed boundary'))
        filed=awp.filings(cur)
    observations=[]
    remaining,ap=D(10),D(0)
    for qty,rate in steps:
        old=journal_ids(cur)
        response,replay=invoice(cur,f,today,e,received,qty,rate,zone)
        pending_flag=awp.report(cur,e)
        api.ordinary(cur);cur.execute('select erp.process_cost_recalc_queue(100)')
        remaining-=D(qty);ap+=cent(D(qty)*D(rate));grni=remaining*10;material=ap+grni
        got=observe(cur,days)
        expected=expected_production(days,e,g,today,material,ap,grni,closed)
        errors=differences(got,before,expected)
        journals=fresh_journals(cur,old)
        for row in journals:
            wanted_e=e if closed or row[1]=='MATERIAL_SUPPLIER_INVOICE' else g
            wanted_book=today if closed else wanted_e
            if (row[2],row[3])!=(wanted_e,wanted_book):
                errors['journal/'+str(row[0])]=dict(expected_economic=wanted_e,expected_book=wanted_book,actual=row)
        if not journals: errors['journals']='No invoice/correction journals observed'
        api.admin(cur)
        events=cur.execute('''select effective_date,delta_amount,counterpart_mapping_key
            from erp.material_cost_revaluation_events where material_id=%s order by effective_date,id''',
            (f['material'],)).fetchall()
        if not events or any(r[0]!=(today if closed else g) for r in events): errors['movement_dates']=events
        quantity=cur.execute('select cached_stock_qty from erp.materials where id=%s',(f['material'],)).fetchone()[0]
        fg_qty=cur.execute('''select coalesce(sum(m.qty_signed),0) from erp.fg_stock_movements m
            join erp.fg_lots l on l.id=m.lot_id where l.po_id=%s''',(f['po'],)).fetchone()[0]
        if quantity!=0 or fg_qty!=3: errors['physical_qty']=dict(raw=quantity,fg=fg_qty)
        docs=cur.execute('''select h.invoice_date from erp.material_supplier_invoices h
            join erp.material_supplier_invoice_lines l on l.invoice_id=h.id
            where l.purchase_item_id=%s and h.status='POSTED' ''',(f['item'],)).fetchall()
        if not docs or any(r[0]!=e for r in docs): errors['invoice_document_dates']=docs
        original=cur.execute('select input_unit_cost from erp.material_stock_movements where id=%s',
                             (f['movement'],)).fetchone()[0]
        # input_unit_cost is a recost projection, not immutable original_unit_cost_snapshot.
        if not replay: errors['replay']='Response or full domain boundary changed'
        contexts=cur.execute('select count(*) from erp.invoice_recost_execution_context').fetchone()[0]
        if contexts: errors['contexts']=contexts
        queue=cur.execute("select status from erp.cost_recalc_queue where entity_type='PO' and entity_id=%s",(f['po'],)).fetchall()
        if any(r[0]!='DONE' for r in queue): errors['queue']=queue
        after_filed=awp.filings(cur) if closed else None
        if closed and after_filed!=filed: errors['filing_changed']=dict(before=filed,after=after_filed)
        observations.append(dict(qty=qty,rate=rate,expected=expected,observed=deltas(got,before),
            fresh_journals=journals,movement_revaluation_dates=events,replay_exact=replay,contexts=contexts,
            raw_qty=quantity,fg_qty=fg_qty,queue=queue,invoice_document_dates=docs,
            source_input_projection=dict(before=source_before,after=original),
            filed_before=filed,filed_after=after_filed,pending_report_state=pending_flag,
            report_confidence={d:v['confidence'] for d,v in got.items()},mismatches=errors))
    return serial(dict(status='COUNTEREXAMPLE' if any(o['mismatches'] for o in observations) else 'PASS',
        old_case=old_id,oracle='C0 D01.1-5 / M3816,3818,3820,3825',new_oracle=True,
        invoice_day=e,goods_day=g,recognition_day=today,session_zone=zone,closed=closed,
        observations=observations,quiet_fixture=quiet,
        limits='Filing contents equality checked; changed_since_filing flags retained for separate contract interpretation. Not full close-gate acceptance.'))


def adjustment_case(cur,today):
    e,a,received=today-timedelta(days=3),today-timedelta(days=2),today-timedelta(days=1)
    days=[e-timedelta(days=1),e,a,received,today]
    before=observe(cur,days)
    f=prod.estimated_receipt(cur,today)
    api.admin(cur)
    adjustment=cur.execute('''insert into erp.material_adjustments(adjustment_number,physical_at,location_id,reason_code,notes,status)
        values(%s,%s,%s,'COUNT_CORRECTION','GPT C0 -2 ordinary adjustment draft','DRAFT') returning id''',
        ('G8C0-'+uuid.uuid4().hex,prod.at(a,12),f['location'])).fetchone()[0]
    cur.execute('insert into erp.material_adjustment_items(adjustment_id,material_id,roll_id,qty_signed) values(%s,%s,%s,-2)',
                (adjustment,f['material'],f['roll']))
    version=cur.execute('select row_version from erp.material_adjustments where id=%s',(adjustment,)).fetchone()[0]
    api.ordinary(cur);cur.execute('select erp.post_material_adjustment_v2(%s,%s,%s,%s)',
                                  (adjustment,uuid.uuid4(),version,'GPT C0 ordinary count correction'))
    old=journal_ids(cur)
    _,replay=invoice(cur,f,today,e,received,10,D('20.003'),'UTC')
    got=observe(cur,days)
    wanted={}
    for day in days:
        row={k:D(0) for k in KEYS}
        if day>=e: row.update(MATERIAL_INVENTORY=D('200.03'),AP_SUPPLIER=D('-200.03'))
        if day>=a: row.update(MATERIAL_INVENTORY=D('160.02'),OTHER_EXPENSE=D('40.01'))
        wanted[str(day)]=row
    errors=differences(got,before,wanted)
    api.admin(cur)
    facts=cur.execute('''select r.effective_date,j.economic_date,j.transaction_date,r.ledger_delta
        from erp.material_adjustment_revaluation_facts r join erp.journal_entries j on j.id=r.journal_entry_id
        where r.adjustment_id=%s order by r.created_at,r.id''',(adjustment,)).fetchall()
    if not facts or any(r[:3]!=(a,a,a) for r in facts): errors['adjustment_dates']=dict(expected=[a,a,a],actual=facts)
    rows=fresh_journals(cur,old)
    invoices=[r for r in rows if r[1]=='MATERIAL_SUPPLIER_INVOICE']
    if not invoices or any(r[2:4]!=(e,e) for r in invoices): errors['supplier_invoice_dates']=invoices
    if not replay: errors['replay']='Not exact'
    doc=cur.execute('''select distinct h.id,h.row_version,h.invoice_date from erp.material_supplier_invoices h
        join erp.material_supplier_invoice_lines l on l.invoice_id=h.id
        where l.purchase_item_id=%s and h.status='POSTED' ''',(f['item'],)).fetchone()
    if doc[2]!=e: errors['invoice_document_date']=doc[2]
    api.receipts.rpc(api,cur,'reverse_material_supplier_invoice_v2',doc[0],
                     'GPT C0 linked invoice reversal',uuid.uuid4(),doc[1])
    api.admin(cur)
    inverses=cur.execute('''select r.effective_date,j.economic_date,j.transaction_date from erp.material_adjustment_revaluation_facts r
        join erp.journal_entries j on j.id=r.journal_entry_id where r.adjustment_id=%s and j.economic_date=%s''',
        (adjustment,today)).fetchall()
    if not inverses or any(r!=(today,today,today) for r in inverses): errors['linked_inverse_dates']=inverses
    after_inverse=observe(cur,days)
    inv_wanted={k:dict(v) for k,v in wanted.items()}
    inv_wanted[str(today)].update(MATERIAL_INVENTORY=D(80),OTHER_EXPENSE=D(20),AP_SUPPLIER=D(0),GRNI_MATERIAL=D(-100))
    errors.update({'inverse/'+k:v for k,v in differences(after_inverse,before,inv_wanted).items()})
    return serial(dict(status='COUNTEREXAMPLE' if errors else 'PASS',old_case='AS:ADJUSTMENT_DATE:False',
        oracle='C0 D01.1 invoice E; D01.3 value part max(E,A); inverse today, no early expense',new_oracle=True,
        expected=wanted,observed=deltas(got,before),facts=facts,fresh_journals=rows,inverse=inverses,
        inverse_expected=inv_wanted,inverse_observed=deltas(after_inverse,before),replay_exact=replay,mismatches=errors))


def month_before(day,n):
    y,m=divmod(day.year*12+day.month-1-n,12)
    return date(y,m+1,min(day.day,calendar.monthrange(y,m+1)[1]))


def cases(cur,today):
    out=[]
    for zone in ('Asia/Jakarta','UTC','Etc/GMT+12','Pacific/Kiritimati'):
        for rate in ('20','20.003'):
            old=f'DATE:False:{zone}:True:{rate}'
            out.append(('G8C0:AS:'+old,lambda z=zone,r=rate,i=old:production_case(cur,today,today-timedelta(days=3),z,[(10,D(r))],i)))
    received=today-timedelta(days=1)
    calendar_days=[(f'{n}_MONTHS',month_before(received,n)) for n in (1,2,3)]
    calendar_days += [('JAN31',date(today.year,1,31)),('FEB28',date(today.year,2,28)),('MAY31',date(today.year,5,31))]
    steps=[(3,D('8.25')),(7,D('11.75'))]
    for tag,day in calendar_days:
        for zone in ('UTC','Pacific/Kiritimati'):
            old=f'CALENDAR:{tag}:{zone}:False'
            out.append(('G8C0:'+old,lambda e=day,z=zone,i=old:production_case(cur,today,e,z,steps,i)))
    for zone in ('UTC','Pacific/Kiritimati'):
        for closed in (False,True):
            old=f'AO:INVOICE:{zone}:{closed}'
            out.append(('G8C0:'+old,lambda z=zone,c=closed,i=old:production_case(cur,today,month_before(received,2),z,steps,i,c)))
    out.append(('G8C0:AS:ADJUSTMENT_DATE:False',lambda:adjustment_case(cur,today)))
    assert len(out)==25 and len({k for k,_ in out})==25
    return out
