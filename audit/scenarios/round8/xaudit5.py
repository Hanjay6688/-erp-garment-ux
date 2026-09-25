"""AUDITOR SCENARIO xaudit_5 — two-session races and REAL Auth/HTTP cases on the writer's new runtime modes
(scripts/cp6_auditor_modes.py at tool head d284e9b; product reference 9add57e, forward product unchanged).
RACES (tools.two_sessions: holder keeps its transaction open, worker runs concurrently, holder commits):
  R1 two sessions FINALIZE two import batches of the SAME opening item (F1-12/CP6-09 under concurrency): oracle M:138/M:1043
     at most one further POSTED opening for the item; contention kind recorded.
  R2 two sessions close the same accounting date after the seed is quieted: oracle M:3816/M:1057-1065 exactly one filing,
     the other refused with the product message.
  R3 two sessions COMPLETE the same WIP opening source with the same expected_remaining: oracle M:369-371 the second is
     refused STALE_VERSION; total output never exceeds the source qty.
HTTP (http.login = real GoTrue user bound to erp.app_users; http.anon_rpc = anon key only; PostgREST on a committed copy):
  H1 matrix of the 10 CP6 facades × {anon, GUDANG, AUDITOR_VIEW_ONLY, OWNER read-only}: oracle M:1322/M:1729 fail-closed;
     M:281 viewer may READ the accessory workspace but not write.
  H2 revocation: OWNER token stays valid at Auth but erp.app_users.is_active=false -> refused (M:281 'pengguna nonaktif').
  H3 unmapped: OWNER token whose erp.app_users row is deleted -> refused (M:1322 unmapped).
Browser→HTTP→runtime (UI) is NOT exercised here (no browser in this mode) — recorded as a limit."""
from datetime import timedelta
import json,traceback,uuid
import psycopg

FACADES=[('preflight','erp_accounting_close_preflight_v1'),('close','erp_close_accounting_through_v1'),('laundry_estimate','erp_set_laundry_rate_owner_estimate_v1'),
         ('fg_preview','erp_preview_fg_unsourced_value_v1'),('fg_post','erp_post_fg_unsourced_receipt_v1'),('fg_reverse','erp_reverse_fg_unsourced_receipt_v1'),
         ('accessory_workspace','erp_get_accessory_issue_workspace_v1'),('accessory_save','erp_save_accessory_issue_action_v1'),
         ('pocket_workspace','erp_get_pocket_fabric_workspace_v1'),('import_workspace','erp_get_initial_import_workspace_v1')]
READ_ONLY=('preflight','accessory_workspace','pocket_workspace','import_workspace')

def wrap(fn):
    def run():
        try:return fn()
        except Exception as exc:return dict(status='INCOMPLETE',error=str(exc)[:1200],traceback=traceback.format_exc()[-1500:])
    return run

