"""Before/after evidence for the stable public-schema comparator (owner D14-8, A2). Disposable; needs a local superuser URL.

On a throwaway database, public functions are created in reverse name order so a sequential scan of pg_proc and an
index scan return them in different orders. The comparator before D14-8 (`order by 1` inside jsonb_agg, a constant)
is read under both plans, then the current comparator. Recorded: the plans, whether each list order changed, that both
comparators list the same members (signature and definition hash, duplicates counted), and that the current one also
sees an owner change and an access (ACL) change the earlier one did not. The cause of the two original A2 failures is
not claimed here; it stays OPEN (D13-10)."""
from pathlib import Path
import json,os,sys
import psycopg
sys.path.insert(0,str(Path(__file__).resolve().parent))
import cp6_auditor_runner as runner
from cp6_auditor_difference import state_difference

URL=os.environ.get('CP6_PUBLIC_STATE_TEST_PGURL','postgresql://postgres:postgres@127.0.0.1:54322/postgres')
DB='cp6_public_state_test'
ROLE='cp6_public_state_test_role'
PLANS={'sequential_scan':'set enable_indexscan=off;set enable_bitmapscan=off;set enable_seqscan=on',
       'index_scan':'set enable_seqscan=off;set enable_bitmapscan=off;set enable_indexscan=on'}

def nodes(plan):
    return [plan.get('Node Type')+(':'+plan['Relation Name'] if plan.get('Relation Name') else '')+(':'+plan['Index Name'] if plan.get('Index Name') else '')]+[x for c in plan.get('Plans',[]) for x in nodes(c)]

def read(cur,query,plan):
    cur.execute('begin');cur.execute(PLANS[plan])
    shape=nodes(cur.execute('explain (format json,costs false) '+query).fetchone()[0][0]['Plan'])
    state=cur.execute(query).fetchone()[0];cur.execute('rollback')
    return state,shape

def main():
    target=URL.rsplit('/',1)[0]+'/'+DB;out=dict(case='CP6_AUDITOR_PUBLIC_STATE_STABLE_ORDER',owner_decision='D14-8',a2_root_cause='OPEN (D13-10)')
    with psycopg.connect(URL,autocommit=True) as admin:
        admin.execute(f'drop database if exists {DB} with (force)');admin.execute(f'create database {DB}')
        admin.execute(f"do $r$ begin if not exists(select 1 from pg_roles where rolname='{ROLE}') then create role {ROLE} nologin; end if; end $r$")
        admin.execute(f'grant {ROLE} to current_user')
    try:
        with psycopg.connect(target,autocommit=True) as cur:
            # Reverse name order on disk, an overloaded name (two members, same name) and a table, so order and duplicates show.
            for i in reversed(range(240)):cur.execute(f'create function public.f_{i:03d}() returns int language sql as $$select {i}$$')
            cur.execute('create function public.same_name(int) returns int language sql as $$select 1$$')
            cur.execute('create function public.same_name(text) returns int language sql as $$select 2$$')
            cur.execute('create table public.t_rows(x int)');cur.execute('analyze')
            members=cur.execute("select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.prokind in('f','p')").fetchone()[0]
            before={p:read(cur,runner.PUBLIC_STATE_BEFORE_D14_8,p) for p in PLANS}
            after={p:read(cur,runner.PUBLIC_STATE,p) for p in PLANS}
            old_a,old_b=before['sequential_scan'][0],before['index_scan'][0];new_a,new_b=after['sequential_scan'][0],after['index_scan'][0]
            pairs=lambda state:sorted(json.dumps(x[:2]) for x in state['functions'])
            out['plans']=dict(before={p:before[p][1] for p in PLANS},after={p:after[p][1] for p in PLANS})
            out['before_d14_8']=dict(same_order_under_both_plans=old_a==old_b,same_members=sorted(map(json.dumps,old_a['functions']))==sorted(map(json.dumps,old_b['functions'])),
                difference=state_difference({},{},old_a,old_b),first_three={p:[x[0] for x in before[p][0]['functions'][:3]] for p in PLANS})
            out['after_d14_8']=dict(identical_under_both_plans=new_a==new_b,first_three=[x[0] for x in new_a['functions'][:3]],entry_fields=['signature','definition_md5','owner','acl'])
            out['members']=dict(catalog=members,before=len(old_a['functions']),after=len(new_a['functions']),same_signature_and_definition_pairs=pairs(old_a)==pairs(new_a),
                overloaded_name_members=sum(1 for x in new_a['functions'] if x[0].startswith('same_name(')))
            assert out['after_d14_8']['identical_under_both_plans'],out
            assert out['members']['before']==out['members']['after']==members==242 and out['members']['same_signature_and_definition_pairs'] and out['members']['overloaded_name_members']==2,out
            assert out['before_d14_8']['same_members'],out
            # Sensitivity: owner and ACL changes are seen by the current comparator; definition and member changes by both.
            base_old=cur.execute(runner.PUBLIC_STATE_BEFORE_D14_8).fetchone()[0];base_new=cur.execute(runner.PUBLIC_STATE).fetchone()[0]
            checks={}
            for name,change,undo in [('acl_grant',f'grant execute on function public.f_007() to {ROLE}',f'revoke execute on function public.f_007() from {ROLE}'),
                                     ('owner_change',f'alter function public.f_008() owner to {ROLE}','alter function public.f_008() owner to postgres'),
                                     ('table_acl_grant',f'grant select on public.t_rows to {ROLE}',f'revoke select on public.t_rows from {ROLE}'),
                                     ('definition_change','create or replace function public.f_009() returns int language sql as $$select -9$$','create or replace function public.f_009() returns int language sql as $$select 9$$'),
                                     ('member_removed','drop function public.f_010()','create function public.f_010() returns int language sql as $$select 10$$')]:
                cur.execute(change)
                checks[name]=dict(before_d14_8_sees=cur.execute(runner.PUBLIC_STATE_BEFORE_D14_8).fetchone()[0]!=base_old,after_d14_8_sees=cur.execute(runner.PUBLIC_STATE).fetchone()[0]!=base_new)
                cur.execute(undo)
            checks['restored_equal']=cur.execute(runner.PUBLIC_STATE).fetchone()[0]==base_new
            out['sensitivity']=checks
            assert all(v['after_d14_8_sees'] for k,v in checks.items() if k!='restored_equal') and checks['restored_equal'],out
            out['status']='PASS'
    finally:
        with psycopg.connect(URL,autocommit=True) as admin:
            admin.execute(f'drop database if exists {DB} with (force)');admin.execute(f'drop role if exists {ROLE}')
        print(json.dumps(out,default=str),flush=True)
if __name__=='__main__':main()
