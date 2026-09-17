#!/usr/bin/env python3
"""Residual audit on unchanged AJ/money product, never a writer PASS oracle.

Existing helpers build ordinary documents. New assertions below cover downstream
sale/recost/reversal, mixed import diagnostics, and historical READY semantics.
Native temporary USAGE is recorded/restored; this is not an HTTP permission test.
"""
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import hashlib, json, os, subprocess, sys, traceback, uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import psycopg
import cp6_v2620aj_runtime as runtime
import cp6_v2620aj_review as setup
import cp6_final_gap_native as gaps
from cp6_v2620n_rollback_guards import function_catalog

PRODUCT = '47671d9ba2cfb8d02658388adb364b2ae6b89e8d'
PRODUCT_TREE = '46f4f605444c72dc32282025b859ab66375178b3'
REPORT = Path('cp6-proof/final-audit/FINAL_INDEPENDENT.json')
actors, base, production, peer = gaps.actors, gaps.base, gaps.production, gaps.peer


def save(report):
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, default=str) + '\n')


def owner(cur):
    production.owner(cur)


def observation(cur, po, baseline, today):
    actors.admin(cur)
    row = cur.execute('select base_output_qty,hpp_total_cost,fg_value,cogs_value '
                      'from erp.po_hpp_gl_state where po_id=%s', (po,)).fetchone()
    qty = cur.execute('select coalesce(sum(m.qty_signed),0) from erp.fg_stock_movements m '
                      'join erp.fg_lots f on f.id=m.lot_id where f.po_id=%s', (po,)).fetchone()[0]
    ledger = {k:v-baseline[k] for k,v in production.ledger(cur).items()}
    report = peer.confidence(cur, today)
    return dict(output=row[0], hpp=row[1], fg=row[2], cogs=row[3], qty=qty,
                ledger=ledger, confidence=report['data_confidence'])


def demand(row, *, qty, unit, sold, material):
    unit, material = Decimal(unit), Decimal(material)
    expected = dict(output=2, hpp=2*unit, fg=(2-sold)*unit, cogs=sold*unit, qty=qty)
    for k,v in expected.items():
        assert row[k] == v, dict(expected=expected, observed=row)
    assert row['ledger']['MATERIAL_INVENTORY'] == 0, row
    assert row['ledger']['WIP'] == material-2*unit, row
    assert row['ledger']['FG_INVENTORY'] == expected['fg'], row
    assert row['ledger']['COGS'] == expected['cogs'], row
    assert row['confidence']['status'] == 'READY', row


