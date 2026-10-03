"""P12 native Nota source qualification; composing/posting/payroll UI remains open."""
from pathlib import Path
import hashlib,json,traceback
import psycopg
import cp7_restore_state as restore_state
import cp7_payroll_bundle as bundle
import cp7_fg_bundle as fg_bundle
import cp7_p10_fg_probe as p10
import cp7_nota_source_cases as cases
import cp7_p09_procurement_probe as p09
import cp6_auditor_modes as modes
import cp6_auditor_runner as native
import cp6_t3_package_run as package
from cp6_t3_aligned_install import advisors,advisor_delta
OUT=bundle.ROOT/'cp6-proof/t3/CP7_P12_NOTA_SOURCE.json'

def verify(cur):
    result=p10.verify(cur)
    assert cur.execute("select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_payroll' and (p.prosecdef or pg_get_userbyid(p.proowner)<>'cp7_payroll_read' or p.proconfig is distinct from array['search_path=\"\"'] or p.provolatile::text<>'s')").fetchone()[0]==0
    assert cur.execute("select p.prosecdef and pg_get_userbyid(p.proowner)='cp7_payroll_read' and p.proconfig=array['search_path=\"\"'] from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proname='erp_cp7_get_nota_sources_v1'").fetchone()==(True,)
    return dict(result,cp7_p12_bundle_sha256=hashlib.sha256(bundle.bundle().encode()).hexdigest())

def run():
    report=dict(label='CP7_P12_NOTA_NATIVE_SOURCE',status='INCOMPLETE',production_go=False,independent_acceptance=False,scope='NATIVE_COMPONENT_SOURCE_READS_ONLY_NO_NOTE_OR_PAYROLL_UI_WRITER',source_sha256=hashlib.sha256(bundle.bundle().encode()).hexdigest())
    installed=False
    try:
        with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
            p09.wip.policy.bf.verified(cur);restore_before=restore_state.capture(cur,package.boundary.snapshot,native.public_state,p09.functions);before=restore_before['boundary'];public_before=restore_before['public'];conn.rollback()
            originals,installation=p09.install(cur);report.update(installation);pre=p09.functions(cur)
            cur.execute(fg_bundle.extension(),prepare=False);cur.execute(bundle.extension(),prepare=False);after=p09.functions(cur)
            grants=('auth.uid()','auth.jwt()','erp.get_my_access_v1()','erp.has_permission(text)','erp.bf_commercial_sku_at_v1(uuid,timestamptz)','erp.bd_lot_laundry_unknown_v1(uuid)','erp.get_hpp_completeness(uuid)')
            # regprocedure prints timestamp with time zone with empty search_path.
            path=cur.execute('show search_path').fetchone()[0];cur.execute("select set_config('search_path','',true)")
            grants={str(cur.execute('select %s::regprocedure::text',(s,)).fetchone()[0]):{('cp7_fg_read','EXECUTE',False)} for s in grants}
            for signature in ('auth.uid()','auth.jwt()','erp.get_my_access_v1()','erp.has_permission(text)','erp.save_fg_adjustment_draft_v2(jsonb,uuid,bigint)','erp.post_fg_adjustment_v2(uuid,uuid,bigint,text)','erp.reverse_fg_adjustment_v2(uuid,text,uuid,bigint)','erp.move_fg_stock_card_row_to_position(uuid,integer)','erp.reset_fg_stock_mutation_book_order()'):
                key=str(cur.execute('select %s::regprocedure::text',(signature,)).fetchone()[0]);grants.setdefault(key,set()).add(('cp7_fg_write','EXECUTE',False))
            for signature in ('auth.uid()','auth.jwt()','erp.get_my_access_v1()','erp.has_permission(text)'):
                key=str(cur.execute('select %s::regprocedure::text',(signature,)).fetchone()[0]);grants.setdefault(key,set()).add(('cp7_payroll_read','EXECUTE',False))
            cur.execute("select set_config('search_path',%s,true)",(path,))
            for signature,old in pre.items():
                new=after[signature];assert new['definition']==old['definition'] and new['owner']==old['owner'],('P12_PREDECESSOR_CHANGED',signature)
                expected={tuple(x) for x in old['acl'] or []}|grants.get(signature,set())
                assert {tuple(x) for x in new['acl'] or []}==expected,('P12_UNDECLARED_ACL_DELTA',signature)
            p09.INSTALLED_FUNCTIONS=after;report['source_declared_execute_grants']={k:sorted(v) for k,v in grants.items()}
            conn.commit();installed=True;verify(cur);conn.rollback()
        report['advisors_with_cp7']=advisors(package.boundary.PG)
        report['native']=native.strict_group('CP7_P12_NOTA_SOURCE',cases.cases,verify)
        report['http']=modes.run_http(cases,verify,'cp7_p12_nota_source')
    except Exception as e:report.update(error=str(e),traceback=traceback.format_exc())
    finally:
        if installed:
            with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
                for definition in originals.values():cur.execute(definition,prepare=False)
                for role in ('cp7_payroll_read','cp7_fg_write','cp7_fg_read','cp7_return_write','cp7_return_read','cp7_invoice_write','cp7_invoice_read','cp7_material_write','cp7_material_read','cp7_procure_write','cp7_procure_read','cp7_policy','cp7_capture'):
                    cur.execute('drop owned by '+role+' cascade;drop role '+role,prepare=False)
                conn.commit();report['cp6_restored']=restore_state.prove(cur,restore_before,package.boundary.snapshot,native.public_state,p09.functions,report)
                conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
            report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report.get('advisors_with_cp7',{}));d=report['advisor_delta']
            report['advisor_gate']=d['status']=='NO_NEW_FINDINGS' or (d['status']=='REVIEW_REQUIRED' and all(f.get('name')=='rls_enabled_no_policy' and f.get('level')=='INFO' and (f.get('metadata') or {}).get('schema') in ('cp7_payroll','cp7_fg','cp7_private','cp7_identity','cp7_wip','cp7_procurement','cp7_material','cp7_supplier_return','cp7_invoice','cp7_receipt_fix') for f in d.get('added',[])))
        groups=[report.get(k,{}) for k in ('native','http')]
        report['status']='PASS' if not report.get('error') and report.get('cp6_restored') and report.get('advisor_gate') and all(r.get('status') in ('PASS','RUN_COMPLETE') and set(r.get('counts',{}))=={'PASS'} and r['counts']['PASS']>0 and r.get('database_remaining',0)==0 for r in groups) else 'INCOMPLETE'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n');print(json.dumps({k:report.get(k) for k in ('label','status','source_sha256','cp6_restored','advisor_gate','error','traceback')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,independent_acceptance=False)

if __name__=='__main__':
    package._writer_runtime=lambda browser_mode=False:run()
    package.run('install')
