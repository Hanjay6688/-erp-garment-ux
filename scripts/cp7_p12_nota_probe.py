"""P12 selected-card Nota and connected browser qualification; full payroll lifecycle remains open."""
from pathlib import Path
import hashlib,json,traceback,sys
from functools import partial
import psycopg
import cp7_payroll_bundle as source_bundle
import cp7_nota_bundle as bundle
import cp7_nota_cases as notes
import cp7_fg_bundle as fg_bundle
import cp7_p10_fg_probe as p10
import cp7_nota_source_cases as cases
import cp7_p09_procurement_probe as p09
import cp6_auditor_modes as modes
import cp6_auditor_runner as native
import cp6_t3_package_run as package
from cp6_t3_aligned_install import advisors,advisor_delta
OUT=bundle.ROOT/'cp6-proof/t3/CP7_P12_NOTA.json'

def verify(cur,with_review=False,with_settlement=False,with_attendance=False,with_roster=False):
    result=p10.verify(cur)
    rules={
      'access_now':('cp7_payroll_read',False,'s'),'source_lines':('cp7_payroll_read',False,'s'),'source_cards':('cp7_payroll_read',False,'s'),'source_workspace':('cp7_payroll_read',False,'s'),
      'note_access':('cp7_payroll_read',True,'s'),'note_capture':('cp7_payroll_read',True,'s'),'note_payroll':('cp7_payroll_read',True,'s'),
      'note_header':('cp7_payroll_header',True,'v'),'note_allocation':('cp7_payroll_read',True,'s'),'note_verify_allocation':('cp7_payroll_read',True,'s'),
      'note_command':('cp7_nota_write',False,'v'),'note_project_card':('cp7_payroll_read',False,'i'),'note_document':('cp7_payroll_read',False,'s'),'note_workspace':('cp7_payroll_read',False,'s')}
    if with_review:
        import cp7_settlement_read_bundle as review
        rules.update(review.RULES)
    if with_settlement:
        import cp7_settlement_bundle as settlement
        rules.update(settlement.RULES)
        for signature in ('cp7_payroll.settlement_access(text)','cp7_payroll.settlement_token(uuid)','cp7_payroll.settlement_document(uuid)'):
            assert cur.execute("select has_function_privilege('postgres',%s,'EXECUTE')",(signature,)).fetchone()[0],('P12_NATIVE_ADAPTER_EXECUTE',signature)
        for table in ('cp7_payroll.settlement_context','cp7_payroll.notes'):
            assert cur.execute("select has_table_privilege('postgres',%s,'SELECT')",(table,)).fetchone()[0],('P12_NATIVE_ADAPTER_SELECT',table)
        for who in ('anon','authenticated','service_role','cp7_capture','cp7_payroll_read','cp7_nota_write','cp7_payroll_header'):
            assert not cur.execute("select has_table_privilege(%s,'cp7_payroll.settlement_context','SELECT,INSERT,UPDATE,DELETE')",(who,)).fetchone()[0],('P12_PRIVATE_CONTEXT',who)
            assert not cur.execute("select has_function_privilege(%s,'cp7_payroll.apply_settlement(text,jsonb,text)','EXECUTE')",(who,)).fetchone()[0],('P12_PRIVATE_ADAPTER',who)
    got=cur.execute("select p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_payroll'").fetchall()
    assert {v[0] for v in got}==set(rules)
    for name,owner,secdef,vol,config in got:assert (owner,secdef,vol)==rules[name] and config==['search_path=""'],(name,owner,secdef,vol,config)
    public_rules=[('erp_cp7_get_nota_sources_v1','cp7_payroll_read','s'),('erp_cp7_get_nota_workspace_v1','cp7_payroll_read','s'),('erp_cp7_save_nota_v1','cp7_nota_write','v')]
    if with_review:public_rules.append(('erp_cp7_get_payroll_workspace_v1','cp7_payroll_read','s'))
    if with_settlement:public_rules.append(('erp_cp7_save_payroll_v1','cp7_payroll_write','v'))
    for name,owner,vol in public_rules:
        assert cur.execute("select pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proname=%s",(name,)).fetchone()==(owner,True,vol,['search_path=""'])
    if with_attendance:
        import cp7_attendance_read_bundle as attendance
        if with_roster:import cp7_roster_bundle as attendance
        funcs=cur.execute("select p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_attendance'").fetchall()
        assert {v[0] for v in funcs}==set(attendance.RULES)
        for name,owner,secdef,vol,config in funcs:assert (owner,secdef,vol)==attendance.RULES[name] and config==['search_path=""']
        assert cur.execute("select pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig from pg_proc p where p.oid='public.erp_cp7_get_attendance_workspace_v1(text,jsonb)'::regprocedure").fetchone()==('cp7_attendance_read',True,'s',['search_path=""'])
        assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p','v') and has_table_privilege('cp7_attendance_read',c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))").fetchone()[0]
        for who in ('anon','authenticated','service_role','cp7_capture'):
            assert not cur.execute("select has_schema_privilege(%s,'cp7_attendance','USAGE')",(who,)).fetchone()[0]
    if with_roster:
        assert cur.execute("select pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig from pg_proc p where p.oid='public.erp_cp7_save_roster_v1(text,jsonb,uuid,text)'::regprocedure").fetchone()==('cp7_roster_write',True,'v',['search_path=""'])
        assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p','v') and has_table_privilege('cp7_roster_write',c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))").fetchone()[0]
        for signature in ('cp7_attendance.roster_access(text)','cp7_attendance.source_token(uuid,date,date)'):
            assert cur.execute("select has_function_privilege('postgres',%s,'EXECUTE')",(signature,)).fetchone()[0],('P12_ROSTER_NATIVE_ADAPTER_EXECUTE',signature)
        for who in ('anon','authenticated','service_role','cp7_capture','cp7_attendance_read','cp7_payroll_read','cp7_payroll_write'):
            assert not cur.execute("select has_table_privilege(%s,'cp7_attendance.roster_requests','SELECT,INSERT,UPDATE,DELETE')",(who,)).fetchone()[0]
            assert not cur.execute("select has_function_privilege(%s,'cp7_attendance.apply_roster(text,jsonb,uuid,text)','EXECUTE')",(who,)).fetchone()[0]
    return dict(result,cp7_p12_bundle_sha256=hashlib.sha256((attendance.bundle() if with_attendance else settlement.bundle() if with_settlement else review.bundle() if with_review else bundle.bundle()).encode()).hexdigest())

