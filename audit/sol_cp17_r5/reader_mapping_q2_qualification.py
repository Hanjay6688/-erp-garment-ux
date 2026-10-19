"""Execute the predeclared finite reader-graph and reversed-Nota qualification once."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import sys
import traceback

ROOT = Path(__file__).resolve().parent
PRODUCT = ROOT.parents[2] / 'auditor'
sys.path.insert(0, str(PRODUCT / 'scripts'))
import psycopg
import cp6_auditor_runner as native
import cp6_t3_package_run as package
import cp7_p09_procurement_probe as p09
import cp7_p21_full_rehearsal_probe as installer
import cp7_cp17_fix_probe as cp17
import cp7_restore_state as restore_state
import reader_mapping_q2_cases as cases
from detector_case import bd

MANIFEST = ROOT / 'READER_MAPPING_Q2_PREEXECUTION_MANIFEST.json'
OUT = PRODUCT / 'cp6-proof/t3/SOL_R5_READER_MAPPING_Q2.json'

def verify(cur):
    return dict(composition=installer.verify(cur), cp17=cp17.verify(cur))

def run():
    m = json.loads(MANIFEST.read_text())
    for p, h in m['pinned_product_sources'].items():
        assert hashlib.sha256((PRODUCT / p).read_bytes()).hexdigest() == h, p
    for p, h in m['audit_tool_sha256'].items():
        assert hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h, p
    report = dict(label='SOL_R5_READER_MAPPING_Q2', status='INCOMPLETE', candidate_sha=m['candidate_sha'],
                  candidate_tree=m['candidate_tree'], manifest_sha256=hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
                  oracle_origin='SOL_LITERAL_NUMBERS_AND_COMPLETE_GRAPH_DIFFERENTIAL', fixture_origin='ACCEPTED_NATIVE_PLUS_EXPLICITLY_REUSED_WRITER_INPUT_FIXTURES',
                  original_r4_case_code_reused=False, production_go=False, independent_acceptance=False,
                  full_family_acceptance=False, groups={})
    installed = False
    try:
        with psycopg.connect(package.boundary.ADMIN) as conn, conn.cursor() as cur:
            p09.wip.policy.bf.verified(cur)
            before = restore_state.capture(cur, package.boundary.snapshot, native.public_state, p09.functions)
            conn.rollback()
            originals, installation = installer.install(cur)
            conn.commit(); installed = True
            report['installation'] = installation
            report['installed_runtime'] = verify(cur)
            definitions = {n:cur.execute('select pg_get_functiondef(%s::regprocedure)', ('erp.'+n+'()',)).fetchone()[0]
                           for n in bd.bcp.DETECTORS}
            for n,h in m['expected_r5_active_function_sha256'].items():
                assert hashlib.sha256(definitions[n].encode()).hexdigest() == h, ('SOL_R5_ACTIVE_DEFINITION_DRIFT', n)
            (OUT.parent / 'SOL_R5_ORIGINAL_CONTROL_FUNCTIONS.json').write_text(json.dumps(definitions,indent=2)+'\n')
            extra = {n:cur.execute('select pg_get_functiondef(%s::regprocedure)', ('erp.'+n,)).fetchone()[0]
                     for n in m['extra_expression_pins']}
            for n,fragments in m['extra_expression_pins'].items():
                assert all(f in extra[n] for f in fragments), ('SOL_R5_ACTIVE_GUARD_DRIFT', n)
            (OUT.parent / 'SOL_R5_ORIGINAL_CONTROL_GUARDS.json').write_text(json.dumps(extra,indent=2)+'\n')
            triggers = cur.execute("select c.relname,t.tgname,t.tgenabled,pg_get_triggerdef(t.oid) from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relname=any(%s) and not t.tgisinternal order by c.relname,t.tgname", (m['runtime_trigger_tables'],)).fetchall()
            (OUT.parent / 'SOL_R5_ORIGINAL_CONTROL_TRIGGERS.json').write_text(json.dumps(triggers,indent=2)+'\n')
            conn.rollback()
        for name, factory in [('reader_mapping_q2', cases.cases)]:
            expected = [r['id'] for r in m['groups'][name]]
            group = native._strict_group_once('SOL_R5_READER_MAPPING_Q2_CASES', factory, verify)
            group['declared_ids_match'] = set(group.get('cases',{})) == set(expected)
            group['expected_case_ids'] = expected
            report['groups'][name] = group
        rows = [r for g in report['groups'].values() for r in g.get('cases',{}).values()]
        report['counts'] = dict(Counter(r['status'] for r in rows))
        report['observed_occurrences'] = len(rows)
        report['observed_unique_ids'] = len({k for g in report['groups'].values() for k in g.get('cases',{})})
    except Exception as e:
        report.update(error=str(e), traceback=traceback.format_exc())
    finally:
        if installed:
            with psycopg.connect(package.boundary.ADMIN) as conn, conn.cursor() as cur:
                installer.uninstall(cur, originals); conn.commit()
                report['cp6_restored'] = restore_state.prove(cur, before, package.boundary.snapshot, native.public_state, p09.functions, report)
                conn.rollback(); p09.wip.policy.bf.verified(cur); conn.rollback()
        groups = report['groups']
        complete = (not report.get('error') and report.get('cp6_restored') is True and set(groups)=={'reader_mapping_q2'}
                    and report.get('observed_occurrences')==1 and report.get('observed_unique_ids')==1
                    and all(g.get('complete_boundary_restored') is True and g.get('declared_ids_match') is True
                            and not g.get('missing') and not g.get('error') and g.get('status') in ('PASS','COUNTEREXAMPLE')
                            for g in groups.values()))
        report['evidence_protocol_complete'] = bool(complete)
        report['status'] = ('COUNTEREXAMPLE' if report.get('counts',{}).get('COUNTEREXAMPLE') else 'PASS') if complete else 'INCOMPLETE'
        if report['status']=='PASS' and report['counts']!={'PASS':1}:
            report['status']='INCOMPLETE'; report['evidence_protocol_complete']=False
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({k:report.get(k) for k in ['label','status','counts','cp6_restored','error']}),flush=True)
    return dict(status=report['status'],production_go=False,independent_acceptance=False,full_family_acceptance=False)

if __name__ == '__main__':
    package._writer_runtime = lambda browser_mode=False: run()
    package.run('install')
