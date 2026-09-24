"""AUDITOR SCENARIO — ACCESS 3 (real non-owner roles from erp.app_roles; access_2 seeded a row with the operator role_id by mistake) (independent auditor). Fixes the auditor's harness error of close_access_1 (the writer helper
r1.peer.attempt re-enters the admin session before running the callable, so the identity switch was lost and every call ran
as supabase_admin, which require_owner_admin bypasses). Here each call switches identity INSIDE its own savepoint and captures
the SQL error itself. Oracle: M:98 (AQ: writer attempts by anon/viewer/unmapped/inactive refused, ERP tables intact), AUD-G07
(M:6356-6380); expected texts from the candidate SQL: require_owner_admin -> 'OWNER or ADMIN access required'
(migrations/20260902043000 l.144); execute revoked from anon -> SQLSTATE 42501."""
import json,traceback,uuid
import psycopg
import cp6_aw_probe as awp
api,boundary=awp.api,awp.boundary
OPERATOR=api.base.OPERATOR_AUTH

def claims(cur,payload):
    cur.execute("select set_config('request.jwt.claim.sub','',true)")
    cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps(payload),))

def become(cur,who,sub=None):
    api.admin(cur)
    if who=='anon':
        claims(cur,dict(role='anon'));cur.execute('set local session authorization anon')
    else:
        claims(cur,dict(sub=sub,role='authenticated'));cur.execute('set local session authorization authenticated')
    return cur.execute("select session_user,current_user,current_setting('request.jwt.claims',true)").fetchone()

def call_as(cur,who,sub,sql,params=()):
    api.admin(cur);cur.execute('savepoint aud_access')
    try:
        ident=become(cur,who,sub)
        row=cur.execute(sql,params).fetchone()
        out=dict(refused=False,result=str(row[0])[:160],identity=[str(x) for x in ident])
    except psycopg.Error as exc:
        out=dict(refused=True,sqlstate=exc.sqlstate,message=(exc.diag.message_primary or str(exc))[:200])
    finally:
        cur.execute('rollback to savepoint aud_access');api.admin(cur);cur.execute('release savepoint aud_access')
    return out

CALLS=[('preflight',"select public.erp_accounting_close_preflight_v1(current_date-1)",()),
       ('close',"select public.erp_close_accounting_through_v1(current_date-1,'auditor access probe')",()),
       ('laundry_estimate',"select public.erp_set_laundry_rate_owner_estimate_v1(%s,1.5,'auditor access probe')",(str(uuid.uuid4()),)),
       ('fg_preview',"select public.erp_preview_fg_unsourced_value_v1(%s,statement_timestamp())",(str(uuid.uuid4()),)),
       ('fg_post',"select public.erp_post_fg_unsourced_receipt_v1(%s::jsonb,%s)",('{}',str(uuid.uuid4()))),
       ('fg_reverse',"select public.erp_reverse_fg_unsourced_receipt_v1(%s,'auditor',%s)",(str(uuid.uuid4()),str(uuid.uuid4()))),
       ('accessory_workspace',"select public.erp_get_accessory_issue_workspace_v1('{}'::jsonb)",()),
       ('accessory_save',"select public.erp_save_accessory_issue_action_v1('SAVE_DRAFT','{}'::jsonb,%s)",(str(uuid.uuid4()),)),
       ('pocket_workspace',"select public.erp_get_pocket_fabric_workspace_v1('')",()),
       ('import_workspace',"select public.erp_get_initial_import_workspace_v1(null)",())]

def control(cur):
    api.admin(cur)
    return dict(closed_through=str(cur.execute('select closed_through from erp.accounting_period_control where singleton_id=1').fetchone()[0]),
                filings=cur.execute('select count(*) from erp.accounting_close_filings_v1').fetchone()[0],
                fg=cur.execute('select count(*) from erp.fg_unsourced_receipts_v1').fetchone()[0],
                journals=cur.execute('select count(*) from erp.journal_entries').fetchone()[0])

