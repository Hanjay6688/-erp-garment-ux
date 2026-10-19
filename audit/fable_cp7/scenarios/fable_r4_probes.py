"""Fable r4 probes on 663f6fae. Oracles fixed before any run.

FABLE_R4:GUARD_SAME_ANSWER_MATRIX — R4-05 claim: erp.require_internal() with its one-probe fast path answers exactly as the
  same guard without it. The guard without the probe is rebuilt by Fable from the installed body (the block from the
  '-- R4-05 one context probe' line through its own closing ' end if;' removed) and installed as a copy with the same
  SECURITY/config attributes and the same EXECUTE grants for anon, authenticated and service_role. Each answer is taken in
  its own fresh transaction on a second connection, as a Data API session (session authorization authenticator, then the
  request role and JWT claims), through an invoker wrapper that returns 'ALLOW' or sqlstate:message. Matrix: every active
  app role present in erp.app_users, an inactive user when present, an unknown user, a JWT without sub, anon, and
  service_role; context states: FRESH (no transaction id; the fast path's null branch), XID (transaction id assigned, no
  context row), SALES_ROW_HERE and PROCUREMENT_ROW_HERE (a command context row of this backend and transaction), and
  COMMITTED_ROW_EARLIER (a sales context row committed by an earlier transaction of the same backend).
  Any cell where the two answers differ -> COUNTEREXAMPLE. FAIL when the matrix is not meaningful: no internal identity
  allowed at FRESH, no refusal at FRESH, or a FRESH cell already had a transaction id before the call.

FABLE_R4:FG_REVERSAL_PATHS — R4-02 excludes from "use" a negative movement that reverses a positive inflow. That would hide
  an active use only if such an outflow can re-establish one: a reversal of a reversal of an outflow, or a reversal of a
  sales return that itself offsets the sale (reversal_of_id pointing to the SALE movement). Collected for the auditor to
  read (status INFO, not a verdict): movement shapes present in the data (type, sign, target type, target sign), every
  installed function body that inserts into erp.fg_stock_movements (statement excerpts), and whether a direct insert of a
  reversal of a positive REVERSAL row is refused by the table's own constraints/triggers (savepoint, rolled back).
"""
import hashlib,json,re,uuid
import psycopg
import cp6_t3_package_run as package
import cp7_misc_cases as misc

MARK='-- R4-05 one context probe'
STATES=('FRESH','XID','SALES_ROW_HERE','PROCUREMENT_ROW_HERE','COMMITTED_ROW_EARLIER')
SALES_ROW="insert into cp7_sales.command_context(backend_pid,transaction_id,actor,sale_id,action)values(pg_backend_pid(),txid_current(),%s,null,'POST')"
PROC_ROW=("insert into cp7_procurement.execution_context(backend_pid,transaction_id,actor,action,permission_key)"
          "values(pg_backend_pid(),txid_current(),%s,'POST','warehouse.procurement.post')")


def unpatched(body):
    i=body.index(MARK);start=body.rindex('\n',0,i)+1
    end=body.index('\n end if;',i)+len('\n end if;')
    return body[:start-1]+body[end:]


