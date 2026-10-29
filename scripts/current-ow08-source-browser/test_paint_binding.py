import unittest
from hashlib import sha256
from paint_binding import APPENDS,verify

class PaintSourceBinding(unittest.TestCase):
    def setUp(self):
        self.before={p:('/* base '+p+' */\n').encode()for p in APPENDS}
        self.after={p:self.before[p]+s.encode()for p,s in APPENDS.items()}
        self.rows=[dict(path=p,before_sha256=sha256(self.before[p]).hexdigest(),after_sha256=sha256(self.after[p]).hexdigest(),exact_append=s)for p,s in APPENDS.items()]
    def check(self,changed=None):return verify(self.rows,list(APPENDS)if changed is None else changed,self.before.__getitem__,self.after.__getitem__)
    def test_exact_appends_return_retained_originals(self):self.assertEqual(self.check(),self.before)
    def test_changed_money_rule_before_append_refused(self):
        p='src/initial-import.css';self.after[p]=self.after[p].replace(b'base ',b'changed money rule ')
        with self.assertRaisesRegex(AssertionError,'NOT_EXACT_APPEND'):self.check()
    def test_other_product_file_refused(self):
        with self.assertRaisesRegex(AssertionError,'UNDECLARED_OW08_PRODUCT_CHANGE'):self.check([*APPENDS,'src/LaundryBdPanel.tsx'])
    def test_declared_extra_rule_cannot_expand_overlay(self):
        self.rows[0]['exact_append']+='body { opacity: .1; }'
        with self.assertRaisesRegex(AssertionError,'OTHER_CSS_APPEND_REFUSED'):self.check()

if __name__=='__main__':unittest.main()