def recovered_sale(cur, today, route, failed):
    baseline = production.ledger(cur)
    # Setup creates ten real pieces, zero original GOOD, two recovery outputs,
    # and reverses one of them. Only two recovered pieces remain saleable.
    fixture = setup.rework_case(cur, today, 0, route, failed)
    alive = fixture['observations'][1]
    actors.admin(cur)
    po, product, group = cur.execute('select po_id,product_id,cutting_group_id '
                                     'from erp.fg_lots where id=%s', (alive['lot'],)).fetchone()
    purchases = cur.execute("""select distinct i.id,i.purchase_id,h.row_version,h.physical_at
      from erp.material_stock_movements m join erp.material_purchase_items i on i.material_id=m.material_id
      join erp.material_purchase_headers h on h.id=i.purchase_id
      where m.source_type='CUTTING_GROUP' and m.source_id=%s and m.qty_signed<0 and h.status='POSTED'""", (group,)).fetchall()
    assert len(purchases)==1, 'Fixture material purchase lineage must be unique'
    item, purchase, pv, physical = purchases[0]
    unit = Decimal(24 if failed else 17)
    total = unit*10
    phases=[]
    start=observation(cur,po,baseline,today);demand(start,qty=2,unit=unit,sold=0,material=total)
    phases.append(dict(stage='RECOVERED_TWO',state=start))
    actors.admin(cur);customer=base.create_customer(cur,uuid.uuid4().hex[:16])
    draft=production.rpc(cur,'erp.save_sale_draft_v2',dict(
      sale_number='RESIDUAL-'+uuid.uuid4().hex,customer_id=customer,source_location_id=base.LOCATION,
      sale_date=production.at(today-timedelta(days=2),16),reason='Independent sale from recovered lot',
      items=[dict(product_id=str(product),qty_pcs=1,unit_price_snapshot=40,discount_amount=0)]))
    reserved=observation(cur,po,baseline,today)
    demand(reserved,qty=1,unit=unit,sold=0,material=total)
    phases.append(dict(stage='DRAFT_RESERVES_ONCE_LEDGER_INERT',state=reserved))
    owner(cur);cur.execute('select erp.post_sale_v2(%s,%s,%s)',
                          (draft['sale_id'],uuid.uuid4(),draft['row_version']))
    posted=observation(cur,po,baseline,today);demand(posted,qty=1,unit=unit,sold=1,material=total)
    phases.append(dict(stage='POST_NO_SECOND_STOCK_OUT',state=posted))
    actors.admin(cur);before=actors.boundary(cur);cur.execute('savepoint downstream_refusal')
    refused=None
    try:
        setup.bs_action(cur,'REVERSE_REWORK_COMPLETION',dict(rework_order_id=alive['order'],
                        change_reason='Recovery still supplies a posted customer sale'),setup.version(cur,'rework_orders',alive['order']))
    except psycopg.Error as exc:
        refused=dict(sqlstate=exc.sqlstate,message=exc.diag.message_primary)
    finally:
        cur.execute('rollback to savepoint downstream_refusal');actors.admin(cur)
        cur.execute('release savepoint downstream_refusal')
    assert refused and refused['sqlstate']=='P0001' and 'downstream' in refused['message'], refused
    assert actors.boundary(cur)==before
    invoice=production.rpc(cur,'erp.finalize_material_purchase_invoice_v2',dict(
      purchase_id=str(purchase),supplier_invoice_number='RECOST-'+uuid.uuid4().hex,
      invoice_date=physical.date(),received_at=production.at(today-timedelta(days=1),15),
      reason='Final invoice after recovered output sold',
      lines=[dict(purchase_item_id=str(item),qty_invoiced=10,final_unit_price='12.75')]),uuid.uuid4(),pv)
    peer.ordinary(cur);cur.execute('select erp.process_cost_recalc_queue(100)')
    corrected=observation(cur,po,baseline,today)
    demand(corrected,qty=1,unit=unit+Decimal('2.75'),sold=1,material=total+Decimal('27.50'))
    assert corrected['ledger']['AP_SUPPLIER']==Decimal('-127.50') and corrected['ledger']['GRNI_MATERIAL']==0
    phases.append(dict(stage='LATE_INVOICE_UPDATES_RECOVERY_FG_AND_COGS',state=corrected))
    actors.admin(cur)
    iv=cur.execute('select row_version from erp.material_supplier_invoices where id=%s',
                   (invoice['supplier_invoice_id'],)).fetchone()[0]
    owner(cur);cur.execute('select erp.reverse_material_supplier_invoice_v2(%s,%s,%s,%s)',
        (invoice['supplier_invoice_id'],'Independent linked invoice reversal',uuid.uuid4(),iv))
    peer.ordinary(cur);cur.execute('select erp.process_cost_recalc_queue(100)')
    restored=observation(cur,po,baseline,today);demand(restored,qty=1,unit=unit,sold=1,material=total)
    assert restored['ledger']['AP_SUPPLIER']==0 and restored['ledger']['GRNI_MATERIAL']==-100
    phases.append(dict(stage='LINKED_INVOICE_REVERSE_RESTORES_ESTIMATE',state=restored))
    owner(cur);cur.execute('select erp.reverse_sale(%s,%s)',(draft['sale_id'],'Independent linked sale reversal'))
    returned=observation(cur,po,baseline,today);demand(returned,qty=2,unit=unit,sold=0,material=total)
    setup.bs_action(cur,'REVERSE_REWORK_COMPLETION',dict(rework_order_id=alive['order'],
                    change_reason='All downstream postings now reversed'),setup.version(cur,'rework_orders',alive['order']))
    final=observation(cur,po,baseline,today)
    assert final['qty']==final['output']==final['fg']==final['cogs']==0, final
    assert final['ledger']['WIP']==total and final['confidence']['status']=='READY',final
    phases.append(dict(stage='ALL_RECOVERIES_REVERSED',state=final))
    return dict(status='PASS',route=route,failed_wash=failed,phases=phases,
                source_reversal_refused=refused,setup_observations_not_counted_as_new_cases=True)


