"""Prepared cutting browser controls: disposable loopback database only.

Setup reviews the real selected calendar and retains its two setup jobs. The
browser must create a distinct request and complete that request itself. There
is no immutable-job deletion, invented snapshot, stock override or forged JWT.
"""
from datetime import date
from urllib.parse import urlparse
import json, os, sys, uuid
import psycopg
import cp7_ow12b_frozen_cutting_cases as cutting

plan=cutting.plan


def state(cur,actor):
    plan.b.api.admin(cur)
    rows=cur.execute('select request_id::text,run_id::text,state,reference from cp7_analysis_stage.jobs where actor=%s order by captured_at,request_id',(actor,)).fetchall()
    return dict(jobs=[dict(zip(('request','run','state','reference'),r))for r in rows],metadata=cutting.metadata(cur))


def main():
    url=os.environ['AUDITOR_BROWSER_DB_URL'];u=urlparse(url)
    assert u.hostname in('localhost','127.0.0.1')and u.path=='/cp6_auditor_browser'
    op,p=sys.argv[1],json.load(sys.stdin)
    actor=str(uuid.UUID(p['actor']));assert actor==p['actor']
    allowed={'prepare':{'actor','today'},'state':{'actor'},'read':{'actor','request'},
             'receipt':{'actor','request'},'deactivate':{'actor'},'restore':{'actor'}}
    assert op in allowed and set(p)==allowed[op]
    with psycopg.connect(url)as conn,conn.cursor()as cur:
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        if op=='prepare':
            today=date.fromisoformat(p['today']);x=plan.fixture(cur,today)
            cutting.native.native.policy.master.role_actor(cur,'OWNER') # Keep last-active-owner guard intact.
            observed={};setup=cutting.reviewed_capture(cur,today,actor,observed)
            options,_,_=plan.draft_payload(cur,x,setup['done']['run_id'],actor)
            assert options['production_state']=='ACTIVE'and options['needed_pcs']is not None and options['capacity_pcs']is not None
            assert cutting.Decimal(options['needed_pcs'])>=2 and cutting.Decimal(options['capacity_pcs'])>=2
            stamp=cur.execute("select to_char((clock_timestamp()-interval '1 hour')at time zone 'Asia/Jakarta','YYYY-MM-DD\"T\"HH24:MI:SS')").fetchone()[0]
            out=dict(query=plan.staged.query(today),target=x['target'],root=x['root'],po=x['po'],
                     material=str(x['fabric']['material']),location=str(x['fabric']['location']),cut_at_wib=stamp,
                     browser_request_precreated=False,setup_requests=[j['request']for j in state(cur,actor)['jobs']],
                     calendar_review=observed['fixture_calendar_review'])
        elif op=='state':out=state(cur,actor)
        elif op=='read':
            request=str(uuid.UUID(p['request']));row=plan.staged.job_row(cur,request,actor);assert row['state']=='DONE'
            original,pages,meta=plan.staged.fetch(cur,row['run_id'],actor)
            assert original['analysis']['scope']['actor_scope_id']==actor and pages['request_id']==request
            out=dict(page_set=pages,reference=row['reference'],recommendations=original['analysis']['recommendations'])
        elif op=='receipt':
            request=str(uuid.UUID(p['request']));plan.b.api.admin(cur)
            rows=cur.execute('select payload,result,draft_id::text from cp7_cutting_checked.receipts where actor=%s and request_id=%s',(actor,request)).fetchall()
            assert len(rows)==1
            payload,result,draft=rows[0];out=dict(payload=payload,result=result,draft_id=draft,
                current_draft=plan.read(cur,draft,actor))
        else:
            cur.execute('update erp.app_users set is_active=%s where auth_user_id=%s',(op=='restore',actor));out=dict(status='PASS')
        plan.b.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    print(json.dumps(out,default=str))


if __name__=='__main__':main()
