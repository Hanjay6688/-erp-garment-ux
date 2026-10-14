"""Q12: first HTTP business execution after a legacy fixture ACL setup failure.

The original test failed before its first Auth request: the old pocket fixture
unconditionally revoked the authenticated schema USAGE already present in the
captured G-01 baseline. Preserve that exact ACL while creating the same fixture.
The original HTTP case, expected permission failures and outer ACL guard remain.
"""
from pathlib import Path
import json, os, sys, traceback, types
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import full_stack
import cp6_auditor_modes as modes
import cp6_be_revision_modes as original
import cp6_pocket_period_trial as pocket

def run():
    label='ASTRA_CP17_SEWING_HTTP_QUALIFICATION'
    report=dict(label=label,status='INCOMPLETE',production_go=False,groups={},qualification='Q12',
                original_run=38558702356,original_job=115834144443,original_status='INCOMPLETE_BEFORE_HTTP',
                oracle_origin='ORIGINAL_BE_REV_HTTP_UNCHANGED',fixture_values_changed=False)
    prior=pocket.production
    def same_fixture(a,cur,*args,**kwargs):
        assert os.environ.get('CP6_FIXTURE_SCHEMA_PROFILE')=='HOSTED_USAGE'
        a.admin(cur)
        before=cur.execute("select nspacl::text,has_schema_privilege('authenticated','erp','USAGE') from pg_namespace where nspname='erp'").fetchone()
        assert before[1] is True
        calls=[]
        class PreserveExistingUsage:
            def __getattr__(self,name):return getattr(cur,name)
            def execute(self,query,params=None,**kw):
                normalized=' '.join(str(query).strip().lower().rstrip(';').split())
                if normalized in ('grant usage on schema erp to authenticated','revoke usage on schema erp from authenticated'):
                    assert params is None
                    calls.append(normalized)
                    return self
                cur.execute(query,params,**kw)
                return self
        result=prior(a,PreserveExistingUsage(),*args,**kwargs)
        a.admin(cur)
        after=cur.execute("select nspacl::text,has_schema_privilege('authenticated','erp','USAGE') from pg_namespace where nspname='erp'").fetchone()
        assert before==after and calls==['grant usage on schema erp to authenticated','revoke usage on schema erp from authenticated'],(before,after,calls)
        report['fixture_acl']=dict(before=before,after=after,exactly_preserved=True,legacy_toggles_not_applied=calls)
        full_stack.save(label,report)
        return result
    def only(http,today):
        cases=[(key,fn)for key,fn in original.http_cases(http,today)if key=='BE_REV_HTTP:PUBLIC_SEWING_AND_PERIOD_ACCESS']
        assert len(cases)==1
        return cases
    try:
        with full_stack.installed(report) as verify:
            pocket.production=same_fixture
            try:report['groups']['http']=modes._run_http_once(types.SimpleNamespace(http_cases=only),verify,'sewing-http-qualified')
            finally:pocket.production=prior
    except Exception as exc:report.update(error=str(exc),traceback=traceback.format_exc())
    group=report['groups'].get('http',{})
    good=group.get('status') in ('PASS','RUN_COMPLETE') and group.get('counts')=={'PASS':1} and group.get('database_remaining')==0
    report['status']='PASS' if good and report.get('cp6_restored') and report.get('advisor_gate') else 'INCOMPLETE'
    full_stack.save(label,report)
    print(json.dumps({k:report.get(k)for k in ('label','status','error','fixture_acl')},default=str),flush=True)
    return dict(status=report['status'],production_go=False)

if __name__=='__main__':
    full_stack.package._writer_runtime=lambda browser_mode=False:run()
    full_stack.package.run('install')
