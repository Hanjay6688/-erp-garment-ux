"""Independent economic examples. These are modeled controls, never ERP credit."""
from copy import deepcopy
from decimal import Decimal as D
from fractions import Fraction as F
import json
import unittest
from oracle import Model,cents

A=('A','WH1','GRADE_A');B=('B','WH1','GRADE_A');C=('C','WH1','GRADE_A')
B2=('B','WH2','GRADE_A')


def example():
    m=Model();m.add_root('ten',A,2,10);m.add_root('thirty',A,2,30);m.add_root('fifty',B,1,50)
    m.convert('first',A,B,1,[('extra',1,10,None)])
    return m


def amounts(m,product):
    row=m.books()[('NONPO',product)]
    return tuple(row[k]for k in ('HPP','FG','COGS','residual'))


class EconomicExamples(unittest.TestCase):
    def check(self,m):
        self.assertEqual(m.conservation()['actual_ERP_cases'],0)

    def refusal(self,m,operation,reason):
        before=deepcopy(m.__dict__)
        with self.assertRaisesRegex(ValueError,reason):operation()
        self.assertEqual(m.__dict__,before,'Refusal must have no modeled state effects')
        self.check(m)

    def test_original_70_plus_2_regression(self):
        m=example();old=m.facts;m.revalue_cost('extra',2)
        self.assertEqual(amounts(m,'A'),(60,60,0,0))
        self.assertEqual(amounts(m,'B'),(72,72,0,0))
        self.assertEqual(m.pool(B).quantity,2);self.assertEqual(m.facts,old);self.check(m)

    def test_late_invoice_changes_cost_without_new_stock(self):
        m=example();m.revalue_cost('extra',2);m.revalue_cost('extra',3)
        self.assertEqual(amounts(m,'B'),(73,73,0,0));self.assertEqual(m.pool(B).quantity,2);self.check(m)

    def test_sale_before_cost_exists_still_owns_late_invoice(self):
        m=example();posted=m.sell('sale',B,1);m.revalue_cost('extra',2)
        self.assertEqual(posted.booked,35);self.assertEqual(amounts(m,'B'),(72,36,36,0))
        self.assertEqual(dict(posted.bundle.costs),{'extra':F(1,2)});self.check(m)

    def test_descendant_before_cost_exists_still_owns_late_invoice(self):
        m=example();m.convert('second',B,C,1,[('descendant_extra',1,10,None)])
        m.revalue_cost('extra',2);m.revalue_cost('descendant_extra',3)
        self.assertEqual(amounts(m,'B'),(36,36,0,0));self.assertEqual(amounts(m,'C'),(39,39,0,0));self.check(m)

    def test_sold_descendant_cost_then_inverse_legitimate(self):
        m=example();m.convert('second',B,C,1,[('descendant_extra',1,10,None)])
        sale=m.sell('sale',C,1);m.revalue_cost('extra',2);m.revalue_cost('descendant_extra',3)
        self.assertEqual(amounts(m,'C'),(39,0,39,0));self.assertEqual(sale.booked,35)
        m.inverse_sale('undo_sale','sale');m.revalue_cost('descendant_extra',0,dependency_open=False)
        m.inverse_conversion('undo_second','second')
        self.assertEqual(amounts(m,'B'),(72,72,0,0));self.check(m)

    def test_partial_returns_recost_and_other_warehouse(self):
        m=example();sale=m.sell('sale',B,2);m.revalue_cost('extra',2)
        first=m.return_sale('return_one','sale',1,B2);m.revalue_cost('extra',4)
        second=m.return_sale('return_two','sale',1)
        self.assertEqual((sale.booked,first.booked,second.booked),(70,36,37))
        self.assertEqual((m.value(m.pool(B)),m.value(m.pool(B2))),(37,37))
        self.assertEqual(amounts(m,'B'),(74,74,0,0));self.check(m)

    def test_fractional_scope_cents_survive_earlier_inverse(self):
        m=Model();m.add_root('root',A,3,F(10,3));m.convert('convert',A,B,3,[('cost',3,10,None)])
        m.sell('sale',B,3);m.revalue_cost('cost',F(1,100))
        first=m.return_sale('first','sale',1);second=m.return_sale('second','sale',1)
        self.assertEqual((first.booked,second.booked),(D('3.34'),D('3.33')))
        m.inverse_return('undo_first','first');replacement=m.return_sale('replacement','sale',1)
        self.assertEqual(replacement.booked,D('3.33'))
        m.return_sale('last','sale',1);self.assertEqual(amounts(m,'B'),(D('10.01'),D('10.01'),0,0));self.check(m)

    def test_base_and_extra_recost_independent(self):
        m=example();m.sell('sale',B,1);m.revalue_base('ten',20);m.revalue_cost('extra',3)
        self.assertEqual(amounts(m,'A'),(75,75,0,0));self.assertEqual(amounts(m,'B'),(78,39,39,0));self.check(m)

    def test_mixed_po_cost_is_attributed_to_its_real_allocation(self):
        m=Model();m.add_root('po_root',A,2,10,'PO1');m.add_root('other_root',A,2,30)
        m.convert('convert',A,B,2,[('po_cost',1,10,'PO1'),('other_cost',1,30,None)])
        m.sell('sale',B,1);m.revalue_cost('po_cost',4);m.revalue_cost('other_cost',6)
        self.assertEqual(m.books()[('PO','PO1')],dict(HPP=24,FG=17,COGS=7,residual=0))
        self.assertEqual(amounts(m,'A'),(30,30,0,0));self.assertEqual(amounts(m,'B'),(36,18,18,0));self.check(m)

    def test_multiple_physical_children_have_separate_zero_cost_roots(self):
        m=Model();m.add_root('root',A,4,20)
        m.convert('convert',A,B,3,[('first_child',1,20,None),('second_child',2,40,None)])
        m.sell('sale',B,1);m.revalue_cost('first_child',3);m.revalue_cost('second_child',6)
        self.assertEqual(amounts(m,'B'),(69,46,23,0));self.assertEqual(m.pool(B).quantity,2);self.check(m)

    def test_native_recovery_limit_is_not_inflated_by_average(self):
        m=example();self.refusal(m,lambda:m.revalue_cost('extra',-11),'UNCHANGED_NATIVE_FIRST_PART')
        m.revalue_cost('extra',-10);self.assertEqual(amounts(m,'B'),(60,60,0,0));self.check(m)

    def test_positive_native_value_cannot_make_economic_pool_negative(self):
        m=Model();m.add_root('cheap',A,9,1);m.add_root('expensive',A,1,100)
        m.convert('convert',A,B,1,[('cost',1,100,None)])
        self.refusal(m,lambda:m.revalue_cost('cost',-20),'NEGATIVE_POOL_VALUE')

    def test_inverse_requires_closed_native_cost_document(self):
        m=example();m.revalue_cost('extra',0,dependency_open=True)
        self.refusal(m,lambda:m.inverse_conversion('undo','first'),'OPEN_NATIVE_COST_DEPENDENCY')
        m.revalue_cost('extra',0,dependency_open=False);m.inverse_conversion('undo','first')
        self.assertEqual(amounts(m,'A'),(80,80,0,0));self.assertEqual(amounts(m,'B'),(50,50,0,0));self.check(m)

    def test_sale_with_live_return_cannot_be_reversed(self):
        m=example();m.sell('sale',B,2);m.return_sale('return','sale',1)
        self.refusal(m,lambda:m.inverse_sale('undo','sale'),'ACTIVE_RETURN_BLOCKS')
        m.inverse_return('undo_return','return');m.inverse_sale('undo_sale','sale');self.check(m)

    def test_duplicate_and_excess_refusals_preserve_every_fact(self):
        m=example();m.sell('sale',B,1)
        self.refusal(m,lambda:m.sell('sale',B,1),'FACT_ID_REUSED')
        self.refusal(m,lambda:m.return_sale('too_many','sale',2),'RETURN_CAPACITY')
        self.refusal(m,lambda:m.return_sale('wrong_product','sale',1,C),'RETURN_PRODUCT_CHANGED')

    def test_half_cents_are_symmetric(self):
        self.assertEqual([cents(F(x,200))for x in (1,-1,3,-3)],list(map(D,['.01','-.01','.02','-.02'])))


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(EconomicExamples)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps(dict(classification='INDEPENDENT_RATIONAL_DESIGN_MODEL_NOT_ERP',cases=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),actual_ERP_cases=0,production_go=False)))
    raise SystemExit(not result.wasSuccessful())