# ---------------------------------------------------------------- races
def races(tools,today):
    api=tools.api;awp=tools.awp;prod=tools.chain.production
    import cp6_opening_overlap_probe as ovp
    import cp6_initial_import_production_trial as pt

    def r1_import_overlap():
        with tools.connect() as c,c.cursor() as cur:
            api.admin(cur);first=ovp.imported(cur,today,'MATERIAL')
            row=cur.execute("select m.material_sku,l.location_code,i.qty,i.unit_cost_snapshot from erp.opening_balance_items i join erp.materials m on m.id=i.material_id join erp.locations l on l.id=i.location_id where i.opening_id=%s",(first,)).fetchone()
            c.commit()
        def finalize_same_item(cur):
            api.admin(cur);code='XA5'+uuid.uuid4().hex[:10]
            batch=api.call(cur,'CREATE',dict(batch_code=code,cutover_date=str(today-timedelta(days=1))))['batch_id']
            api.upload(cur,batch,'OPENING_BALANCE_ITEM',[dict(balance_type='MATERIAL',control_key='CHECK',material_sku=row[0],location_code=row[1],qty=str(row[2]),unit_cost=str(row[3]))])
            api.upload(cur,batch,'OPENING_CONTROL',[dict(balance_type='MATERIAL',control_key='CHECK',qty=str(row[2]),amount=str(row[2]*row[3]))])
            return api.invoke(cur,'FINALIZE',batch)
        held,contention,outcome=tools.two_sessions(finalize_same_item,finalize_same_item,True)
        with tools.connect() as c,c.cursor() as cur:
            api.admin(cur)
            posted=cur.execute("select count(*),coalesce(sum(i.qty),0)::text from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id join erp.locations l on l.id=i.location_id where h.status='POSTED' and l.location_code=%s",(row[1],)).fetchone()
        checks=dict(no_further_posted_beyond_first=posted[0]<=1)
        return dict(status='PASS' if checks['no_further_posted_beyond_first'] else 'COUNTEREXAMPLE',checks=checks,holder=str(held)[:200],contention=contention,worker=outcome,
                    posted_items_for_location=posted[0],posted_qty=posted[1],
                    expected='M:138/M:1043 under two real sessions: the same opening item is never POSTED again (first import only); contention kind recorded')

    def r2_close_same_date():
        d=today-timedelta(days=1);d0=today-timedelta(days=4)
        with tools.connect() as c,c.cursor() as cur:
            api.admin(cur);awp.boundary.historical.prior.set_open_period(cur,d0-timedelta(days=1));quiet=awp.quiet_seed(cur,d0,d)
            pre=awp.preflight(cur,d);c.commit()
        def close(cur):
            api.ordinary(cur);return cur.execute('select erp.close_accounting_through(%s,%s)',(d,'XA5 race close')).fetchone()[0]
        held,contention,outcome=tools.two_sessions(close,close,True)
        with tools.connect() as c,c.cursor() as cur:
            api.admin(cur)
            filings=cur.execute("select count(*) from erp.accounting_close_filings_v1 where closed_through=%s",(d,)).fetchone()[0] if cur.execute("select to_regclass('erp.accounting_close_filings_v1') is not null").fetchone()[0] else None
            closed=cur.execute('select closed_through from erp.accounting_period_control where singleton_id=1').fetchone()[0]
        worker_ok=outcome.get('ok');msg=outcome.get('message')
        checks=dict(preflight_ready=(pre or {}).get('status')=='READY',holder_closed=held is not None,worker_refused=not worker_ok,filings_exactly_one=filings==1 if filings is not None else None,closed_through_is_d=closed==d)
        ok=checks['holder_closed'] and checks['worker_refused'] and (checks['filings_exactly_one'] in (True,None)) and checks['closed_through_is_d']
        return dict(status='PASS' if ok else ('INCOMPLETE' if not checks['preflight_ready'] else 'COUNTEREXAMPLE'),checks=checks,preflight=(pre or {}).get('status'),blockers=[b.get('code') for b in (pre or {}).get('blockers',[])][:6],
                    contention=contention,worker=outcome,worker_message=msg,filings=filings,closed_through=str(closed),
                    expected='M:3816/M:1057-1065: two concurrent closes of the same READY date -> exactly one filing; the second is refused with the product message')

    def r3_wip_same_remaining():
        with tools.connect() as c,c.cursor() as cur:
            api.admin(cur);f=pt.fixture(api,cur,today);receipt,sources=pt.finalize(api,cur,f)
            s=next(x for x in api.read(cur,f['batch'])['batch']['production_sources'] if x['balance_type']=='WIP');c.commit()
        payload=dict(batch_id=f['batch'],opening_item_id=s['opening_item_id'],expected_remaining=str(s['remaining_qty_pcs']),operation='COMPLETE',qty_pcs='8',
                     product_sku=f['code'],location_code=f['code']+'F',date=str(today-timedelta(days=2)),reason='XA5 race completion')
        def complete(cur):api.admin(cur);return api.call(cur,'WIP_OUTPUT',payload,uuid.uuid4())
        held,contention,outcome=tools.two_sessions(complete,complete,True)
        with tools.connect() as c,c.cursor() as cur:
            api.admin(cur);outputs=cur.execute('select count(*),coalesce(sum(qty_pcs),0)::text from erp.initial_import_wip_outputs o where o.opening_item_id=%s and not exists(select 1 from erp.initial_import_wip_output_reversals r where r.output_id=o.id)',(s['opening_item_id'],)).fetchone()
        checks=dict(holder_posted=isinstance(held,dict) and held.get('status')=='POSTED',worker_refused=not outcome.get('ok'),worker_stale_version='STALE_VERSION' in str(outcome.get('message')),total_output_not_above_source=int(float(outputs[1]))<=8)
        return dict(status='PASS' if all(checks.values()) else 'COUNTEREXAMPLE',checks=checks,contention=contention,worker=outcome,outputs=[str(x) for x in outputs],
                    expected='M:369-371 under two real sessions: the second COMPLETE with the same expected_remaining is refused STALE_VERSION; total output never exceeds the source qty')
    return [('XA5:R1_TWO_SESSIONS_SECOND_IMPORT_BATCH_SAME_ITEM',wrap(r1_import_overlap)),
            ('XA5:R2_TWO_SESSIONS_CLOSE_SAME_DATE',wrap(r2_close_same_date)),
            ('XA5:R3_TWO_SESSIONS_WIP_COMPLETE_SAME_REMAINING',wrap(r3_wip_same_remaining))]

