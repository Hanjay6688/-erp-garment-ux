#!/usr/bin/env python3
"""Run an auditor's own scenario on the final CP6 candidate in a disposable clone (GPT audit of 737649b, request 3:
independent acceptance of AY rev7.4 and AZ rev2.1 needs a runtime the auditor controls). Label AUDITOR_SCENARIO:
not release evidence, production_go=false.

Chain: the untouched AN clone of the CP6 probe workflows, then AU, AV, AW, AX, AY from the committed T1 family files;
phase after adds AZ and BA (the current candidate, BA: the independent audit's product fixes, see scripts/cp6_ba_build.py),
phase pre_ba adds AZ only (the candidate before BA), phase before adds neither. The committed candidate is verified before
any case runs (function text equal to the committed files, T1 markers).

The scenario is plain Python supplied at dispatch time (workflow input, base64), written by the auditor, not by the writer.
It defines at least one of
    def cases(cur, today): return [(case_id, zero_argument_callable), ...]
    def races(tools, today): return [(race_id, zero_argument_callable), ...]      (two sessions, committed copy per race)
    def http_cases(http, today): return [(case_id, zero_argument_callable), ...]  (real Auth login, real PostgREST)
where each callable returns a dict with at least 'status'. Races and HTTP cases are described in
scripts/cp6_auditor_modes.py. It may import the probe helpers already on sys.path
(import cp6_az_probe as azp: produce, cut_only, invoice, ledger_days, adjust, final_receipt, ...; cp6_aw_probe as awp:
preflight; chain.production for the ordinary product RPCs). Each case runs inside a savepoint that is rolled back, through the strict
group of scripts/cp6_auditor_runner.py (duplicate ids refused; status vocabulary; public schema, advisory locks and other
sessions checked after every case); its full result is printed as one JSON line. The scenario file's sha256 is printed first, so the
auditor can tie the log to the file.

A browser module (ES module, workflow input browser_b64) may be given as well: --browser PATH runs its cases(ui, today)
in Playwright against this branch's UI with real Auth (scripts/cp6_auditor_modes.py run_browser, independent audit B4).

Usage (workflow .github/workflows/cp6-auditor-scenario.yml):
    python scripts/cp6_auditor_scenario.py --phase after --scenario /path/to/scenario.py
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,subprocess,sys,traceback
import psycopg

AUDITOR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path.cwd()/'scripts'))
sys.path.append(str(AUDITOR/'scripts'))
import cp6_aw_probe as awp
import cp6_ax_probe as axp
import cp6_ay_probe as ayp
import cp6_az_probe as azp
import cp6_ba_probe as bap
import cp6_auditor_modes as modes
import cp6_auditor_runner as runner
import cp6_run_identity as run_identity
r1,boundary,prior=awp.r1,awp.boundary,awp.prior

OUT=AUDITOR/'cp6-proof/auditor'
LABEL='AUDITOR_SCENARIO'


def load(path):
    spec=importlib.util.spec_from_file_location('auditor_scenario',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert any(callable(getattr(module,n,None)) for n in ('cases','races','http_cases')),'AUDITOR_SCENARIO_NEEDS_cases_races_OR_http_cases'
    return module


def run(phase,scenario,selftest=False,browser=None):
    assert os.environ.get('CP6_AR_CONFIRM')=='cp6_rollback' and os.environ.get('CP6_DATABASE_CONTAINER')=='supabase_db_cp5-local'
    text=Path(scenario).read_bytes()
    print(json.dumps(dict(auditor_scenario_sha256=hashlib.sha256(text).hexdigest(),bytes=len(text),phase=phase)),flush=True)
    module=load(scenario)
    r1.OUT=OUT
    report=dict(status='INCOMPLETE',label=LABEL,phase=phase,scenario_sha256=hashlib.sha256(text).hexdigest(),
                production_go=False,independent_acceptance=False,release_evidence=False)
    report['run_identity']=run_identity.announce(LABEL+('_SELFTEST' if selftest else ''),phase=phase,scenario_sha256=report['scenario_sha256'])
    primary=None
    try:
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:prior.verified(cur,'AN');primary=boundary.snapshot(cur)
        r1.writer.install_at()
        control_url=os.environ['CP6_ADMISSION_CONTROL_PGURL']
        report['au_install']=awp.au_runtime.change('install',boundary.PG,control_url)['status']
        report['av_install']=awp.av_runtime.change('install',boundary.PG,control_url)['status']
        report['aw_install']=awp.install_aw();report['ax_install']=axp.install_ax();report['ay_install']=ayp.install_ay();verify=ayp.ay_verified
        if phase in('pre_ba','after'):report['az_install']=azp.install_az();verify=azp.az_verified
        if phase=='after':report['ba_install']=bap.install_ba();verify=bap.ba_verified
        print(json.dumps(dict(auditor_setup={k:report.get(k) for k in ('au_install','av_install','ay_install','az_install','ba_install')}),default=str),flush=True)
        # B1 (CP6-10): the strict group (duplicate ids refused, status vocabulary, public schema, advisory locks and
        # leaked sessions checked after every case, planned vs final printed).
        group=runner.strict_group('AUDITOR_CASES_'+phase.upper(),getattr(module,'cases',None) or (lambda cur,today:[]),verify)
        report['auditor_cases']={k:group.get(k) for k in ('status','counts','planned_case_ids','final','error')}
        complete=group['status']!='INCOMPLETE'
        if selftest:
            duplicate=runner.strict_group('AUDITOR_SELFTEST_DUPLICATE_IDS',
                lambda cur,today:[('ST:SAME',lambda:dict(status='PASS')),('ST:SAME',lambda:dict(status='PASS'))],verify)
            # Round 9, W4: a case that commits the group transaction ends the group as a structured INCOMPLETE (the next
            # case is listed as missing), not as a crash on the missing savepoint.
            ended=runner.strict_group('AUDITOR_SELFTEST_CASE_COMMITS',
                lambda cur,today:[('ST:COMMITS',lambda:(cur.connection.commit(),dict(status='PASS'))[1]),('ST:AFTER',lambda:dict(status='PASS'))],verify)
            verdict=module.check(group.get('cases'))
            report['selftest']=dict(cases=verdict,planned_equal=group.get('planned_case_ids')==list(module.EXPECTED),
                                    duplicate_group_refused=duplicate.get('error')=='AUDITOR_DUPLICATE_CASE_IDS' and not duplicate['cases'],
                                    committing_case_structured=ended.get('error')=='AUDITOR_CASE_ENDED_GROUP_TRANSACTION' and ended['status']=='INCOMPLETE'
                                        and (ended['cases'].get('ST:COMMITS') or {}).get('status')=='INCOMPLETE' and ended.get('missing')==['ST:AFTER'])
            complete=all(v['ok'] for v in verdict.values()) and report['selftest']['planned_equal'] and report['selftest']['duplicate_group_refused'] \
                and report['selftest']['committing_case_structured']
            print(json.dumps(dict(auditor_selftest=report['selftest']),default=str),flush=True)
        # Two-session and HTTP modes run on committed copies of the installed clone, after the savepoint cases.
        if callable(getattr(module,'races',None)):
            races=modes.run_races(module,verify,phase);report['auditor_races']={k:races.get(k) for k in ('status','counts','database_remaining','error')}
            complete=complete and races['status']=='RUN_COMPLETE'
        if callable(getattr(module,'http_cases',None)):
            http=modes.run_http(module,verify,phase)
            report['auditor_http']={k:http.get(k) for k in ('status','counts','database_remaining','cleanup','auth_counts','error')}
            complete=complete and http['status']=='RUN_COMPLETE'
        # Browser mode (independent audit B4): the auditor's Playwright module on the candidate UI.
        if browser:
            b=modes.run_browser(browser,verify,phase)
            report['auditor_browser']={k:b.get(k) for k in ('status','counts','script_sha256','database_remaining','cleanup','auth_counts',
                                                            'console_errors','users_created','error')}
            complete=complete and b['status']=='RUN_COMPLETE'
        report['status']=('SELFTEST_PASS' if complete else 'SELFTEST_FAIL') if selftest else ('RUN_COMPLETE' if complete else 'INCOMPLETE')
    except Exception as exc:report.update(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
    finally:
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1','cp6_rollback'],check=True)
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            prior.verified(cur,'AN');report['primary_unchanged']=primary is not None and boundary.snapshot(cur)==primary
            report['clone_remaining']=cur.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]
        if not report['primary_unchanged'] or report['clone_remaining']:report['status']='INCOMPLETE'
    print(json.dumps(dict(auditor_phase=phase,**report),default=str),flush=True)
    # The job fails only when the run itself is incomplete; case outcomes (PASS/FAIL/COUNTEREXAMPLE) are the auditor's to read.
    assert report['status']==('SELFTEST_PASS' if selftest else 'RUN_COMPLETE'),report.get('error',report['status'])


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--phase',choices=('before','pre_ba','after'),required=True)
    parser.add_argument('--scenario',required=True)
    parser.add_argument('--selftest',action='store_true',help='the runner self-test (B1): expect the scenario EXPECTED statuses')
    parser.add_argument('--browser',help='ES module with cases(ui, today) for the browser mode (B4)')
    args=parser.parse_args();run(args.phase,args.scenario,args.selftest,args.browser)
