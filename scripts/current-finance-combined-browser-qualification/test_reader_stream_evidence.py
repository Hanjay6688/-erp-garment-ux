from copy import deepcopy
from unittest import TestCase,main
import evidence


def valid_observation():
    stream=dict(status='PASS',old_SQLSTATE='54000',large_rows=1024,
        minimum_large_payload_bytes=307200000,large_streamed_digest=[1024,'a'*64],
        excluded_tables=0,skipped_rows_or_fields=0,ordinary_statement_limits_changed=False)
    for key in ('old_hashes_equal_before_and_after','actual_old_array_limit_reproduced',
        'duplicate_multiplicity_preserved','temporary_regression_fully_removed',
        'ERP_rows_sequences_and_catalog_definitions_unchanged'):stream[key]=True
    guard=dict(old_jsonb_array_text_hash_algorithm_unchanged=True,
        namespace_table_selection_authority_GUC_and_all_sequences_unchanged=True,
        qualified_role_oracles_unchanged=True,excluded_tables_added=0,rows_or_fields_skipped=0)
    opening=dict(private_STABLE_opening_reader=True,original_Native_body_and_metadata_unchanged=True,
        private_HPP_only_one_callee_replaced=True,opening_date_and_HPP_arithmetic_unchanged=True,
        new_public_rpcs=0,broadened_role_privileges=0)
    installed=dict(status='EXACT_COMBINED_CONSISTENT_READERS_ALL22',
        Native_money_stock_HPP_definitions_unchanged=True,new_private_functions=4,
        changed_private_functions=5,opening=opening)
    restored=dict(pre_restore_observation_complete=True)
    price=dict(observed_nonstable_financial_readers={},observed_reader_catalog={
        'cp7_finance.read_opening_physical_at_consistent_v1(uuid,date)':dict(
            volatility='s',owner='postgres',config=['search_path=""'])})
    cases={name:dict(installed_baseline_restoration=deepcopy(restored))for name in evidence.CHILDREN}
    cases['COMBINED_SMALL_PRICE_FACTORY_REPORT_PAIRS']['pairs']={'PRICE_PERCENT':{'combined_reader':price}}
    return dict(exact_streaming_data_validation=stream,streaming_data_source_guard=guard,
        complete_installed_verification=installed),cases


class CorrectedReaderAdmission(TestCase):
    def test_complete_contract_requires_the_actual_large_regression(self):
        value,cases=valid_observation()
        self.assertTrue(evidence.consistent_validation(value,cases)['actual_307MB_exact_hash_regression'])
        for changes in ({'actual_old_array_limit_reproduced':False},{'duplicate_multiplicity_preserved':False},
            {'skipped_rows_or_fields':1},{'ordinary_statement_limits_changed':True},
            {'minimum_large_payload_bytes':307200},{'old_SQLSTATE':'00000'}):
            changed=deepcopy(value);changed['exact_streaming_data_validation'].update(changes)
            with self.subTest(changes=changes),self.assertRaises(AssertionError):
                evidence.consistent_validation(changed,cases)

    def test_failed_observation_or_restore_cannot_be_relabelled(self):
        value,cases=valid_observation()
        for changes in ({'pre_restore_observation_complete':False},{'guard_error':'FIRST_ARRAY_FAILURE'}):
            changed=deepcopy(cases)
            changed['COMBINED_CURRENT_PUBLIC_FACTORY1200X3_ACTUAL_CRON']['installed_baseline_restoration'].update(changes)
            with self.subTest(changes=changes),self.assertRaises(AssertionError):
                evidence.consistent_validation(value,changed)

    def test_observed_native_volatile_reader_still_refuses(self):
        value,cases=valid_observation();changed=deepcopy(cases)
        price=changed['COMBINED_SMALL_PRICE_FACTORY_REPORT_PAIRS']['pairs']['PRICE_PERCENT']['combined_reader']
        price['observed_reader_catalog']['erp.product_opening_physical_at(uuid,date)']={'volatility':'v'}
        with self.assertRaises(AssertionError):evidence.consistent_validation(value,changed)
        changed=deepcopy(cases)
        price=changed['COMBINED_SMALL_PRICE_FACTORY_REPORT_PAIRS']['pairs']['PRICE_PERCENT']['combined_reader']
        price['observed_reader_catalog']['cp7_finance.read_opening_physical_at_consistent_v1(uuid,date)']['volatility']='v'
        with self.assertRaises(AssertionError):evidence.consistent_validation(value,changed)

    def test_native_or_opening_arithmetic_change_cannot_unlock_browser(self):
        value,cases=valid_observation()
        for key in ('original_Native_body_and_metadata_unchanged','opening_date_and_HPP_arithmetic_unchanged'):
            changed=deepcopy(value);changed['complete_installed_verification']['opening'][key]=False
            with self.subTest(key=key),self.assertRaises(AssertionError):
                evidence.consistent_validation(changed,cases)


if __name__=='__main__':main()
