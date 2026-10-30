"""Old full14/full5 gate plus exact lawful-fixture successor provenance."""
from pathlib import Path
import importlib.util
import json
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PARENT=ROOT/'scripts/current-attendance-choice-reader-native14-qualification'
OLD_NAME='CP7 A S03 attendance choice plus owning readers Native14'
NEW_NAME='CP7 A S03 lawful fixture successor Native11 then Reader3'
LABEL='CP7_S03_ATTENDANCE_CHOICE_NATIVE14'
CASE='S03_ATTENDANCE_NATIVE14_AND_USED_INVERSE'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def checked(report,original11,reader3,package,files,drill,cfg,expected_head=None):
    helper=load('s03_lawful_result_workflow_context_only',HERE/'derive.py')
    parent,proof=helper.module('s03_lawful_unchanged_full_outer14_result_gate',PARENT/'result_gate.py',[(OLD_NAME,NEW_NAME)])
    value=parent.checked(report,original11,reader3,package,files,drill,cfg,expected_head)
    own=json.loads((HERE/'CONFIG.json').read_bytes())
    component=report['committed'][CASE]
    derivation=component.get('lawful_fixture_successor_derivation',{}).get('business',{})
    if (derivation.get('adapted_callback_ids')!=own['adapted_callback_ids']
            or derivation.get('original_eight_callbacks_unchanged')is not True
            or derivation.get('original_helpers_and_committed_witness_unchanged')is not True
            or derivation.get('original_eleven_runtime_callbacks_byte_exact')is not False):
        raise ValueError('S03_LAWFUL_EXACT_PRIVATE_THREE_CALLBACK_PROVENANCE_REQUIRED')
    data=component.get('lawful_fixture_successor',{})
    workers=data.get('P2_known_worker',[])
    if len(workers)!=2 or any(r.get('exact_eligible_worker_ids')!=[r.get('known_worker')]
            or r.get('unknown_cells_synthesized')is not False
            or r.get('P1_facts_before')!=r.get('P1_facts_after')for r in workers):
        raise ValueError('S03_LAWFUL_ACTUAL11_AND_READER3_KNOWN_WORKER_RAW_REQUIRED')
    reopen=data.get('OWNER_REOPEN',[])
    if len(reopen)!=1 or reopen[0].get('administrative_control_reset_used')is not False or reopen[0].get('closed_REVERSE_full_census_negative')is not True:
        raise ValueError('S03_LAWFUL_ACTUAL_OWNER_REOPEN_AND_CLOSED_NEGATIVE_REQUIRED')
    valuation=data.get('Native_finished_valuation',[]);cancel=data.get('Native_finished_cancel',[])
    if (len(valuation)!=1 or valuation[0].get('proof',{}).get('old_full_row_predicate')is not False
            or len(cancel)!=1 or cancel[0].get('full_FG_rows_exact')is not True
            or cancel[0].get('current_HPP_money_and_GL_exact')is not True
            or cancel[0].get('linked_inverse_signs_dimensions_both_dates_exact')is not True
            or cancel[0].get('frozen_post_allocation_history_retained')is not True
            or cancel[0].get('full_original_pool_lines_immutable')is not True
            or cancel[0].get('all_intermediate_HPP_versions_and_components_retained')is not True):
        raise ValueError('S03_LAWFUL_ACTUAL_NATIVE_CACHE_AND_FULL_CANCEL_RAW_REQUIRED')
    return dict(value,lawful_fixture_provenance_required=True,old_gate_workflow_context_derivation=proof,
        original_eleven_runtime_callbacks_byte_exact=False,adapted_callbacks=3,original_eight_callbacks_exact=True)


def main():
    out=ROOT/'cp6-proof/t3'
    read=lambda name:json.loads((out/name).read_bytes())
    try:
        result=checked(read(LABEL+'.json'),read('CP7_S03_ATTENDANCE_CHOICE_NATIVE11_CASES.json'),
            read('CP7_S03_ATTENDANCE_CHOICE_READER_NATIVE3_CASES.json'),read('T3_PACKAGE_INSTALL.json'),
            read('T3_PACKAGE_FILES_INSTALL.json'),read('T3_BACKUP_RESTORE_DRILL.json'),
            json.loads((PARENT/'CONFIG.json').read_bytes()),
            expected_head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip())
    except Exception as error:
        result=dict(status='INCOMPLETE',error=str(error),actual_Native_cases=0,production_go=False)
        (out/'S03_NATIVE14_FINAL_GATE.json').write_text(json.dumps(result,indent=2)+'\n')
        raise
    (out/'S03_NATIVE14_FINAL_GATE.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
