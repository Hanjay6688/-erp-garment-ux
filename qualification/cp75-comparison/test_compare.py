"""The cross-path reader must preserve all six comparisons even when generated identities differ."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from compare import business, compare, OLD, TARGET

EXPECTED = json.loads(Path(__file__).with_name("case-values.json").read_text())
H = lambda value: hashlib.sha256(value.encode()).hexdigest()


def history(prefix):
    summary, part = H(prefix+"summary"),H(prefix+"section")
    supplier = EXPECTED["supplier_correction"]
    sales = []
    for label in ("a","b"):
        invoice=deepcopy(EXPECTED["last_20_pcs"][label])
        invoice["allocations"]=[[prefix+"lot",invoice["sold"],6]]
        sales.append(invoice)
    payments = [prefix+str(n) for n in range(27)]
    return {"accounts_payable":{"AP":{"paid":supplier["paid_after"],"remaining":supplier["payable_after"]},
                "cash_delta":supplier["cash_delta_after"],"history_pages":[payments[:25],payments[25:]],
                "selected_id":payments[25],"replacement":payments[26],"original_journal":prefix+"old-journal",
                "inverse":prefix+"reverse-journal","original_status":"REVERSED","all_stock_and_cost_same":True},
            "sales":sales,"available":0,"draft":"SAVED","draft_id":prefix+"draft","job_id":prefix+"job",
            "snapshot_id":prefix+"snapshot","stored_snapshot":H(prefix+"snapshot"),"snapshot_identity":H(prefix+"id"),
            "page_count":2,"planner_values":{"fg":"15","wip":"40","need":"85","capacity":"60","selected":"2"},
            "published":{"id":prefix+"publication","summary":summary,"sections":[part],"hash":H(summary+"\n"+part)},
            "role_access":{"matrix":{"OWNER":{"own_report":"READ","foreign_report":"42501"},
                                   "ADMIN":{"foreign_report":"42501"},"KEUANGAN":{"foreign_report":"42501"}},
                           "active_roles":3,"granted_pairs":120,"active_role_grants_sha256":H("grant rows")},
            "foreign_report":{"sqlstate":"42501","reason":"CP7_REPORT_UNAVAILABLE"}}


class EvidenceComparison(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.clean,self.upgrade=(self.root/n for n in ("clean","upgrade"))
        self.clean.mkdir()
        self.upgrade.mkdir()
        self.c,self.u=history("C-"),history("U-")
        self.files={
            (self.clean,"factory-posted"):{"origin":"parser example","target":TARGET,"history":self.c},
            (self.clean,"factory-restored"):{"full25":{"sha256":TARGET,"groups":25},"history_equal":True,
                                             "raw_state_equal":True,"physical_sha256":H("clean archive")},
            (self.upgrade,"upgrade-before"):{"seal":OLD,"rows_sequences":{"erp.sales":[2,H("rows")]},"history":deepcopy(self.u)},
            (self.upgrade,"upgrade-after"):{"seal":TARGET,"rows_sequences":{"erp.sales":[2,H("rows")]},"history":deepcopy(self.u),
                                             "changed_rows_or_sequences":[],"history_equal":True},
            (self.upgrade,"upgrade-restored"):{"origin_seal":OLD,"all_rows_sequences_equal":True,"history_equal":True,
                                                "physical_sha256":H("old archive"),"history":deepcopy(self.u)}}

    def run_compare(self, **catalogue):
        for (folder,name),value in self.files.items():
            (folder/(name+".json")).write_text(json.dumps(value))
        return compare(self.clean,self.upgrade,**catalogue)

    def test_distinct_generated_ids_keep_ledger_and_links(self):
        self.assertTrue(all(self.run_compare()["six_areas"].values()))
        self.assertNotEqual(self.c["published"]["hash"],self.u["published"]["hash"])

    def test_incorrect_cash_amount(self):
        self.c["accounts_payable"]["cash_delta"]="-256"
        with self.assertRaises(ValueError): self.run_compare()

    def test_missing_units(self):
        self.c["available"]=1
        with self.assertRaises(ValueError): self.run_compare()

    def test_cost_per_allocation(self):
        self.c["sales"][1]["allocations"][0][2]=7
        self.assertFalse(self.run_compare()["six_areas"]["hpp"])

    def test_unlinked_supplier_replacement(self):
        self.c["accounts_payable"]["replacement"]="unknown"
        with self.assertRaises(ValueError): self.run_compare()

    def test_stored_report_corruption(self):
        self.c["published"]["sections"][0]=H("changed")
        with self.assertRaises(ValueError): self.run_compare()

    def test_changed_role_grants(self):
        self.c["role_access"]["active_role_grants_sha256"]=H("different")
        self.assertFalse(self.run_compare()["six_areas"]["hak_akses"])

    def test_changed_upgrade_history_uuid(self):
        self.files[(self.upgrade,"upgrade-after")]["history"]["draft_id"]="other"
        with self.assertRaises(ValueError): self.run_compare()

    def test_missing_physical_restore(self):
        self.files[(self.clean,"factory-restored")]["raw_state_equal"]=False
        with self.assertRaises(ValueError): self.run_compare()

    def test_archived_identity_stays_mandatory_on_the_original_path(self):
        alternate=H("a reconstructed target")
        self.files[self.clean,"factory-posted"]["target"]=alternate
        self.files[self.clean,"factory-restored"]["full25"]["sha256"]=alternate
        self.files[self.upgrade,"upgrade-after"]["seal"]=alternate
        with self.assertRaisesRegex(ValueError,"Versions or catalogue differ"):
            self.run_compare()
        observed=self.run_compare(target=alternate)
        self.assertEqual(observed["target"],alternate)
        self.assertTrue(all(observed["six_areas"].values()))

    def test_reconstructed_target_requires_matching_physical_recovery(self):
        alternate=H("a reconstructed target")
        self.files[self.clean,"factory-posted"]["target"]=alternate
        self.files[self.upgrade,"upgrade-after"]["seal"]=alternate
        with self.assertRaisesRegex(ValueError,"Versions or catalogue differ"):
            self.run_compare(target=alternate)
