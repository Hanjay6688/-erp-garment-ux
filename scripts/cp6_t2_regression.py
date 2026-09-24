"""T2 regression for the combined CP6 candidate: AU + AV + AW (T1 install) + AX (T1 install).

Owner decision A+B: once every family passes its T1 probe, the whole existing regression runs once on the combined
candidate, then goes to independent audit. The case declarations, oracles and race schedules are the unchanged ones
the AV trial runs (AR 174, AT 16 / AU 15 with races, the original 326 plus AS 34); only the installed runtime differs.
Every case is compared with the AU recorded outcome per case id (H-01 comparator), so each moved case is listed for
disposition instead of being absorbed by a count. No oracle is edited and no historical HOLD is resolved here.

Label: T2_REGRESSION while the candidate is stable; T2_PRELIMINARY otherwise (set CP6_T2_LABEL).

CP6_T2_SEED=QUIETED (run 2): run 1 (35911656309) moved 145 regression and 7 AR cases, every one stopped by POLICY
blockers of the harness seed itself (4 seed workers without attendance, one seed payroll CALCULATED, seed contractor
work outside any payroll) under the recorded owner policy of AW (P-03: hold every date). Run 2 clears exactly those
seed items once per group, before any case, the way the owner would (awp.quiet_seed: attendance OFF through the
attendance RPCs, payroll approval, seed work into an approved payroll), inside the group transaction that is rolled
back afterwards. Oracles, cases and races are unchanged; a case that still moves is disposed of on its own.
"""
from datetime import date,timedelta
from pathlib import Path
import argparse,json,os,sys,types

AUDITOR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path.cwd()/'scripts'))
sys.path.append(str(AUDITOR/'scripts'))
import cp6_av_trial as avt
import cp6_av_runtime as av_runtime
import cp6_aw_probe as awp
import cp6_ax_probe as axp
import cp6_regression_identity as identity

LABEL=os.environ.get('CP6_T2_LABEL','T2_PRELIMINARY')
SEED=os.environ.get('CP6_T2_SEED','AS_IS')
QUIET_DAYS=120
avt.OUT=AUDITOR/'cp6-proof/t2'
assert SEED in ('AS_IS','QUIETED')


ORIGINAL_GROUP=avt.group


def group(name,factory):
    """Run 2 only: clear the seed's own open items in the group transaction before the cases are built."""
    if SEED!='QUIETED':return ORIGINAL_GROUP(name,factory)
    def quieted(cur,today):
        # group() has just closed through 2026-08-31. The seed payroll ends 2026-02-01 and the calendar cases reopen up
        # to three months back, so the seed items are cleared with the books open from 2026-01-02, then the group's
        # boundary is put back (the same administrative helper group() uses).
        prior=avt.predecessor.historical.prior
        prior.set_open_period(cur,date(2026,1,1))
        done=awp.quiet_seed(cur,today-timedelta(days=QUIET_DAYS),today)
        prior.set_open_period(cur,date(2026,8,31))
        after=awp.preflight(cur,today)
        print(json.dumps(dict(group='T2_SEED_QUIETED',target=name,window=[str(today-timedelta(days=QUIET_DAYS)),str(today)],
                              attendance=len(done['attendance']),approved=len(done['approved']),work_payrolls=len(done['work_payrolls']),
                              refused=done['refused'],after_status=after and after['status'],after_blockers=awp.blockers_brief(after)),
                         default=str),flush=True)
        return [(key,diagnosed(key,op,cur,today)) for key,op in factory(cur,today)]
    return ORIGINAL_GROUP(name,quieted)


ELIGIBLE="select coalesce(array_agg(md5(e::text)),'{}') from erp.v_payroll_eligible_work_lines e where e.remaining_qty>0"


def diagnosed(key,op,cur,today):
    """Side channel only: when a case fails with a Python assertion (its transaction still usable), print the engine
    answer and how many payroll-eligible work lines the case itself created. The case outcome is re-raised unchanged."""
    def run():
        awp.api.admin(cur);before=set(cur.execute(ELIGIBLE).fetchone()[0])
        try:
            return op()
        except Exception as exc:
            if not isinstance(exc,awp.psycopg.Error):
                try:
                    r=awp.preflight(cur,today);awp.api.admin(cur)
                    created=set(cur.execute(ELIGIBLE).fetchone()[0])-before
                    print(json.dumps(dict(group='T2_CASE_DIAG',case=key,engine_status=r and r['status'],blockers=awp.blockers_brief(r),
                                          uncovered_work_lines_created_by_case=len(created)),default=str),flush=True)
                except Exception as diag:
                    print(json.dumps(dict(group='T2_CASE_DIAG',case=key,diagnostic_error=str(diag)[:300])),flush=True)
            raise
    return run


