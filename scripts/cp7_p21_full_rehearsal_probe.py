"""P21 rehearsal of the FULL composition on the disposable aligned clone (never hosted).

The F03 rehearsal (cp7_p21_rehearsal_probe.py) installs the combined F03 stack only and holds its USE open, then
rolls it back. This rehearsal installs the complete composition the Native analysis/reminder suites install
(F03 + planning + baseline + supply + schedule + netting + analysis with the staged 5,000-target path + reminders,
rule source, obligations and the report appendix), commits a real use, and proves the two restore paths of a
used installation:

 0. PRE-INSTALL BACKUP: pg_dump -Fc of the clone inside the disposable container, with its catalog
    fingerprint, per-object texts and per-table row hashes.
 1. INSTALL: every declared predecessor-definition and ACL assertion; every family verifier.
 2. PRE-USE ROLLBACK: CP7 private tables hold only install-seeded rows, so the declared rollback runs and the
    complete pre-install state is proved equal.
 3. REINSTALL: the installed catalog equals the first install exactly.
 4. USE, COMMITTED: a supplier payment through its owning command, then a staged analysis job requested,
    stepped to DONE and every page read through the actor's public readers.
 5. POST-USE ROLLBACK GUARD: refuses, because the CP7 rows of committed business writes would be dropped.
 6. BACKUP OF THE USED INSTALLATION: dump, restore into a fresh database; catalog fingerprint, every table's rows
    and the CP7 catalog equal; the staged result re-read on the restored database through the actor's public
    readers equals the source (identity_hash, every page, the reassembled Original).
 7. ROLLBACK OF A USED INSTALLATION = RESTORE OF THE PRE-INSTALL BACKUP into a fresh database, proved equal to the
    pre-install fingerprints. Business writes after the install are lost by construction; they are listed.
 8. HARNESS RESTORE of the disposable clone (restore databases dropped first; the clone is dropped by the harness).

Rehearsal evidence only: not the P21 release receipt (that needs a P20-accepted candidate, installed T2 parity and
the owner's release decision). Nothing here touches a hosted database.
"""
import hashlib,json,traceback,uuid
from datetime import date
import psycopg
import cp7_restore_state as restore_state
import cp7_f05_analysis_probe as f05
import cp7_obligation_report_bundle as top
import cp7_p21_rehearsal_probe as p21
import cp7_p19_native_load_cases as load
import cp7_p19_staged_cases as staged
import cp7_supplier_payment_create_cases as create
import cp6_t3_backup_restore_drill as drill
import cp6_auditor_runner as native
import cp6_t3_package_run as package
from cp6_t3_aligned_install import advisors,advisor_delta
p09=f05.p09
OUT=f05.bundle.ROOT/'cp6-proof/t3/CP7_P21_FULL_REHEARSAL.json'
PRE_DUMP='/tmp/cp7_p21_full_preinstall.dump'
USED_DUMP='/tmp/cp7_p21_full_used.dump'
PRE_RESTORE='cp7_p21_preinstall_restore'
USED_RESTORE='cp7_p21_used_restore'
KNOWN=('VARCHAR_IN_LIST_REPARSE','PG_CRON_ONLY_IN_DATABASE_POSTGRES')


