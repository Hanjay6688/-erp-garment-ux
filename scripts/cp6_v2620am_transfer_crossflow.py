#!/usr/bin/env python3
"""Actual warehouse transfer -> cutting -> wages -> FG/sale -> late invoices.

The established independent invoice/custody/money assertions stay unchanged.
Only its receipt fixture is extended by an ordinary physical transfer, so the
existing cutting API consumes the real roll at the new warehouse. No guard,
posted transaction, price policy, or report oracle is substituted.
"""
from pathlib import Path
from datetime import timedelta
from decimal import Decimal
import hashlib,json,os,subprocess,traceback,uuid
import psycopg
import cp6_v2620am_runtime as runtime
import cp6_v2620al_review as setup
import cp6_final_crossflow_review as invoice
from cp6_v2620n_rollback_guards import function_catalog
from cp6_v2620u_install_diagnostic import snapshot

ROOT=Path('cp6-proof/writer-am')
production=invoice.production


def case(cur,today,zone,qty,closed):
    original_receipt=production.estimated_receipt
    evidence={}
    def relocated(cur,day):
        fixture=original_receipt(cur,day)
        production.admin(cur)
        destination=cur.execute("insert into erp.locations(location_code,location_name,location_type,is_active) values(%s,'AM actual transfer destination','RAW_MATERIAL_WAREHOUSE',true) returning id",
            ('AM-X-'+uuid.uuid4().hex[:20],)).fetchone()[0]
        payload=dict(transfer_number='AM-X-'+uuid.uuid4().hex[:20],from_location_id=fixture['location'],
            to_location_id=destination,physical_at=production.at(fixture['purchase_day'],23,45),
            change_reason='AM ordinary warehouse relocation before cutting',
            items=[dict(material_id=fixture['material'],roll_id=fixture['roll'],qty=10)])
        production.owner(cur)
        assert cur.execute('select session_user').fetchone()[0]=='authenticated'
        draft=cur.execute('select erp.save_material_transfer_draft_v2(%s::jsonb,%s,null)',
            (json.dumps(payload,default=str),uuid.uuid4())).fetchone()[0]
        posted=cur.execute('select erp.post_material_transfer_v2(%s,%s,%s,%s)',
            (draft['material_transfer_id'],uuid.uuid4(),draft['row_version'],'AM consume at the actual destination')).fetchone()[0]
        production.admin(cur)
        assert posted['status']=='POSTED' and posted['movement_count']==2
        before=cur.execute("select sum(qty_signed),sum(qty_signed*unit_cost_snapshot) from erp.material_stock_movements where material_id=%s",(fixture['material'],)).fetchone()
        assert before==(10,100),before
        originals=cur.execute("select id,original_unit_cost_snapshot from erp.material_stock_movements where source_type='MATERIAL_TRANSFER' and source_id=%s order by id",(posted['material_transfer_id'],)).fetchall()
        assert len(originals)==2 and all(cost==10 for _,cost in originals),originals
        evidence.update(transfer=posted,material=fixture['material'],source=fixture['location'],destination=destination,
            originals=originals,before_production=before)
        fixture['location']=destination
        return fixture
    production.estimated_receipt=relocated
    try:
        result=invoice.case(cur,today,zone,qty,closed)
    finally:production.estimated_receipt=original_receipt
    production.admin(cur)
    assert evidence,'Transfer fixture was not invoked'
    transfer=evidence['transfer']
    movements=cur.execute("select movement_type,qty_signed,unit_cost_snapshot,original_unit_cost_snapshot,location_id from erp.material_stock_movements where source_type='MATERIAL_TRANSFER' and source_id=%s order by movement_type",(transfer['material_transfer_id'],)).fetchall()
    assert len(movements)==2 and sum(row[1] for row in movements)==0 and sum(row[1]*row[2] for row in movements)==0,movements
    assert movements[0][2]==movements[1][2]
    assert cur.execute("select id,original_unit_cost_snapshot from erp.material_stock_movements where source_type='MATERIAL_TRANSFER' and source_id=%s order by id",(transfer['material_transfer_id'],)).fetchall()==evidence['originals']
    # Ten units have become ten physical production pieces. Reversing their
    # transfer cannot remove the source while leaving downstream WIP/FG/sales.
    before=snapshot(cur);cur.execute('savepoint am_consumed_transfer')
    refused=None
    try:
        production.owner(cur)
        cur.execute('select erp.reverse_material_transfer_v2(%s,%s,%s,%s)',
            (transfer['material_transfer_id'],'AM consumed roll cannot be returned',uuid.uuid4(),transfer['row_version']))
    except psycopg.Error as exc:
        refused=dict(sqlstate=exc.sqlstate,message=exc.diag.message_primary)
        cur.execute('rollback to savepoint am_consumed_transfer')
    finally:
        production.admin(cur);cur.execute('release savepoint am_consumed_transfer')
    assert refused and snapshot(cur)==before,refused
    if not closed:
        assert any(token in refused['message'].lower() for token in ('stock','negative','insufficient')),refused
    result.update(transfer_evidence=evidence,final_transfer_movements=movements,
        reversal_refused_atomically=refused,closed_period=closed,transfer_value_neutral=True,original_snapshots_preserved=True)
    return result


