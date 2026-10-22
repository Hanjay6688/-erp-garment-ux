"""Real-Auth HTTP16 on the exact actually qualified Native22 financial source.

Original14 consumer HTTP cases and two real owning payment corrections.
No browser, race, hosted or production qualification.
"""
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import lzma
import subprocess
import sys
import traceback

sys.dont_write_bytecode=True
if sys.argv[1:]:raise SystemExit('Payment HTTP qualification accepts no arguments')
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path[:0]=[str(REPO/'scripts'),str(REPO/'scripts/cp7_customer_credit/consumer'),
    str(REPO/'scripts/ow04-payment-source-qualification'),str(REPO/'scripts/ow04-qualification'),
    str(REPO/'scripts/ow04-consumer-qualification')]
import source_probe as control
import psycopg
import cp6_auditor_modes as modes
from cp6_t3_aligned_install import advisors,advisor_delta

spec=importlib.util.spec_from_file_location('ow04_payment_source_http_cases',HERE/'http_cases.py')
business=importlib.util.module_from_spec(spec);spec.loader.exec_module(business)
product,previous,native,package,core,p09=control.product,control.previous,control.native,control.package,control.core,control.p09
IDS=business.IDS
LABEL='CP7_OW04_PAYMENT_SOURCE_HTTP16'
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'


def declared():
    source=json.loads((HERE/'SOURCE.json').read_bytes())
    assert source['base_candidate']=='e830604509210377f19c24b49c2fe22cc7476b6b'
    assert source['product_sources']==product.sources()
    for path,expected in source['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==expected,('BOUND_HTTP_SOURCE_CHANGED',path)
    changed=subprocess.check_output(['git','-C',str(REPO),'diff','--name-only',source['base_candidate'],'HEAD',
        '--','scripts','src','supabase','tests','.github/workflows/cp7-ow04-payment-http-bound.yml'],text=True).splitlines()
    assert set(changed)<=set(source['files'])|{'scripts/ow04-payment-http-bound-qualification/SOURCE.json'},changed
    assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain','--',
        'scripts/ow04-payment-http-bound-qualification','.github/workflows/cp7-ow04-payment-http-bound.yml'],text=True).strip()
    assert len(IDS)==16 and tuple(json.loads((HERE/'EXPECTED.json').read_bytes())['required_case_ids'])==IDS
    business.credit.expected()
    return source


def admitted():
    source=declared()
    binding=json.loads((HERE/'QUALIFIED_NATIVE22.json').read_bytes())
    assert binding['candidate_commit']==source['base_candidate']
    originals={}
    for label,row in binding['original_reports'].items():
        packed=(REPO/row['file']).read_bytes()
        raw=lzma.decompress(packed)if row['file'].endswith('.xz')else __import__('gzip').decompress(packed)
        assert sha256(raw).hexdigest()==row['raw_sha256']
        originals[label]=json.loads(raw)
    accepted,outer=originals['native22'],originals['package']
    assert accepted['candidate_commit']==binding['candidate_commit']
    assert accepted['status']=='PASS'and accepted['native']['counts']=={'PASS':22}
    assert accepted['expected_case_count']==accepted['observed_case_count']==22
    assert accepted['required_case_ids_pass']and accepted['cp6_restored']and accepted['advisor_gate']
    assert accepted['source_declaration']['product_sources']==product.sources(),'ACTUAL_NATIVE22_FINANCIAL_SOURCE_CHANGED'
    assert all(outer['gate'].values())and outer['primary_unchanged']and outer['auth_users_after']==0
    assert outer['writer_runtime']['status']=='PASS'
    return binding


COPY_ADMISSIONS=[]
ORIGINAL_COPY_DATABASE=modes.copy_db


