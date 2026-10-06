"""P21 rehearsal on the disposable aligned clone (never hosted): install -> pre-use rollback -> reinstall -> use ->
post-use rollback refused -> restore.

The installed product is the explicitly qualified combined F03 stack (the same composition E01/P18 install).
1. Install and capture the complete installed catalog: every erp/public/cp7_* function definition, owner and ACL,
   plus every cp7_* table, column, policy and role.
2. Pre-use rollback: the CP7 private tables are empty, so the declared rollback runs (original Native definitions
   back, CP7 roles and objects dropped) and the complete pre-install state is proved equal.
3. Reinstall: the second installed catalog must equal the first exactly (a deterministic package).
4. Use: one real CP7 write (a new supplier payment through the owning command) is committed.
5. Post-use: the rollback guard must refuse, because rollback would drop CP7 request/outcome records of committed
   business writes. Restoration of a used installation is a backup restore, never a silent drop.
6. The disposable clone is then restored by the harness and the catalog proved equal again; the Native rows written
   in step 4 are reported, not hidden.

Rehearsal evidence only: not the P21 release receipt (that needs the P20-accepted candidate and installed T2 parity).
"""
import hashlib,json,traceback
from datetime import date
import psycopg
from psycopg import sql
import cp7_restore_state as restore_state
import cp7_f03_bundle as bundle
import cp7_p12_nota_probe as payroll
import cp7_p13_finance_probe as finance
import cp7_p09_procurement_probe as p09
import cp7_supplier_payment_create_bundle as create_bundle
import cp7_supplier_payment_create_cases as create
import cp6_auditor_runner as native
import cp6_t3_package_run as package
from cp6_t3_aligned_install import advisors,advisor_delta
OUT=bundle.ROOT/'cp6-proof/t3/CP7_P21_REHEARSAL.json'

def install(cur):
    """Exactly the E01/P18 combined install, including every declared predecessor-definition and ACL assertion."""
    originals,installation=p09.install(cur);pre=p09.functions(cur)
    internal_before=cur.execute("select pg_get_functiondef('erp.require_internal()'::regprocedure)").fetchone()[0]
    originals['erp.require_owner_admin()']=cur.execute("select pg_get_functiondef('erp.require_owner_admin()'::regprocedure)").fetchone()[0]
    bundle.note_report.capture(cur,originals)
    cur.execute(bundle.extension(),prepare=False);after=p09.functions(cur)
    path=cur.execute('show search_path').fetchone()[0];cur.execute("select set_config('search_path','',true)");grants={}
    for principal,signatures in bundle.GRANTS.items():
        for signature in signatures:
            key=str(cur.execute('select %s::regprocedure::text',(signature,)).fetchone()[0]);grants.setdefault(key,set()).add((principal,'EXECUTE',False))
    cur.execute("select set_config('search_path',%s,true)",(path,))
    expected=bundle.note_report.expected_definitions(internal_before,originals,bundle.patched_internal,bundle.settlement.patched_owner)
    for sig,old in pre.items():
        new=after[sig];want=hashlib.md5(expected[sig].encode()).hexdigest() if sig in expected else old['definition']
        assert new['definition']==want and new['owner']==old['owner'],('P21_UNDECLARED_PREDECESSOR_CHANGE',sig)
        assert {tuple(x)for x in new['acl']or[]}=={tuple(x)for x in old['acl']or[]}|grants.get(sig,set()),('P21_UNDECLARED_ACL_DELTA',sig)
    p09.INSTALLED_FUNCTIONS=after
    return originals,installation

def uninstall(cur,originals):
    for definition in originals.values():cur.execute(definition,prepare=False)
    for role in bundle.ROLES:cur.execute('drop owned by '+role+' cascade;drop role '+role,prepare=False)

def verify(cur):
    payroll.verify(cur,True,True,True,True,True);finance.verify(cur);create_bundle.verify(cur)
    return dict(stage='P21_REHEARSAL_COMBINED_F03_STACK')