def import_mixed(cur,today,variant):
    batch,material=gaps.raw_batch(cur,today,'VALID');actors.admin(cur)
    original=cur.execute('select normalized_payload from erp.migration_staging_rows where batch_id=%s',(batch,)).fetchone()[0]
    payload=dict(original)
    if variant=='NONNUMERIC':payload['qty']='two'
    elif variant=='MISSING_COST':payload.pop('unit_cost')
    elif variant=='UNKNOWN_LOCATION':payload['location_code']='ABSENT-'+uuid.uuid4().hex
    else:raise AssertionError(variant)
    cur.execute("""insert into erp.migration_staging_rows(id,batch_id,entity_type,source_row_no,legacy_key,source_payload,normalized_payload,validation_status)
      values(%s,%s,'OPENING_BALANCE_ITEM',2,'second-row',%s::jsonb,%s::jsonb,'PENDING')""",(uuid.uuid4(),batch,json.dumps(payload),json.dumps(payload)))
    before=production.ledger(cur);owner(cur)
    totals=cur.execute('select * from erp.validate_migration_batch(%s)',(batch,)).fetchall()
    actors.admin(cur)
    rows=cur.execute('select source_row_no,validation_status,validation_errors from erp.migration_staging_rows where batch_id=%s order by source_row_no',(batch,)).fetchall()
    assert production.ledger(cur)==before,'Preview wrote to ledger'
    row_error=totals==[(2,1,1)] and rows[0][1]=='VALID' and rows[1][1]=='ERROR' and bool(rows[1][2])
    cur.execute('savepoint invalid_prepare');prepare_error=None
    try:
        owner(cur);cur.execute('select erp.prepare_migration_opening_balance(%s,%s)',(batch,'INVALID-'+uuid.uuid4().hex))
    except psycopg.Error as exc:prepare_error=dict(sqlstate=exc.sqlstate,message=exc.diag.message_primary)
    finally:
        cur.execute('rollback to savepoint invalid_prepare');actors.admin(cur);cur.execute('release savepoint invalid_prepare')
    assert prepare_error is not None and production.ledger(cur)==before,'Invalid import was admitted'
    cur.execute('update erp.migration_staging_rows set normalized_payload=%s::jsonb where batch_id=%s and source_row_no=2',
                (json.dumps(original),batch))
    owner(cur);corrected=cur.execute('select * from erp.validate_migration_batch(%s)',(batch,)).fetchall()
    assert corrected==[(2,2,0)] and production.ledger(cur)==before
    owner(cur);opening=cur.execute('select erp.prepare_migration_opening_balance(%s,%s)',(batch,'MIXED-'+uuid.uuid4().hex)).fetchone()[0]
    again=cur.execute('select erp.prepare_migration_opening_balance(%s,null)',(batch,)).fetchone()[0]
    assert opening==again and production.ledger(cur)==before
    owner(cur);cur.execute('select erp.post_opening_balance(%s)',(opening,));cur.execute('select erp.finalize_migration_batch(%s)',(batch,))
    actors.admin(cur)
    actual=cur.execute('select sum(qty_signed),sum(qty_signed*unit_cost_snapshot) from erp.material_stock_movements where material_id=%s',(material,)).fetchone()
    assert actual==(20,Decimal('25.00')),actual
    return dict(status='PASS' if row_error else 'GAP_PROVEN',variant=variant,preview_totals=totals,rows=rows,
                prepare_refusal=prepare_error,corrected_totals=corrected,posted_totals=actual,
                parser_csv_tested=False,requirement='Owner master 21.1 row errors before import')


def history(cur,today,zone):
    purchased=gaps.months_before(today-timedelta(days=1),3)
    evidence=gaps.calendar_case(cur,today,purchased,today-timedelta(days=1),zone,False)
    assert evidence['current_totals_reconciled'],'Original ordinary fixture did not qualify'
    owner(cur);report=cur.execute('select erp.get_owner_financial_snapshot_v2(%s,%s,%s)',
        (purchased,today-timedelta(days=2),today-timedelta(days=2))).fetchone()[0]
    # Capture the historical confidence, not the current day's confidence.
    return dict(status='DATE_POLICY_REVIEW_REQUIRED',zone=zone,as_of=today-timedelta(days=2),
                confidence=report['data_confidence'],financial_position=report['financial_position'],
                performance=report['performance'],ordinary_invoice_observations=evidence['observations'],
                policy_not_invented=True)