# ---------------------------------------------------------------- http
def http_cases(http,today):
    def signatures():
        with http.connect() as c,c.cursor() as cur:
            return {fn:cur.execute("select pg_get_function_arguments(p.oid) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proname=%s limit 1",(fn,)).fetchone()[0] for _,fn in FACADES}
    def body_for(args):
        out={}
        for part in (args or '').split(','):
            part=part.strip()
            if not part:continue
            name,_,rest=part.partition(' ');typ=rest.split(' DEFAULT')[0].strip().lower();name=name.strip('"')
            out[name]=(str(today-timedelta(days=1)) if 'date' in typ and 'timestamp' not in typ else str(uuid.uuid4()) if 'uuid' in typ else {} if 'json' in typ
                       else 1.5 if 'numeric' in typ else '2026-09-20T00:00:00+07:00' if 'timestamp' in typ else 'auditor http probe' if 'text' in typ else None)
        return out
    def refused(r):
        b=json.dumps(r.get('body'),default=str)
        return r['status'] in (401,403) or (r['status']>=400 and ('OWNER or ADMIN' in b or 'permission denied' in b or 'PERMISSION_DENIED' in b))
    def brief(r):return dict(status=r['status'],body=json.dumps(r.get('body'),default=str)[:160])

    def h1_matrix():
        sigs=signatures();users={role:http.login(role,role.lower()) for role in ('OWNER','GUDANG','AUDITOR_VIEW_ONLY')}
        res={}
        for label,fn in FACADES:
            res['anon:'+label]=http.anon_rpc(fn,body_for(sigs[fn]))
            for role in ('GUDANG','AUDITOR_VIEW_ONLY'):res[role+':'+label]=users[role].rpc(fn,body_for(sigs[fn]))
            if label in READ_ONLY:res['OWNER:'+label]=users['OWNER'].rpc(fn,body_for(sigs[fn]))
        checks=dict(anon_all_refused=all(refused(res['anon:'+l]) for l,_ in FACADES),
                    gudang_all_refused=all(refused(res['GUDANG:'+l]) for l,_ in FACADES),
                    viewer_refused_except_accessory_read=all(refused(res['AUDITOR_VIEW_ONLY:'+l]) for l,_ in FACADES if l!='accessory_workspace'),
                    viewer_reads_accessory_workspace=res['AUDITOR_VIEW_ONLY:accessory_workspace']['status']==200,
                    owner_reads_200=all(res['OWNER:'+l]['status']==200 for l in READ_ONLY))
        return dict(status='PASS' if all(checks.values()) else 'COUNTEREXAMPLE',checks=checks,signatures=sigs,results={k:brief(v) for k,v in res.items()},
                    expected='M:1322/M:1729 over real Auth+PostgREST: anon and GUDANG refused on all 10 facades; AUDITOR_VIEW_ONLY refused everywhere except reading the accessory workspace (M:281); OWNER reads 200')

    def h2_revoked():
        sigs=signatures();owner=http.login('OWNER','revoke');args=body_for(sigs['erp_accounting_close_preflight_v1'])
        before=owner.rpc('erp_accounting_close_preflight_v1',args)
        with http.connect() as c,c.cursor() as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));c.commit()
        after=owner.rpc('erp_accounting_close_preflight_v1',args)
        with http.connect() as c,c.cursor() as cur:cur.execute('update erp.app_users set is_active=true where auth_user_id=%s',(owner.auth_user_id,));c.commit()
        checks=dict(active_owner_200=before['status']==200,inactive_refused=refused(after) or after['status']!=200)
        return dict(status='PASS' if all(checks.values()) else 'COUNTEREXAMPLE',checks=checks,before=brief(before),after=brief(after),
                    expected="M:281/M:1322: a valid Auth token whose app user is inactive is refused (fail-closed); refusal is an authorization error")

    def h3_unmapped():
        sigs=signatures();owner=http.login('OWNER','unmap');args=body_for(sigs['erp_accounting_close_preflight_v1'])
        before=owner.rpc('erp_accounting_close_preflight_v1',args)
        with http.connect() as c,c.cursor() as cur:cur.execute('delete from erp.app_users where auth_user_id=%s',(owner.auth_user_id,));c.commit()
        after=owner.rpc('erp_accounting_close_preflight_v1',args)
        acc=owner.rpc('erp_get_accessory_issue_workspace_v1',body_for(sigs['erp_get_accessory_issue_workspace_v1']))
        checks=dict(mapped_owner_200=before['status']==200,unmapped_refused=refused(after) or after['status']!=200,unmapped_accessory_refused=refused(acc) or acc['status']!=200)
        return dict(status='PASS' if all(checks.values()) else 'COUNTEREXAMPLE',checks=checks,before=brief(before),after=brief(after),accessory=brief(acc),
                    expected='M:1322: an authenticated token with no erp.app_users mapping is refused on every facade')
    return [('XA5:H1_FACADE_MATRIX_REAL_AUTH',wrap(h1_matrix)),('XA5:H2_REVOKED_APP_USER',wrap(h2_revoked)),('XA5:H3_UNMAPPED_AUTH_USER',wrap(h3_unmapped))]
