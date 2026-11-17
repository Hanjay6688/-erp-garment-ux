"""Extend the closed Global lifecycle with the exact dated child comparator."""

from .dated_parent import OwningParent
from .lifecycle import INVERSE_FLAGS, Installed, Lifecycle, exact_fields, existing_native_usage
from .package_routes import require
from scope_witness import capture, compare, outside_state
from snapshot_prerequisites import observe as observe_prerequisites


class DatedLifecycle(Lifecycle):
    def __init__(self, sku, provider, parent_raw, profile_raw, fixtures, *, credit, sku_catalogue,
                 inputs, foundation):
        super().__init__(sku, provider, parent_raw, profile_raw, fixtures)
        self.parent = OwningParent(sku, provider, credit, sku_catalogue, inputs)
        self.foundation = foundation
        self.relations = inputs['relations']

    def bootstrap(self, cur, report):
        before = capture(cur, expected_database='cp6_rollback', mode='transaction')
        self.foundation.bootstrap(cur, report)
        after = capture(cur, expected_database='cp6_rollback', mode='transaction')
        counters = compare(before, after, self.relations)
        foundation = report['preseal_foundation']
        delta = outside_state(foundation['before_rows_and_sequences'], foundation['after_rows_and_sequences'],
                              self.relations)
        foundation['relation_scope'] = dict(counters, **delta)
        require(not any(counters[key] for key in ('outside_write_attempts', 'relation_identity_changes',
                                                  'unexpected_temporary_relations'))
                and not delta['changed_tables_outside_scope'] and before.temp_namespace == after.temp_namespace == 0,
                'GLOBAL_FOUNDATION_WRITER_RELATION_SCOPE_REFUSED')
        return foundation['after_rows_and_sequences']

    def install_cycle(self, cur, timings, report):
        self.foundation.initialize(cur, report)
        measure = self.sku.measured
        installed = measure(timings, 'ACTUAL_SKU_DATED_LAUNDRY_PARENT_INSTALL', self.parent.install, cur)
        report['verified_SKU_and_dated_Laundry_before_Global'] = installed.proof
        existing_native_usage(cur)
        report['supplier_accessory_prerequisites'] = exact_fields(observe_prerequisites(cur), {'status': 'PASS'},
                                                                 'GLOBAL_SUPPLIER_ACCESSORY_PREREQUISITES_REFUSED')
        data = measure(timings, 'PRESEAL_FIXTURE_FOUNDATION', self.bootstrap, cur, report)
        # owning.runtime supplies a private provider for this attempt.
        original_comparison = self.provider._automatic_parent_catalogue
        self.provider._automatic_parent_catalogue = installed.comparison
        try:
            first = measure(timings, 'FIRST_GLOBAL_INSTALL', self.provider.install, cur, self.parent_raw, self.profile_raw)
            inverse = measure(timings, 'GLOBAL_UNUSED_INVERSE', self.provider.rollback_preuse, cur, first)
            report['focused_preuse_removal'] = exact_fields(inverse, INVERSE_FLAGS,
                                                            'GLOBAL_CALLER_COMPLETE_UNUSED_INVERSE_REQUIRED')
            report['verified_SKU_and_dated_Laundry_after_Global_unused_inverse'] = measure(
                timings, 'DATED_SKU_VERIFY_AFTER_GLOBAL_UNUSED_INVERSE',
                self.parent.verify_after_unused_global_inverse, cur, installed, data)
            successor = measure(timings, 'SECOND_GLOBAL_INSTALL', self.provider.install, cur,
                                self.parent_raw, self.profile_raw)
        finally:
            self.provider._automatic_parent_catalogue = original_comparison
        return Installed(installed.sku, successor)

    def verify(self, cur, state):
        self.foundation.verify(cur)
        return super().verify(cur, state)