def run():
    assert os.environ.get('PGURL')==setup.URL and os.environ.get('CP6_AI_INDEPENDENT_CONFIRM')=='postgres'
    head,tree=runtime.verify_audit_source()
    git=lambda *args:subprocess.check_output(['git','-C',str(runtime.ROOT),*args],text=True).strip()
    assert git('rev-parse',PRODUCT+'^{tree}')==PRODUCT_TREE
    assert not git('diff','--name-only',PRODUCT,'HEAD','--','src','supabase','package.json','package-lock.json'),'Business product drift'
    report=dict(status='INCOMPLETE',business_head=PRODUCT,business_tree=PRODUCT_TREE,harness_head=head,harness_tree=tree,
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cases={},production_go=False)
    with psycopg.connect(setup.ADMIN) as conn,conn.cursor() as cur:
        cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='240s';set local lock_timeout='8s'")
        assert len(runtime.verified_successor(cur))==690
        baseline,catalog=actors.boundary(cur),function_catalog(cur)
        usage=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        report['temporary_schema_usage_grant']=not usage
        if not usage:cur.execute('grant usage on schema erp to authenticated')
        actors.actors.claims(cur,dict(sub=base.OPERATOR_AUTH,role='authenticated'));base.load_fixture_foundation(cur);actors.admin(cur)
        today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
        specs=[(f'RECOVERED_SALE:{route}:failed={failed}',lambda c,r=route,f=failed:recovered_sale(c,today,r,f))
               for route in ('CONTRACTOR','LAUNDRY') for failed in (False,True)]
        specs += [('MIXED_IMPORT:'+v,lambda c,v=v:import_mixed(c,today,v)) for v in ('NONNUMERIC','MISSING_COST','UNKNOWN_LOCATION')]
        specs += [('HISTORICAL_READY:'+z,lambda c,z=z:history(c,today,z)) for z in ('UTC','Pacific/Kiritimati')]
        report['planned_case_ids']=[n for n,_ in specs];save(report)
        for name,fn in specs:
            actors.admin(cur);before=actors.boundary(cur);cur.execute('savepoint independent_case')
            try:row=fn(cur)
            except Exception as exc:row=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
            finally:
                cur.execute('rollback to savepoint independent_case');actors.admin(cur);cur.execute('release savepoint independent_case')
            row['full_boundary_restored']=actors.boundary(cur)==before
            if not row['full_boundary_restored']:row['status']='INCOMPLETE'
            report['cases'][name]=row;save(report)
            print(json.dumps(dict(case=name,status=row['status'],error=row.get('error'))),flush=True)
        report['catalog_unchanged']=function_catalog(cur)==catalog
        conn.rollback();cur.execute("set local timezone='Asia/Jakarta'")
        report['boundary_restored']=actors.boundary(cur)==baseline
        report['schema_usage_restored']=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]==usage
        report['auth_users'],report['app_users']=cur.execute('select (select count(*) from auth.users),(select count(*) from erp.app_users)').fetchone()
        conn.rollback()
    report['counts']={s:sum(c['status']==s for c in report['cases'].values()) for s in ('PASS','GAP_PROVEN','BUG_PROVEN','DATE_POLICY_REVIEW_REQUIRED','INCOMPLETE')}
    complete=len(report['cases'])==len(report['planned_case_ids']) and all(report[k] for k in ('catalog_unchanged','boundary_restored','schema_usage_restored'))
    report['status']='INCOMPLETE' if not complete or report['counts']['INCOMPLETE'] else 'HOLD' if any(report['counts'][s] for s in ('GAP_PROVEN','BUG_PROVEN','DATE_POLICY_REVIEW_REQUIRED')) else 'PASS_REVIEWED_SCOPE'
    save(report);return report


if __name__=='__main__':
    try:result=run()
    except Exception as exc:
        result=json.loads(REPORT.read_text()) if REPORT.exists() else {}
        result.update(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc(),production_go=False);save(result)
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},default=str))
    raise SystemExit(0 if result['status']=='PASS_REVIEWED_SCOPE' else 1)