def copy_database(name):
    # Qualifier setup only, on the one declared local disposable HTTP copy.
    # Reproduce the source database authority, then run the unchanged complete
    # verifier. No catalog projection, dropped group, or product grant.
    from urllib.parse import urlparse
    from psycopg import sql
    assert name=='cp6_auditor_http'
    url=ORIGINAL_COPY_DATABASE(name)
    parsed=urlparse(url)
    assert parsed.hostname in('127.0.0.1','localhost')and parsed.path=='/cp6_auditor_http'
    with psycopg.connect(url)as conn,conn.cursor()as cur:
        assert cur.execute('select current_database()').fetchone()[0]==name
        before=product.catalog._catalog_rows(cur)
        expected=control.STATE['installed_catalog']
        changes={group:sorted(key for key in set(before[group])|set(expected[group])
            if before[group].get(key)!=expected[group].get(key))
            for group in expected if before[group]!=expected[group]}
        record=dict(classification='LOCAL_HTTP_TEMPLATE_COPY_AUTHORITY_PRESERVATION',
            before_changed_catalog_members=changes,source_database_authority=expected['database_authority'],
            actual_copy_before_authority=before['database_authority'],
            full22_after_must_equal_original_install=True,product_state_modified=False,
            Native_or_schema_or_RPC_permissions_changed=False)
        COPY_ADMISSIONS.append(record)
        assert changes=={'database_authority':['CURRENT']},('UNDECLARED_HTTP_COPY_CATALOG_CHANGE',changes)
        source=expected['database_authority']['CURRENT']
        assert source[0]=='postgres'and source[8]is None
        # The actual generic createdb template copy has the admin owner and
        # default database ACL/settings; every other observed object is exact.
        acl=product.catalog._acl('null::aclitem[]','r.oid','d')
        query="select jsonb_build_array(pg_get_userbyid(r.oid),%s::text,%s::text,%s::text,-1,false,true,"+acl+",null)from pg_roles r where r.rolname='supabase_admin'"
        fresh=cur.execute(query,tuple(source[1:4])).fetchone()[0]
        assert before['database_authority']=={'CURRENT':fresh},'HTTP_COPY_IS_NOT_EXACT_FRESH_CREATEDB_AUTHORITY'
        cur.execute(sql.SQL('alter database {} owner to postgres').format(sql.Identifier(name)))
        cur.execute('set local role postgres')
        with product.catalog._catalog(cur):
            current=cur.execute(product.catalog.QUERIES['database_authority']).fetchone()[1]
        if current[7]!=source[7]:
            assert all(row[1]=='postgres'and row[2]in('CONNECT','CREATE','TEMPORARY')for row in source[7])
            for principal in sorted({row[0]for row in current[7]}):
                who=sql.SQL('PUBLIC')if principal=='PUBLIC'else sql.Identifier(principal)
                cur.execute(sql.SQL('revoke all privileges on database {} from {}').format(sql.Identifier(name),who))
            for principal,grantor,privilege,grantable in source[7]:
                who=sql.SQL('PUBLIC')if principal=='PUBLIC'else sql.Identifier(principal)
                cur.execute(sql.SQL('grant {} on database {} to {}{}').format(sql.SQL(privilege),
                    sql.Identifier(name),who,sql.SQL(' with grant option')if grantable else sql.SQL('')))
        cur.execute('reset role')
        after=product.catalog._catalog_rows(cur)
        assert after==expected,'HTTP_TEMPLATE_COPY_COMPLETE22_NOT_IDENTICAL_AFTER_AUTHORITY_PRESERVATION'
        record.update(actual_copy_after_authority=after['database_authority'],
            all22_groups_equal_original_install=True,exact_catalog_sha256=product.catalog.digest(after))
        product.verify(cur,control.STATE)
        conn.commit()
    return url


def verify(cur):return product.verify(cur,control.STATE)


def run():
    binding=admitted()
    report=dict(label=LABEL,status='INCOMPLETE',expected_case_count=16,required_case_ids=list(IDS),
        candidate_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        qualified_Native22_binding=binding,actual_financial_sources=product.sources(),
        literal_expectations=json.loads((HERE/'EXPECTED.json').read_bytes()),Native22_rerun_in_HTTP_phase=False,formal_CP7C_started=False,
        real_Auth_HTTP_qualified=False,browser_or_races_qualified=False,production_go=False,feature_complete=False,hosted=False)
    installed=False
    try:
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            p09.wip.policy.bf.verified(cur)
            before=previous.restore_state.capture(cur,package.boundary.snapshot,core.predecessor.public_state,p09.functions)
            conn.rollback()
            control.STATE=product.install(cur)
            report['complete_installed_verification']=product.verify(cur,control.STATE)
            report['verified_predecessor_info_manifest']=core.predecessor_info_manifest(cur)
            conn.commit();installed=True
        report['advisors_with_cp7']=advisors(package.boundary.PG)
        modes.copy_db=copy_database
        try:report['http']=modes.run_http(business,verify,'ow04_payment_current16')
        finally:modes.copy_db=ORIGINAL_COPY_DATABASE
        report['copy_catalog_admissions']=COPY_ADMISSIONS
    except Exception as error:report.update(error=str(error),traceback=traceback.format_exc(),copy_catalog_admissions=COPY_ADMISSIONS)
    finally:
        if installed:
            try:
                with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
                    report['complete_preuse_removal']=product.rollback_preuse(cur,control.STATE)
                    conn.commit()
                    report['cp6_restored']=previous.restore_state.prove(cur,before,package.boundary.snapshot,
                        core.predecessor.public_state,p09.functions,report)
                    conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
                report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report['advisors_with_cp7'])
                report['advisor_disposition']=core.advisor_disposition(report['advisor_delta'],report['verified_predecessor_info_manifest'])
                report['advisor_gate']=report['advisor_disposition']['gate']
            except Exception as error:
                report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),cp6_restored=False,advisor_gate=False)
        group=report.get('http',{})
        report['observed_case_count']=sum(group.get('counts',{}).values())
        report['required_case_ids_pass']=set(group.get('cases',{}))==set(IDS)
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate')and report['required_case_ids_pass'] \
         and group.get('status')in('PASS','RUN_COMPLETE')and group.get('counts')=={'PASS':16}and group.get('database_remaining',1)==0 \
         and(group.get('auth_counts')or{}).get('restored')and not group.get('cleanup_failures'):
            report['status']='PASS'
            report['real_Auth_HTTP_qualified']=True
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({key:report.get(key)for key in('label','status','expected_case_count','observed_case_count',
            'cp6_restored','advisor_gate','error','restore_error')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,feature_complete=False,independent_acceptance=False)


if __name__=='__main__':
    admitted()
    package._writer_runtime=lambda browser_mode=False:run()
    package.run('install')
