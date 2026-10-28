"""Guard the observed Native varchar(50) fixture failure without a DB double."""
from pathlib import Path
import ast,subprocess,unittest

ROOT=Path(__file__).resolve().parents[2]
PATH='scripts/cp7_vendor_receivable/cases.py'
FIRST='54b786f3e38ba41d362a23fd75fb0d5c0520150d'


def labels(text):
    provenance=next(n for n in ast.walk(ast.parse(text))if isinstance(n,ast.FunctionDef)and n.name=='provenance')
    plans=next(n.value for n in provenance.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='plans'for t in n.targets))
    names=[ast.literal_eval(n.elts[0])for n in plans.elts]
    journal=next(n for n in ast.walk(provenance)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and isinstance(n.func.value,ast.Name)and n.func.value.id=='journals'and n.func.attr=='journal')
    prefix=ast.literal_eval(journal.args[3].left)
    return names,[prefix+name for name in names]


class FixtureLabelControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=subprocess.check_output(['git','-C',str(ROOT),'show',FIRST+':'+PATH]).decode()
        cls.after=(ROOT/PATH).read_text()

    def test_exactly_one_fixture_prefix_changes(self):
        old="'OW08b explicit unrelated sensitivity '+name";new="'OW08b_AR_SENS_'+name"
        self.assertEqual(self.before.count(old),1)
        self.assertEqual(self.after,self.before.replace(old,new,1))

    def test_all_four_controls_fit_native_source_type(self):
        names,values=labels(self.after)
        self.assertEqual(names,['SAME_VENDOR_ZERO_NET','NO_VENDOR_NONZERO','NO_VENDOR_ZERO_NET','UNREGISTERED_VENDOR_ZERO_NET'])
        self.assertEqual(len(set(values)),4)
        self.assertTrue(all(0<len(value)<=50 for value in values),values)

    def test_observed_first_labels_really_exceeded_limit(self):
        names,values=labels(self.before)
        self.assertEqual(names,labels(self.after)[0])
        self.assertTrue(all(len(value)>50 for value in values),values)


if __name__=='__main__':unittest.main()
