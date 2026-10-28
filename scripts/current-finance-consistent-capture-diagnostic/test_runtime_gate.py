from copy import deepcopy
import unittest
import patch


class RuntimeEvidenceRequired(unittest.TestCase):
    def proof(self):
        return dict(status='INCOMPLETE',error='ASSIGNED_TRANSACTION_MUST_NOT_SEAL_MIXED_BOOK',
            unsafe_ready_observed=True,mixed_signature_confirmed=True,observed_report_snapshot=None,
            source_commit_after_early_chunks=True,
            installed_baseline_restoration=dict(all22_all_rows_all_sequences_roles_exact=True,
                complete_database_dump_restored=True))

    def test_no_candidate_before_actual_first_baseline_and_full_restore(self):
        proof=self.proof();patch.require_actual_baseline(proof)
        for key in proof:
            changed=deepcopy(proof);del changed[key]
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'ACTUAL_NULL_SNAPSHOT_COUNTEREXAMPLE_REQUIRED'):
                patch.require_actual_baseline(changed)
        for changed in (None,{},dict(proof,status='PASS'),dict(proof,observed_report_snapshot='1:2:')):
            with self.assertRaisesRegex(ValueError,'ACTUAL_NULL_SNAPSHOT_COUNTEREXAMPLE_REQUIRED'):
                patch.require_actual_baseline(changed)


if __name__=='__main__':unittest.main()