def cases(cur,today):
    def guard_matrix():
        conn=psycopg.connect(package.boundary.ADMIN,autocommit=False);c=conn.cursor()
        out=dict(cells={},identities={})
        try:
            body,secdef,config,defn,owner=c.execute("select prosrc,prosecdef,proconfig,pg_get_functiondef(oid),proowner::regrole::text from pg_proc where oid='erp.require_internal()'::regprocedure").fetchone()
            assert body.count(MARK)==1,('NO_PROBE_IN_INSTALLED_GUARD',body[:400])
            before=unpatched(body);assert 'txid_current_if_assigned' not in before and MARK not in before
            assert defn.count(body)==1
            copy=defn.replace(body,before).replace('erp.require_internal()','fable_r4_guard.guard_before()',1)
            out['installed_sha']=hashlib.sha256(body.encode()).hexdigest();out['secdef']=secdef;out['config']=config;out['owner']=owner
            out['removed_lines']=len(body.splitlines())-len(before.splitlines())
            c.execute('create schema fable_r4_guard');c.execute(copy,prepare=False)
            c.execute('alter function fable_r4_guard.guard_before() owner to '+owner)
            c.execute("""create function fable_r4_guard.answer(p_before boolean)returns text language plpgsql security invoker set search_path='' as $f$
begin
 if p_before then perform fable_r4_guard.guard_before();else perform erp.require_internal();end if;
 return 'ALLOW';
exception when others then return sqlstate||':'||sqlerrm;
end $f$""",prepare=False)
            acl={}
            for role in ('anon','authenticated','service_role'):
                c.execute(f'grant usage on schema fable_r4_guard to {role}');c.execute(f'grant execute on function fable_r4_guard.answer(boolean) to {role}')
                acl[role]=c.execute("select has_function_privilege(%s,'erp.require_internal()','EXECUTE')",(role,)).fetchone()[0]
                if acl[role]:c.execute(f'grant execute on function fable_r4_guard.guard_before() to {role}')
            c.execute('revoke execute on function fable_r4_guard.guard_before() from public')
            out['execute_on_guard']=acl
            conn.commit()
            users=c.execute("""select distinct on(u.role,u.is_active) u.role,u.is_active,u.auth_user_id::text from erp.app_users u
                               where u.auth_user_id is not null order by u.role,u.is_active,u.auth_user_id""").fetchall()
            conn.rollback()
            ident={}
            for role,active,sub in users:ident[('APP_'+str(role)+('' if active else '_INACTIVE'))]=(sub,'authenticated')
            ident['UNKNOWN_USER']=(str(uuid.uuid4()),'authenticated');ident['JWT_WITHOUT_SUB']=(None,'authenticated')
            ident['ANON']=(None,'anon');ident['SERVICE_ROLE']=(str(uuid.uuid4()),'service_role')
            out['identities']={k:v[1] for k,v in ident.items()}
            def answer(sub,role,state,old):
                try:
                    if state in('XID','COMMITTED_ROW_EARLIER'):c.execute('select txid_current()')
                    if state=='SALES_ROW_HERE':c.execute(SALES_ROW,(sub or str(uuid.uuid4()),))
                    if state=='PROCUREMENT_ROW_HERE':c.execute(PROC_ROW,(sub or str(uuid.uuid4()),))
                    claims={'role':role} if sub is None else {'sub':sub,'role':role}
                    c.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps(claims),))
                    c.execute('set local session authorization authenticator');c.execute('set local role '+role)
                    xid_before=c.execute('select txid_current_if_assigned() is not null').fetchone()[0]
                    a=c.execute('select fable_r4_guard.answer(%s)',(old,)).fetchone()[0]
                    xid_after=c.execute('select txid_current_if_assigned() is not null').fetchone()[0]
                    return a,xid_before,xid_after
                finally:conn.rollback()
            bad=[];fresh_allow=[];fresh_refuse=[];fresh_had_xid=[]
            earlier=None
            for state in STATES:
                if state=='COMMITTED_ROW_EARLIER':
                    # One committed sales context row of this backend, written by an earlier transaction.
                    earlier=c.execute(SALES_ROW.replace('%s','%s::uuid')+' returning transaction_id',(str(uuid.uuid4()),)).fetchone()[0];conn.commit()
                for name,(sub,role) in ident.items():
                    try:
                        o=answer(sub,role,state,True);n=answer(sub,role,state,False)
                    except Exception as e:
                        out['cells'][name+'/'+state]=dict(error=str(e)[:300]);continue
                    out['cells'][name+'/'+state]=dict(before=o[0],after=n[0],xid_before_call=[o[1],n[1]],xid_after_call=[o[2],n[2]])
                    # The copy's own name may appear in a privilege error; the answers are compared without it.
                    if o[0].replace('guard_before','require_internal')!=n[0]:bad.append(name+'/'+state)
                    if state=='FRESH':
                        (fresh_allow if n[0]=='ALLOW' else fresh_refuse).append(name)
                        if o[1] or n[1]:fresh_had_xid.append(name)
            if earlier is not None:
                c.execute('delete from cp7_sales.command_context where backend_pid=pg_backend_pid() and transaction_id=%s',(earlier,));conn.commit()
            meaningful=bool(fresh_allow) and bool(fresh_refuse) and not fresh_had_xid
            out.update(differences=bad,fresh_allow=fresh_allow,fresh_refuse=fresh_refuse,fresh_had_xid=fresh_had_xid,
                       status='COUNTEREXAMPLE' if bad else ('PASS' if meaningful else 'FAIL'),
                       oracle='R4-05: installed guard and the same guard without its probe answer alike in every cell')
            return out
        finally:
            try:
                conn.rollback();c.execute('drop schema if exists fable_r4_guard cascade');conn.commit()
            finally:conn.close()

    def fg_paths():
        misc.b.api.admin(cur)
        shapes=cur.execute("""select m.movement_type,sign(m.qty_signed)::int,o.movement_type,sign(o.qty_signed)::int,
                                     (o.reversal_of_id is not null),count(*)
                              from erp.fg_stock_movements m left join erp.fg_stock_movements o on o.id=m.reversal_of_id
                              group by 1,2,3,4,5 order by 1,2,3,4,5""").fetchall()
        constraints=cur.execute("""select conname,pg_get_constraintdef(oid) from pg_constraint where conrelid='erp.fg_stock_movements'::regclass order by 1""").fetchall()
        triggers=cur.execute("""select t.tgname,p.oid::regprocedure::text,t.tgenabled,substr(p.prosrc,1,1500) from pg_trigger t join pg_proc p on p.oid=t.tgfoid
                                where t.tgrelid='erp.fg_stock_movements'::regclass and not t.tgisinternal order by 1""").fetchall()
        writers={}
        for oid,src in cur.execute("""select p.oid::regprocedure::text,p.prosrc from pg_proc p join pg_namespace n on n.oid=p.pronamespace
                                      where p.prosrc ~* 'insert\\s+into\\s+erp\\.fg_stock_movements' order by 1""").fetchall():
            writers[oid]=[re.sub(r'\s+',' ',m.group(0))[:900] for m in re.finditer(r'insert\s+into\s+erp\.fg_stock_movements.*?;',src,re.S|re.I)]
        attempt=None
        row=cur.execute("""select m.id from erp.fg_stock_movements m join erp.fg_stock_movements o on o.id=m.reversal_of_id
                           where m.movement_type='REVERSAL' and m.qty_signed>0 and o.qty_signed<0 order by m.id limit 1""").fetchone()
        if row:
            cur.execute('savepoint fable_r4_rr')
            try:
                cur.execute('reset role')
                cur.execute("""insert into erp.fg_stock_movements select (jsonb_populate_record(null::erp.fg_stock_movements,
                                 to_jsonb(m)||jsonb_build_object('id',gen_random_uuid(),'qty_signed',-m.qty_signed,'reversal_of_id',m.id,'movement_type','REVERSAL'))).*
                               from erp.fg_stock_movements m where m.id=%s""",(row[0],))
                attempt='ACCEPTED_BY_TABLE'
            except Exception as e:attempt='REFUSED: '+str(e).split('\n')[0][:300]
            finally:cur.execute('rollback to savepoint fable_r4_rr');cur.execute('release savepoint fable_r4_rr');misc.b.api.admin(cur)
        return dict(status='INFO',shapes=[list(map(str,r)) for r in shapes],constraints=constraints,
                    triggers=[[a,b,str(c),d] for a,b,c,d in triggers],writers=writers,reversal_of_reversal_direct_insert=attempt,
                    note='read by the auditor; not a verdict')

    return [('FABLE_R4:GUARD_SAME_ANSWER_MATRIX',guard_matrix),('FABLE_R4:FG_REVERSAL_PATHS',fg_paths)]

def races(tools,today):return []
def http_cases(http,today):return []
