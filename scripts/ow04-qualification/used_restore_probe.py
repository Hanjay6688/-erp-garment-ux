"""Whole used OW04 backup/restore on the existing disposable aligned clone.

The exact already-qualified product is installed unchanged. Actual CREDIT and
REFUND operations are committed, dumped and restored to a fresh database. A
restored reader must agree, and a restored owning source inverse plus replay
must work. Source OID seals are not disabled/replaced to obtain a PASS.
Only this private disposable cluster and its two fixed test DB names are used.
"""
from pathlib import Path
import hashlib,json,subprocess,traceback,uuid
import psycopg
from psycopg import sql
import transport_probe as transport
import full_backend
import cp7_p21_full_rehearsal_probe as old_drill
import cp6_t3_backup_restore_drill as drill

core=transport.core
signed=core.signed_source
nf=signed.native
product=full_backend.product
package=transport.package
SOURCE='cp6_rollback'
RESTORED='ow04_used_restore'
PRE_DUMP='/tmp/ow04_used_restore_pre.dump'
USED_DUMP='/tmp/ow04_used_restore_used.dump'
OUT=product.ROOT/'cp6-proof/t3/CP7_OW04_USED_RESTORE.json'
DECLARATION_BYTES=(product.ROOT/'docs/cp7/d17-14/ow04/USED_RESTORE_QUALIFICATION.json').read_bytes()
DECLARATION=json.loads(DECLARATION_BYTES)
assert DECLARATION['expected_scenario_count']==1 and DECLARATION['required_native_case_count']==87


def _database_profile(db):
    with psycopg.connect(drill.url(db))as conn,conn.cursor()as cur:
        owner,encoding,collate,ctype,limit=cur.execute('select pg_get_userbyid(datdba),pg_encoding_to_char(encoding),'
            'datcollate,datctype,datconnlimit from pg_database where datname=current_database()').fetchone()
        grants=cur.execute("select case when x.grantee=0 then'PUBLIC'else pg_get_userbyid(x.grantee)end,"
            'x.privilege_type,x.is_grantable,pg_get_userbyid(x.grantor)from pg_database d '
            "cross join lateral aclexplode(coalesce(d.datacl,acldefault('d',d.datdba)))x "
            'where d.datname=current_database()order by 1,2,3,4').fetchall()
        settings=cur.execute("select case when s.setrole=0 then null else pg_get_userbyid(s.setrole)end,s.setconfig "
            'from pg_db_role_setting s join pg_database d on d.oid=s.setdatabase '
            'where d.datname=current_database()order by 1 nulls first').fetchall()
        assert owner=='postgres'and all(row[3]==owner for row in grants),'USED_RESTORE_SOURCE_DATABASE_AUTHORITY_CHANGED'
        return dict(owner=owner,encoding=encoding,collate=collate,ctype=ctype,limit=limit,grants=grants,settings=settings)


def _restore(path,db,profile):
    assert db in(SOURCE,RESTORED)and profile['owner']=='postgres'
    drill.docker('dropdb','-U','supabase_admin','--if-exists','--force',db,check=False)
    drill.docker('createdb','-U','supabase_admin','--maintenance-db=template1','-T','template0',
        '--owner=postgres','--encoding='+profile['encoding'],'--lc-collate='+profile['collate'],
        '--lc-ctype='+profile['ctype'],db)
    result=drill.docker('pg_restore','-U','supabase_admin','-d',db,'--no-password',path,check=False)
    errors=[line for line in result.stderr.splitlines()if line.startswith('pg_restore: error:')]
    unexplained=[line for line in errors if not drill.CRON_ERROR.match(line)]
    with psycopg.connect(drill.url(db))as conn,conn.cursor()as cur:
        actual=_database_profile(db)
        for grantee in sorted({'PUBLIC'}|{v[0]for v in actual['grants']}):
            principal=sql.SQL('public')if grantee=='PUBLIC'else sql.Identifier(grantee)
            cur.execute(sql.SQL('revoke all privileges on database {} from {}').format(sql.Identifier(db),principal))
        for grantee,privilege,grantable,grantor in profile['grants']:
            assert privilege in('CONNECT','CREATE','TEMPORARY')and grantor=='postgres'
            principal=sql.SQL('public')if grantee=='PUBLIC'else sql.Identifier(grantee)
            cur.execute(sql.SQL('grant {} on database {} to {}{}').format(sql.SQL(privilege),sql.Identifier(db),principal,
                sql.SQL(' with grant option'if grantable else'')))
        cur.execute(sql.SQL('alter database {} connection limit {}').format(sql.Identifier(db),sql.Literal(profile['limit'])))
        for role,settings in profile['settings']:
            for setting in settings:
                key,separator,value=setting.partition('=');assert separator
                if role is None:
                    command=sql.SQL('alter database {} set {} to {}').format(sql.Identifier(db),sql.Identifier(key),sql.Literal(value))
                else:
                    command=sql.SQL('alter role {} in database {} set {} to {}').format(sql.Identifier(role),sql.Identifier(db),sql.Identifier(key),sql.Literal(value))
                cur.execute(command)
        conn.commit()
    assert _database_profile(db)==profile,'USED_RESTORE_DATABASE_OWNER_ACL_OR_SETTINGS_CHANGED'
    return dict(exit=result.returncode,error_count=len(errors),unexplained=unexplained[:40],
        only_pg_cron_errors=not unexplained,database_owner_acl_and_settings_preserved=True)


