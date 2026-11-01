"""Pure census/history and closed-parent controls, not actual HTTP/race proof."""
from datetime import date
import copy,unittest
from . import access_cases as cases,admission

def census():
    return dict(catalog={str(n):{}for n in range(22)},
        data_and_all_sequences={'erp.journal_lines':[2,'money'],'erp.app_users':[1,'actor'],
            'sequence:erp.audit_logs_id_seq':['10',True],
            'cp7_accessory_nonpayable.category_versions_v1':[1,'history'],
            'cp7_accessory_nonpayable.date_requests_v1':[1,'requests']},
        date_versions=[dict(id='v1',day='2026-11-01')],date_requests=[dict(request_id='r1',intent='old')])

class AccessPreparationControls(unittest.TestCase):
    def test_factories_remain_closed_before_any_connection_or_domain_import(self):
        for factory in(cases.http_cases,cases.races):
            with self.subTest(factory=factory.__name__),self.assertRaisesRegex(ValueError,'ACTUAL_FREE3_ROOT_INTAKE_PENDING'):
                factory(object(),date(2026,11,1),state={})
        for name in('PARENT_HEAD','PARENT_TREE','PARENT_RUN','PARENT_JOB','PARENT_RECEIPT'):
            self.assertIsNone(getattr(admission,name))

    def test_full_census_refuses_unrelated_money_sequence_key_or_catalog_change(self):
        for mode in('money','sequence','extra_key','catalog','private_history'):
            before=census();after=copy.deepcopy(before)
            if mode=='money':after['data_and_all_sequences']['erp.journal_lines']=[2,'wrong']
            elif mode=='sequence':after['data_and_all_sequences']['sequence:erp.audit_logs_id_seq']=['11',True]
            elif mode=='extra_key':after['data_and_all_sequences']['erp.hidden']=[1,'unproven']
            elif mode=='catalog':after['catalog']['0']={'new':'grant'}
            else:after['date_requests'][0]['intent']='changed'
            with self.subTest(mode=mode),self.assertRaises(ValueError):cases.require_changes(before,after)
        before=census();self.assertEqual(cases.require_changes(before,copy.deepcopy(before)),[])
        after=copy.deepcopy(before);after['data_and_all_sequences']['cp7_accessory_nonpayable.date_requests_v1']=[2,'new']
        self.assertEqual(cases.require_changes(before,after,{'cp7_accessory_nonpayable.date_requests_v1'}),
            ['cp7_accessory_nonpayable.date_requests_v1'])

    def test_append_only_oracle_refuses_erased_changed_duplicate_or_extra_history(self):
        before=census();after=copy.deepcopy(before);after['date_versions'].append(dict(id='v2',day='2026-11-02'))
        cases.require_append(before,after,'date_versions','id',['v2'])
        for mode in('erased','changed','duplicate','extra'):
            bad=copy.deepcopy(after)
            if mode=='erased':bad['date_versions'].pop(0)
            elif mode=='changed':bad['date_versions'][0]['day']='2026-11-03'
            elif mode=='duplicate':bad['date_versions'].append(copy.deepcopy(bad['date_versions'][1]))
            else:bad['date_versions'].append(dict(id='v3',day='2026-11-04'))
            with self.subTest(mode=mode),self.assertRaises(ValueError):cases.require_append(before,bad,'date_versions','id',['v2'])

    def test_command_retains_exact_reviewed_actor_source_epoch_and_explicit_date(self):
        workspace=dict(actor='owner',access_epoch='epoch',current_source=dict(id='event',version='35'),timeline_token='timeline')
        body=cases.payload(workspace,date(2026,11,2),'Reviewed physical GOOD policy date')
        self.assertEqual(body,dict(contract_version='cp7.good-policy-date-command.v1',actor='owner',access_epoch='epoch',
            effective_from='2026-11-02',source_event_id='event',expected_current_version='35',
            expected_timeline='timeline',reason='Reviewed physical GOOD policy date',reviewed=True))

if __name__=='__main__':unittest.main()