def catalog(cur):
    """Installed shape without OIDs: definitions/owners/ACLs, cp7 tables/columns/RLS/policies and CP7 roles."""
    tables=cur.execute("""select coalesce(jsonb_agg(jsonb_build_array(n.nspname,c.relname,c.relkind::text,pg_get_userbyid(c.relowner),c.relrowsecurity,
      (select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull)order by a.attnum)from pg_attribute a where a.attrelid=c.oid and a.attnum>0 and not a.attisdropped),
      (select jsonb_agg(x::text order by x::text)from unnest(c.relacl)x))order by n.nspname,c.relname),'[]')
      from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname like 'cp7\\_%' and c.relkind in('r','p','v','m','S')""").fetchone()[0]
    policies=cur.execute("select coalesce(jsonb_agg(jsonb_build_array(schemaname,tablename,policyname,cmd,roles::text,qual,with_check)order by schemaname,tablename,policyname),'[]') from pg_policies where schemaname like 'cp7\\_%'").fetchone()[0]
    roles=cur.execute("select coalesce(jsonb_agg(jsonb_build_array(rolname,rolcanlogin,rolinherit,rolbypassrls)order by rolname),'[]') from pg_roles where rolname like 'cp7\\_%'").fetchone()[0]
    functions={k:v for k,v in p09.functions(cur).items()}
    return dict(functions=functions,tables=tables,policies=policies,roles=roles,
      sha256=hashlib.sha256(json.dumps(dict(functions=functions,tables=tables,policies=policies,roles=roles),sort_keys=True,default=str).encode()).hexdigest())

def used(cur):
    """Rows held by CP7 private tables. Any row means a committed CP7 business write already depends on them."""
    out={}
    for schema,table in cur.execute("select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname like 'cp7\\_%' and c.relkind in('r','p') order by 1,2").fetchall():
        n=cur.execute(sql.SQL('select count(*) from {}').format(sql.Identifier(schema,table))).fetchone()[0]
        if n:out[schema+'.'+table]=n
    return out

def guarded_rollback(cur,originals,installed_rows):
    """Rows seeded by the installation itself are not use; anything beyond them is."""
    rows=used(cur);extra={k:v-installed_rows.get(k,0)for k,v in rows.items()if v!=installed_rows.get(k,0)}
    if extra:return dict(status='REFUSED',reason='CP7_ROLLBACK_AFTER_USE_REQUIRES_BACKUP_RESTORE',cp7_rows_since_install=extra)
    uninstall(cur,originals);return dict(status='ROLLED_BACK',cp7_rows_since_install={})