def run(with_review=False,with_settlement=False,with_attendance=False,with_roster=False):
    with_attendance=with_attendance or with_roster
    with_settlement=with_settlement or with_attendance
    with_review=with_review or with_settlement
    verifier=partial(verify,with_review=with_review,with_settlement=with_settlement,with_attendance=with_attendance,with_roster=with_roster)
    runtime=bundle
    if with_review:
        import cp7_settlement_read_bundle as runtime
        import cp7_settlement_read_cases as review_cases
    if with_settlement:
        import cp7_settlement_bundle as runtime
        import cp7_settlement_cases as settlement_cases
    source_sql=runtime.bundle()
    if with_attendance:
        import cp7_attendance_read_bundle as attendance
        import cp7_attendance_read_cases as attendance_cases
        source_sql=attendance.bundle()
    if with_roster:
        import cp7_roster_bundle as roster
        import cp7_roster_cases as roster_cases
        source_sql=roster.bundle()
    report=dict(label='CP7_P12_NOTA_COMPOSER',status='INCOMPLETE',production_go=False,independent_acceptance=False,scope='NATIVE_SOURCE_SELECTED_CARD_COMPOSITION_ALLOCATION_AND_BROWSER_NO_PAYROLL_SETTLEMENT_UI',source_sha256=hashlib.sha256(source_sql.encode()).hexdigest())
    out=OUT
    if with_review:
        report.update(label='CP7_P12_NOTA_AND_PAYROLL_REVIEW',scope=report['scope']+'_WITH_FINANCE_PAYROLL_READ_AND_REVIEW_BROWSER',nota_bundle_sha256=hashlib.sha256(bundle.bundle().encode()).hexdigest())
        out=OUT.with_name('CP7_P12_PAYROLL_REVIEW.json')
    if with_settlement:
        report.update(label='CP7_P12_NATIVE_SETTLEMENT',scope='NOTA_FINANCE_REVIEW_AND_NATIVE_BROWSER_PREPARE_APPROVE_FULL_PAY_CANCEL_REVERSE_WITH_EXACT_LOST_REPLY_RECOVERY')
        out=OUT.with_name('CP7_P12_SETTLEMENT.json')
    if with_attendance:
        report.update(label='CP7_P12_ATTENDANCE_READ',scope=report['scope']+'_WITH_DATED_ATTENDANCE_READER_AND_BROWSER_NO_ATTENDANCE_WRITER_UI')
        out=OUT.with_name('CP7_P12_ATTENDANCE_READ.json')
    if with_roster:
        report.update(label='CP7_P12_ROSTER',scope=report['scope']+'_WITH_NATIVE_ROSTER_RATE_WRITER_AND_CONNECTED_SOURCE_BROWSER')
        out=OUT.with_name('CP7_P12_ROSTER.json')
    installed=False
    try:
        with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
            p09.wip.policy.bf.verified(cur);before=package.boundary.snapshot(cur);public_before=native.public_state(cur);conn.rollback()
            originals,installation=p09.install(cur);report.update(installation);pre=p09.functions(cur)
            internal_before=cur.execute("select pg_get_functiondef('erp.require_internal()'::regprocedure)").fetchone()[0]
            cur.execute(fg_bundle.extension(),prepare=False);cur.execute(source_bundle.extension(),prepare=False);cur.execute(bundle.extension(),prepare=False)
            if with_review:
                import cp7_settlement_read_bundle as read_bundle
                cur.execute(read_bundle.extension(),prepare=False)
            if with_settlement:
                originals['erp.require_owner_admin()']=cur.execute("select pg_get_functiondef('erp.require_owner_admin()'::regprocedure)").fetchone()[0]
                cur.execute(runtime.extension(),prepare=False)
            if with_attendance:cur.execute(attendance.extension(),prepare=False)
            if with_roster:cur.execute(roster.extension(),prepare=False)
            after=p09.functions(cur)
            grants=('auth.uid()','auth.jwt()','erp.get_my_access_v1()','erp.has_permission(text)','erp.bf_commercial_sku_at_v1(uuid,timestamptz)','erp.bd_lot_laundry_unknown_v1(uuid)','erp.get_hpp_completeness(uuid)')
            # regprocedure prints timestamp with time zone with empty search_path.
            path=cur.execute('show search_path').fetchone()[0];cur.execute("select set_config('search_path','',true)")
            grants={str(cur.execute('select %s::regprocedure::text',(s,)).fetchone()[0]):{('cp7_fg_read','EXECUTE',False)} for s in grants}
            for signature in ('auth.uid()','auth.jwt()','erp.get_my_access_v1()','erp.has_permission(text)','erp.save_fg_adjustment_draft_v2(jsonb,uuid,bigint)','erp.post_fg_adjustment_v2(uuid,uuid,bigint,text)','erp.reverse_fg_adjustment_v2(uuid,text,uuid,bigint)','erp.move_fg_stock_card_row_to_position(uuid,integer)','erp.reset_fg_stock_mutation_book_order()'):
                key=str(cur.execute('select %s::regprocedure::text',(signature,)).fetchone()[0]);grants.setdefault(key,set()).add(('cp7_fg_write','EXECUTE',False))
            for signature in ('auth.uid()','auth.jwt()','erp.get_my_access_v1()','erp.has_permission(text)'):
                key=str(cur.execute('select %s::regprocedure::text',(signature,)).fetchone()[0]);grants.setdefault(key,set()).add(('cp7_payroll_read','EXECUTE',False))
            for who in ('cp7_nota_write','cp7_payroll_header')+(('cp7_payroll_write',) if with_settlement else ())+(('cp7_attendance_read',) if with_attendance else ())+(('cp7_roster_write',) if with_roster else ()):
                for signature in ('auth.uid()','auth.jwt()','erp.get_my_access_v1()','erp.has_permission(text)'):
                    key=str(cur.execute('select %s::regprocedure::text',(signature,)).fetchone()[0]);grants.setdefault(key,set()).add((who,'EXECUTE',False))
            key=str(cur.execute("select 'erp.merge_eligible_work_into_payroll_v2(uuid,jsonb,uuid,bigint)'::regprocedure::text").fetchone()[0]);grants.setdefault(key,set()).add(('cp7_nota_write','EXECUTE',False))
            cur.execute("select set_config('search_path',%s,true)",(path,))
            for signature,old in pre.items():
                new=after[signature];expected_definition=hashlib.md5(bundle.patched_internal(internal_before).encode()).hexdigest() if signature=='erp.require_internal()' else old['definition']
                if with_settlement and signature=='erp.require_internal()':expected_definition=hashlib.md5(runtime.patched_internal(bundle.patched_internal(internal_before)).encode()).hexdigest()
                if with_settlement and signature=='erp.require_owner_admin()':expected_definition=hashlib.md5(runtime.patched_owner(originals[signature]).encode()).hexdigest()
                assert new['definition']==expected_definition and new['owner']==old['owner'],('P12_PREDECESSOR_CHANGED',signature)
                expected={tuple(x) for x in old['acl'] or []}|grants.get(signature,set())
                assert {tuple(x) for x in new['acl'] or []}==expected,('P12_UNDECLARED_ACL_DELTA',signature)
            p09.INSTALLED_FUNCTIONS=after;report['source_declared_execute_grants']={k:sorted(v) for k,v in grants.items()}
            internal_after=cur.execute("select pg_get_functiondef('erp.require_internal()'::regprocedure)").fetchone()[0]
            expected_internal=bundle.patched_internal(internal_before)
            if with_settlement:expected_internal=runtime.patched_internal(expected_internal)
            assert internal_after==expected_internal,'P12_EXACT_ADMISSION_DELTA'
            if with_settlement:
                actual_owner=cur.execute("select pg_get_functiondef('erp.require_owner_admin()'::regprocedure)").fetchone()[0]
                assert actual_owner==runtime.patched_owner(originals['erp.require_owner_admin()'])
                derived=cur.execute("select pg_get_functiondef('cp7_payroll.rebuild_nonwork(uuid)'::regprocedure)").fetchone()[0]
                assert derived==runtime.derive_nonwork(runtime.accepted('populate_payroll_draft'))
                report['settlement_deltas']=dict(owner_before_sha256=hashlib.sha256(originals['erp.require_owner_admin()'].encode()).hexdigest(),owner_after_sha256=hashlib.sha256(actual_owner.encode()).hexdigest(),nonwork_derived_sha256=hashlib.sha256(derived.encode()).hexdigest(),selected_work_removal_insertion_only_removed=True)
            report['nota_admission_delta']={k:hashlib.sha256(v.encode()).hexdigest() for k,v in [('before',internal_before),('after',internal_after)]}
            conn.commit();installed=True;verifier(cur);conn.rollback()
        report['advisors_with_cp7']=advisors(package.boundary.PG)
        report['native']=native.strict_group('CP7_P12_NOTA_SOURCE',cases.cases,verifier)
        report['http']=modes.run_http(cases,verifier,'cp7_p12_nota_source')
        report['notes']=native.strict_group('CP7_P12_NOTA',notes.cases,verifier)
        report['note_races']=modes.run_races(notes,verifier,'cp7_p12_nota')
        report['note_http']=modes.run_http(notes,verifier,'cp7_p12_nota')
        report['admission_regression']=modes.run_http(p09.cases,verifier,'cp7_p12_p09_admission')
        report['browser']=modes.run_browser(bundle.ROOT/'scripts/cp7_p12_browser.mjs',verifier,'cp7_p12_nota')
        if with_review:
            report['payroll_review']=native.strict_group('CP7_P12_PAYROLL_REVIEW',review_cases.cases,verifier)
            report['payroll_review_http']=modes.run_http(review_cases,verifier,'cp7_p12_payroll_review')
            report['payroll_review_browser']=modes.run_browser(bundle.ROOT/'scripts/cp7_p12_payroll_browser.mjs',verifier,'cp7_p12_payroll_review')
        if with_settlement:
            report['settlement']=native.strict_group('CP7_P12_SETTLEMENT',settlement_cases.cases,verifier)
            report['settlement_races']=modes.run_races(settlement_cases,verifier,'cp7_p12_settlement')
            report['settlement_http']=modes.run_http(settlement_cases,verifier,'cp7_p12_settlement')
            report['settlement_browser']=modes.run_browser(bundle.ROOT/'scripts/cp7_p12_settlement_browser.mjs',verifier,'cp7_p12_settlement')
        if with_attendance:
            report['attendance_read']=native.strict_group('CP7_P12_ATTENDANCE_READ',attendance_cases.cases,verifier)
            report['attendance_read_http']=modes.run_http(attendance_cases,verifier,'cp7_p12_attendance_read')
            report['attendance_read_browser']=modes.run_browser(bundle.ROOT/'scripts/cp7_p12_attendance_browser.mjs',verifier,'cp7_p12_attendance_read')
        if with_roster:
            report['roster']=native.strict_group('CP7_P12_ROSTER',roster_cases.cases,verifier)
            report['roster_races']=modes.run_races(roster_cases,verifier,'cp7_p12_roster')
            report['roster_http']=modes.run_http(roster_cases,verifier,'cp7_p12_roster')
            report['roster_browser']=modes.run_browser(bundle.ROOT/'scripts/cp7_p12_roster_browser.mjs',verifier,'cp7_p12_roster')
    except Exception as e:report.update(error=str(e),traceback=traceback.format_exc())
    finally:
        if installed:
            with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
                for definition in originals.values():cur.execute(definition,prepare=False)
                for role in (('cp7_roster_write',) if with_roster else ())+(('cp7_attendance_read',) if with_attendance else ())+(('cp7_payroll_write',) if with_settlement else ())+('cp7_nota_write','cp7_payroll_header','cp7_payroll_read','cp7_fg_write','cp7_fg_read','cp7_return_write','cp7_return_read','cp7_invoice_write','cp7_invoice_read','cp7_material_write','cp7_material_read','cp7_procure_write','cp7_procure_read','cp7_policy','cp7_capture'):
                    cur.execute('drop owned by '+role+' cascade;drop role '+role,prepare=False)
                conn.commit();report['cp6_restored']=package.boundary.snapshot(cur)==before and native.public_state(cur)==public_before
                conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
            report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report.get('advisors_with_cp7',{}));d=report['advisor_delta']
            report['advisor_gate']=d['status']=='NO_NEW_FINDINGS' or (d['status']=='REVIEW_REQUIRED' and all(f.get('name')=='rls_enabled_no_policy' and f.get('level')=='INFO' and (f.get('metadata') or {}).get('schema') in ('cp7_attendance','cp7_payroll','cp7_fg','cp7_private','cp7_identity','cp7_wip','cp7_procurement','cp7_material','cp7_supplier_return','cp7_invoice') for f in d.get('added',[])))
        group_keys=('native','http','notes','note_races','note_http','admission_regression','browser')+(('payroll_review','payroll_review_http','payroll_review_browser') if with_review else ())+(('settlement','settlement_races','settlement_http','settlement_browser') if with_settlement else ())+(('attendance_read','attendance_read_http','attendance_read_browser') if with_attendance else ())+(('roster','roster_races','roster_http','roster_browser') if with_roster else ())
        groups=[report.get(k,{}) for k in group_keys]
        report['status']='PASS' if not report.get('error') and report.get('cp6_restored') and report.get('advisor_gate') and all(r.get('status') in ('PASS','RUN_COMPLETE') and set(r.get('counts',{}))=={'PASS'} and r['counts']['PASS']>0 and r.get('database_remaining',0)==0 for r in groups) else 'INCOMPLETE'
        out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2,default=str)+'\n');print(json.dumps({k:report.get(k) for k in ('label','status','source_sha256','cp6_restored','advisor_gate','error','traceback')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,independent_acceptance=False)

if __name__=='__main__':
    assert sys.argv[1:] in ([],['--payroll-review'],['--settlement'],['--attendance-review'],['--roster']),'UNKNOWN_P12_PROBE_ARGUMENT'
    package._writer_runtime=lambda browser_mode=False:run(with_review='--payroll-review' in sys.argv,with_settlement='--settlement' in sys.argv,with_attendance='--attendance-review' in sys.argv,with_roster='--roster' in sys.argv)
    package.run('install')