def seeded_user(cur,role_code,active):
    """Administrative fixture (labelled setup): a new active app user bound to the REAL erp.app_roles row `role_code`."""
    api.admin(cur)
    rid=cur.execute("select id from erp.app_roles where role_code=%s and is_active",(role_code,)).fetchone()
    assert rid,('ROLE_NOT_FOUND',role_code)
    sub=str(uuid.uuid4())
    cur.execute("insert into erp.app_users(auth_user_id,full_name,role,is_active,role_id) values(%s,%s,%s,%s,%s)",(sub,'auditor '+role_code,role_code,active,rid[0]))
    return sub

def non_owner_roles(cur):
    api.admin(cur)
    return [r[0] for r in cur.execute("select role_code from erp.app_roles where is_active and role_code not in ('OWNER','ADMIN') order by role_code").fetchall()]

def run_matrix(cur,today,who,sub,expect):
    before=control(cur);out={}
    for name,sql,params in CALLS:out[name]=call_as(cur,who,sub,sql,params)
    after=control(cur)
    def ok(v):
        if not v['refused']:return False
        m=(v.get('message') or '').lower()
        if expect=='anon':return v.get('sqlstate')=='42501'
        if expect=='owner_admin':return m.startswith('owner or admin access required')
        return v.get('sqlstate')=='42501' or 'access required' in m or 'not active' in m or 'nonaktif' in m or 'inactive' in m or 'forbidden' in m or 'permission' in m
    verdict={k:ok(v) for k,v in out.items()}
    return dict(status='PASS' if all(verdict.values()) and before==after else 'COUNTEREXAMPLE',who=who,sub=sub,calls=out,verdict=verdict,control_before=before,control_after=after,
                expected=dict(anon='SQLSTATE 42501 (execute revoked from anon)',owner_admin="'OWNER or ADMIN access required'",any_auth='an authorization refusal, never a business validation message')[expect])

def cases(cur,today):
    def wrap(fn,*a):
        def run():
            try:return fn(cur,today,*a)
            except Exception as exc:return dict(status='INCOMPLETE',error=str(exc)[:900],traceback=traceback.format_exc()[-1200:])
        return run
    def unmapped(cur,today):return run_matrix(cur,today,'auth',str(uuid.uuid4()),'owner_admin')
    def anon(cur,today):return run_matrix(cur,today,'anon',None,'anon')
    def role_case(code):
        def fn(cur,today):
            r=run_matrix(cur,today,'auth',seeded_user(cur,code,True),'any_auth');r['role_code']=code
            r['role_perms']=[x[0] for x in cur.execute("select p.permission_code from erp.role_permissions rp join erp.permissions p on p.id=rp.permission_id join erp.app_roles r on r.id=rp.role_id where r.role_code=%s order by 1",(code,)).fetchall()] if cur.execute("select to_regclass('erp.role_permissions') is not null and to_regclass('erp.permissions') is not null").fetchone()[0] else 'n/a'
            return r
        return fn
    def roles_list(cur,today):
        codes=non_owner_roles(cur)
        return dict(status='PASS' if codes else 'INCOMPLETE',roles=codes,all_roles=[list(map(str,r)) for r in cur.execute("select role_code,is_active,is_system from erp.app_roles order by 1").fetchall()],expected='informational: which non-owner roles exist in the seed')
    def operator_positive(cur,today):
        r=call_as(cur,'auth',OPERATOR,"select public.erp_accounting_close_preflight_v1(current_date-1)")
        r2=call_as(cur,'auth',OPERATOR,"select public.erp_get_accessory_issue_workspace_v1('{}'::jsonb)")
        api.admin(cur);role=cur.execute("select role,is_active from erp.app_users where auth_user_id=%s",(OPERATOR,)).fetchone()
        return dict(status='PASS' if not r['refused'] and not r2['refused'] else 'COUNTEREXAMPLE',preflight=r,workspace=r2,operator_role=[str(x) for x in role] if role else None,expected='seeded operator (owner) allowed; proves the identity switch is effective')
    out=[('ACCESS3:ROLES_IN_SEED',wrap(roles_list)),('ACCESS3:OPERATOR_POSITIVE',wrap(operator_positive))]
    try:
        api.admin(cur);codes=non_owner_roles(cur)
    except Exception:codes=[]
    for code in codes[:6]:out.append(('ACCESS3:ROLE_'+code,wrap(role_case(code))))
    return out
