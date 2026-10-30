"""Source/workflow/output controls on labelled doubles; no database access."""
from copy import deepcopy
from pathlib import Path
from unittest import TestCase,main
from unittest.mock import patch
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import yaml

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PARENT=ROOT/'scripts/current-attendance-choice-reader-native14-qualification'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


class Source(TestCase):
    def test_pure_gate_rejects_old_captures_partial_credit_or_runtime_edits(self):
        gate=load('s03_lawful_test_pure_gate',HERE/'gate.py');cfg=json.loads((HERE/'CONFIG.json').read_bytes())
        self.assertEqual(gate.selected(cfg),cfg)
        for key,value in [('expected_captures',13),('fresh_groups',[14]),('failed9ac_partial8PASS_is_prerequisite',True),
            ('runtime_files_changed',True),('Native_executed',True),('actual_Native_cases',8)]:
            bad=deepcopy(cfg);bad[key]=value
            with self.assertRaisesRegex(ValueError,'CLOSED_SOURCE15'):gate.selected(bad)

    def test_five_outer_and_four_inner_scope_bindings_reverse_full_frozen_checkers_exact(self):
        helper=load('s03_lawful_test_four_source_bindings',HERE/'derive.py')
        raw=(PARENT/'source_check.py').read_bytes();value,proof=helper.substitute(raw,helper.SOURCE_PAIRS)
        self.assertEqual(proof['counted_changes'],5)
        for before,after in reversed(helper.SOURCE_PAIRS):value=value.replace(after,before,1)
        self.assertEqual(value.encode(),raw)
        self.assertIn("if not untracked <= allowed_untracked:",value)
        parent=load('s03_lawful_test_inner_history_deriver',PARENT/'derive.py')
        inner=(ROOT/'scripts/current-attendance-period-choice-native11-qualification/source_check.py').read_bytes()
        metadata,_=parent.source_checker(inner)
        derived,scope=helper.substitute(metadata.encode(),helper.INNER_SOURCE_PAIRS)
        self.assertEqual(scope['counted_changes'],4)
        for before,after in reversed(helper.INNER_SOURCE_PAIRS):derived=derived.replace(after,before,1)
        self.assertEqual(derived,metadata)

    def test_workflow_only_bounded_metadata_and_six_routing_steps_change(self):
        flow=load('s03_lawful_test_wf',HERE/'workflow.py')
        before=yaml.safe_load((ROOT/flow.OLD).read_bytes());after=yaml.safe_load((ROOT/flow.NEW).read_bytes())
        self.assertEqual(flow.derive(before),after)
        self.assertEqual(len(before['jobs']['p21']['steps']),len(after['jobs']['p21']['steps']))
        self.assertEqual(before['permissions'],after['permissions'])
        self.assertEqual(before['jobs']['p21']['env'],after['jobs']['p21']['env'])
        for old,new in zip(before['jobs']['p21']['steps'],after['jobs']['p21']['steps']):
            if 'run'in old and flow.PARENT_NS in old['run']:
                self.assertEqual(new,dict(old,run=old['run'].replace(flow.PARENT_NS,flow.NS)))
            elif old.get('uses','').startswith('actions/upload-artifact@'):
                self.assertEqual({k:v for k,v in new.items()if k!='with'},{k:v for k,v in old.items()if k!='with'})
                self.assertEqual({k:v for k,v in new['with'].items()if k!='name'},{k:v for k,v in old['with'].items()if k!='name'})
            else:self.assertEqual(new,old)
            if 'run'in new:
                r=subprocess.run(['bash','-n'],input=new['run'],capture_output=True,text=True)
                self.assertEqual(r.returncode,0,(new.get('name'),r.stderr))

    def test_generated_producer_contract_rebinds_only_new_WF_and_name(self):
        flow=load('s03_lawful_test_generated_context',HERE/'workflow.py')
        from hashlib import sha256
        for name in ('GENERATED_RECEIPTS.json','LATER_GENERATED_RECEIPTS.json'):
            old=json.loads((PARENT/name).read_bytes());new=json.loads((HERE/name).read_bytes())
            pins=dict(old['producer_files']);pins.pop(flow.OLD)
            raw=(ROOT/flow.NEW).read_bytes();pins[flow.NEW]=dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
            self.assertEqual(new['producer_files'],pins)
            for key in old:
                if key not in ('producer_files','package_workflow_name','S03_contract_derivation'):self.assertEqual(new[key],old[key])
            if name.startswith('LATER'):self.assertEqual(new['package_workflow_name'],flow.NAME)

    def test_actual_first_failure_and_source15_transform_provenance_exact(self):
        negative=load('s03_lawful_test_actual_negative',HERE/'negative.py').check()
        self.assertEqual(negative['strict11_counts'],{'PASS':8,'INCOMPLETE':3})
        self.assertEqual(negative['complete_bundle_credit'],0)
        self.assertFalse(negative['Reader3_reached']);self.assertFalse(negative['all5_pass'])

    def test_CI_cannot_reseal_and_unknown_cli_flags_reject_before_source(self):
        with patch.dict(os.environ,{'CI':'true'}):
            with self.assertRaisesRegex(ValueError,'REGENERATION_IN_CI_FORBIDDEN'):
                load('s03_lawful_test_no_CI_reseal',HERE/'seal.py').seal()
        for name in ('check.py','probe.py'):
            flags=['--offline','--unknown-flag']if name=='check.py'else['--unknown-flag']
            r=subprocess.run([sys.executable,'-B',str(HERE/name),*flags],capture_output=True,text=True)
            self.assertNotEqual(r.returncode,0);self.assertIn('unrecognized arguments',r.stderr)