def run():
    assert os.environ['PGURL']==setup.URL and os.environ['CP6_AI_INDEPENDENT_CONFIRM']=='postgres'
    head,tree=runtime.verify_audit_source()
    original_head='4b085e70569e63cd4ecc15a4460574aef86368a2'
    oracle_path='scripts/cp6_final_crossflow_review.py'
    raw=subprocess.check_output(['git','-C',str(runtime.ROOT),'show',original_head+':'+oracle_path])
    assert raw==(runtime.ROOT/oracle_path).read_bytes(),'AM invoice oracle changed'
    report=dict(status='INCOMPLETE',head=head,tree=tree,runtime_generation='AM',cases={},
        oracle_sha256=hashlib.sha256(raw).hexdigest(),oracle_source_head=original_head,
        independent_acceptance=False,production_go=False)
    ROOT.mkdir(parents=True,exist_ok=True)
    def save():(ROOT/'TRANSFER_CROSSFLOW.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
    save()
    with psycopg.connect(setup.ADMIN) as conn,conn.cursor() as cur:
        cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='240s';set local lock_timeout='8s'")
        assert len(runtime.verified_successor(cur))==690
        initial,catalog=snapshot(cur),function_catalog(cur)
        usage=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if not usage:cur.execute('grant usage on schema erp to authenticated')
        setup.actors.actors.claims(cur,dict(sub=setup.base.OPERATOR_AUTH,role='authenticated'))
        setup.base.load_fixture_foundation(cur);setup.actors.admin(cur)
        today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
        for zone in ('UTC','Asia/Jakarta'):
            for qty in (4,7):
                for closed in (False,True):
                    name=f'{zone}:{qty}:{closed}';production.admin(cur);before=snapshot(cur);cur.execute('savepoint am_bridge')
                    try:row=case(cur,today,zone,qty,closed)
                    except Exception as exc:row=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
                    finally:
                        cur.execute('rollback to savepoint am_bridge');production.admin(cur);cur.execute('release savepoint am_bridge')
                    row['boundary_restored']=snapshot(cur)==before
                    if not row['boundary_restored']:row['status']='INCOMPLETE'
                    report['cases'][name]=row;save()
                    print(json.dumps(dict(case=name,status=row['status'],error=row.get('error'))),flush=True)
        report['catalog_unchanged']=function_catalog(cur)==catalog
        conn.rollback();cur.execute("set local timezone='Asia/Jakarta'")
        report['boundary_restored']=snapshot(cur)==initial
        report['schema_usage_restored']=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]==usage
        assert len(runtime.verified_successor(cur))==690
        conn.rollback()
    report['counts']={s:sum(r['status']==s for r in report['cases'].values()) for s in ('CONTROL_PASS','BUG_PROVEN','INCOMPLETE')}
    if len(report['cases'])==8 and report['counts']['CONTROL_PASS']==8 and all(report[k] for k in ('boundary_restored','catalog_unchanged','schema_usage_restored')):
        report['status']='WRITER_PASS'
    save();return report

if __name__=='__main__':
    result=run();print(json.dumps({k:v for k,v in result.items() if k!='cases'},default=str))
    raise SystemExit(0 if result['status']=='WRITER_PASS' else 1)
