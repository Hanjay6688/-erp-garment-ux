"""Independent bounded follow-up of Fable012; catalogue != ordinary-user bypass.
No grant, function, API-schema, or actor guard is altered. Only disposable app identity
and period-control fixture state is set by admin before real authenticated attempts.
"""
import json,uuid,hashlib,re,subprocess
from datetime import timedelta
import psycopg
import cp7_snapshot_cases as auth
from cases_stage import admin,check,wrap,save

WRITER=re.compile(r'(^|_)(post|save|reverse|resolve|create|update|delete|approve|pay|close|reopen|apply|set|cancel|dispose|complete|insert|import|manage|record|correct|run|process)(_|$)')

def state(cur):
    admin(cur)
    return dict(period=cur.execute('select to_jsonb(x) from erp.accounting_period_control x where singleton_id=1').fetchone()[0],
        audit=cur.execute("select count(*),md5(coalesce(string_agg(to_jsonb(x)::text,E'\n' order by id),''))from erp.audit_logs x where entity_type='accounting_period_control'").fetchone())

def invoke(cur,subject,command,args):
    admin(cur);before=state(cur);cur.execute('savepoint astra_rbac_action');got={}
    try:
        auth.actor(cur,subject)
        session=cur.execute('select current_user,session_user,auth.uid()::text,erp.current_app_role()').fetchone()
        got['session']=session
        assert session[:2]==('authenticated','authenticated') and session[2]==subject,session
        cur.execute(command,args)
        got.update(accepted=True,after=state(cur))
    except psycopg.Error as exc:
        got.update(accepted=False,sqlstate=exc.sqlstate,message=exc.diag.message_primary)
    finally:
        cur.execute('rollback to savepoint astra_rbac_action');admin(cur);cur.execute('release savepoint astra_rbac_action')
    got['restored']=state(cur)==before
    return got

def owner(cur,active=True):
    admin(cur);subject=str(uuid.uuid4());role=cur.execute("select id from erp.app_roles where role_code='OWNER' and is_active").fetchone()[0]
    cur.execute("insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)values(%s,%s,'Astra disposable RBAC owner','OWNER',%s,%s)",(uuid.uuid4(),subject,role,active))
    return subject

def cases(cur,today):
    def catalog():
        admin(cur)
        fns=cur.execute("""select p.oid::regprocedure::text,p.proname,p.prorettype::regtype::text,
          has_function_privilege('anon',p.oid,'EXECUTE'),has_function_privilege('authenticated',p.oid,'EXECUTE'),
          p.prosecdef,p.proconfig,md5(pg_get_functiondef(p.oid))
          from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='erp' and p.prokind='f' order by 1""").fetchall()
        usage=cur.execute("select has_schema_privilege('anon','erp','USAGE'),has_schema_privilege('authenticated','erp','USAGE')").fetchone()
        tables=cur.execute("select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p') and not c.relrowsecurity order by 1").fetchall()
        public=cur.execute("select p.oid::regprocedure::text,p.prosecdef,p.proconfig,has_function_privilege('anon',p.oid,'EXECUTE') from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and left(p.proname,4)='erp_' and p.prokind='f' order by 1").fetchall()
        writer=[x for x in fns if x[4] and WRITER.search(x[1])]
        facts=dict(erp_functions=fns,schema_usage=dict(anon=usage[0],authenticated=usage[1]),without_rls=tables,public_facades=public,
          authenticated_execute=sum(x[4]for x in fns),writer_like=len(writer),writer_like_nontrigger=sum(x[2]not in('trigger','event_trigger')for x in writer),
          scope='Writer-name classifier includes integrity check functions; not a count of independently exploitable writers.')
        save('CP17_RBAC_CATALOG_FIRST',facts)
        check(not tables,'Every ERP table uses RLS on FULL',tables=tables)
        check(not usage[0] or not any(x[3] and x[2]not in('trigger','event_trigger') and WRITER.search(x[1]) for x in fns),'Anon has no reachable native writer',facts=facts)
        check(bool(public) and all(not x[3] and (not x[1] or any(v.startswith('search_path=')for v in (x[2]or[])))for x in public),'Public facades deny anon and pin definer search_path',facts=facts)
        return facts
    def roles():
        admin(cur)
        closed=today-timedelta(days=2)
        cur.execute('update erp.accounting_period_control set closed_through=%s where singleton_id=1',(closed,))
        custom,role=auth.custom_actor(cur)
        cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.payroll.approve'),(%s,'finance.payroll.pay') on conflict do nothing",(role,role))
        active=owner(cur);inactive=owner(cur,False);unknown=str(uuid.uuid4())
        start=state(cur);obs={}
        for label,subject in [('custom_finance_role',custom),('inactive_owner',inactive),('unregistered',unknown)]:
            obs[label]={}
            for action in ['reopen','close']:
                sql='select erp.'+action+'_accounting_through(%s,%s)'
                args=(closed-timedelta(days=1) if action=='reopen' else today-timedelta(days=1),'Astra bounded role control')
                out=invoke(cur,subject,sql,args);obs[label][action]=out
        positive=invoke(cur,active,'select erp.reopen_accounting_through(%s,%s)',(closed-timedelta(days=1),'Astra authorized owner control'))
        witness=dict(before=start,refusals=obs,owner_control=positive,after=state(cur),scope='Native SQL, real session authorization; no HTTP/hosted exposure claim; two functions only')
        save('CP17_RBAC_ROLE_FIRST',witness)
        check(all(not v['accepted'] and 'OWNER or ADMIN' in v.get('message','') and v['restored'] for group in obs.values() for v in group.values()),'All six non-owner/inactive attempts fail at owner guard',witness=witness)
        check(positive['accepted'] and positive['session'][3]=='OWNER' and str(positive['after']['period']['closed_through'])==str(closed-timedelta(days=1)) and positive['restored'],'Owner positive control actually changes period within rollback',witness=witness)
        check(witness['after']==start,'All attempted changes restored',witness=witness)
        return witness
    return [wrap('CP17-ASTRA-RBAC-01-CATALOG',catalog),wrap('CP17-ASTRA-RBAC-02-ROLE-BOUNDARY',roles)]