class Result(TestCase):
    def values(self):
        old=load('s03_lawful_labelled_old_result_doubles',PARENT/'test_result_gate.py')
        values=list(deepcopy(old.doubles()))
        own=json.loads((HERE/'CONFIG.json').read_bytes())
        component=values[0]['committed'][old.gate.CASE]
        component['lawful_fixture_successor_derivation']=dict(business=dict(adapted_callback_ids=own['adapted_callback_ids'],
            original_eight_callbacks_unchanged=True,original_helpers_and_committed_witness_unchanged=True,
            original_eleven_runtime_callbacks_byte_exact=False))
        component['lawful_fixture_successor']=dict(
            P2_known_worker=[dict(known_worker='LOCAL_WORKER_DOUBLE',exact_eligible_worker_ids=['LOCAL_WORKER_DOUBLE'],
                unknown_cells_synthesized=False,P1_facts_before={'LOCAL':'DOUBLE'},P1_facts_after={'LOCAL':'DOUBLE'})for _ in range(2)],
            OWNER_REOPEN=[dict(administrative_control_reset_used=False,closed_REVERSE_full_census_negative=True)],
            Native_finished_valuation=[dict(proof=dict(old_full_row_predicate=False))],
            Native_finished_cancel=[dict(full_FG_rows_exact=True,current_HPP_money_and_GL_exact=True,linked_inverse_signs_dimensions_both_dates_exact=True,
                frozen_post_allocation_history_retained=True,full_original_pool_lines_immutable=True,all_intermediate_HPP_versions_and_components_retained=True)])
        values[3]['run_identity']['workflow']='CP7 A S03 lawful fixture successor Native11 then Reader3'
        return values

    def test_complete_structural_double_requires_old_full14_and_lawful_provenance(self):
        gate=load('s03_lawful_test_full_gate',HERE/'result_gate.py')
        r=gate.checked(*self.values());self.assertEqual(r['actual_Native_cases'],14)
        self.assertEqual(r['adapted_callbacks'],3);self.assertFalse(r['original_eleven_runtime_callbacks_byte_exact'])

    def test_missing_actual_helper_provenance_or_false_byte_exact_claim_refuses(self):
        gate=load('s03_lawful_test_full_gate_negative',HERE/'result_gate.py')
        changes=(lambda c:c['lawful_fixture_successor'].pop('P2_known_worker'),
            lambda c:c['lawful_fixture_successor']['OWNER_REOPEN'][0].update(administrative_control_reset_used=True),
            lambda c:c['lawful_fixture_successor']['Native_finished_cancel'][0].update(full_FG_rows_exact=False),
            lambda c:c['lawful_fixture_successor_derivation']['business'].update(original_eleven_runtime_callbacks_byte_exact=True))
        for mutate in changes:
            values=self.values();mutate(values[0]['committed'][gate.CASE])
            with self.assertRaisesRegex(ValueError,'S03_LAWFUL_'):gate.checked(*values)

    def test_old_partial8_or_missing_writer_gate_cannot_gain_credit(self):
        gate=load('s03_lawful_test_partial_refusal',HERE/'result_gate.py')
        values=self.values();values[1]['counts']={'PASS':8,'INCOMPLETE':3}
        with self.assertRaisesRegex(ValueError,'COMPLETE_STRICT_GROUP'):gate.checked(*values)
        values=self.values();values[3]['gate']['writer_runtime']=False
        with self.assertRaisesRegex(ValueError,'ALL5_PACKAGE_GATES'):gate.checked(*values)

    def test_final_gate_uses_actual_current_head_and_refuses_a_matching_foreign_bundle(self):
        gate=load('s03_lawful_test_actual_head_binding',HERE/'result_gate.py')
        with self.assertRaisesRegex(ValueError,'SAME_CURRENT_OUTER_PACKAGE_RUN_SOURCE'):
            gate.checked(*self.values(),expected_head='c'*40)
        source=(HERE/'result_gate.py').read_text()
        self.assertIn("expected_head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD']",source)


if __name__=='__main__':main(verbosity=2)
