"""Offline result-gate mutation controls; zero database or ERP credit."""
from copy import deepcopy
import unittest
import matrix


class Matrix(unittest.TestCase):
    def rows(self):
        return [dict(held=h,requested=r,refused=matrix.conflicts(h,r),
            sqlstate='55P03'if matrix.conflicts(h,r)else None,two_actual_backends=True,holder_lock_observed=True)
            for h in matrix.MODES for r in('SHARE','SHARE ROW EXCLUSIVE','EXCLUSIVE')]

    def test_conflicts_symmetric_and_documented_row_share_counterexample(self):
        for a in matrix.MODES:
            for b in matrix.MODES:self.assertEqual(matrix.conflicts(a,b),matrix.conflicts(b,a))
        self.assertFalse(matrix.conflicts('ROW SHARE','SHARE ROW EXCLUSIVE'))
        self.assertTrue(matrix.conflicts('ROW SHARE','EXCLUSIVE'))
        self.assertFalse(matrix.conflicts('ACCESS SHARE','EXCLUSIVE'))

    def test_exact24_and_duplicate_missing_wrong_mode_refuse(self):
        rows=self.rows();self.assertEqual(matrix.complete(rows)['actual_lock_pairs'],24)
        for change in('missing','duplicate','unknown'):
            bad=deepcopy(rows)
            if change=='missing':bad.pop()
            elif change=='duplicate':bad[-1]=deepcopy(bad[0])
            else:bad[-1]['requested']='UNDECLARED'
            with self.subTest(change=change),self.assertRaises(ValueError):matrix.complete(bad)

    def test_each_result_sqlstate_or_real_backend_claim_is_required(self):
        rows=self.rows()
        for i in range(24):
            for key in('refused','sqlstate','two_actual_backends','holder_lock_observed'):
                bad=deepcopy(rows);bad[i][key]='57014'if key=='sqlstate'else not bad[i][key]
                with self.subTest(i=i,key=key),self.assertRaises(ValueError):matrix.complete(bad)


if __name__=='__main__':unittest.main()
