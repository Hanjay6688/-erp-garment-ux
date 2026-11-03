"""Two reversible hash-only routes over exact retained lock/review sources.

This module is inert. It does not open the final-parent gate, execute SQL or
replace either original source/model. Raw observed OIDs remain in graph output.
"""
from pathlib import Path
from hashlib import sha256
import importlib.util,json

HERE=Path(__file__).resolve().parent
LOCK_BEFORE="""authority_hash_:=encode(extensions.digest(convert_to((authority_-array[
  'session_user','current_user','runtime_entry','required_final_parent',
  'actual_Native_qualification_credit','production_go'])::text,'UTF8'),'sha256'),'hex');"""
LOCK_AFTER="""authority_hash_:=encode(extensions.digest(convert_to(
  cp7_global_nonpo_envelope.semantic_authority_v1(authority_)::text,'UTF8'),'sha256'),'hex');"""
REVIEW_BEFORE="""hash_:=encode(sha256(convert_to((authority_-array['session_user','current_user',
  'runtime_entry','required_final_parent','actual_Native_qualification_credit','production_go'])::text,'UTF8')),'hex');"""
REVIEW_AFTER="""hash_:=encode(sha256(convert_to(
  cp7_global_nonpo_envelope.semantic_authority_v1(authority_)::text,'UTF8')),'hex');"""
REVIEW_PIN=dict(bytes=2956,sha256='875e1924412175f962ca7610d18d7375537e85ac381ed4870dbba0a073ee5ff6')


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def derive():
    spec=importlib.util.spec_from_file_location('exact_global_catalogue_bridge',HERE/'catalog_bridge.py')
    bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)
    locked,bridge_proof=bridge.derive()
    raw=(HERE/'review.sql').read_bytes()
    if pin(raw)!=REVIEW_PIN:raise ValueError('GLOBAL_SEMANTIC_EXACT_ORIGINAL_REVIEW_REQUIRED')
    review=raw.decode();result={};routes={}
    for name,original,before,after in(('lock',locked,LOCK_BEFORE,LOCK_AFTER),
        ('review',review,REVIEW_BEFORE,REVIEW_AFTER)):
        if original.count(before)!=1 or after in original:
            raise ValueError('GLOBAL_SEMANTIC_EXACT_ONE_HASH_SITE_REQUIRED:'+name)
        derived=original.replace(before,after,1)
        if derived.replace(after,before,1)!=original:
            raise ValueError('GLOBAL_SEMANTIC_COMPLETE_ORIGINAL_NOT_RECOVERED:'+name)
        result[name]=derived
        routes[name]=dict(before=before,after=after,count=1,original=pin(original.encode()),derived=pin(derived.encode()))
    return result,dict(status='PORTABLE_AUTHORITY_TWO_HASH_SOURCE_ROUTES_NOT_FINAL_PARENT_OR_RUNTIME',
        source_routes=2,routes=routes,original_review=REVIEW_PIN,
        semantic_helper=pin((HERE/'semantic_authority.sql').read_bytes()),
        observed_OID_paths_removed_from_semantic_hash_only=['functions[].oid','new_private_functions[].oid','view.oid'],
        previous_six_session_or_admission_fields_excluded_unchanged=True,
        all_other_authority_fields_and_array_order_preserved=True,
        raw_graph_authority_and_observed_OIDs_unchanged=True,
        full_current_catalogue_profile_route_retained=bridge_proof['full_current_catalogue_checked_before_post_fence_source_graph_reads'],
        old_lock_review_graph_and_models_bytes_unchanged=True,
        original_full_sources_recovered=True,actual_SQL_executed=0,actual_Native_cases=0,
        parent_gate_opened=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':print(json.dumps(derive()[1],indent=2)+'\n')
