"""P09 public receipt bridge on a disposable accepted CP6 install; writer proof."""
from pathlib import Path
import hashlib,json,traceback
import psycopg
import cp7_procurement_bundle as bundle
import cp7_procurement_cases as cases
import cp7_material_cases as material
import cp7_material_count_cases as counts
import cp7_invoice_cases as invoice
import cp7_supplier_return_cases as returns
import cp7_receipt_reversal_cases as reversal
import cp7_procurement_uom_cases as uom
import cp7_p04_wip_probe as wip
import cp6_auditor_modes as modes
import cp6_auditor_runner as native
import cp6_t3_package_run as package
from cp6_t3_aligned_install import advisors,advisor_delta
OUT=Path(__file__).resolve().parents[1]/'cp6-proof/t3/CP7_P09_PROCUREMENT.json'
INSTALLED_FUNCTIONS=None

def functions(cur):
    path=cur.execute('show search_path').fetchone()[0]
    cur.execute("select set_config('search_path','',true)")
    try:return dict(cur.execute("""select p.oid::regprocedure::text,jsonb_build_object(
      'definition',md5(pg_get_functiondef(p.oid)),'owner',pg_get_userbyid(p.proowner),
      'acl',(select jsonb_agg(jsonb_build_array(case when a.grantee=0 then 'PUBLIC' else pg_get_userbyid(a.grantee) end,a.privilege_type,a.is_grantable) order by a.grantee,a.privilege_type,a.is_grantable)
        from aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a))
      from pg_proc p join pg_namespace n on n.oid=p.pronamespace where p.prokind='f' and
      (n.nspname in ('erp','public') or n.nspname like 'cp7_%' or n.nspname='auth' and p.proname in ('uid','jwt')) order by 1""").fetchall())
    finally:cur.execute("select set_config('search_path',%s,true)",(path,))

def verify(cur):
    # Accepted CP6 and F02 verification ran before the declared extension. Once
    # it is installed, all function definitions/ACLs must match the captured
    # installation, including the two explicitly replaced predecessor guards.
    assert INSTALLED_FUNCTIONS is not None and functions(cur)==INSTALLED_FUNCTIONS,'P09_INSTALLED_FUNCTION_OR_ACL_CHANGED'
    assert cur.execute("select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_procurement' and (p.prosecdef is distinct from (p.proname in('reverse_receipt_locked','validate_uom_lines')) or pg_get_userbyid(p.proowner)<>case when p.proname='reverse_receipt_locked' then 'postgres' when p.proname in('command','reverse_request','save_draft_request') then 'cp7_procure_write' else 'cp7_procure_read' end or p.proconfig is distinct from array['search_path=\"\"'])").fetchone()[0]==0
    for name,role in [('erp_cp7_get_procurement_v1','cp7_procure_read'),('erp_cp7_get_procurement_options_v1','cp7_procure_read'),('erp_cp7_get_procurement_uom_v1','cp7_procure_read'),('erp_cp7_save_procurement_v1','cp7_procure_write'),
      ('erp_cp7_preview_material_count_v1','cp7_material_read'),('erp_cp7_get_material_counts_v1','cp7_material_read'),('erp_cp7_save_material_count_v1','cp7_material_write'),
      ('erp_cp7_get_materials_v1','cp7_material_read'),('erp_cp7_get_material_ledger_v1','cp7_material_read'),
      ('erp_cp7_get_material_transfers_v1','cp7_material_read'),('erp_cp7_get_material_locations_v1','cp7_material_read'),('erp_cp7_save_materials_v1','cp7_material_write'),
      ('erp_cp7_get_purchase_invoices_v1','cp7_invoice_read'),('erp_cp7_save_purchase_invoice_v1','cp7_invoice_write'),
      ('erp_cp7_get_supplier_returns_v1','cp7_return_read'),('erp_cp7_save_supplier_return_v1','cp7_return_write')]:
        assert cur.execute("select p.prosecdef and pg_get_userbyid(p.proowner)=%s and p.proconfig=array['search_path=\"\"'] from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proname=%s",(role,name)).fetchone()==(True,)
    assert cur.execute("select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_material' and (p.prosecdef is distinct from (p.proname in('validate_lines','validate_transfer_scope','count_lines','count_signature')) or pg_get_userbyid(p.proowner)<>case when p.proname in('command','count_command') then 'cp7_material_write' else 'cp7_material_read' end or p.proconfig is distinct from array['search_path=\"\"'])").fetchone()[0]==0
    assert cur.execute("select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_invoice' and (p.prosecdef is distinct from (p.proname='assert_single_receipt') or pg_get_userbyid(p.proowner)<>case when p.proname='command' then 'cp7_invoice_write' else 'cp7_invoice_read' end or p.proconfig is distinct from array['search_path=\"\"'])").fetchone()[0]==0
    assert cur.execute("select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_supplier_return' and (p.prosecdef is distinct from (p.proname in('validate_source','assert_document','validate_post')) or pg_get_userbyid(p.proowner)<>case when p.proname='command' then 'cp7_return_write' else 'cp7_return_read' end or p.proconfig is distinct from array['search_path=\"\"'])").fetchone()[0]==0
    return dict(stage='CP7_F02_PLUS_DECLARED_P09' ,cp7_p09_bundle_sha256=hashlib.sha256(bundle.bundle().encode()).hexdigest())

