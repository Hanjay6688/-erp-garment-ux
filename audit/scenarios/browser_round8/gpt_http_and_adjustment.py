"""C0 adjustment transport retry and genuine Auth HTTP oracle corrections.
Business oracle reused byte-for-byte from the frozen C0 file. Native temporary
schema access is restored after the receipt helper's unconditional revoke.
HTTP uses unchanged public-only PostgREST without schema grants.
"""
from pathlib import Path
from datetime import timedelta
import importlib.util,json,uuid

spec=importlib.util.spec_from_file_location('gpt_c0_frozen',Path(__file__).parent.parent/'c0_round8/gpt_c0_oracles.py')
c0=importlib.util.module_from_spec(spec);spec.loader.exec_module(c0)
original_observe=c0.observe


def restored_native_observe(cur,days):
    c0.api.admin(cur)
    if not cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]:
        cur.execute('grant usage on schema erp to authenticated')
    return original_observe(cur,days)


def cases(cur,today):
    def adjustment():
        c0.observe=restored_native_observe
        try:
            out=c0.adjustment_case(cur,today)
            out['native_fixture_correction']='restore only the runner grant removed by cp6_initial_import_receipt_trial.rpc; HTTP and browser use separate copies without this grant'
            return out
        finally: c0.observe=original_observe
    return [('G8C0:AS:ADJUSTMENT_DATE:False:transport_rev2',adjustment)]


def http_cases(http,today):
    def refused(r):
        b=r.get('body') or {}
        return r['status'] in (401,403) or (r['status']>=400 and
            any(s in str(b.get('message','')) for s in ('OWNER or ADMIN','permission denied','PERMISSION_DENIED')))
    def brief(r):
        b=r.get('body');return dict(status=r['status'],code=b.get('code') if isinstance(b,dict) else None,
                                   message=b.get('message') if isinstance(b,dict) else None)
    def matrix():
        users={r:http.login(r,'g8valid-'+r.lower()) for r in ('OWNER','GUDANG','AUDITOR_VIEW_ONLY')}
        reads=[('preflight','erp_accounting_close_preflight_v1',dict(p_through=str(today-timedelta(days=1)))),
            ('accessory','erp_get_accessory_issue_workspace_v1',dict(p_filters={})),
            ('pocket','erp_get_pocket_fabric_workspace_v1',dict(p_query='')),
            ('import','erp_get_initial_import_workspace_v1',dict(p_batch_id=None))]
        results={};checks={}
        for label,fn,args in reads:
            anon=http.anon_rpc(fn,args);results['anon:'+label]=brief(anon);checks['anon:'+label]=refused(anon)
            for role,user in users.items():
                r=user.rpc(fn,args);results[role+':'+label]=brief(r)
                allowed=role=='OWNER' or role=='AUDITOR_VIEW_ONLY' and label=='accessory'
                checks[role+':'+label]=r['status']==200 if allowed else refused(r)
        args=dict(p_action='SAVE_DRAFT',p_payload={},p_client_request_id=str(uuid.uuid4()))
        for role in ('GUDANG','AUDITOR_VIEW_ONLY'):
            r=users[role].rpc('erp_save_accessory_issue_action_v1',args)
            results[role+':accessory_valid_action']=brief(r);checks[role+':accessory_valid_action']=refused(r)
        return dict(status='PASS' if all(checks.values()) else 'COUNTEREXAMPLE',checks=checks,results=results,
            oracle='M281,1322: valid read arguments; valid SAVE_DRAFT action denied by permissions before required-field validation; real Auth')
    def revoked():
        user=http.login('OWNER','g8revoke');args=dict(p_filters={})
        before=user.rpc('erp_get_accessory_issue_workspace_v1',args)
        with http.connect() as c,c.cursor() as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(user.auth_user_id,));c.commit()
        after=user.rpc('erp_get_accessory_issue_workspace_v1',args)
        return dict(status='PASS' if before['status']==200 and refused(after) else 'COUNTEREXAMPLE',
            before=brief(before),after=brief(after),oracle='M281/1322 live app-user revocation blocks even read with previously valid Auth session')
    def prepared_reachability():
        user=http.login('OWNER','g8prepare');names=['prepare_migration_opening_balance','apply_migration_master_rows','apply_migration_open_pos']
        with http.connect() as c,c.cursor() as cur:
            usage=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
            functions=cur.execute('''select n.nspname,p.proname,pg_get_function_identity_arguments(p.oid),
                has_function_privilege('authenticated',p.oid,'EXECUTE') from pg_proc p join pg_namespace n on n.oid=p.pronamespace
                where p.proname=any(%s) and n.nspname in ('erp','public') order by 1,2''',(names,)).fetchall()
        direct=user.rpc('prepare_migration_opening_balance',dict(p_batch_id=str(uuid.uuid4()),p_opening_number=None))
        closed=not usage and all(r[0]!='public' for r in functions) and direct['status']==404
        return dict(status='PASS' if closed else 'INCOMPLETE',schema_usage_authenticated=usage,functions=[list(r) for r in functions],
            public_rpc=brief(direct),oracle='Reachability observation only: private helper EXECUTE is not a callable browser facade when schema USAGE and public endpoint are absent',
            limits='Does not resolve legacy/private-client prepared-draft editability; cannot promote native prepared case to ordinary browser defect')
    return [('G8HTTP:VALID_FACADE_MATRIX',matrix),('G8HTTP:REVOKED_OWNER_READ',revoked),('G8HTTP:PREPARED_HELPER_REACHABILITY',prepared_reachability)]
