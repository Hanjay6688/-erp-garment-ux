"""Prepare old seed HPP through retained Native facades, inside each case.

No report oracle, monetary expectation, policy or product body is replaced.
The strict group owns the savepoint and verifies complete rollback afterward.
"""
FILING_IDS = frozenset(('P13_REPORT_FILED_LATE_CORRECTION',
                        'P13_REPORT_FILED_UNCHANGED_CONTROL',
                        'P13_REPORT_FILING_PAGES'))


def prepared(operation, cur, today, prepare):
    receipt = prepare(cur, today)
    if receipt.get('status') != 'PASS':
        raise ValueError('READONLY_FILING_NATIVE_HPP_FIXTURE_NOT_READY')
    result = operation()
    return dict(result, fixture_preparation=receipt,
                original_report_case_and_oracles_unchanged=True,
                fixture_preparation_inside_case_savepoint=True)


def wrap(cases, cur, today, prepare):
    if not FILING_IDS.issubset(key for key, _ in cases):
        raise ValueError('READONLY_FILING_CASES_MISSING')
    return [(key, (lambda operation=operation: prepared(operation, cur, today, prepare))
             if key in FILING_IDS else operation) for key, operation in cases]