def run():
    report=dict(label='CP7_P21_REHEARSAL',status='INCOMPLETE',production_go=False,independent_acceptance=False,installed_P21_acceptance=False,hosted=False,
      scope='DISPOSABLE_ALIGNED_CLONE_INSTALL_PREUSE_ROLLBACK_REINSTALL_USE_POSTUSE_REFUSAL_RESTORE',source_sha256=hashlib.sha256(bundle.bundle().encode()).hexdigest(),steps=[])
    installed=False;originals=None
    try:
        with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
            p09.wip.policy.bf.verified(cur);before=restore_state.capture(cur,package.boundary.snapshot,native.public_state,p09.functions);conn.rollback()
            originals,installation=install(cur);conn.commit();installed=True;verify(cur);first=catalog(cur);seeded=used(cur);conn.rollback()
            report['installation']=installation;report['steps'].append(dict(step='INSTALL_1',catalog_sha256=first['sha256'],functions=len(first['functions']),cp7_tables=len(first['tables']),cp7_roles=len(first['roles']),rows_seeded_by_install=seeded))
            pre=guarded_rollback(cur,originals,seeded);conn.commit();installed=pre['status']!='ROLLED_BACK'
            assert pre['status']=='ROLLED_BACK',('P21_PREUSE_ROLLBACK',pre)
            proof={};assert restore_state.prove(cur,before,package.boundary.snapshot,native.public_state,p09.functions,proof),('P21_PREUSE_RESTORE',proof);conn.rollback()
            report['steps'].append(dict(step='PREUSE_ROLLBACK',status=pre['status'],restored_exactly=True,restore_components=proof['restore_components']))
            originals,_=install(cur);conn.commit();installed=True;verify(cur);second=catalog(cur);reseeded=used(cur);conn.rollback()
            same=first==second and reseeded==seeded
            report['steps'].append(dict(step='REINSTALL',catalog_sha256=second['sha256'],identical_to_first=same))
            if not same:
                report['reinstall_difference']={k:dict(first=first[k],second=second[k])for k in('tables','policies','roles')if first[k]!=second[k]}
                report['reinstall_function_difference']=sorted(k for k in set(first['functions'])|set(second['functions'])if first['functions'].get(k)!=second['functions'].get(k))
            assert same,'P21_REINSTALL_NOT_IDENTICAL'
            # The same foundation preparation the Native runner performs before any case. The use transaction stays
            # open: the guard reads the real CP7 rows of a real write, then everything is rolled back so the disposable
            # clone can still be proved restored. A committed use differs only in durability, not in what the guard reads.
            if not cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]:cur.execute('grant usage on schema erp to authenticated')
            if not cur.execute('select count(*) from erp.app_users').fetchone()[0]:native.api.seed(cur)
            cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='240s';set local lock_timeout='8s'")
            today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
            native.boundary.historical.prior.set_open_period(cur,date(2026,8,31))
            f=create.fixture(cur,today);r=create.command(cur,create.payload(cur,f,'100.00'))
            assert r['status']=='POSTED' and r['remaining_after']=='900.00',r
            report['steps'].append(dict(step='USE',supplier_payment_created=r['payment_id'],remaining_after=r['remaining_after'],transaction='HELD_OPEN_THEN_ROLLED_BACK'))
            cur.execute('savepoint p21_guard');held=used(cur);post=guarded_rollback(cur,originals,reseeded);cur.execute('rollback to savepoint p21_guard')
            assert post['status']=='REFUSED' and post['cp7_rows_since_install'].get('cp7_supplier_payment_create.requests')==1,('P21_POSTUSE_REFUSAL',post)
            assert used(cur)==held,'P21_REFUSAL_CHANGED_STATE'
            report['steps'].append(dict(step='POSTUSE_ROLLBACK',**post,catalog_unchanged=catalog(cur)==second))
            conn.rollback()
        report['advisors_with_cp7']=advisors(package.boundary.PG)
    except Exception as e:report.update(error=str(e),traceback=traceback.format_exc())
    finally:
        if installed and originals is not None:
            with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
                uninstall(cur,originals);conn.commit()
                report['cp6_restored']=restore_state.prove(cur,before,package.boundary.snapshot,native.public_state,p09.functions,report);conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
                report['steps'].append(dict(step='HARNESS_RESTORE_AFTER_USE',catalog_restored=report['cp6_restored'],note='Native rows written by the USE step stay in this disposable clone; a used installation is restored from backup, not rolled back'))
        if 'advisors_with_cp7' in report:
            report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report['advisors_with_cp7']);d=report['advisor_delta']
            report['advisor_gate']=d['status']=='NO_NEW_FINDINGS' or(d['status']=='REVIEW_REQUIRED' and all(x.get('name')=='rls_enabled_no_policy' and x.get('level')=='INFO' and(x.get('metadata')or{}).get('schema','').startswith('cp7_')for x in d.get('added',[])))
        names=[s['step']for s in report['steps']]
        report['status']='PASS' if not report.get('error') and report.get('cp6_restored') and report.get('advisor_gate') and names==['INSTALL_1','PREUSE_ROLLBACK','REINSTALL','USE','POSTUSE_ROLLBACK','HARNESS_RESTORE_AFTER_USE'] else 'INCOMPLETE'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({k:report.get(k)for k in('label','status','source_sha256','steps','cp6_restored','advisor_gate','error','traceback')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,independent_acceptance=False,installed_P21_acceptance=False)
if __name__=='__main__':
    package._writer_runtime=lambda browser_mode=False:run();package.run('install')