def _roles(cur):
    return {r[0] for r in cur.execute("select rolname from pg_roles where rolname like 'cp7_%'").fetchall()}


def _read(cur,x,credit,result):
    cohort=cur.execute('select id from cp7_credit.cohorts where id=%s',(result['credit_id'],)).fetchone()[0]
    detail=nf.source.read(cur,x['f'])['detail']
    return dict(invoice={key:detail[key]for key in('id','status','row_version','review_token','returned_qty')},
        financial=nf.source.numbers(detail),credit=signed._profile(cur,x,credit,str(cohort)))


def _foundation(cur):
    granted=not cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
    if granted:cur.execute('grant usage on schema erp to authenticated')
    seeded=not cur.execute('select count(*)from erp.app_users').fetchone()[0]
    if seeded:core.native.api.seed(cur)
    cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='240s';set local lock_timeout='8s'")
    return granted,seeded


def run():
    reused=transport.qualified_core()
    assert reused['native_case_count']==87,'USED_RESTORE_REQUIRES_ACTUAL_NATIVE87'
    report=dict(label='CP7_OW04_USED_RESTORE',status='INCOMPLETE',candidate_commit=transport.git('rev-parse','HEAD'),
        reused_native_binding=reused,scope='COMMITTED_CREDIT_AND_REFUND_DUMP_FRESH_RESTORE_READ_WRITE_REPLAY',
        qualification_only=True,hosted=False,native_rerun=False,production_go=False,
        audit_complete=False,feature_complete=False,steps=[],
        predeclared_scenario_sha256=hashlib.sha256(DECLARATION_BYTES).hexdigest(),scenario_id=DECLARATION['scenario_id'])
    before=None;before_roles=set();new_roles=set();installed=False;pre_dumped=False
    try:
        assert drill.SOURCE==SOURCE and drill.CONTAINER=='supabase_db_cp5-local'
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            assert cur.execute('select current_database()').fetchone()==(SOURCE,)
            assert conn.info.host in('127.0.0.1','localhost'), 'USED_RESTORE_DISPOSABLE_LOOPBACK_REQUIRED'
            core.p09.wip.policy.bf.verified(cur)
            before_roles=_roles(cur)
            before=core.restore_state.capture(cur,package.boundary.snapshot,core.predecessor.public_state,core.p09.functions)
            conn.rollback()
        pre_data=drill.data_hashes(SOURCE)
        pre_profile=_database_profile(SOURCE)
        old_drill.dump(SOURCE,PRE_DUMP);pre_dumped=True
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            state=full_backend.install(cur,report);installed=True
            new_roles=_roles(cur)-before_roles
            assert new_roles<=set(product.top.ROLES)|set(product.credit.NEW_ROLES),'USED_RESTORE_UNDECLARED_CLUSTER_ROLE'
            conn.commit()
            granted,seeded=_foundation(cur)
            today=cur.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
            fixtures=[]
            for mode in('CREDIT','REFUND'):
                x,credit,result,actual=signed._setup(cur,today,mode)
                nf.b.api.admin(cur)
                fixtures.append((x,credit,result,actual,_read(cur,x,credit,result)))
                nf.b.api.admin(cur)
            cur.execute('set constraints all immediate')
            if granted:cur.execute('revoke usage on schema erp from authenticated')
            conn.commit()
            assert product.private_rows(cur)!=state['seeded_private_rows']
            held=product.private_rows(cur)
            try:product.rollback_preuse(cur,state)
            except ValueError as error:
                assert str(error)=='CP7_FULL_ROLLBACK_AFTER_USE_REQUIRES_BACKUP_RESTORE'
            else:raise AssertionError('USED_RESTORE_UNSAFE_PREUSE_ROLLBACK_ACCEPTED')
            assert product.private_rows(cur)==held
            conn.rollback()
            report['steps'].append(dict(step='COMMITTED_CREDIT_AND_REFUND',status='PASS',
                outcomes=[v[2]for v in fixtures],rollback_after_use_refused=True,
                administrative_harness_users_seeded=seeded,test_usage_grant_revoked=granted))
        used_data=drill.data_hashes(SOURCE)
        used_profile=_database_profile(SOURCE)
        old_drill.dump(SOURCE,USED_DUMP)
        restored=_restore(USED_DUMP,RESTORED,used_profile)
        assert restored['only_pg_cron_errors'],('USED_RESTORE_DUMP_ERRORS',restored)
        restored_data=drill.data_hashes(RESTORED)
        assert used_data==restored_data,'USED_RESTORE_DATA_CHANGED'
        report['steps'].append(dict(step='DUMP_AND_FRESH_RESTORE',status='PASS',restore=restored,
            all_schema_table_hashes_equal=True,table_count=len(used_data)))
        with psycopg.connect(drill.url(RESTORED))as conn,conn.cursor()as cur:
            assert cur.execute('select current_database()').fetchone()==(RESTORED,)
            granted,_=_foundation(cur)
            for x,credit,result,actual,wanted in fixtures:
                nf.b.api.admin(cur)
                assert _read(cur,x,credit,result)==wanted,'USED_RESTORE_AUTHORITATIVE_READ_CHANGED'
            report['steps'].append(dict(step='RESTORED_CREDIT_AND_REFUND_READS',status='PASS'))
            x,credit,result,actual,_=fixtures[0]
            action='RETURN_REVERSE'
            payload,version=signed._intent(cur,x,result,action)
            request=uuid.uuid4()
            nf.b.api.admin(cur)
            before_write=signed._preserved(cur,x,actual)
            began=signed._business_day(cur)
            answer=signed.cmd.command(cur,action,payload,version,request)
            signed._assert_same_business_day(cur,began)
            gold=next(v for v in signed.expected()['cases']if v.get('action')==action)
            proof=signed._assert_positive(cur,x,credit,result,actual,gold,request,answer,before_write)
            observed=signed._observe(cur,x)
            assert signed.cmd.command(cur,action,payload,version,request)==answer
            assert signed._observe(cur,x)==observed,'USED_RESTORE_REPLAY_CREATED_SECOND_EFFECT'
            nf.b.api.admin(cur)
            cur.execute('set constraints all immediate')
            if granted:cur.execute('revoke usage on schema erp from authenticated')
            conn.commit()
            report['steps'].append(dict(step='RESTORED_OWNING_WRITE_AND_REPLAY',status='PASS',
                outcome=answer,proof=proof,one_effect=True,deferred_constraints_forced=True))
        report['runtime_status']='PASS'
    except Exception as error:
        report.update(error=str(error),traceback=traceback.format_exc())
    finally:
        # A used installation is never uninstalled or silently row-deleted.
        # Dispose its restored copy, then restore the actual original clone
        # from its full pre-install backup, including all committed facts.
        drill.docker('dropdb','-U','supabase_admin','--if-exists','--force',RESTORED,check=False)
        if installed and pre_dumped:
            try:
                baseline_restore=_restore(PRE_DUMP,SOURCE,pre_profile)
                assert baseline_restore['only_pg_cron_errors'],('USED_RESTORE_BASELINE_ERRORS',baseline_restore)
                assert drill.data_hashes(SOURCE)==pre_data,'USED_RESTORE_PREINSTALL_DATA_CHANGED'
                with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
                    for role in sorted(new_roles):
                        cur.execute(sql.SQL('drop role {}').format(sql.Identifier(role)))
                    conn.commit()
                    assert _roles(cur)==before_roles,'USED_RESTORE_CLUSTER_ROLE_RESIDUE'
                    report['cp6_restored']=core.restore_state.prove(cur,before,package.boundary.snapshot,
                        core.predecessor.public_state,core.p09.functions,report)
                    conn.rollback()
                    core.p09.wip.policy.bf.verified(cur)
                    conn.rollback()
                report['baseline_restore']=baseline_restore
            except Exception as error:
                report.update(cp6_restored=False,restore_error=str(error),restore_traceback=traceback.format_exc())
        for path in(PRE_DUMP,USED_DUMP):drill.docker('rm','-f',path,check=False)
        exact_steps=[row['step']for row in report['steps']]==DECLARATION['required_steps']and all(row['status']=='PASS'for row in report['steps'])
        if report.get('runtime_status')=='PASS'and exact_steps and report.get('cp6_restored')is True and not report.get('error'):
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({k:report.get(k)for k in('label','status','runtime_status','cp6_restored','error','restore_error')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,feature_complete=False)


if __name__=='__main__':
    package._writer_runtime=lambda browser_mode=False:run()
    package.run('install')
