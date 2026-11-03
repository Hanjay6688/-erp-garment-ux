"""Rebind the unchanged callback review to exact current money source facts.

The retained reviewer is loaded in a private namespace. Its parser, source
derivation, overlap refusals and callback walk stay unchanged. The sole new
input is the pinned source review; this never represents an installed parent.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
PRIOR=ROOT/'scripts/current-global-sku-input-preparation/callback_preflight.py'
PRIOR_PIN=dict(bytes=638122,sha256='1021b85e354e7d7505a7113a6e5697c6a4bcbe0662a002727c0932a129fe56dc')


def retained():
    spec=importlib.util.spec_from_file_location('global_money_private_callback_review',PRIOR)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.PINS=dict(module.PINS,prior=(PRIOR_PIN['bytes'],PRIOR_PIN['sha256']))
    return module


def review(actual_path,prior_path,parser_sources,parser_runtime):
    return retained().review(actual_path,prior_path,parser_sources,parser_runtime)


def requirements():
    original=retained();require=original.require
    report=json.loads((HERE/'CALLBACK_SOURCE_REVIEW.json').read_bytes())
    reviewed=json.loads((HERE/'INPUT_REVIEW_CONTROLS.json').read_bytes())
    require(report['status']=='PREPARED_COMPOSITE_CALLBACK_REVIEW_NOT_FINAL_INPUT_PROFILE'
        and report['complete_input_review']is False and report['actual_final_parent_adopted']is False
        and report['focused_callback_source_has_no_unresolved']is True,
        'GLOBAL_MONEY_CALLBACK_SOURCE_NOT_ACCEPTANCE')
    require(report['installation_SQL']=={n:original.pin(t.encode())
        for n,t in original.current_source_expectations().items()},
        'GLOBAL_MONEY_CURRENT_CALLBACK_INSTALLATION_SOURCE_CHANGED')
    require(report['prior_source_review']==PRIOR_PIN==reviewed['full_source_review'],
        'GLOBAL_MONEY_CURRENT_CALLBACK_INPUT_CHANGED')
    require(reviewed['classification']=='PREPARED_SOURCE_REVIEW_NOT_ACTUAL_INPUT_PROFILE'
        and reviewed['selected_source_projection_has_no_unresolved']is True
        and reviewed['complete_input_review']is False and reviewed['actual_final_parent_adopted']is False,
        'GLOBAL_MONEY_CURRENT_SOURCE_REVIEW_NOT_ACCEPTANCE')
    names=report['required_relation_lower_bound']
    require(type(names)is list and all(type(n)is str for n in names)
        and names==sorted(set(names)) and len(names)==244
        and len(reviewed['physical_relation_candidates'])==232
        and len(report['new_physical_relation_candidates'])==12,
        'GLOBAL_MONEY_EXACT_PREPARED_RELATION_LOWER_BOUND')
    require(set(names)==set(reviewed['physical_relation_candidates'])|set(report['new_physical_relation_candidates']),
        'GLOBAL_MONEY_COMPLETE_CURRENT_SOURCE_AND_CALLBACK_INPUTS_REQUIRED')
    require(len(report['additional_firing_triggers'])==4
        and len(report['additional_parent_side_foreign_keys'])==2
        and len(report['new_callback_sources'])==6
        and report['direct_Native_function_overlap_with_prior_review']==[],
        'GLOBAL_MONEY_EXACT_CALLBACK_AND_NATIVE_OVERLAP_REVIEW')
    return report


def require_input_relations(profile):
    report=requirements();names=profile.get('relations')if type(profile)is dict else None
    require=retained().require
    require(type(names)is list and all(type(n)is str for n in names)and names==sorted(set(names)),
        'GLOBAL_MONEY_DISTINCT_SORTED_INPUT_RELATIONS_REQUIRED')
    missing=set(report['required_relation_lower_bound'])-set(names)
    require(not missing,'GLOBAL_MONEY_INPUT_RELATIONS_MISSING:'+','.join(sorted(missing)))
    return dict(required_relation_lower_bound=244,complete_input_review=False,actual_final_parent_adopted=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('actual','prior','parser-sources','parser-runtime','report'):
        parser.add_argument('--'+name,required=True,type=Path)
    args=parser.parse_args()
    result=review(args.actual,args.prior,args.parser_sources,args.parser_runtime)
    with args.report.open('x')as out:json.dump(result,out,indent=2);out.write('\n')
    print(json.dumps({k:result[k]for k in ('status','new_physical_relation_candidates','focused_callback_source_has_no_unresolved')}))
