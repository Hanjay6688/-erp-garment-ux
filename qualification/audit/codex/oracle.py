"""Independent literal P20 oracle, frozen before the auditor CI execution."""
from decimal import Decimal
import json
from pathlib import Path

MANIFEST = json.loads(Path(__file__).with_name('p20_a752_manifest.json').read_text())
EXPECTED = {case['id']: case['expected'] for case in MANIFEST['cases']}

def require(ok, code):
    if not ok:
        raise AssertionError(code)

def compare(cases):
    require(MANIFEST['candidate_sha'] == 'a752459a0a8baf1920d0e6d1c1fba6f4ef14af8d',
            'AUDITOR_P20_CANDIDATE_CHANGED')
    required = ('P20_OW07_REPORT_EXPENSE','P20_OW07_REPORT_CARRY',
                'P20_CASH_OW09_03','P20_CARRY_CASH_04',
                'P20_CARRY_DATE_05','P20_CARRY_CLOSED_06',
                'P20_AUTH_CASH_01_02','P20_SALE_SERIES_BROWSER','P20_OW07_POSITIVE_CLOSE',
                'P19P_FG_INCREASE_NEED_CHANGED','P19P_WIP_INCREASE_NEED_CHANGED',
                'P19P_APPLY_AFTER_UNRELATED_CHANGE','P20_PLANNER_CURRENT_CUTTING_PERMISSION')
    require(set(cases) == set(required) and all(cases[key].get('status') == 'PASS' for key in required),
            'AUDITOR_P20_CASE_SET_OR_STATUS')
    series = cases['P20_SALE_SERIES_BROWSER']
    expect = EXPECTED['AUD-P20-SERIES']
    require(series['series_counts'] == [2,2] and series['full_lifecycle'] == ['CREATE','EDIT','POST']
            and series['sale_hpp'] == int(Decimal(expect['hpp']))
            and [row[2] for row in series['stock']['posted']] == expect['post_stock_pcs_by_series_size']
            and series['replay'] is True and series['inverse'] is True,
            'AUDITOR_P20_SERIES_COUNTS_STOCK_OR_HPP')
    expected_journal = dict(AR_CUSTOMER=620, SALES_REVENUE=-620, COGS=250, FG_INVENTORY=-250)
    require(series['journal'] == expected_journal, 'AUDITOR_P20_SERIES_JOURNAL_BY_ACCOUNT')
    credit = cases['P20_CARRY_CASH_04']
    expect = EXPECTED['AUD-P20-CREDIT']
    require(credit['before_AR'] == expect['receivable_before']
            and credit['after_AR'] == expect['receivable_after']
            and credit['replacement_net'] == expect['replacement_note']
            and credit['carried_credit'] == expect['credit']
            and credit['cash_delta'] == expect['cash_delta']
            and credit['stale_refusal']['sqlstate'] == expect['stale_error_sqlstate']
            and credit['stale_refusal']['message'] == expect['stale_error_code']
            and credit['exact_uuid_replay'] is True
            and credit['real_auth_owner_profile'] is True
            and credit['real_auth_replacement_money'] == dict(net_total=expect['replacement_note'],
                    paid_total=expect['credit'], open_balance=expect['receivable_after'])
            and credit['real_auth_cash_matches_pretransfer'] is True,
            'AUDITOR_P20_CREDIT_RECEIVABLE_OR_ATOMICITY')
    cash = cases['P20_CASH_OW09_03']
    expect = EXPECTED['AUD-P20-CASH']
    require(cash['fixture_opening_delta'] == expect['opening']
            and cash['receipts'] == expect['inflow']
            and cash['outflow'] == expect['outflow']
            and cash['closing_delta'] == expect['balance']
            and cash['matched_pages'] == expect['page_lengths']
            and cash['post_transfer_closing_delta'] == expect['balance']
            and cash['draft_99_excluded'] is True
            and cash['inactive_alias_not_double_counted'] is True,
            'AUDITOR_P20_CASH_BOOK_OR_PAGINATION')
    auth = cases['P20_AUTH_CASH_01_02']
    require(auth['cash_pages'] == expect['page_lengths']
            and auth['old_cash'] == expect['revoked_current_session_http']
            and auth['old_report'] == [expect['revoked_current_session_http'],expect['comparison_http']]
            and auth['fresh_cash'] == expect['revoked_new_session_http']
            and auth['fresh_report'] == expect['comparison_http']
            and auth['stale_data_retired'] is True and auth['exact_grant_restored'] is True
            and auth['separate_issuer_sessions'] is True,
            'AUDITOR_P20_CASH_AUTH_OR_UI')
    for choice, field in (('CARRY','wip_inventory'),('EXPENSE','operating_and_other_expense')):
        case = cases['P20_OW07_REPORT_' + choice]
        expect = EXPECTED['AUD-P20-OW07']
        require(case['choice'] == choice and case['amount'] == expect['approved_absence']
                and case['amounts'] == {'liabilities':expect['carry_payable'],field:expect['approved_absence']}
                and case['pending_choice_blocks_report_and_close'] is True
                and case['official_report_matches_close'] is True
                and case['choice_replay'] is True,
                'AUDITOR_P20_OW07_' + choice)
    close = cases['P20_OW07_POSITIVE_CLOSE']
    require(close['source_choice'] == 'EXPENSE' and close['amount'] == EXPECTED['AUD-P20-OW07']['approved_absence']
            and close['initial_ready'] is True and close['pending_choice_blocked'] is True
            and close['ready_after_choice'] is True and close['filing_delta'] == 1
            and close['same_uuid_replay_no_extra_filing'] is True
            and close['post_close_correction_refused'] is True
            and close['gl_and_stock_unchanged_by_close'] is True
            and close['rollback_boundary_verified'] is True,
            'AUDITOR_P20_OW07_POSITIVE_CLOSE')
    for case_id in required[9:]:
        case, expect = cases[case_id], EXPECTED[case_id]
        require(all(json.dumps(case.get(key), sort_keys=True) == json.dumps(value, sort_keys=True)
                    for key, value in expect.items()),
                'AUDITOR_P20_PLANNER_EXPECTED_' + case_id)
        if case_id.startswith('P19P_'):
            require(case.get('rollback_boundary_verified') is True,
                    'AUDITOR_P20_PLANNER_ROLLBACK_MISSING')
    return dict(status='PASS', case_ids=list(required), oracle_origin='AUDITOR_LITERAL_PRECOMMITTED',
                fixture_origin='RETAINED_WRITER_SYNTHETIC_WITH_INDEPENDENT_EXPECTED',
                positive_close='TESTED_IN_DISPOSABLE_GLOBAL', production_go=False, independent_acceptance=False)
