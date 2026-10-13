"""Diagnosis only (owner 13 Oct 2026, Fable retest of 7a0b4a90): repeat the CP7_SUPPLIER_PAYMENT_CREATE native group on
one install and record, at every public_state read of the runner, where each public function row sits (ctid, xmin) and
the order the runner read them in. A group-end difference can then be attributed to rows that moved (a committed
update between the reads) or to a changed read order with the rows in place. Not a qualification: no case result here
counts, races/HTTP/browser are not run, and the runner and its comparisons are unchanged.

Run in place of scripts/cp7_supplier_payment_create_probe.py (same workflow steps, same install, same restore):
CP7_GROUP_END_REPEAT=20 python ../auditor/scripts/cp7_group_end_repeat_diagnosis.py
"""
import json,os,sys,time
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import psycopg
import cp6_auditor_runner as runner
import cp6_auditor_modes as modes
import cp7_supplier_payment_create_probe as probe

REPEAT=int(os.environ.get('CP7_GROUP_END_REPEAT','20'))
LOCATIONS="""select coalesce(jsonb_agg(jsonb_build_array(p.oid::regprocedure::text,p.ctid::text,p.xmin::text) order by p.ctid),'[]')
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.prokind in('f','p')"""
ACTIVITY="""select coalesce(jsonb_agg(jsonb_build_object('pid',pid,'backend_type',backend_type,'application',application_name,'state',state,
  'xact_start',xact_start,'query',left(query,160)) order by pid),'[]') from pg_stat_activity
  where datname=current_database() and pid<>pg_backend_pid()"""
SIZE="select pg_relation_size('pg_catalog.pg_proc'),relpages,reltuples from pg_class where oid='pg_catalog.pg_proc'::regclass"

reads=[]
_public_state=runner.public_state


def observed_public_state(cur):
    """The runner's own read, unchanged, plus the row locations read in the same transaction right after it."""
    state=_public_state(cur)
    reads.append(dict(order=[f[0] for f in state['functions']],locations=cur.execute(LOCATIONS).fetchone()[0]))
    return state


def side_view():
    with psycopg.connect(runner.boundary.ADMIN,autocommit=True) as conn,conn.cursor() as cur:
        return dict(at=time.strftime('%H:%M:%S'),activity=cur.execute(ACTIVITY).fetchone()[0],pg_proc_size=cur.execute(SIZE).fetchone())


def classify(start,end):
    if start['order']==end['order']:return 'READ_ORDER_EQUAL'
    if start['locations']!=end['locations']:return 'ROWS_MOVED'
    return 'READ_ORDER_CHANGED_ROWS_IN_PLACE'


def compare(start,end):
    a={s:(c,x) for s,c,x in start['locations']};b={s:(c,x) for s,c,x in end['locations']}
    moved=[dict(signature=s,before=a.get(s),after=b.get(s)) for s in sorted(set(a)|set(b)) if a.get(s)!=b.get(s)]
    by_ctid=lambda r:[s for s,_,_ in r['locations']]
    return dict(kind=classify(start,end),moved_rows=moved[:40],moved_count=len(moved),
                start_read_follows_ctid=start['order']==by_ctid(start),end_read_follows_ctid=end['order']==by_ctid(end))


_strict_group=runner.strict_group
summary=[]


def repeated(name,factory,verify):
    first=None
    for i in range(1,REPEAT+1):
        reads.clear();before=side_view()
        report=_strict_group(name,factory,verify)
        after=side_view()
        line=dict(diagnosis='CP7_GROUP_END_REPEAT',iteration=i,status=report['status'],final=report.get('final'),
                  complete_boundary_restored=report.get('complete_boundary_restored'),public_state_reads=len(reads),
                  group_end_difference=report.get('group_end_difference'),
                  start_vs_end=compare(reads[0],reads[-1]) if len(reads)>=2 else None,
                  catalog_observation_start=report.get('catalog_observation_start'),catalog_observation_end=report.get('catalog_observation_end'),
                  side_before=before,side_after=after)
        print(json.dumps(line,default=str),flush=True)
        summary.append(dict(iteration=i,status=report['status'],restored=report.get('complete_boundary_restored'),
                            kind=(line['start_vs_end'] or {}).get('kind')))
        first=first or report
    print(json.dumps(dict(diagnosis='CP7_GROUP_END_REPEAT_SUMMARY',repeat=REPEAT,iterations=summary,
                          not_restored=sum(1 for s in summary if s['restored'] is False)),default=str),flush=True)
    return first


def install():
    """Wrap the runner's public_state read and strict_group; races/HTTP/browser are not run in this diagnosis."""
    not_run=lambda *a,**k:dict(status='NOT_RUN_DIAGNOSIS_ONLY',counts={})
    runner.public_state=observed_public_state
    runner.strict_group=repeated
    modes.run_races=modes.run_http=modes.run_browser=not_run


if __name__=='__main__':
    install()
    probe.package._writer_runtime=lambda browser_mode=False:probe.run()
    try:probe.package.run('install')
    except AssertionError as exc:
        # The T3 gate is red here by construction (races/HTTP/browser are not run); its full line is printed above.
        print(json.dumps(dict(diagnosis='CP7_GROUP_END_REPEAT_GATE',red_because='RACES_HTTP_BROWSER_NOT_RUN_DIAGNOSIS_ONLY',gate=str(exc)[:2000])),flush=True)
    assert len(summary)==REPEAT,('CP7_GROUP_END_REPEAT_DID_NOT_COMPLETE',len(summary),REPEAT)