def install(cur):
    """The exact full-composition install of the Native analysis/reminder suites, with every declared assertion."""
    f03=f05.f03
    originals,installation=p09.install(cur);pre=p09.functions(cur)
    internal_before=cur.execute("select pg_get_functiondef('erp.require_internal()'::regprocedure)").fetchone()[0]
    originals['erp.require_owner_admin()']=cur.execute("select pg_get_functiondef('erp.require_owner_admin()'::regprocedure)").fetchone()[0]
    f03.note_report.capture(cur,originals)
    cur.execute(f03.extension()+'\n'+f05.planning.extension()+'\n'+f05.baseline.extension()+'\n'+f05.supply.extension()+'\n'
                +f05.schedule.extension()+'\n'+f05.bundle.predecessor.extension()+'\n'+f05.bundle.extension()+'\n'+top.extension(),prepare=False)
    after=p09.functions(cur)
    path=cur.execute('show search_path').fetchone()[0];cur.execute("select set_config('search_path','',true)");grants={}
    for principal,signatures in top.GRANTS.items():
        for signature in signatures:
            key=str(cur.execute('select %s::regprocedure::text',(signature,)).fetchone()[0]);grants.setdefault(key,set()).add((principal,'EXECUTE',False))
    cur.execute("select set_config('search_path',%s,true)",(path,))
    expected=f03.note_report.expected_definitions(internal_before,originals,f03.patched_internal,f03.settlement.patched_owner)
    for sig,old in pre.items():
        new=after[sig];want=hashlib.md5(expected[sig].encode()).hexdigest() if sig in expected else old['definition']
        assert new['definition']==want and new['owner']==old['owner'],('P21F_UNDECLARED_PREDECESSOR_CHANGE',sig)
        assert {tuple(x)for x in new['acl']or[]}=={tuple(x)for x in old['acl']or[]}|grants.get(sig,set()),('P21F_UNDECLARED_ACL_DELTA',sig)
    for signature,definition in expected.items():
        assert cur.execute('select pg_get_functiondef(%s::regprocedure)',(signature,)).fetchone()[0]==definition,('P21F_EXACT_ADMISSION_DELTA',signature)
    p09.INSTALLED_FUNCTIONS=after
    return originals,installation


def uninstall(cur,originals):
    for definition in originals.values():cur.execute(definition,prepare=False)
    for role in top.ROLES:cur.execute('drop owned by '+role+' cascade;drop role '+role,prepare=False)


def verify(cur):
    f05.verify(cur);top.verify(cur)
    staged_tables=cur.execute("select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='cp7_analysis_stage' and c.relkind in('r','p')").fetchone()[0]
    assert staged_tables>0,'P21F_STAGED_SCHEMA_NOT_INSTALLED'
    return dict(stage='P21_FULL_COMPOSITION',staged_tables=staged_tables)


def guarded_rollback(cur,originals,installed_rows):
    rows=p21.used(cur);extra={k:v-installed_rows.get(k,0)for k,v in rows.items()if v!=installed_rows.get(k,0)}
    if extra:return dict(status='REFUSED',reason='CP7_ROLLBACK_AFTER_USE_REQUIRES_BACKUP_RESTORE',cp7_rows_since_install=extra)
    uninstall(cur,originals);return dict(status='ROLLED_BACK',cp7_rows_since_install={})


def texts_all(db):
    return {kind:drill.texts(db,kind) for kind in drill.TEXTS}


def compare_catalog(expected_fp,expected_texts,db):
    """Fingerprint per kind; every differing object classified as a known same-meaning form or kept with both texts."""
    got=drill.catalog(db);differ=sorted(k for k in set(expected_fp)|set(got) if expected_fp.get(k)!=got.get(k));objects={}
    for kind in differ:
        if kind not in drill.TEXTS:objects[kind]=dict(detail='NOT_COMPARED_PER_OBJECT');continue
        a,b=expected_texts[kind],drill.texts(db,kind);rows=[]
        for key in sorted(set(a)|set(b)):
            if a.get(key)==b.get(key):continue
            if kind=='extension' and key=='pg_cron' and b.get(key) is None:cls='PG_CRON_ONLY_IN_DATABASE_POSTGRES'
            else:cls='VARCHAR_IN_LIST_REPARSE' if drill.same_meaning(a.get(key),b.get(key)) else 'UNCLASSIFIED'
            row=dict(object=key,cls=cls)
            if cls=='UNCLASSIFIED':row.update(expected=(a.get(key) or '')[:600],restored=(b.get(key) or '')[:600])
            rows.append(row)
        objects[kind]=dict(differing=len(rows),objects=rows)
    explained=all('objects' in v and v['differing']>0 and all(o['cls'] in KNOWN for o in v['objects']) for v in objects.values())
    return dict(differ_kinds=differ,objects=objects,identical=not differ,explained=explained)


def dump(db,path):
    d=drill.docker('pg_dump','-U','supabase_admin','-d',db,'-Fc','-f',path,check=False)
    assert d.returncode==0,('P21F_DUMP_FAILED',db,d.stderr[-2000:])
    return int(drill.docker('stat','-c','%s',path).stdout.strip() or 0)


