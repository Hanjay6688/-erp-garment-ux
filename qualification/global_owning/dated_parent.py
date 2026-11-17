"""Install the verified SKU and dated Laundry base in the owning Global cycle."""

from dataclasses import dataclass
from functools import partial

import dated_sku_install
import dated_sku_parent
from sku_progress import before_mandor


@dataclass(frozen=True)
class InstalledParent:
    sku: dict
    dated: dated_sku_install.Installed
    comparison: object
    proof: dict


class OwningParent:
    def __init__(self, sku, provider, credit, sku_catalogue, inputs):
        self.sku = sku
        self.provider = provider
        self.credit = credit
        self.sku_catalogue = sku_catalogue
        self.inputs = inputs
        self._compare_sku = provider._automatic_parent_catalogue

    def install(self, cur):
        provider = self.provider
        with provider.atomic(cur):
            with before_mandor(partial(self.credit.record_baseline, cur)):
                prior = self.sku._sku_install_parent(cur)
            state = self.sku._sku_install_delta(cur, prior)
            self.sku._sku_verify_installed(cur, state)
            before = provider._timezone_snapshot(cur, lock=False)
            self.credit.install_final(cur)

            def verify_base(cursor, value, inputs, fingerprint):
                with self.credit.owning._postgres_reader(cursor):
                    return self._compare_sku(cursor, value, inputs, fingerprint)

            catalogue = provider.capture(cur)
            reviewed = verify_base(cur, catalogue, self.inputs, provider.fingerprint)
            dated = dated_sku_install.install_delta(cur, provider, reviewed)
            if dated.data != before:
                raise ValueError('GLOBAL_OWNING_CREDIT_SEAL_CHANGED_ROWS_OR_SEQUENCES')
            compare = dated_sku_parent.prepare(verify_base, self.sku_catalogue, provider.all22, dated.installed_identity)
            composite = compare(cur, dated.after, self.inputs, provider.fingerprint)

        return InstalledParent(state, dated, compare, composite)

    def verify_after_unused_global_inverse(self, cur, installed, expected_data):
        provider = self.provider
        current = provider.capture(cur)
        if current != installed.dated.after or provider._timezone_snapshot(cur, lock=False) != expected_data:
            raise ValueError('GLOBAL_OWNING_UNUSED_GLOBAL_INVERSE_CHANGED_DATED_PARENT')
        return installed.comparison(cur, current, self.inputs, provider.fingerprint)
