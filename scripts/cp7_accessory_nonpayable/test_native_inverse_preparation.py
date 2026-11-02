"""New refusal/oracle preparation controls; synthetic records, zero ERP credit."""
import builtins,copy,unittest
from contextlib import ExitStack
from datetime import date
from unittest.mock import patch
from . import admission,native_inverse_cases as inverse

def records():
    economics=dict(snapshots=[dict(basis={'frozen':'identity'},actual_fixed_identity={'id':'snapshot'})],
        entitlements=[],booked=dict(WIP='0.03',CONTRACTOR_PAYABLE='0',ACCESSORY_REIMBURSE_VARIANCE='-0.03'),
        physical_material_movements=[{'id':'issue','qty_signed':-3}],accessory_stock='997')
    header=dict(id='journal',source_type='ACCESSORY_HPP_RECOST',source_id='revision',status='POSTED',
        transaction_date='2026-11-01',economic_date='2026-11-01',posting_at='2026-11-01T08:00:00Z',reversal_of_id=None)
    lines=[dict(id='line1',account_id='WIP',po_id='PO',product_id='SKU',contractor_id='MANDOR',debit='0.03',credit='0'),
        dict(id='line2',account_id='VARIANCE',po_id='PO',product_id='SKU',contractor_id='MANDOR',debit='0',credit='0.03')]
    before=dict(lot={'lot_origin':'PRODUCTION'},net_FG='3',economics=economics,
        journals=[dict(header=header,lines=lines)],movements=[dict(id='fg',qty_signed=3)])
    after=copy.deepcopy(before);after['lot']['lot_origin']='VOIDED_PRODUCTION';after['net_FG']='0'
    after['economics']['booked']={k:'0'for k in economics['booked']}
    after['journals'][0]['header']['status']='REVERSED'
    reversed_lines=[dict(line,id='inverse-'+line['id'],debit=line['credit'],credit=line['debit'])for line in lines]
    after['journals'].append(dict(header=dict(header,id='reversal',reversal_of_id='journal'),lines=reversed_lines))
    after['movements'].append(dict(id='fg-inverse',qty_signed=-3,reversal_of_id='fg'))
    return before,after

class NativeInversePreparationControls(unittest.TestCase):
    def test_lawful_reversal_and_later_historical_cost_revision_preserve_zero_money(self):
        before,after=records();inverse.require_inverse(before,after)
        later=copy.deepcopy(after)
        later['economics']['snapshots'][0]['snapshot']={'total_hpp_cost':'0.06'}
        inverse.require_voided_stays_voided(before,after,later)

    def test_wrong_sign_duplicate_reversal_changed_original_or_revived_cost_refuse(self):
        for mode in('wrong_sign','wrong_party','duplicate','original_line','original_date','basis','revived','stock'):
            before,after=records()
            if mode=='wrong_sign':after['journals'][1]['lines']=copy.deepcopy(before['journals'][0]['lines'])
            elif mode=='wrong_party':after['journals'][1]['lines'][0]['contractor_id']='WRONG_MANDOR'
            elif mode=='duplicate':after['journals'].append(copy.deepcopy(after['journals'][1]))
            elif mode=='original_line':after['journals'][0]['lines'][0]['debit']='0.04'
            elif mode=='original_date':after['journals'][0]['header']['economic_date']='2026-11-02'
            elif mode=='basis':after['economics']['snapshots'][0]['basis']={'frozen':'different'}
            elif mode=='revived':after['journals'].append(copy.deepcopy(before['journals'][0]))
            else:after['economics']['physical_material_movements'][0]['qty_signed']=-6
            with self.subTest(mode=mode),self.assertRaises(ValueError):inverse.require_inverse(before,after)

    def test_inverse_case_factory_refuses_before_domain_import_or_cursor(self):
        original=builtins.__import__
        def guarded(name,*args,**kwargs):
            if name.startswith(('cp6_','cp7_p21_','cp7_invoice_','cp7_qc_')):
                raise AssertionError('DOMAIN_IMPORT_BEFORE_ACTUAL_PARENT')
            return original(name,*args,**kwargs)
        with ExitStack()as scope:
            for name in('PARENT_HEAD','PARENT_TREE','PARENT_RUN','PARENT_JOB','PARENT_RECEIPT'):
                scope.enter_context(patch.object(admission,name,None))
            scope.enter_context(patch.object(builtins,'__import__',guarded))
            with self.assertRaisesRegex(ValueError,'ACTUAL_FREE3_ROOT_INTAKE_PENDING'):
                inverse.cases(object(),date(2026,11,1),{})

if __name__=='__main__':unittest.main()