def restore(path,db):
    drill.docker('dropdb','-U','supabase_admin','--if-exists','--force',db,check=False)
    drill.docker('createdb','-U','supabase_admin','-T','template0',db)
    r=drill.docker('pg_restore','-U','supabase_admin','-d',db,'--no-password',path,check=False)
    errors=[l for l in r.stderr.splitlines() if l.startswith('pg_restore: error:')]
    unexplained=[l for l in errors if not drill.CRON_ERROR.match(l)]
    return dict(exit=r.returncode,error_count=len(errors),unexplained=unexplained[:40],only_pg_cron_errors=not unexplained)


def cp7_catalog(db):
    with psycopg.connect(drill.url(db)) as conn,conn.cursor() as cur:
        out=p21.catalog(cur);conn.rollback();return out


def staged_reread(db,run_id):
    """The actor's own public readers on the given database: page set, every page, reassembled Original."""
    with psycopg.connect(drill.url(db)) as conn,conn.cursor() as cur:
        original,ps,shape=staged.fetch(cur,run_id);conn.rollback()
    return dict(identity_hash=ps['identity_hash'],pages=[(p['index'],p['sha256'])for p in ps['pages']],shape=shape,
                original_sha256=hashlib.sha256(json.dumps(original,sort_keys=True,default=str).encode()).hexdigest())


