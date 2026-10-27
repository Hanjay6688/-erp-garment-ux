"""Check Native price input precision before the expensive composed DB run."""
from pathlib import Path
from decimal import Decimal
import ast,re,subprocess,unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FAILED_HEAD='e352901d6975346fa6a099770d179ffc6a59475d'
NAMES={'PRICE','CURRENT_PRICE','PERCENT','PCS','PRICE_PATTERN'}

def extracted(text,include_guard=False):
    nodes=[]
    for node in ast.parse(text).body:
        if isinstance(node,ast.ImportFrom)and node.module=='decimal':nodes.append(node)
        elif isinstance(node,ast.Import)and all(x.name=='re'for x in node.names):nodes.append(node)
        elif isinstance(node,ast.Assign)and len(node.targets)==1 and isinstance(node.targets[0],ast.Name)and node.targets[0].id in NAMES:nodes.append(node)
        elif include_guard and isinstance(node,ast.FunctionDef)and node.name=='fixture_amounts':nodes.append(node)
    values={};exec(compile(ast.Module(body=nodes,type_ignores=[]),'fixture-amounts-only','exec'),values)
    return values

class FixtureMoneyPrecision(unittest.TestCase):
    def setUp(self):self.fixture=extracted((HERE/'price_fixture.py').read_text(),True)
    def test_prices_match_unchanged_native_money_contract(self):
        native=(ROOT/'scripts/cp6_bd_objects_policy.sql').read_text().split('CREATE OR REPLACE FUNCTION erp.bd_amount_v1(',1)[1].split('end;$function$;',1)[0]
        pattern=re.search(r"!~'([^']+)'",native).group(1)
        self.assertEqual(pattern,'^'+self.fixture['PRICE_PATTERN']+'$')
        for name in ['PRICE','CURRENT_PRICE']:self.assertRegex(str(self.fixture[name]),pattern)
        self.assertIn("perform erp.bd_amount_v1(cfg->'price','price',true)",(ROOT/'scripts/cp6_bf_objects_master.sql').read_text())
    def test_exact_failed_e352_input_is_refused_before_database(self):
        text=subprocess.check_output(['git','-C',str(ROOT),'show',FAILED_HEAD+':scripts/current-finance-check-reuse-diagnostic/price_fixture.py'],text=True)
        old=extracted(text)
        self.assertEqual(old['PRICE'],Decimal('20.123456'))
        with self.assertRaisesRegex(ValueError,'FIXTURE_PRICE_REQUIRES_TWO_DECIMALS:legacy'):
            self.fixture['fixture_amounts'](old['PRICE'],old['CURRENT_PRICE'],old['PERCENT'],old['PCS'])
    def test_unit_hpp_keeps_six_decimals_before_posted_value_rounding(self):
        hpp,value=self.fixture['fixture_amounts']()
        self.assertEqual(hpp,Decimal('2.483935'))
        self.assertEqual(value,Decimal('24.84'))
        self.assertNotEqual(value,hpp.quantize(Decimal('.01'))*self.fixture['PCS'])
    def test_malformed_current_price_percentage_or_quantity_is_refused(self):
        examples=[{'current_price':Decimal('25.990')},{'price':Decimal('20.125')},
                  {'percent':Decimal('12.34567')},{'pcs':10.0}]
        for example in examples:
            with self.subTest(example=example),self.assertRaises(ValueError):self.fixture['fixture_amounts'](**example)

if __name__=='__main__':unittest.main()
