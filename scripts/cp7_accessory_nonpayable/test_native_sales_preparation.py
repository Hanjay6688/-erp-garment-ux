"""Independent cent/conservation and closed-parent controls, no ERP credit."""
from datetime import date
from decimal import Decimal
import unittest
from . import native_sales_cases as sales

class NativeSalesPreparationControls(unittest.TestCase):
    def test_finished_cost_correction_has_independent_sold_and_unsold_shares(self):
        before=dict(WIP='0',FG_INVENTORY='60',COGS='40')
        self.assertEqual({k:Decimal(v)for k,v in sales.require_cost_delta(before,dict(WIP='0',FG_INVENTORY='54',COGS='36'),'-10').items()},
            dict(WIP=Decimal(0),FG_INVENTORY=Decimal(-6),COGS=Decimal(-4)))
        self.assertEqual({k:Decimal(v)for k,v in sales.require_cost_delta(before,dict(WIP='0',FG_INVENTORY='69',COGS='46'),'15').items()},
            dict(WIP=Decimal(0),FG_INVENTORY=Decimal(9),COGS=Decimal(6)))

    def test_wrong_sold_share_wip_residue_or_unbalanced_delta_refuse(self):
        before=dict(WIP='0',FG_INVENTORY='60',COGS='40')
        for after in(dict(WIP='0',FG_INVENTORY='66',COGS='49'),dict(WIP='1',FG_INVENTORY='68',COGS='46'),
                     dict(WIP='0',FG_INVENTORY='69',COGS='47')):
            with self.subTest(after=after),self.assertRaises(ValueError):sales.require_cost_delta(before,after,'15')

    def test_sales_case_factory_refuses_before_cursor_or_domain_import(self):
        with self.assertRaisesRegex(ValueError,'ACTUAL_FREE3_ROOT_INTAKE_PENDING'):
            sales.cases(object(),date(2026,11,1),{})

if __name__=='__main__':unittest.main()