def run():
    report=dict(label='CP7_P21_FULL_REHEARSAL',status='INCOMPLETE',production_go=False,independent_acceptance=False,installed_P21_acceptance=False,
      hosted=False,scope='DISPOSABLE_ALIGNED_CLONE_FULL_COMPOSITION_INSTALL_PREUSE_ROLLBACK_REINSTALL_COMMITTED_USE_POSTUSE_REFUSAL_USED_BACKUP_RESTORE_PREINSTALL_RESTORE',
      source_sha256=hashlib.sha256(top.bundle().encode()).hexdigest(),steps=[])
    installed=False;originals=None;source=drill.SOURCE;before=None;pre=None
    try:
        with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
            p09.wip.policy.bf.verified(cur);before=restore_state.capture(cur,package.boundary.snapshot,f05.public_state,p09.functions);conn.rollback()
            assert cur.execute('select current_database()').fetchone()[0]==source,('P21F_UNEXPECTED_DATABASE',source)
        # 0. Pre-install backup and its fingerprints.
        pre=dict(fp=drill.catalog(source),texts=texts_all(source),data=drill.data_hashes(source),cp7=cp7_catalog(source))
        pre_bytes=dump(source,PRE_DUMP)
        report['steps'].append(dict(step='PREINSTALL_BACKUP',dump_bytes=pre_bytes,tables=len(pre['data']),rows=sum(v['rows'] for v in pre['data'].values()),
                                    cp7_tables=len(pre['cp7']['tables'])))
        with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
            # 1. Install.
            originals,installation=install(cur);conn.commit();installed=True;report['verify']=verify(cur);first=p21.catalog(cur);seeded=p21.used(cur);conn.rollback()
            report['installation']=installation
            report['steps'].append(dict(step='INSTALL_1',catalog_sha256=first['sha256'],functions=len(first['functions']),cp7_tables=len(first['tables']),
                                        cp7_roles=len(first['roles']),rows_seeded_by_install=seeded))
            report['advisors_with_cp7']=advisors(package.boundary.PG)
            # 2. Pre-use rollback.
            r=guarded_rollback(cur,originals,seeded);conn.commit();installed=r['status']!='ROLLED_BACK'
            assert r['status']=='ROLLED_BACK',('P21F_PREUSE_ROLLBACK',r)
            proof={};assert restore_state.prove(cur,before,package.boundary.snapshot,f05.public_state,p09.functions,proof),('P21F_PREUSE_RESTORE',proof);conn.rollback()
            report['steps'].append(dict(step='PREUSE_ROLLBACK',status=r['status'],restored_exactly=True,restore_components=proof['restore_components']))
            # 3. Reinstall.
            originals,_=install(cur);conn.commit();installed=True;verify(cur);second=p21.catalog(cur);reseeded=p21.used(cur);conn.rollback()
            same=first==second and reseeded==seeded
            report['steps'].append(dict(step='REINSTALL',catalog_sha256=second['sha256'],identical_to_first=same))
            if not same:
                report['reinstall_difference']={k:dict(first=first[k],second=second[k])for k in('tables','policies','roles')if first[k]!=second[k]}
                report['reinstall_function_difference']=sorted(k for k in set(first['functions'])|set(second['functions'])if first['functions'].get(k)!=second['functions'].get(k))
            assert same,'P21F_REINSTALL_NOT_IDENTICAL'
            # 4. Use, committed. The foundation preparation the Native runner performs before any case; a test-only
            # USAGE grant (absent on the hosted profile only) is revoked again inside the same transaction.
            granted=not cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
            if granted:cur.execute('grant usage on schema erp to authenticated')
            seeded_users=not cur.execute('select count(*) from erp.app_users').fetchone()[0]
            if seeded_users:native.api.seed(cur)
            cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='240s';set local lock_timeout='8s'")
            today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
            native.boundary.historical.prior.set_open_period(cur,date(2026,8,31))
            f=create.fixture(cur,today);pay=create.command(cur,create.payload(cur,f,'100.00'))
            assert pay['status']=='POSTED' and pay['remaining_after']=='900.00',pay
            if granted:staged.b.api.admin(cur);cur.execute('revoke usage on schema erp from authenticated')
            conn.commit()
            if granted:cur.execute('grant usage on schema erp to authenticated')
            cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='240s';set local lock_timeout='8s'")
            load.real_workload(cur,today)
            key,first_job,done,calls=staged.staged_done(cur,today)
            original,ps,shape=staged.fetch(cur,done['run_id'])
            if granted:staged.b.api.admin(cur);cur.execute('revoke usage on schema erp from authenticated')
            conn.commit()
            source_staged=dict(identity_hash=ps['identity_hash'],pages=[(p['index'],p['sha256'])for p in ps['pages']],shape=shape,
                               original_sha256=hashlib.sha256(json.dumps(original,sort_keys=True,default=str).encode()).hexdigest())
            report['steps'].append(dict(step='USE',transaction='COMMITTED',supplier_payment_created=pay['payment_id'],remaining_after=pay['remaining_after'],
                                        staged_request=str(key),staged_run=done['run_id'],staged_units=len(calls),staged_pages=shape['page_count'],
                                        staged_targets=shape['targets_total'],identity_hash=ps['identity_hash'],test_usage_grant_revoked=granted,
                                        harness_users_seeded=seeded_users))
            # 5. Post-use rollback guard.
            cur.execute('savepoint p21f_guard');held=p21.used(cur);post=guarded_rollback(cur,originals,reseeded);cur.execute('rollback to savepoint p21f_guard')
            since=post.get('cp7_rows_since_install',{})
            assert post['status']=='REFUSED' and since.get('cp7_supplier_payment_create.requests')==1,('P21F_POSTUSE_REFUSAL',post)
            assert since.get('cp7_analysis_stage.jobs',0)>=1 and since.get('cp7_analysis_stage.pages',0)>=1,('P21F_POSTUSE_STAGED_ROWS',since)
            assert p21.used(cur)==held,'P21F_REFUSAL_CHANGED_STATE'
            used_catalog=p21.catalog(cur)
            report['steps'].append(dict(step='POSTUSE_ROLLBACK',**post,catalog_unchanged=used_catalog==second))
            conn.rollback()
        # 6. Backup of the used installation, restored into a fresh database.
        used_fp,used_texts,used_data=drill.catalog(source),texts_all(source),drill.data_hashes(source)
        used_bytes=dump(source,USED_DUMP);rest=restore(USED_DUMP,USED_RESTORE)
        cat=compare_catalog(used_fp,used_texts,USED_RESTORE);data=drill.data_hashes(USED_RESTORE)
        data_differ={t:dict(source=used_data.get(t),restored=data.get(t)) for t in sorted(set(used_data)|set(data)) if used_data.get(t)!=data.get(t)}
        cp7_equal=cp7_catalog(USED_RESTORE)==used_catalog
        restored_staged=staged_reread(USED_RESTORE,done['run_id'])
        ok=rest['only_pg_cron_errors'] and (cat['identical'] or cat['explained']) and not data_differ and cp7_equal and restored_staged==source_staged
        report['steps'].append(dict(step='USED_BACKUP_RESTORE',status='RESTORED_SAME_MEANING' if ok else 'DIFFERENCES_RECORDED',dump_bytes=used_bytes,restore=rest,
                                    catalog=cat,data_tables=len(data),data_differ=data_differ,cp7_catalog_equal=cp7_equal,
                                    cp7_rows=sum(v['rows'] for k,v in data.items() if k.startswith('cp7_')),
                                    staged_reread_equal=restored_staged==source_staged,staged_identity_hash=restored_staged['identity_hash']))
        assert ok,'P21F_USED_BACKUP_RESTORE'
        # 7. Rollback of a used installation: the pre-install backup restored into a fresh database.
        rest=restore(PRE_DUMP,PRE_RESTORE)
        cat=compare_catalog(pre['fp'],pre['texts'],PRE_RESTORE);data=drill.data_hashes(PRE_RESTORE)
        data_differ={t:dict(expected=pre['data'].get(t),restored=data.get(t)) for t in sorted(set(pre['data'])|set(data)) if pre['data'].get(t)!=data.get(t)}
        restored_cp7=cp7_catalog(PRE_RESTORE)
        # CP7 roles are cluster objects (still present while the clone holds the installation); everything else must match.
        no_cp7=restored_cp7['tables']==pre['cp7']['tables'] and restored_cp7['policies']==pre['cp7']['policies'] and restored_cp7['functions']==pre['cp7']['functions']
        lost=sorted(t for t in set(used_data)|set(data) if used_data.get(t)!=data.get(t))
        ok=rest['only_pg_cron_errors'] and (cat['identical'] or cat['explained']) and not data_differ and no_cp7
        report['steps'].append(dict(step='ROLLBACK_BY_PREINSTALL_RESTORE',status='RESTORED_PRE_INSTALL_STATE' if ok else 'DIFFERENCES_RECORDED',restore=rest,
                                    catalog=cat,data_differ=data_differ,cp7_objects_absent=no_cp7,cluster_roles_still_present=len(restored_cp7['roles']),
                                    business_tables_lost_by_restore=lost,note='writes after the install are lost by construction; a used installation is restored from a backup, never rolled back silently'))
        assert ok,'P21F_PREINSTALL_RESTORE'
    except Exception as e:report.update(error=str(e),traceback=traceback.format_exc())
    finally:
        for db in (USED_RESTORE,PRE_RESTORE):drill.docker('dropdb','-U','supabase_admin','--if-exists','--force',db,check=False)
        for path in (PRE_DUMP,USED_DUMP):drill.docker('rm','-f',path,check=False)
        if installed and originals is not None:
            with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
                uninstall(cur,originals);conn.commit()
                report['cp6_restored']=restore_state.prove(cur,before,package.boundary.snapshot,f05.public_state,p09.functions,report);conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
            if pre:
                after=drill.data_hashes(source)
                changed=sorted(t for t in set(pre['data'])|set(after) if pre['data'].get(t)!=after.get(t))
            else:changed=None
            report['steps'].append(dict(step='HARNESS_RESTORE_AFTER_USE',catalog_restored=report['cp6_restored'],native_tables_changed_by_committed_use=changed,
                                        note='the clone keeps the committed Native rows of step 4 and is dropped by the harness; a used installation is restored from backup'))
        if 'advisors_with_cp7' in report:
            report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report['advisors_with_cp7']);d=report['advisor_delta']
            report['advisor_gate']=d['status']=='NO_NEW_FINDINGS' or(d['status']=='REVIEW_REQUIRED' and all(x.get('name')=='rls_enabled_no_policy' and x.get('level')=='INFO' and(x.get('metadata')or{}).get('schema','').startswith('cp7_')for x in d.get('added',[])))
        names=[s['step']for s in report['steps']]
        report['status']='PASS' if not report.get('error') and report.get('cp6_restored') and report.get('advisor_gate') and names==[
            'PREINSTALL_BACKUP','INSTALL_1','PREUSE_ROLLBACK','REINSTALL','USE','POSTUSE_ROLLBACK','USED_BACKUP_RESTORE','ROLLBACK_BY_PREINSTALL_RESTORE','HARNESS_RESTORE_AFTER_USE'] else 'INCOMPLETE'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({k:report.get(k)for k in('label','status','source_sha256','steps','cp6_restored','advisor_gate','error','traceback')},default=str)[:60000],flush=True)
    return dict(status=report['status'],production_go=False,independent_acceptance=False,installed_P21_acceptance=False)


if __name__=='__main__':
    package._writer_runtime=lambda browser_mode=False:run();package.run('install')
