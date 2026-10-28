"""Local source/SQL contract checks; never labeled actual Native qualification."""
from pathlib import Path
import re,unittest
from pglast import parse_sql
from . import native_delta as delta
ROOT=Path(__file__).resolve().parents[1]

def originals():
    texts='\n'.join((ROOT/f).read_text()for f in ('cp6_bd_objects_invoice.sql','cp6_bd_objects_claimcredit.sql','cp6_bd_objects_router.sql'))
    return {sig:re.search(r'CREATE OR REPLACE FUNCTION '+re.escape(sig.split('(')[0])+r'\(.*?\$function\$;',texts,re.S).group()for sig in delta.SIGNATURES}

class Contracts(unittest.TestCase):
    def test_exact_seven_derivations_parse(self):
        result=delta.patched(originals())
        self.assertEqual(set(result),set(delta.SIGNATURES))
        for sql in result.values():parse_sql(sql)
    def test_schema_sql_parses(self):parse_sql((ROOT/'cp7_vendor_receivable/receivable.sql').read_text())
    def test_changed_post_payload_anchor_refused(self):
        old=originals();old[delta.POST]=old[delta.POST].replace("'post invoice'","'changed post invoice'")
        with self.assertRaisesRegex(ValueError,'post-payload'):delta.patched(old)
    def test_missing_function_refused(self):
        old=originals();del old[delta.APPLIED]
        with self.assertRaisesRegex(ValueError,'NATIVE_SET'):delta.patched(old)
    def test_qualified_unknown_wash_router_remains(self):
        old=originals()
        old[delta.ROUTER]=old[delta.ROUTER].replace("'REVERSE_VENDOR_SETTLEMENT') then","'REVERSE_VENDOR_SETTLEMENT','SET_FAILED_WASH_PRICE') then")
        new=delta.patched(old)
        self.assertIn("'REVERSE_VENDOR_REFUND','SET_FAILED_WASH_PRICE') then",new[delta.ROUTER])
    def test_old_payable_refusal_and_permission_recheck_retained(self):
        new=delta.patched(originals())
        self.assertIn('BD_CORRECTION_EXCEEDS_PAYABLE',new[delta.POST])
        self.assertIn('vendor_receivable_account_id',new[delta.POST])
        body=new[delta.ROUTER]
        self.assertLess(body.index("perform erp.require_permission('finance.hpp.manage')"),body.index('return v_prior.response'))
        self.assertIn("v_prior.payload<>p_payload",body)

if __name__=='__main__':unittest.main()
