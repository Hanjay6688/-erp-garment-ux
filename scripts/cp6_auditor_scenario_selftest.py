"""Self-test of the auditor runtime's strict group (independent audit B1 / CP6-10). Each case below leaks on purpose in
one of the ways the audit found the shared group blind to; the runner must end every one of them INCOMPLETE, keep the
clean case PASS, and refuse a group with duplicate case ids (checked by the runner itself in --selftest mode). A case
passes the self-test only when the expected detector fired and no other one did (check below).
Run: python scripts/cp6_auditor_scenario.py --phase before --scenario scripts/cp6_auditor_scenario_selftest.py --selftest
Label: tool self-test, not product evidence."""
import psycopg
import cp6_aw_probe as awp
import cp6_auditor_runner as runner

LEAKED=[]
# Expected outcome per case: the status and the detector that must fire. Every other detector must stay clean, so a case
# that ends INCOMPLETE for another reason (an exception in the fixture, a second leak) fails the self-test.
EXPECTED={'ST:CLEAN':dict(status='PASS'),
          'ST:STATUS_OUTSIDE_VOCABULARY':dict(status='INCOMPLETE',status_outside_vocabulary='OK'),
          'ST:RESULT_NOT_A_DICT':dict(status='INCOMPLETE',error='AUDITOR_CASE_RESULT_NOT_A_DICT'),
          'ST:PUBLIC_COMMIT_SECOND_CONNECTION':dict(status='INCOMPLETE',public_schema_unchanged=False),
          'ST:ERP_COMMIT_SECOND_CONNECTION':dict(status='INCOMPLETE',full_boundary_restored=False),
          'ST:ADVISORY_LOCK_LEFT':dict(status='INCOMPLETE',advisory_locks=1),
          'ST:SECOND_SESSION_LEFT_OPEN':dict(status='INCOMPLETE',other_sessions=1),
          'ST:DUPLICATE_ID_HELPER':dict(status='PASS')}
CLEAN=dict(status_outside_vocabulary=None,error=None,public_schema_unchanged=True,full_boundary_restored=True,
           advisory_locks=0,other_sessions=0)


def observed(row):
    leaks=row.get('session_leaks') or {}
    return dict(status=row.get('status'),status_outside_vocabulary=row.get('status_outside_vocabulary'),error=row.get('error'),
                public_schema_unchanged=row.get('public_schema_unchanged'),full_boundary_restored=row.get('full_boundary_restored'),
                advisory_locks=leaks.get('advisory_locks'),other_sessions=len(leaks.get('other_sessions') or []))


def check(cases):
    """Per planned case: expected vs observed detectors; ok only when they are equal."""
    verdict={}
    for key,want in EXPECTED.items():
        expect={**CLEAN,**want};got=observed((cases or {}).get(key) or {})
        verdict[key]=dict(ok=got==expect,expected=expect,observed=got)
    return verdict


def cases(cur,today):
    admin=awp.boundary.ADMIN

    def public_commit():
        with psycopg.connect(admin,autocommit=True) as other:
            other.execute('create table if not exists public.cp6_runner_selftest(x integer)')
            other.execute('insert into public.cp6_runner_selftest values(1)')
        return dict(status='PASS')

    def erp_commit():
        with psycopg.connect(admin,autocommit=True) as other:
            other.execute("insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason) "
                          "values('cp6_runner_selftest',gen_random_uuid(),'INSERT','{}'::jsonb,null,'auditor runner self-test')")
        return dict(status='PASS')

    def advisory():
        cur.execute('select pg_advisory_lock(424242)')
        return dict(status='PASS')

    def session():
        LEAKED.append(psycopg.connect(admin))
        return dict(status='PASS')

    def duplicates():
        ok=runner.duplicate_ids(['A','B','A','C','C'])==['A','C'] and runner.duplicate_ids(['A','B'])==[]
        return dict(status='PASS' if ok else 'FAIL')

    return [('ST:CLEAN',lambda:dict(status='PASS')),
            ('ST:STATUS_OUTSIDE_VOCABULARY',lambda:dict(status='OK')),
            ('ST:RESULT_NOT_A_DICT',lambda:'PASS'),
            ('ST:PUBLIC_COMMIT_SECOND_CONNECTION',public_commit),
            ('ST:ERP_COMMIT_SECOND_CONNECTION',erp_commit),
            ('ST:ADVISORY_LOCK_LEFT',advisory),
            ('ST:SECOND_SESSION_LEFT_OPEN',session),
            ('ST:DUPLICATE_ID_HELPER',duplicates)]