def run():
    global INSTALLED_FUNCTIONS
    report=dict(label='CP7_P09_RECEIPT_BRIDGE',status='INCOMPLETE',production_go=False,independent_acceptance=False,
      scope='BOUNDED_RECEIPT_MATERIAL_TRANSFER_COUNT_INVOICE_RETURN_AND_RECEIPT_INVERSE_CONNECTED',source_sha256=hashlib.sha256(bundle.bundle().encode()).hexdigest())
    installed=False
    try:
        with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
            wip.policy.bf.verified(cur);before=package.boundary.snapshot(cur);public_before=native.public_state(cur);conn.rollback()
            originals={s:cur.execute('select pg_get_functiondef(%s::regprocedure)',(s,)).fetchone()[0] for s in bundle.REPLACED}
            cur.execute(bundle.cp7_wip_bundle.bundle(),prepare=False);report['accepted_and_f02_verified']=wip.verify(cur)
            pre_functions=functions(cur)
            cur.execute(bundle.extension(),prepare=False)
            INSTALLED_FUNCTIONS=functions(cur)
            changed={s for s,v in pre_functions.items() if INSTALLED_FUNCTIONS.get(s,{}).get('definition')!=v['definition']}
            assert changed==set(bundle.REPLACED),('P09_UNDECLARED_PREDECESSOR_CHANGE',changed)
            grants={s:{(r,'EXECUTE',False) for r in ('cp7_procure_read','cp7_procure_write','cp7_material_read','cp7_material_write','cp7_invoice_read','cp7_invoice_write','cp7_return_read','cp7_return_write')} for s in ('auth.uid()','auth.jwt()','erp.get_my_access_v1()','erp.has_permission(text)')}
            grants.update({s:{('cp7_procure_write','EXECUTE',False)} for s in ('erp.save_material_purchase_draft_v2(jsonb,uuid,bigint)','erp.post_material_purchase_v2(uuid,uuid,bigint,text)')})
            grants.update({s:{('cp7_material_write','EXECUTE',False)} for s in ('erp.save_material_transfer_draft_v2(jsonb,uuid,bigint)','erp.post_material_transfer_v2(uuid,uuid,bigint,text)','erp.reverse_material_transfer_v2(uuid,text,uuid,bigint)','erp.save_material_adjustment_draft_v2(jsonb,uuid,bigint)','erp.post_material_adjustment_v2(uuid,uuid,bigint,text)','erp.reverse_material_adjustment_v2(uuid,text,uuid,bigint)')})
            grants.update({s:{('cp7_invoice_read','EXECUTE',False)} for s in ('erp.material_purchase_invoice_capacity(uuid)','erp.material_purchase_posted_invoice_qty(uuid)')})
            grants.update({s:{('cp7_invoice_write','EXECUTE',False)} for s in ('erp.finalize_material_purchase_invoice_v2(jsonb,uuid,bigint)','erp.reverse_material_supplier_invoice_v2(uuid,text,uuid,bigint)')})
            grants.update({s:{('cp7_return_write','EXECUTE',False)} for s in ('erp.save_material_supplier_return_draft_v2(jsonb,uuid,bigint)','erp.post_material_supplier_return_v2(uuid,uuid,bigint,text)','erp.reverse_material_supplier_return_v2(uuid,text,uuid,bigint)')})
            for signature,old in pre_functions.items():
                new=INSTALLED_FUNCTIONS[signature]
                assert new['owner']==old['owner'],('P09_PREDECESSOR_OWNER_CHANGED',signature)
                old_acl={tuple(x) for x in old['acl'] or []};new_acl={tuple(x) for x in new['acl'] or []}
                assert new_acl==old_acl|grants.get(signature,set()),('P09_UNDECLARED_ACL_DELTA',signature,new_acl-old_acl,old_acl-new_acl)
            report['declared_execute_grants']={s:sorted(rows) for s,rows in grants.items()}
            report['replaced_functions']={s:dict(before_sha256=hashlib.sha256(originals[s].encode()).hexdigest(),after_sha256=hashlib.sha256(cur.execute('select pg_get_functiondef(%s::regprocedure)',(s,)).fetchone()[0].encode()).hexdigest()) for s in bundle.REPLACED}
            conn.commit();installed=True;verify(cur);conn.rollback()
        report['advisors_with_cp7']=advisors(package.boundary.PG)
        report['smoke']=native.strict_group('CP7_P09_SMOKE',cases.smoke,verify)
        assert report['smoke']['status']=='PASS','P09_SMOKE_INCOMPLETE'
        report['native']=native.strict_group('CP7_P09_NATIVE',cases.cases,verify)
        report['races']=modes.run_races(cases,verify,'cp7_p09')
        report['http']=modes.run_http(cases,verify,'cp7_p09')
        report['material_smoke']=native.strict_group('CP7_P09_MATERIAL_SMOKE',material.smoke,verify)
        assert report['material_smoke']['status']=='PASS','P09_MATERIAL_SMOKE_INCOMPLETE'
        report['material']=native.strict_group('CP7_P09_MATERIAL',material.cases,verify)
        report['material_crossflow']=native.strict_group('CP7_P09_MATERIAL_CROSSFLOW',material.crossflow_cases,verify)
        report['material_races']=modes.run_races(material,verify,'cp7_p09_material')
        report['material_http']=modes.run_http(material,verify,'cp7_p09_material')
        report['material_count']=native.strict_group('CP7_P09_MATERIAL_COUNT',counts.cases,verify)
        report['material_count_races']=modes.run_races(counts,verify,'cp7_p09_material_count')
        report['material_count_http']=modes.run_http(counts,verify,'cp7_p09_material_count')
        report['invoice']=native.strict_group('CP7_P09_INVOICE',invoice.cases,verify)
        report['invoice_races']=modes.run_races(invoice,verify,'cp7_p09_invoice')
        report['invoice_http']=modes.run_http(invoice,verify,'cp7_p09_invoice')
        report['browser']=modes.run_browser(bundle.ROOT/'scripts/cp7_p09_browser.mjs',verify,'cp7_p09')
        report['return_smoke']=native.strict_group('CP7_P09_RETURN_SMOKE',returns.smoke,verify)
        assert report['return_smoke']['status']=='PASS','P09_RETURN_SMOKE_INCOMPLETE'
        report['returns']=native.strict_group('CP7_P09_RETURN',returns.cases,verify)
        report['return_races']=modes.run_races(returns,verify,'cp7_p09_return')
        report['return_http']=modes.run_http(returns,verify,'cp7_p09_return')
        report['receipt_reversal']=native.strict_group('CP7_P09_RECEIPT_REVERSE',reversal.cases,verify)
        report['receipt_reversal_races']=modes.run_races(reversal,verify,'cp7_p09_receipt_reverse')
        report['receipt_reversal_http']=modes.run_http(reversal,verify,'cp7_p09_receipt_reverse')
        report['uom']=native.strict_group('CP7_P09_UOM',uom.cases,verify)
        report['uom_races']=modes.run_races(uom,verify,'cp7_p09_uom')
        report['uom_http']=modes.run_http(uom,verify,'cp7_p09_uom')
    except Exception as e:report.update(error=str(e),traceback=traceback.format_exc())
    finally:
        if installed:
            with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
                for definition in originals.values():cur.execute(definition,prepare=False)
                cur.execute('drop owned by cp7_return_write cascade;drop role cp7_return_write;drop owned by cp7_return_read cascade;drop role cp7_return_read;drop owned by cp7_invoice_write cascade;drop role cp7_invoice_write;drop owned by cp7_invoice_read cascade;drop role cp7_invoice_read;drop owned by cp7_material_write cascade;drop role cp7_material_write;drop owned by cp7_material_read cascade;drop role cp7_material_read;drop owned by cp7_procure_write cascade;drop role cp7_procure_write;drop owned by cp7_procure_read cascade;drop role cp7_procure_read;drop owned by cp7_policy cascade;drop role cp7_policy;drop owned by cp7_capture cascade;drop role cp7_capture',prepare=False);conn.commit()
                report['cp6_restored']=package.boundary.snapshot(cur)==before and native.public_state(cur)==public_before
                conn.rollback();wip.policy.bf.verified(cur);conn.rollback()
            report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report.get('advisors_with_cp7',{}))
            d=report['advisor_delta'];report['advisor_gate']=d['status']=='NO_NEW_FINDINGS' or (d['status']=='REVIEW_REQUIRED' and all(
             f.get('name')=='rls_enabled_no_policy' and f.get('level')=='INFO' and (f.get('metadata') or {}).get('schema') in ('cp7_private','cp7_identity','cp7_wip','cp7_procurement','cp7_material','cp7_supplier_return') for f in d.get('added',[])))
        groups=[report.get(k,{}) for k in ('smoke','native','races','http','browser','material_smoke','material','material_races','material_http','material_crossflow','material_count','material_count_races','material_count_http','invoice','invoice_races','invoice_http','return_smoke','returns','return_races','return_http','receipt_reversal','receipt_reversal_races','receipt_reversal_http','uom','uom_races','uom_http')]
        report['status']='PASS' if not report.get('error') and report.get('cp6_restored') and report.get('advisor_gate') and all(r.get('status') in ('PASS','RUN_COMPLETE') and set(r.get('counts',{}))=={'PASS'} and r['counts']['PASS']>0 and r.get('database_remaining',0)==0 for r in groups) else 'INCOMPLETE'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({k:report.get(k) for k in ('label','status','source_sha256','cp6_restored','advisor_gate','error','traceback')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,independent_acceptance=False)

if __name__=='__main__':
    package._writer_runtime=lambda browser_mode=False:run()
    package.run('install')
