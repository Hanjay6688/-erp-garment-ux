"""Static source-format stand-ins only. Actual install captures verified D1.

No Native execution or live-source/authority claim is made by this test.
"""
from pathlib import Path
import json,re,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cp7_credit_correction_de import e_native_delta as e,local_delta_check as local
C=local.CREDIT

def captures(dump):
    mapping={}
    for sig,file,name in (
      (e.COMMAND,'../cp7-src/sales/correction.sql','cp7_note.command'),
      (e.SNAPSHOT,'reconciliation/03_source_requests.sql','cp7_credit.source_native_snapshot_v1'),
      (e.PUBLIC_COMMAND,'../cp7-src/sales/correction.sql','public.erp_cp7_correct_note_v1'),
      (e.PUBLIC_WORKSPACE,'../cp7-src/sales/correction-actors.sql','public.erp_cp7_get_note_correction_v2'),
      (e.CORE,'readers/01_current_reader_capability.proposal.sql','erp._cp7_current_credit_adjustment'),
      (e.OBJECTS,'readers/02_materialized_profile.proposal.sql','cp7_credit.current_materialized_objects'),
      (e.EVENTS,'coordinator/01_coordinator_facts.sql','cp7_credit.initial_base_events_v1'),
      (e.ORDINAL,'coordinator/05_factual_profile.sql','cp7_credit.initial_ordinal_input_v1'),
      (e.FUNDING,'consumer/05_event_data.sql','cp7_credit.consumer_incoming_funding_v1'),
      (e.INCOMING,'../cp7_credit_incoming/incoming.sql','cp7_credit_incoming.incoming_applied_v1'),
      (e.SELECTION,'consumer/07_locked_projection.sql','cp7_credit.consumer_selection_v1'),
      (e.CAPTURE,'consumer/07_locked_projection.sql','cp7_credit.consumer_capture_sources_v1'),
      (e.PROJECTION,'consumer/07_locked_projection.sql','cp7_credit.consumer_projection_v1'),
      (e.EXECUTE,'consumer/08_owning_command.sql','cp7_credit.consumer_execute_v1'),
      (e.CLOSURE,'consumer/09_deferred_closure.sql','cp7_credit.assert_consumer_closed_v1'),
      (e.INVARIANT,'consumer/07_locked_projection.sql','cp7_credit.consumer_native_invariant_v1'),
      (e.INVOICE,'consumer/08_owning_command.sql','cp7_credit.consumer_invoice_profile_v1'),
      (e.CONSUMER,'consumer/05_event_data.sql','cp7_credit.consumer_event_data_v1'),
      (e.QUOTE,'consumer/08_owning_command.sql','cp7_credit.consumer_quote_v1')):
        mapping[sig]=local.statement(C/file,name)
    mapping[e.SOURCE_ENTER]=local.statement(C/'native-empty/04_exact_overlays.sql','cp7_credit.native_source_enter')
    text=(C/'consumer/composition.py').read_text()
    found=re.findall(r'result\[identity\]="""(create or replace function cp7_credit.assert_current_source_plan_profile\(.*?\$consumer_roots\$;)"""',text,re.S)
    assert len(found)==1
    mapping[e.PROFILE]=re.sub('^create or replace function','CREATE OR REPLACE FUNCTION',found[0])
    admission=local.load('e_native_admission',C/'admission/03_native_admission_transform.py')
    original=local.statement(dump,'erp.reverse_sale');body=local.body(original)
    changed=re.sub(r'\bbegin\b','begin\n perform cp7_note.require_context();',body,count=1,flags=re.I)
    for name in('reverse_fg_movement','reverse_journal','_cp3_r4_reverse_journal_internal'):changed=changed.replace('erp.'+name+'(','cp7_note.'+name+'(')
    changed=changed.replace("((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date","((h.sale_date AT TIME ZONE 'Asia/Jakarta'::text))::date")
    mapping[e.REVERSE]=original.replace(body,admission.reverse_sale(changed),1).replace('FUNCTION erp.reverse_sale(','FUNCTION cp7_note.reverse_sale(',1)
    return mapping

def main(dump):
    original=captures(dump);derived=e.derive(original);refused=[]
    for sig in e.CAPTURES:
        changed=dict(original);changed[sig]=original[sig]+original[sig]
        try:e.derive(changed)
        except ValueError:refused.append(sig)
        else:raise AssertionError('E1_DUPLICATE_PREDECESSOR_ACCEPTED:'+sig)
    return dict(status='PASS',scope='STATIC_SOURCE_FORMAT_STANDINS_ONLY',derivations=len(derived),duplicate_predecessor_refused=len(refused),Native_execution=False,installed_parent_verified=False)
if __name__=='__main__':print(json.dumps(main(sys.argv[1]),indent=2))
