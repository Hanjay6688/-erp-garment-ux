"""Thirteen unchanged Native finance cases for the composed readonly reader.

These are qualification inputs, not an executed result. The eight original
report cases retain independent expected ledger/HPP amounts and actual Native
close/reopen fixtures. The five public staged cases retain the ordinary 8s
limit, exact replay, source-change refusal and current-access checks.
"""
from hashlib import sha256
from pathlib import Path
import importlib.util
import json

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
REPORT_IDS = tuple('P13_REPORT_' + name for name in (
    'LEDGER_LIFECYCLE', 'EXACT_LARGE', 'QUERY', 'ACCESS',
    'FILED_LATE_CORRECTION', 'FILED_UNCHANGED_CONTROL', 'FILING_PAGES',
    'READ_ONLY_PRIVATE'))
PUBLIC_IDS = tuple('OW12_FROZEN_PUBLIC_FINANCE_' + name for name in (
    'REQUEST_EXACT_ONCE', 'OPERATIONAL_FIRST_OFFICIAL_FINANCE',
    'CHANGED_BOOK_REFUSED', 'DEFERRED_NO_CAPTURE', 'CURRENT_FINANCE_ACCESS'))
IDS = REPORT_IDS + PUBLIC_IDS


def source_binding():
    pins = json.loads((HERE / 'CASE_SOURCES.json').read_bytes())
    if pins['case_ids'] != list(IDS) or len(set(IDS)) != 13:
        raise ValueError('READONLY_FINANCE_CASE_SET_CHANGED')
    for path, digest in pins['files'].items():
        if sha256((REPO / path).read_bytes()).hexdigest() != digest:
            raise ValueError('READONLY_FINANCE_RETAINED_CASE_CHANGED:' + path)
    return dict(case_ids=list(IDS), exact_source_files=pins['files'],
                retained_business_case_bodies_unchanged=True,
                filing_fixture_preparation=pins['fixture_preparation'],
                independent_ledger_and_HPP_expected_amounts=True,
                real_Auth_browser_claim=False, factory3600_claim=False,
                ordinary_staged_call_limit='8s', actual_cases_executed=False)


def runtime():
    import cp7_finance_cases as reports
    path = REPO / 'scripts/current-frozen-public-native-qualification/public_finance_cases.py'
    spec = importlib.util.spec_from_file_location('readonly_composition_public_finance_cases', path)
    public = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(public)
    return reports, public


def cases(cur, today):
    source_binding()
    reports, public = runtime()
    public.source_binding()
    result = reports.cases(cur, today) + public.cases(cur, today)
    if tuple(key for key, _ in result) != IDS:
        raise ValueError('READONLY_FINANCE_ACTUAL_CASE_SET_CHANGED')
    # OW07 correctly blocks old unallocated attendance in this aligned seed.
    # Reuse its existing Native preparation before the three unchanged filing
    # bodies, within their individual strict-group rollback boundaries.
    import cp7_p21_current_chain_rehearsal_probe as chain
    spec = importlib.util.spec_from_file_location('readonly_filing_fixture', HERE / 'filing_fixture.py')
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    return fixture.wrap(result, cur, today, chain.prepare_attendance_pools)
