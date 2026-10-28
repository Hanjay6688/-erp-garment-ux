"""Retain each first failure; run the next case only after complete restoration."""
import traceback


def exercise(cases, run, restore, report):
    results = report.setdefault('cases', {})
    if not cases or len({key for key, _ in cases}) != len(cases):
        raise ValueError('FOLLOWUP_CASE_IDENTITIES_REQUIRED')
    for key, operation in cases:
        result = results.setdefault(key, {'status': 'INCOMPLETE'})
        if result != {'status': 'INCOMPLETE'}:
            raise ValueError('FOLLOWUP_FIRST_RESULT_ALREADY_EXISTS')
        print('FOLLOWUP_CASE_START ' + key, flush=True)
        try:
            run(operation, result)
            if result.get('status') != 'PASS':
                raise AssertionError('FOLLOWUP_CASE_DID_NOT_PROVE_PASS')
        except Exception as error:
            result.update(status='INCOMPLETE', error=str(error), traceback=traceback.format_exc())
        finally:
            try:
                proof = restore()
                if proof.get('all22_all_rows_all_sequences_roles_exact') is not True:
                    raise ValueError('FOLLOWUP_RESTORE_PROOF_INCOMPLETE')
                result['installed_baseline_restoration'] = proof
            except Exception as error:
                result.update(status='INCOMPLETE', restore_error=str(error),
                              restore_traceback=traceback.format_exc())
                # A broken baseline must never become the next case's fixture.
                raise
        print('FOLLOWUP_CASE_END ' + key + ' ' + result['status'], flush=True)
    report['all_cases_pass'] = all(value['status'] == 'PASS' for value in results.values())
    if not report['all_cases_pass']:
        raise AssertionError('FOLLOWUP_FIRST_FAILURES_RETAINED')
    return results
