"""Exercise actual preuse removal and partial-install recovery boundaries."""
import unittest
from restore_roles import restore_roles

class Cursor:
    def __init__(self,roles):self.roles=set(roles);self.calls=[];self.error=None;self.after_drop=None
    def execute(self,query):
        text=query.as_string();self.calls.append(text)
        if self.error:raise self.error
        role=text.split('"')[1];self.roles.remove(role)
        if self.after_drop:self.roles.add(self.after_drop)

class RestoreRolesTest(unittest.TestCase):
    before={'postgres','authenticated'}
    new={'cp7_alert','cp7_capture'}
    def restore(self,cur):return restore_roles(cur,self.before,self.new,lambda c:c.roles)
    def test_preuse_already_removed_all_no_duplicate_drop(self):
        cur=Cursor(self.before);r=self.restore(cur)
        self.assertEqual(cur.calls,[]);self.assertEqual(r['already_removed_by_preuse'],sorted(self.new))
    def test_partial_install_drops_only_remaining_created_roles(self):
        cur=Cursor(self.before|{'cp7_capture'});r=self.restore(cur)
        self.assertEqual(cur.calls,['drop role "cp7_capture"']);self.assertEqual(cur.roles,self.before)
        self.assertEqual(r['already_removed_by_preuse'],['cp7_alert'])
    def test_missing_baseline_role_refused_before_any_drop(self):
        cur=Cursor({'postgres'}|self.new)
        with self.assertRaisesRegex(AssertionError,'BASELINE_ROLE_MISSING'):self.restore(cur)
        self.assertEqual(cur.calls,[])
    def test_unexpected_role_refused_before_any_drop(self):
        cur=Cursor(self.before|self.new|{'unrelated'})
        with self.assertRaisesRegex(AssertionError,'UNEXPECTED_ROLE'):self.restore(cur)
        self.assertEqual(cur.calls,[])
    def test_drop_error_is_not_swallowed(self):
        cur=Cursor(self.before|self.new);error=RuntimeError('dependent object');cur.error=error
        with self.assertRaises(RuntimeError)as caught:self.restore(cur)
        self.assertIs(caught.exception,error);self.assertEqual(len(cur.calls),1)
    def test_final_role_drift_refused(self):
        cur=Cursor(self.before|{'cp7_capture'});cur.after_drop='unrelated'
        with self.assertRaisesRegex(AssertionError,'ROLE_SET_NOT_EXACTLY_RESTORED'):self.restore(cur)
    def test_baseline_role_never_treated_as_created(self):
        cur=Cursor(self.before)
        with self.assertRaisesRegex(AssertionError,'ROLE_BASELINE_AND_CREATED_OVERLAP'):
            restore_roles(cur,self.before,{'authenticated'},lambda c:c.roles)
        self.assertEqual(cur.calls,[])

if __name__=='__main__':unittest.main()