avt.group=group


def change(kind,pg,control_url):
    """AV through its own closed-admission runtime, then the AW and AX T1 installs (development files)."""
    assert kind=='install'
    av=av_runtime.change('install',pg,control_url)
    aw=awp.install_aw();ax=axp.install_ax()
    return dict(status='PASS' if av['status']=='PASS' else 'FAIL',av=av['status'],aw=aw,ax=ax)


# The trial modules read `runtime`; point them at the combined candidate without touching their code.
avt.runtime=types.SimpleNamespace(change=change,verified=axp.ax_verified,pins=av_runtime.pins,
                                  qualify=None,refuse_post_use=None)


def ar_phase(report):
    """AR 174: the sequential group and the 28 races, on the combined candidate (no package cycles: that is T3)."""
    report['au_install']=avt.install_au()
    with avt.psycopg.connect(avt.ADMIN) as conn,conn.cursor() as cur:avt.api.seed(cur)
    report['candidate_install']=change('install',avt.PG,avt.control())
    seq=avt.group('AR_SEQUENTIAL',avt.ar_sequential)
    report['sequential']={k:seq[k] for k in ('status','counts')}
    with avt.psycopg.connect(avt.ADMIN) as conn,conn.cursor() as cur:
        axp.ax_verified(cur)
        today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
    races=[]
    for kind in avt.inherited.KINDS:
        for winner in ('imported','legacy'):
            races.append(('CONCURRENT_'+kind+'_'+winner.upper()+'_FIRST',lambda k=kind,w=winner:avt.inherited.concurrency(today,k,w)))
    for winner in ('imported','legacy'):
        for same in (False,True):
            races.append((('SAME_HEADER_' if same else 'WINNER_ABORT_')+winner.upper(),lambda w=winner,s=same:avt.inherited.concurrency(today,'MATERIAL',w,commit=s,same_header=s)))
    for variant in ('REPLAY','PAYLOAD','ACTION'):
        races.append(('REQUEST_CONCURRENT_'+variant,lambda v=variant:avt.inherited.request_concurrency(today,v)))
    races.append(('STALE_SNAPSHOT_ISOLATION',lambda:avt.inherited.isolation_guard(today)))
    report['races']={}
    for name,operation in races:
        try:row=operation()
        except Exception as exc:row=dict(status='INCOMPLETE',error=str(exc))
        report['races'][name]=row;avt.save('AR',report)
        print(json.dumps(dict(group='AR_CONCURRENCY',case=name,**row),default=str),flush=True)
    report['case_count']=len(seq['cases'])+len(report['races'])
    ok=report['case_count']==174 and seq['status']=='WRITER_PASS' and all(r['status']=='PASS' for r in report['races'].values())
    report['status']='WRITER_PASS' if ok else 'DISPOSITION_REQUIRED'


ORIGINAL_REGRESSION=avt.regression


def regression_phase(report):
    ORIGINAL_REGRESSION(report)
    # H-01: per-case identity against the AU recorded outcome, next to the old count summary.
    observed={}
    for name in ('business','imports','values'):
        path=avt.OUT/(name.upper()+'.json')
        observed[name.upper()]={k:r['status'] for k,r in json.loads(path.read_text())['cases'].items()}
    new=json.loads((avt.OUT/'NEW_CASES.json').read_text())
    observed['NEW_CASES']={k:r['status'] for k,r in new['cases'].items()}
    report['per_case_identity']=identity.compare(identity.load_expected(),observed)
    print(json.dumps(dict(group='T2_IDENTITY',**report['per_case_identity']),default=str),flush=True)
    if report['per_case_identity']['status']!='IDENTICAL_PER_CASE':report['status']='DISPOSITION_REQUIRED'


def run(phase):
    # Reuse the AV trial driver (writer checkout, clone lifecycle, primary check) with the combined candidate.
    if phase=='ar':avt.qualify=ar_phase
    if phase=='regression':avt.regression=regression_phase
    print(json.dumps(dict(t2_label=LABEL,phase=phase,seed=SEED)),flush=True)
    avt.run({'ar':'qualify','regression':'regression','temporal':'temporal'}[phase])


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=('ar','regression','temporal'),required=True)
    run(parser.parse_args().phase)
