"""Independent monetary expectations, with no SQL or ERP admission credit."""
from copy import deepcopy
from decimal import Decimal as D
from fractions import Fraction as F
import json,unittest
from cent_ownership import CostOwnership


def start(units=1):
    m=CostOwnership();m.origin('origin','cost','B',units,native_floor=-10);return m


class CentExamples(unittest.TestCase):
    def amounts(self,m):return {k:D(v.cents)/100 for k,v in m.cells['cost'].items()}

    def test_later_401_invoice_creates_exactly_201_delta(self):
        m=start();m.price('price2','cost',2);m.transfer('split','cost','B','C',F(1,2))
        before=m.facts;fact=m.price('price401','cost',D('4.01'))
        self.assertEqual(self.amounts(m),{'B':D('2.01'),'C':D('2')})
        self.assertEqual(sum(change[2]for change in fact.changes),201);self.assertEqual(m.facts[:-1],before)

    def test_invoice_before_transfer_keeps_posted_cent_on_noop(self):
        m=start();m.price('price','cost',D('4.01'));m.transfer('split','cost','B','C',F(1,2))
        self.assertEqual(self.amounts(m),{'B':D('2'),'C':D('2.01')})
        before=deepcopy(m.__dict__);self.assertIsNone(m.price('same','cost',D('4.01')))
        self.assertEqual(m.__dict__,before)

    def test_zero_source_clears_all_custody_cents(self):
        m=start();m.price('price','cost',D('.01'));m.transfer('split','cost','B','C',F(1,2));m.price('zero','cost',0)
        self.assertEqual(self.amounts(m),{'B':D(0),'C':D(0)})

    def test_inverse_takes_current_value_and_preserves_old_transfer(self):
        m=start();m.price('price','cost',2);posted=m.transfer('split','cost','B','C',F(1,2))
        m.price('new','cost',D('4.01'));m.transfer('inverse','cost','C','B',F(1,2))
        self.assertEqual(self.amounts(m),{'B':D('4.01'),'C':D(0)})
        self.assertEqual(posted.changes,(('B',F(-1,2),-100),('C',F(1,2),100)))

    def test_repeated_transfers_use_current_remainder(self):
        m=start(3);m.price('price','cost',10)
        m.transfer('first','cost','B','C',1);m.transfer('second','cost','B','D',1);m.transfer('last','cost','B','E',1)
        self.assertEqual(self.amounts(m),{'B':D(0),'C':D('3.33'),'D':D('3.34'),'E':D('3.33')})

    def test_signed_source_and_inventory_cogs_always_conserve(self):
        m=start(3);m.transfer('one','cost','B','C',1);m.transfer('two','cost','B','D',1)
        for integer in range(-201,202):
            m.price('source'+str(integer),'cost',D(integer)/100)
            self.assertEqual(sum(c.cents for c in m.cells['cost'].values()),integer)
            for scope in m.cells['cost']:
                total,fg,cogs=m.buckets('cost',scope,F(1,2));self.assertEqual(fg+cogs,total)
            before=deepcopy(m.__dict__);m.price('nochange','cost',D(integer)/100);self.assertEqual(m.__dict__,before)

    def test_recovery_floor_and_capacity_refusals_are_atomic(self):
        m=start();before=deepcopy(m.__dict__)
        for operation,reason in[(lambda:m.price('bad','cost',-11),'RECOVERY_FLOOR'),
            (lambda:m.transfer('bad','cost','B','C',2),'CUSTODY_CAPACITY'),
            (lambda:m.price('bad','cost',D('.001')),'EXACT_CENTS')]:
            with self.assertRaisesRegex(ValueError,reason):operation()
            self.assertEqual(m.__dict__,before)


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CentExamples))
    print(json.dumps({'classification':'INDEPENDENT_CENT_CUSTODY_MODEL_NOT_PRODUCT_SQL','cases':result.testsRun,
        'failures':len(result.failures),'errors':len(result.errors),'actual_ERP_cases':0,'SQL_fix_implemented':False}))
    raise SystemExit(not result.wasSuccessful())
